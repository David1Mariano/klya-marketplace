from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class AuthTests(TestCase):
    def test_signup_creates_user(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "alice",
                "email": "alice@example.com",
                "password1": "TestPass1234!",
                "password2": "TestPass1234!",
            },
        )
        self.assertIn(response.status_code, [200, 302])
        self.assertTrue(User.objects.filter(username="alice").exists())

    def test_login_logout(self):
        User.objects.create_user(
            username="bob", password="TestPass1234!", email="bob@example.com"
        )
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "bob",
                "password": "TestPass1234!",
            },
        )
        self.assertIn(response.status_code, [200, 302])
        self.assertTrue("_auth_user_id" in self.client.session)
        response = self.client.get(reverse("accounts:logout"))
        self.assertIn(response.status_code, [200, 302])
        self.assertFalse("_auth_user_id" in self.client.session)

    def test_profile_requires_login(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertIn(response.status_code, [302, 403])
