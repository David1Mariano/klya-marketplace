from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Product
from sellers.models import Store

User = get_user_model()


class SellerProductManagementTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            username="seller", password="TestPass1234!"
        )
        self.other = User.objects.create_user(
            username="other", password="TestPass1234!"
        )
        self.nostore = User.objects.create_user(
            username="nostore", password="TestPass1234!"
        )
        self.pending = User.objects.create_user(
            username="pending", password="TestPass1234!"
        )

        self.store = Store.objects.create(
            owner=self.seller, name="Loja1", status="approved"
        )
        self.store_other = Store.objects.create(
            owner=self.other, name="Loja2", status="approved"
        )
        self.store_pending = Store.objects.create(
            owner=self.pending, name="LojaP", status="pending"
        )

        self.cat = Category.objects.create(name="Eletrônicos", slug="eletronicos")

    def test_seller_without_store_cannot_create(self):
        self.client.login(username="nostore", password="TestPass1234!")
        response = self.client.get(reverse("catalog:product_create"))
        self.assertIn(response.status_code, [302, 403])

    def test_pending_store_seller_cannot_create(self):
        self.client.login(username="pending", password="TestPass1234!")
        response = self.client.get(reverse("catalog:product_create"))
        self.assertIn(response.status_code, [302, 403])

    def test_seller_can_create_product(self):
        self.client.login(username="seller", password="TestPass1234!")
        response = self.client.post(
            reverse("catalog:product_create"),
            {
                "category": self.cat.id,
                "name": "Produto X",
                "slug": "produto-x",
                "description": "desc",
                "price": "10.50",
                "stock": "3",
                "status": "draft",
                "is_active": True,
            },
        )
        self.assertIn(response.status_code, [200, 302])
        self.assertTrue(
            Product.objects.filter(name="Produto X", store=self.store).exists()
        )

    def test_seller_can_edit_own_product(self):
        p = Product.objects.create(
            store=self.store,
            category=self.cat,
            name="P1",
            slug="p1",
            price=5.00,
            stock=2,
            status="draft",
        )
        self.client.login(username="seller", password="TestPass1234!")
        response = self.client.post(
            reverse("catalog:product_edit", kwargs={"pk": p.pk}),
            {
                "category": self.cat.id,
                "name": "P1 Edit",
                "slug": "p1",
                "description": "",
                "price": "7.00",
                "stock": "4",
                "status": "published",
                "is_active": True,
            },
        )
        self.assertIn(response.status_code, [200, 302])
        p.refresh_from_db()
        self.assertEqual(p.name, "P1 Edit")
        self.assertEqual(float(p.price), 7.00)

    def test_seller_cannot_edit_other_product(self):
        p = Product.objects.create(
            store=self.store_other,
            category=self.cat,
            name="P2",
            slug="p2",
            price=5.00,
            stock=2,
            status="draft",
        )
        self.client.login(username="seller", password="TestPass1234!")
        response = self.client.get(reverse("catalog:product_edit", kwargs={"pk": p.pk}))
        self.assertEqual(response.status_code, 404)
        p.refresh_from_db()
        self.assertEqual(p.name, "P2")

    def test_form_validates_price_stock_required(self):
        self.client.login(username="seller", password="TestPass1234!")
        response = self.client.post(
            reverse("catalog:product_create"),
            {
                "category": self.cat.id,
                "name": "Bad",
                "slug": "bad",
                "price": "0",
                "stock": "-1",
                "status": "draft",
                "is_active": True,
            },
        )
        self.assertEqual(response.status_code, 200)
