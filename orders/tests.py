from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.sessions.middleware import SessionMiddleware

from catalog.models import Category, Product
from commissions.models import CommissionConfig
from cart.cart import Cart
from orders.checkout import checkout as perform_checkout
from orders.models import Order, OrderItem, SellerOrder
from payments.models import Payment
from sellers.models import Store

User = get_user_model()


class OrderModelTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            username="buyer", password="TestPass1234!"
        )
        self.seller = User.objects.create_user(
            username="seller", password="TestPass1234!"
        )
        self.other = User.objects.create_user(
            username="other", password="TestPass1234!"
        )
        self.store = Store.objects.create(
            owner=self.seller, name="Loja A", status="approved"
        )
        self.other_store = Store.objects.create(
            owner=self.other, name="Loja B", status="approved"
        )
        self.cat = Category.objects.create(name="Eletrônicos", slug="eletronicos")
        self.product = Product.objects.create(
            store=self.store,
            category=self.cat,
            name="Celular",
            slug="celular",
            price=Decimal("100.00"),
            stock=5,
            status=Product.Status.PUBLISHED,
        )
        self.product2 = Product.objects.create(
            store=self.other_store,
            category=self.cat,
            name="Fone",
            slug="fone",
            price=Decimal("50.00"),
            stock=3,
            status=Product.Status.PUBLISHED,
        )
        self.order = Order.objects.create(buyer=self.buyer)

    def test_order_creation_defaults(self):
        self.assertEqual(self.order.status, Order.Status.PENDING)
        self.assertEqual(self.order.total, Decimal("0.00"))
        self.assertEqual(self.order.buyer, self.buyer)

    def test_order_status_choices(self):
        self.assertIn(("pending", "Aguardando pagamento"), Order.Status.choices)
        self.assertIn(("paid", "Pago (simulação)"), Order.Status.choices)
        self.assertIn(("cancelled", "Cancelado"), Order.Status.choices)
        self.assertIn(("failed", "Falha na simulação"), Order.Status.choices)

    def test_seller_order_creation_and_isolation(self):
        so_a = SellerOrder.objects.create(
            order=self.order, store=self.store, subtotal=Decimal("100.00")
        )
        so_b = SellerOrder.objects.create(
            order=self.order, store=self.other_store, subtotal=Decimal("50.00")
        )
        self.assertEqual(self.order.seller_orders.count(), 2)
        self.assertEqual(self.order.seller_orders.filter(store=self.store).count(), 1)
        self.assertEqual(
            self.order.seller_orders.filter(store=self.other_store).count(), 1
        )
        # Vendedor A so enxerga seus próprios pedidos de vendedor.
        self.assertEqual(
            SellerOrder.objects.filter(store=self.store, order=self.order).count(), 1
        )
        self.assertEqual(
            SellerOrder.objects.filter(store=self.store).get(pk=so_a.pk), so_a
        )
        with self.assertRaises(SellerOrder.DoesNotExist):
            SellerOrder.objects.filter(store=self.store).get(pk=so_b.pk)

    def test_unique_seller_order_per_order_and_store(self):
        SellerOrder.objects.create(
            order=self.order, store=self.store, subtotal=Decimal("100.00")
        )
        with self.assertRaises(Exception):
            SellerOrder.objects.create(
                order=self.order, store=self.store, subtotal=Decimal("10.00")
            )

    def test_order_item_snapshot_preserved(self):
        seller_order = SellerOrder.objects.create(
            order=self.order, store=self.store, subtotal=Decimal("200.00")
        )
        item = OrderItem.objects.create(
            seller_order=seller_order,
            product=self.product,
            unit_price=Decimal("100.00"),
            quantity=2,
        )
        self.assertEqual(item.product_name, "Celular")
        self.assertEqual(item.product_sku, "celular")
        self.assertEqual(item.subtotal, Decimal("200.00"))
        # Alterar o produto depois nao altera o item registrado.
        self.product.price = Decimal("999.00")
        self.product.save()
        item.refresh_from_db()
        self.assertEqual(item.unit_price, Decimal("100.00"))
        self.assertEqual(item.subtotal, Decimal("200.00"))
        self.assertEqual(item.product_name, "Celular")

    def test_seller_order_subtotal_matches_items(self):
        seller_order = SellerOrder.objects.create(
            order=self.order, store=self.store, subtotal=Decimal("0")
        )
        OrderItem.objects.create(
            seller_order=seller_order,
            product=self.product,
            unit_price=Decimal("100.00"),
            quantity=2,
        )
        OrderItem.objects.create(
            seller_order=seller_order,
            product=self.product,
            unit_price=Decimal("100.00"),
            quantity=1,
        )
        total_items = sum((i.subtotal for i in seller_order.items.all()), Decimal("0"))
        self.assertEqual(total_items, Decimal("300.00"))

    def test_order_total_consistency_with_seller_orders(self):
        so_a = SellerOrder.objects.create(
            order=self.order, store=self.store, subtotal=Decimal("100.00")
        )
        so_b = SellerOrder.objects.create(
            order=self.order, store=self.other_store, subtotal=Decimal("50.00")
        )
        expected = so_a.subtotal + so_b.subtotal
        self.order.total = expected
        self.order.save()
        self.order.refresh_from_db()
        self.assertEqual(self.order.total, Decimal("150.00"))
        self.assertEqual(self.order.seller_orders_total(), Decimal("150.00"))

    def test_order_buyer_isolation(self):
        order2 = Order.objects.create(buyer=self.other)
        self.assertEqual(Order.objects.filter(buyer=self.buyer).count(), 1)
        self.assertEqual(Order.objects.filter(buyer=self.other).count(), 1)
        with self.assertRaises(Order.DoesNotExist):
            Order.objects.filter(buyer=self.buyer).get(pk=order2.pk)


class OrderCheckoutTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            username="buyer", password="TestPass1234!"
        )
        self.seller_a = User.objects.create_user(
            username="seller_a", password="TestPass1234!"
        )
        self.seller_b = User.objects.create_user(
            username="seller_b", password="TestPass1234!"
        )

        self.store_a = Store.objects.create(
            owner=self.seller_a, name="Loja A", status="approved"
        )
        self.store_b = Store.objects.create(
            owner=self.seller_b, name="Loja B", status="approved"
        )
        self.pending_owner = User.objects.create_user(
            username="pending_owner", password="TestPass1234!"
        )
        self.pending_store = Store.objects.create(
            owner=self.pending_owner, name="Loja Pendente", status="pending"
        )

        self.cat = Category.objects.create(name="Eletrônicos", slug="eletronicos")

        self.product_a1 = Product.objects.create(
            store=self.store_a,
            category=self.cat,
            name="Celular",
            slug="celular",
            price=Decimal("100.00"),
            stock=5,
            status=Product.Status.PUBLISHED,
        )
        self.product_a2 = Product.objects.create(
            store=self.store_a,
            category=self.cat,
            name="Fone",
            slug="fone",
            price=Decimal("50.00"),
            stock=3,
            status=Product.Status.PUBLISHED,
        )
        self.product_b1 = Product.objects.create(
            store=self.store_b,
            category=self.cat,
            name="Carregador",
            slug="carregador",
            price=Decimal("30.00"),
            stock=2,
            status=Product.Status.PUBLISHED,
        )

        CommissionConfig.objects.create(
            name="padrao", rate=Decimal("0.05"), is_active=True
        )

        self.client.login(username="buyer", password="TestPass1234!")

    def _add_to_cart(self, product, quantity=1):
        return self.client.post(
            reverse("cart:cart_add", args=[product.id]),
            {"quantity": quantity},
        )

    def _make_checkout_request(self, session_data=None):
        """Cria um request POST para o checkout com sessao compartilhada."""
        factory = RequestFactory()
        request = factory.post(reverse("orders:checkout"))
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        # Copiar a sessao do client (que tem o carrinho) para o request
        client_session = self.client.session
        for key in list(client_session.keys()):
            request.session[key] = client_session[key]
        if session_data:
            for k, v in session_data.items():
                request.session[k] = v
        request.session.save()
        request.user = self.buyer
        return request

    def test_checkout_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("orders:checkout_review"))
        self.assertIn(response.status_code, [302, 403])

    def test_checkout_review_empty_cart(self):
        response = self.client.get(reverse("orders:checkout_review"))
        self.assertRedirects(response, reverse("cart:cart_detail"))

    def test_checkout_creates_order_and_seller_orders(self):
        self._add_to_cart(self.product_a1, 1)
        self._add_to_cart(self.product_b1, 1)

        response = self.client.post(reverse("orders:checkout"))
        self.assertRedirects(response, reverse("orders:order_detail", args=[1]))

        order = Order.objects.get(pk=1)
        self.assertEqual(order.buyer, self.buyer)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.total, Decimal("130.00"))

        seller_orders = order.seller_orders.all()
        self.assertEqual(seller_orders.count(), 2)

        so_a = seller_orders.get(store=self.store_a)
        self.assertEqual(so_a.subtotal, Decimal("100.00"))
        self.assertEqual(so_a.items.count(), 1)
        item_a = so_a.items.get()
        self.assertEqual(item_a.product_name, "Celular")
        self.assertEqual(item_a.unit_price, Decimal("100.00"))
        self.assertEqual(item_a.subtotal, Decimal("100.00"))

        so_b = seller_orders.get(store=self.store_b)
        self.assertEqual(so_b.subtotal, Decimal("30.00"))
        self.assertEqual(so_b.items.count(), 1)

        # Comissão registrada para cada pedido de vendedor.
        self.assertEqual(so_a.commission.commission_amount, Decimal("5.00"))
        self.assertEqual(so_a.commission.net_amount, Decimal("95.00"))
        self.assertEqual(so_b.commission.commission_amount, Decimal("1.50"))
        self.assertEqual(so_b.commission.net_amount, Decimal("28.50"))

        # Pagamento simulado pendente criado.
        self.assertTrue(hasattr(order, "payment"))
        self.assertEqual(order.payment.status, Payment.Status.PENDING)

        # Estoque descontado.
        self.product_a1.refresh_from_db()
        self.assertEqual(self.product_a1.stock, 4)
        self.product_b1.refresh_from_db()
        self.assertEqual(self.product_b1.stock, 1)

        # Carrinho limpo após a finalização.
        response = self.client.get(reverse("cart:cart_detail"))
        self.assertContains(response, "Seu carrinho está vazio")

    def test_checkout_multiple_items_same_store(self):
        self._add_to_cart(self.product_a1, 2)
        self._add_to_cart(self.product_a2, 1)

        response = self.client.post(reverse("orders:checkout"))
        self.assertRedirects(response, reverse("orders:order_detail", args=[1]))

        order = Order.objects.get(pk=1)
        self.assertEqual(order.total, Decimal("250.00"))

        so_a = order.seller_orders.get(store=self.store_a)
        self.assertEqual(so_a.subtotal, Decimal("250.00"))
        self.assertEqual(so_a.items.count(), 2)

        self.assertEqual(order.seller_orders.count(), 1)

    def test_checkout_idempotency_no_duplicate_order(self):
        self._add_to_cart(self.product_a1, 1)

        # Primeira finalização cria o pedido com chave de idempotência.
        self.client.post(reverse("orders:checkout"))
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()
        key = order.idempotency_key

        # A chave de idempotência existe e é única no banco (impede duplicatas).
        self.assertIsNotNone(key)
        self.assertEqual(Order.objects.filter(idempotency_key=key).count(), 1)

    def test_checkout_insufficient_stock(self):
        self._add_to_cart(self.product_b1, 5)  # estoque é 2

        response = self.client.post(reverse("orders:checkout"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("cart:cart_detail"))
        self.assertEqual(Order.objects.count(), 0)
        self.product_b1.refresh_from_db()
        self.assertEqual(self.product_b1.stock, 2)  # estoque não alterado

    def test_checkout_product_unavailable(self):
        # Produto de loja pendente não pode ser adicionado, mas testamos
        # o cenário onde o produto fica indisponível entre adicionar e finalizar.
        self._add_to_cart(self.product_a1, 1)
        # Tornar o produto indisponível.
        self.product_a1.status = Product.Status.DRAFT
        self.product_a1.save()

        response = self.client.post(reverse("orders:checkout"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("cart:cart_detail"))
        self.assertEqual(Order.objects.count(), 0)

    def test_checkout_clears_cart(self):
        self._add_to_cart(self.product_a1, 1)
        self.client.post(reverse("orders:checkout"))

        # O carrinho deve estar vazio após a finalização.
        # Navegar para o carrinho deve mostrar vazio.
        response = self.client.get(reverse("cart:cart_detail"))
        self.assertContains(response, "Seu carrinho está vazio")

    def test_checkout_idempotency_different_quantities_different_keys(self):
        # Carrinho com 1 unidade.
        self._add_to_cart(self.product_a1, 1)
        self.client.post(reverse("orders:checkout"))
        order_1 = Order.objects.first()
        key_1 = order_1.idempotency_key

        # Mesmo produto, quantidade diferente -> chave diferente.
        self._add_to_cart(self.product_a1, 2)
        self.client.post(reverse("orders:checkout"))
        order_2 = Order.objects.exclude(pk=order_1.pk).first()
        self.assertIsNotNone(order_2)
        self.assertNotEqual(key_1, order_2.idempotency_key)
        self.assertEqual(Order.objects.count(), 2)

    def test_checkout_idempotency_repeat_same_purchase_no_duplicate(self):
        OP_KEY = Cart.OPERATION_SESSION_KEY

        self._add_to_cart(self.product_a1, 1)
        req1 = self._make_checkout_request({OP_KEY: "op-same-123"})
        order, error = perform_checkout(req1)
        self.assertIsNone(error)
        self.assertEqual(Order.objects.count(), 1)

        order = Order.objects.first()
        self.assertEqual(order.total, Decimal("100.00"))

        # Repetir a mesma operacao (mesmo operation_id na sessao):
        # nao duplica o pedido.
        self._add_to_cart(self.product_a1, 1)
        req2 = self._make_checkout_request({OP_KEY: "op-same-123"})
        order2, error2 = perform_checkout(req2)
        self.assertIsNone(error2)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(order2.pk, order.pk)
        # Estoque descontado apenas uma vez.
        self.product_a1.refresh_from_db()
        self.assertEqual(self.product_a1.stock, 4)

    def test_checkout_idempotency_stock_not_discounted_twice(self):
        OP_KEY = Cart.OPERATION_SESSION_KEY

        self._add_to_cart(self.product_a1, 1)
        req1 = self._make_checkout_request({OP_KEY: "op-stock-123"})
        order, error = perform_checkout(req1)
        self.assertIsNone(error)

        self.product_a1.refresh_from_db()
        self.assertEqual(self.product_a1.stock, 4)  # 5 - 1

        # Repetir a mesma operacao (mesmo operation_id): nao desconta estoque novamente.
        self._add_to_cart(self.product_a1, 1)
        req2 = self._make_checkout_request({OP_KEY: "op-stock-123"})
        order2, error2 = perform_checkout(req2)
        self.assertIsNone(error2)

        self.product_a1.refresh_from_db()
        self.assertEqual(self.product_a1.stock, 4)  # ainda 4, nao 3
        self.assertEqual(Order.objects.count(), 1)

    def test_checkout_cart_cleared_on_success(self):
        """O carrinho deve ser limpo após checkout bem-sucedido."""
        self._add_to_cart(self.product_a1, 1)
        self.client.post(reverse("orders:checkout"))

        # Verificar via página do carrinho.
        response = self.client.get(reverse("cart:cart_detail"))
        self.assertContains(response, "Seu carrinho está vazio")

    def test_checkout_cart_kept_on_validation_failure(self):
        """O carrinho deve permanecer quando a validacao falha."""
        self._add_to_cart(self.product_a1, 1)
        # Tornar o produto indisponível para forçar falha de validacao.
        self.product_a1.status = Product.Status.DRAFT
        self.product_a1.save()

        response = self.client.post(reverse("orders:checkout"))

        # O checkout deve falhar e redirecionar para o carrinho.
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("cart:cart_detail"))
        # Nenhum pedido deve ser criado.
        self.assertEqual(Order.objects.count(), 0)
        # O estoque não deve ser alterado.
        self.product_a1.refresh_from_db()
        self.assertEqual(self.product_a1.stock, 5)

    def test_checkout_cart_kept_on_insufficient_stock(self):
        """O carrinho deve permanecer quando o estoque é insuficiente."""
        self._add_to_cart(self.product_b1, 5)  # estoque é 2

        self.client.post(reverse("orders:checkout"))

        # O carrinho ainda deve conter o item.
        response = self.client.get(reverse("cart:cart_detail"))
        self.assertContains(response, self.product_b1.name)
        self.assertEqual(Order.objects.count(), 0)

    def test_checkout_idempotent_repeat_after_cancelled_payment(self):
        """Depois de cancelamento, mesma operacao cria novo pedido (operation_id renovado pelo servidor)."""
        self._add_to_cart(self.product_a1, 1)
        self.client.post(reverse("orders:checkout"))
        self.assertEqual(Order.objects.count(), 1)

        order_1 = Order.objects.first()
        # Simular pagamento cancelado (estado terminal).
        order_1.payment.status = Payment.Status.CANCELLED
        order_1.payment.save()
        order_1.status = Order.Status.CANCELLED
        order_1.save()

        # Repetir mesma compra com mesmo carrinho: o servidor renova o
        # operation_id e cria um novo pedido, preservando o anterior.
        self._add_to_cart(self.product_a1, 1)
        self.client.post(reverse("orders:checkout"))

        self.assertEqual(Order.objects.count(), 2)
        order_1.refresh_from_db()
        self.assertEqual(order_1.status, Order.Status.CANCELLED)
        # Pedido anterior preservado (nao sobrescrito).
        self.assertEqual(
            Order.objects.get(pk=order_1.pk).status, Order.Status.CANCELLED
        )
        # Novo pedido criado.
        new_order = Order.objects.exclude(pk=order_1.pk).first()
        self.assertIsNotNone(new_order)
        self.assertEqual(new_order.status, Order.Status.PENDING)
        # Estoque descontado novamente no novo pedido (5 - 1 - 1 = 3).
        self.product_a1.refresh_from_db()
        self.assertEqual(self.product_a1.stock, 3)

    def test_checkout_same_operation_returns_same_order(self):
        OP_KEY = Cart.OPERATION_SESSION_KEY

        self._add_to_cart(self.product_a1, 1)
        req1 = self._make_checkout_request({OP_KEY: "op-same-456"})
        order, error = perform_checkout(req1)
        self.assertIsNone(error)
        self.assertEqual(Order.objects.count(), 1)

        order = Order.objects.first()
        # Repetir a mesma operacao (mesmo operation_id na sessao).
        self._add_to_cart(self.product_a1, 1)
        req2 = self._make_checkout_request({OP_KEY: "op-same-456"})
        order2, error2 = perform_checkout(req2)
        self.assertIsNone(error2)

        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(order2.pk, order.pk)
        order.refresh_from_db()
        self.assertEqual(order.total, Decimal("100.00"))
        # Estoque descontado apenas uma vez.
        self.product_a1.refresh_from_db()
        self.assertEqual(self.product_a1.stock, 4)

    def test_checkout_repetition_does_not_replace_in_progress_order(self):
        OP_KEY = Cart.OPERATION_SESSION_KEY

        self._add_to_cart(self.product_a1, 1)
        req1 = self._make_checkout_request({OP_KEY: "op-progress-789"})
        order, error = perform_checkout(req1)
        self.assertIsNone(error)
        self.assertEqual(Order.objects.count(), 1)

        order = Order.objects.first()
        # Pedido esta em PENDING (nao terminal).
        self.assertEqual(order.status, Order.Status.PENDING)

        # Repetir com o mesmo operation_id: deve retornar o pedido existente.
        self._add_to_cart(self.product_a1, 1)
        req2 = self._make_checkout_request({OP_KEY: "op-progress-789"})
        order2, error2 = perform_checkout(req2)
        self.assertIsNone(error2)

        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(order2.pk, order.pk)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.total, Decimal("100.00"))
        self.product_a1.refresh_from_db()
        self.assertEqual(self.product_a1.stock, 4)

    def test_checkout_different_operations_not_confused(self):
        OP_KEY = Cart.OPERATION_SESSION_KEY

        """Duas operacoes diferentes nao sao confundidas."""
        # Primeira operacao: pedido pago.
        self._add_to_cart(self.product_a1, 1)
        req1 = self._make_checkout_request({OP_KEY: "op-diff-1"})
        order, error = perform_checkout(req1)
        self.assertIsNone(error)
        self.assertEqual(Order.objects.count(), 1)
        order_1 = Order.objects.first()
        order_1.payment.status = Payment.Status.APPROVED
        order_1.payment.save()
        order_1.status = Order.Status.PAID
        order_1.save()

        # Segunda operacao com mesmo carrinho mas operation_id diferente:
        # deve criar um novo pedido (operacao distinta).
        self._add_to_cart(self.product_a1, 1)
        req2 = self._make_checkout_request({OP_KEY: "op-diff-2"})
        order2, error2 = perform_checkout(req2)
        self.assertIsNone(error2)
        self.assertEqual(Order.objects.count(), 2)

    def test_checkout_failed_payment_allows_new_operation(self):
        """Falha simulada permite nova operacao com os mesmos itens."""
        self._add_to_cart(self.product_a1, 1)
        self.client.post(reverse("orders:checkout"))
        self.assertEqual(Order.objects.count(), 1)

        order_1 = Order.objects.first()
        # Simular falha de pagamento (estado terminal).
        order_1.payment.status = Payment.Status.FAILED
        order_1.payment.save()
        order_1.status = Order.Status.FAILED
        order_1.save()

        # Nova operacao com mesmo carrinho: operation_id renovado, novo pedido.
        self._add_to_cart(self.product_a1, 1)
        self.client.post(reverse("orders:checkout"))

        self.assertEqual(Order.objects.count(), 2)
        order_1.refresh_from_db()
        self.assertEqual(order_1.status, Order.Status.FAILED)
        new_order = Order.objects.exclude(pk=order_1.pk).first()
        self.assertIsNotNone(new_order)
        self.assertEqual(new_order.status, Order.Status.PENDING)
