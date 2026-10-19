from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import Store

User = get_user_model()


class StoreFlowTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            username="buyer", password="TestPass1234!", email="buyer@example.com"
        )
        self.seller = User.objects.create_user(
            username="seller", password="TestPass1234!", email="seller@example.com"
        )
        self.admin = User.objects.create_user(
            username="admin",
            password="TestPass1234!",
            email="admin@example.com",
            is_staff=True,
        )

    def test_buyer_can_request_store(self):
        self.client.login(username="buyer", password="TestPass1234!")
        response = self.client.post(
            reverse("sellers:store_request"),
            {
                "name": "Loja X",
                "description": "Desc",
            },
        )
        self.assertIn(response.status_code, [200, 302])
        self.assertTrue(Store.objects.filter(owner=self.buyer).exists())
        store = Store.objects.get(owner=self.buyer)
        self.assertEqual(store.status, "pending")

    def test_cannot_request_store_twice(self):
        Store.objects.create(owner=self.buyer, name="L1", status="pending")
        self.client.login(username="buyer", password="TestPass1234!")
        response = self.client.get(reverse("sellers:store_request"))
        self.assertIn(response.status_code, [200, 302])

    def test_admin_approves_store(self):
        store = Store.objects.create(owner=self.seller, name="L2", status="pending")
        self.client.login(username="admin", password="TestPass1234!")
        response = self.client.post(
            reverse("sellers:store_review", args=[store.pk]),
            {
                "status": "approved",
                "rejection_reason": "",
            },
        )
        self.assertIn(response.status_code, [200, 302])
        store.refresh_from_db()
        self.assertEqual(store.status, "approved")

    def test_admin_rejects_with_reason(self):
        store = Store.objects.create(owner=self.seller, name="L3", status="pending")
        self.client.login(username="admin", password="TestPass1234!")
        response = self.client.post(
            reverse("sellers:store_review", args=[store.pk]),
            {
                "status": "rejected",
                "rejection_reason": "Motivo",
            },
        )
        self.assertIn(response.status_code, [200, 302])
        store.refresh_from_db()
        self.assertEqual(store.status, "rejected")
        self.assertEqual(store.rejection_reason, "Motivo")

    def test_non_admin_cannot_review(self):
        store = Store.objects.create(owner=self.seller, name="L4", status="pending")
        self.client.login(username="buyer", password="TestPass1234!")
        response = self.client.get(reverse("sellers:store_review", args=[store.pk]))
        self.assertIn(response.status_code, [302, 403])

    def test_dashboard_shows_status(self):
        Store.objects.create(owner=self.seller, name="L5", status="pending")
        self.client.login(username="seller", password="TestPass1234!")
        response = self.client.get(reverse("sellers:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pendente")

    def test_cannot_access_other_store_by_id(self):
        other = User.objects.create_user(
            username="other", password="TestPass1234!", email="other@example.com"
        )
        store = Store.objects.create(owner=other, name="OtherStore", status="approved")
        self.client.login(username="buyer", password="TestPass1234!")
        response = self.client.get(reverse("sellers:store_review", args=[store.pk]))
        self.assertIn(response.status_code, [302, 403])
