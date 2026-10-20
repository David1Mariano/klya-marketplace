from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth import get_user_model
from django.test import TestCase

from commissions.models import Commission, CommissionConfig
from orders.models import Order, SellerOrder
from sellers.models import Store

User = get_user_model()


def money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class CommissionConfigTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            username="seller", password="TestPass1234!"
        )
        self.store = Store.objects.create(
            owner=self.seller, name="Loja A", status="approved"
        )
        self.buyer = User.objects.create_user(
            username="buyer", password="TestPass1234!"
        )
        self.order = Order.objects.create(buyer=self.buyer)
        self.seller_order = SellerOrder.objects.create(
            order=self.order, store=self.store, subtotal=Decimal("100.00")
        )

    def test_default_rate_is_provisional(self):
        CommissionConfig.objects.create(
            name="padrao", rate=Decimal("0.05"), is_active=True
        )
        self.assertEqual(CommissionConfig.get_active_rate(), Decimal("0.05"))

    def test_only_one_active_config(self):
        CommissionConfig.objects.create(name="a", rate=Decimal("0.05"), is_active=True)
        config2 = CommissionConfig.objects.create(
            name="b", rate=Decimal("0.10"), is_active=True
        )
        config2.refresh_from_db()
        first = CommissionConfig.objects.filter(is_active=True).first()
        self.assertEqual(first.pk, config2.pk)
        self.assertEqual(CommissionConfig.get_active_rate(), Decimal("0.10"))

    def test_get_active_rate_none_when_no_config(self):
        CommissionConfig.objects.all().delete()
        self.assertIsNone(CommissionConfig.get_active_rate())

    def test_commission_calculation_and_records(self):
        rate = CommissionConfig.get_active_rate() or Decimal("0.05")
        gross = self.seller_order.subtotal
        commission = money(gross * rate)
        net = money(gross - commission)
        Commission.objects.create(
            seller_order=self.seller_order,
            rate=rate,
            gross_amount=gross,
            commission_amount=commission,
            net_amount=net,
        )
        self.seller_order.refresh_from_db()
        commission_record = self.seller_order.commission
        self.assertEqual(commission_record.rate, rate)
        self.assertEqual(commission_record.gross_amount, gross)
        self.assertEqual(commission_record.commission_amount, commission)
        self.assertEqual(commission_record.net_amount, net)
        self.assertEqual(commission + net, gross)

    def test_commission_rate_preserved_at_purchase_time(self):
        config = CommissionConfig.objects.create(
            name="padrao", rate=Decimal("0.05"), is_active=True
        )
        commission = Commission.objects.create(
            seller_order=self.seller_order,
            rate=config.rate,
            gross_amount=self.seller_order.subtotal,
            commission_amount=Decimal("5.00"),
            net_amount=Decimal("95.00"),
        )
        # Mudar a configuracao depois nao altera a comissao registrada.
        config.rate = Decimal("0.20")
        config.save()
        commission.refresh_from_db()
        self.assertEqual(commission.rate, Decimal("0.05"))

    def test_seller_cannot_see_other_store_commission(self):
        other = User.objects.create_user(username="other", password="TestPass1234!")
        other_store = Store.objects.create(
            owner=other, name="Loja B", status="approved"
        )
        other_order = Order.objects.create(buyer=self.buyer)
        other_so = SellerOrder.objects.create(
            order=other_order, store=other_store, subtotal=Decimal("50.00")
        )
        Commission.objects.create(
            seller_order=self.seller_order,
            rate=Decimal("0.05"),
            gross_amount=Decimal("100.00"),
            commission_amount=Decimal("5.00"),
            net_amount=Decimal("95.00"),
        )
        Commission.objects.create(
            seller_order=other_so,
            rate=Decimal("0.05"),
            gross_amount=Decimal("50.00"),
            commission_amount=Decimal("2.50"),
            net_amount=Decimal("47.50"),
        )
        self.assertEqual(
            Commission.objects.filter(seller_order__store=self.store).count(), 1
        )
        self.assertEqual(
            Commission.objects.filter(seller_order__store=other_store).count(), 1
        )
        with self.assertRaises(Commission.DoesNotExist):
            Commission.objects.filter(seller_order__store=self.store).get(
                pk=other_so.commission.pk
            )

    def test_totals_consistency_across_sellers(self):
        rate = Decimal("0.05")
        order_multi = Order.objects.create(buyer=self.buyer)
        so_a = SellerOrder.objects.create(
            order=order_multi, store=self.store, subtotal=Decimal("100.00")
        )
        other = User.objects.create_user(username="other2", password="TestPass1234!")
        other_store = Store.objects.create(
            owner=other, name="Loja C", status="approved"
        )
        so_b = SellerOrder.objects.create(
            order=order_multi, store=other_store, subtotal=Decimal("200.00")
        )
        gross_total = so_a.subtotal + so_b.subtotal
        commission_total = money(gross_total * rate)
        net_total = money(gross_total - commission_total)
        self.assertEqual(gross_total, Decimal("300.00"))
        self.assertEqual(commission_total, Decimal("15.00"))
        self.assertEqual(net_total, Decimal("285.00"))
        self.assertEqual(commission_total + net_total, gross_total)
        self.assertEqual(
            Commission.objects.filter(seller_order__order=order_multi).count(), 0
        )
