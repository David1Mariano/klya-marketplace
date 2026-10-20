from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Product
from sellers.models import Store

User = get_user_model()


class CartTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            username="buyer", password="TestPass1234!"
        )
        self.seller = User.objects.create_user(
            username="seller", password="TestPass1234!"
        )
        self.other_seller = User.objects.create_user(
            username="other_seller", password="TestPass1234!"
        )

        self.store = Store.objects.create(
            owner=self.seller, name="Loja A", status="approved"
        )
        self.pending_store = Store.objects.create(
            owner=self.other_seller, name="Loja Pendente", status="pending"
        )

        self.cat = Category.objects.create(name="Eletrônicos", slug="eletronicos")

        self.product = Product.objects.create(
            store=self.store,
            category=self.cat,
            name="Celular",
            slug="celular",
            price="100.00",
            stock=5,
            status=Product.Status.PUBLISHED,
            is_active=True,
        )
        self.product2 = Product.objects.create(
            store=self.store,
            category=self.cat,
            name="Fone",
            slug="fone",
            price="50.00",
            stock=3,
            status=Product.Status.PUBLISHED,
            is_active=True,
        )
        self.other_product = Product.objects.create(
            store=self.pending_store,
            category=self.cat,
            name="Item Pendente",
            slug="item-pendente",
            price="30.00",
            stock=2,
            status=Product.Status.PUBLISHED,
            is_active=True,
        )
        self.inactive_product = Product.objects.create(
            store=self.store,
            category=self.cat,
            name="Inativo",
            slug="inativo",
            price="10.00",
            stock=2,
            status=Product.Status.DRAFT,
            is_active=False,
        )

        self.client.login(username="buyer", password="TestPass1234!")

    def _add(self, product, quantity=1):
        return self.client.post(
            reverse("cart:cart_add", args=[product.id]),
            {"quantity": quantity},
        )

    def test_cart_detail_empty(self):
        response = self.client.get(reverse("cart:cart_detail"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Seu carrinho está vazio")

    def test_cart_detail_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("cart:cart_detail"))
        self.assertIn(response.status_code, [302, 403])

    def test_add_product_to_cart(self):
        response = self._add(self.product, 2)
        self.assertRedirects(response, self.product.get_absolute_url())
        response = self.client.get(reverse("cart:cart_detail"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Celular")
        self.assertContains(response, "R$ 100,00")
        self.assertContains(response, "R$ 200,00")

    def test_add_multiple_products_different_total(self):
        self._add(self.product, 1)
        self._add(self.product2, 2)
        response = self.client.get(reverse("cart:cart_detail"))
        self.assertContains(response, "Celular")
        self.assertContains(response, "Fone")
        self.assertContains(response, "R$ 200,00")

    def test_add_quantity_above_stock(self):
        response = self.client.post(
            reverse("cart:cart_add", args=[self.product.id]),
            {"quantity": 10},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Estoque insuficiente")
        response = self.client.get(reverse("cart:cart_detail"))
        self.assertContains(response, "Seu carrinho está vazio")

    def test_add_invalid_quantity(self):
        response = self._add(self.product, 0)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse("cart:cart_detail"))
        self.assertContains(response, "Seu carrinho está vazio")

    def test_add_negative_quantity(self):
        response = self.client.post(
            reverse("cart:cart_add", args=[self.product.id]),
            {"quantity": -2},
        )
        self.assertEqual(response.status_code, 302)

    def test_add_product_from_pending_store(self):
        response = self._add(self.other_product)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse("cart:cart_detail"))
        self.assertContains(response, "Seu carrinho está vazio")

    def test_add_inactive_or_draft_product(self):
        response = self._add(self.inactive_product)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse("cart:cart_detail"))
        self.assertContains(response, "Seu carrinho está vazio")

    def test_add_nonexistent_product(self):
        response = self.client.post(
            reverse("cart:cart_add", args=[99999]),
            {"quantity": 1},
        )
        self.assertEqual(response.status_code, 404)

    def test_update_quantity(self):
        self._add(self.product, 1)
        response = self.client.post(
            reverse("cart:cart_update", args=[self.product.id]),
            {"quantity": 3},
        )
        self.assertRedirects(response, reverse("cart:cart_detail"))
        response = self.client.get(reverse("cart:cart_detail"))
        self.assertContains(response, "R$ 300,00")

    def test_update_quantity_above_stock(self):
        self._add(self.product, 1)
        self.client.post(
            reverse("cart:cart_update", args=[self.product.id]),
            {"quantity": 10},
        )
        response = self.client.get(reverse("cart:cart_detail"))
        self.assertContains(response, "R$ 100,00")

    def test_remove_item(self):
        self._add(self.product, 1)
        self._add(self.product2, 1)
        response = self.client.post(reverse("cart:cart_remove", args=[self.product.id]))
        self.assertRedirects(response, reverse("cart:cart_detail"))
        response = self.client.get(reverse("cart:cart_detail"))
        self.assertNotContains(response, "Celular")
        self.assertContains(response, "Fone")

    def test_cart_add_requires_login(self):
        self.client.logout()
        response = self.client.post(
            reverse("cart:cart_add", args=[self.product.id]),
            {"quantity": 1},
        )
        self.assertIn(response.status_code, [302, 403])
