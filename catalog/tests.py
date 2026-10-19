from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Product
from sellers.models import Store

User = get_user_model()


class CatalogPublicTests(TestCase):
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
        self.admin = User.objects.create_user(
            username="admin", password="TestPass1234!", is_staff=True
        )

        self.store = Store.objects.create(
            owner=self.seller, name="Loja1", status="approved"
        )
        self.pending_store = Store.objects.create(
            owner=self.other, name="LojaPend", status="pending"
        )

        self.cat = Category.objects.create(name="Eletrônicos", slug="eletronicos")

        self.published = Product.objects.create(
            store=self.store,
            category=self.cat,
            name="Celular",
            slug="celular",
            price=100.00,
            stock=5,
            status=Product.Status.PUBLISHED,
        )
        self.draft = Product.objects.create(
            store=self.store,
            category=self.cat,
            name="Tablet",
            slug="tablet",
            price=200.00,
            stock=3,
            status=Product.Status.DRAFT,
        )
        self.pending_store_product = Product.objects.create(
            store=self.pending_store,
            category=self.cat,
            name="Item",
            slug="item",
            price=50.00,
            stock=1,
            status=Product.Status.PUBLISHED,
        )

    def test_catalog_shows_only_published_approved(self):
        response = self.client.get(reverse("catalog:product_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Celular")
        self.assertNotContains(response, "Tablet")
        self.assertNotContains(response, "Item")

    def test_product_detail_published(self):
        response = self.client.get(
            reverse(
                "catalog:product_detail",
                kwargs={"slug": self.published.slug, "pk": self.published.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Celular")

    def test_product_detail_draft_not_public(self):
        response = self.client.get(
            reverse(
                "catalog:product_detail",
                kwargs={"slug": self.draft.slug, "pk": self.draft.pk},
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_product_detail_pending_store_not_public(self):
        response = self.client.get(
            reverse(
                "catalog:product_detail",
                kwargs={
                    "slug": self.pending_store_product.slug,
                    "pk": self.pending_store_product.pk,
                },
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_product_detail_not_found(self):
        response = self.client.get(
            reverse("catalog:product_detail", kwargs={"slug": "nao-existe", "pk": 9999})
        )
        self.assertEqual(response.status_code, 404)

    def test_product_list_search(self):
        response = self.client.get(reverse("catalog:product_list") + "?q=Cel")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Celular")

    def test_product_list_filter_by_category(self):
        cat2 = Category.objects.create(name="Livros", slug="livros")
        Product.objects.create(
            store=self.store,
            category=cat2,
            name="Livro",
            slug="livro",
            price=10.00,
            stock=1,
            status=Product.Status.PUBLISHED,
        )
        response = self.client.get(
            reverse("catalog:product_list") + f"?category={self.cat.id}"
        )
        self.assertContains(response, "Celular")
        content = response.content.decode("utf-8")
        self.assertNotIn(">Livro<", content)
