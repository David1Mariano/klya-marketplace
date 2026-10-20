from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from orders.models import Order, SellerOrder
from payments.models import Payment
from sellers.models import Store

User = get_user_model()


class PaymentModelTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            username="buyer", password="TestPass1234!"
        )
        self.seller = User.objects.create_user(
            username="seller", password="TestPass1234!"
        )
        self.store = Store.objects.create(
            owner=self.seller, name="Loja A", status="approved"
        )
        self.order = Order.objects.create(buyer=self.buyer)

    def test_payment_creation_defaults(self):
        payment = Payment.objects.create(
            order=self.order,
            amount=self.order.total,
        )
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertEqual(payment.method, "simulado")
        self.assertEqual(payment.order, self.order)

    def test_payment_status_choices(self):
        self.assertIn(("pending", "Aguardando pagamento"), Payment.Status.choices)
        self.assertIn(("approved", "Aprovado (simulação)"), Payment.Status.choices)
        self.assertIn(("cancelled", "Cancelado"), Payment.Status.choices)
        self.assertIn(("failed", "Falha na simulação"), Payment.Status.choices)

    def test_one_payment_per_order(self):
        Payment.objects.create(order=self.order, amount=Decimal("100.00"))
        with self.assertRaises(Exception):
            Payment.objects.create(order=self.order, amount=Decimal("100.00"))

    def test_payment_transitions_explicit(self):
        payment = Payment.objects.create(order=self.order, amount=Decimal("100.00"))
        payment.status = Payment.Status.APPROVED
        payment.save()
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.APPROVED)

        payment.status = Payment.Status.CANCELLED
        payment.save()
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.CANCELLED)

        payment.status = Payment.Status.FAILED
        payment.save()
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.FAILED)

    def test_payment_is_tied_to_its_order(self):
        other = User.objects.create_user(username="other", password="TestPass1234!")
        other_order = Order.objects.create(buyer=other)
        Payment.objects.create(order=self.order, amount=Decimal("100.00"))
        self.assertEqual(Payment.objects.filter(order=self.order).count(), 1)
        self.assertEqual(Payment.objects.filter(order=other_order).count(), 0)
        with self.assertRaises(Payment.DoesNotExist):
            Payment.objects.filter(order=self.order).get(pk=9999)


class PaymentSimulateTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            username="buyer", password="TestPass1234!"
        )
        self.other_buyer = User.objects.create_user(
            username="other_buyer", password="TestPass1234!"
        )
        self.seller = User.objects.create_user(
            username="seller", password="TestPass1234!"
        )
        self.store = Store.objects.create(
            owner=self.seller, name="Loja A", status="approved"
        )
        self.order = Order.objects.create(
            buyer=self.buyer, total=Decimal("100.00"), status=Order.Status.PENDING
        )
        self.payment = Payment.objects.create(
            order=self.order, amount=Decimal("100.00"), status=Payment.Status.PENDING
        )
        self.seller_order = SellerOrder.objects.create(
            order=self.order, store=self.store, subtotal=Decimal("100.00")
        )
        self.client.login(username="buyer", password="TestPass1234!")

    def test_simulate_payment_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("payments:simulate", args=[self.order.pk]))
        self.assertIn(response.status_code, [302, 403])

    def test_simulate_payment_approve(self):
        response = self.client.post(
            reverse("payments:simulate", args=[self.order.pk]),
            {"action": "approve"},
        )
        self.assertRedirects(
            response, reverse("orders:order_detail", args=[self.order.pk])
        )
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.APPROVED)
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.seller_order.refresh_from_db()
        self.assertEqual(self.seller_order.status, SellerOrder.Status.PAID)

    def test_simulate_payment_cancel(self):
        self.client.post(
            reverse("payments:simulate", args=[self.order.pk]),
            {"action": "cancel"},
        )
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.CANCELLED)
        self.assertEqual(self.order.status, Order.Status.CANCELLED)

    def test_simulate_payment_fail(self):
        self.client.post(
            reverse("payments:simulate", args=[self.order.pk]),
            {"action": "fail"},
        )
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.FAILED)
        self.assertEqual(self.order.status, Order.Status.FAILED)

    def test_simulate_payment_invalid_action(self):
        response = self.client.post(
            reverse("payments:simulate", args=[self.order.pk]),
            {"action": "invalid_action"},
        )
        self.assertEqual(response.status_code, 302)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PENDING)

    def test_simulate_payment_terminal_cannot_change(self):
        self.payment.status = Payment.Status.APPROVED
        self.payment.save()
        self.client.post(
            reverse("payments:simulate", args=[self.order.pk]),
            {"action": "cancel"},
        )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.APPROVED)

    def test_other_buyer_cannot_simulate_payment(self):
        self.client.login(username="other_buyer", password="TestPass1234!")
        response = self.client.post(
            reverse("payments:simulate", args=[self.order.pk]),
            {"action": "approve"},
        )
        self.assertEqual(response.status_code, 404)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PENDING)

    def test_no_payment_redirects_to_order_detail(self):
        order_no_payment = Order.objects.create(
            buyer=self.buyer, total=Decimal("50.00"), status=Order.Status.PENDING
        )
        response = self.client.get(
            reverse("payments:simulate", args=[order_no_payment.pk])
        )
        self.assertRedirects(
            response, reverse("orders:order_detail", args=[order_no_payment.pk])
        )
