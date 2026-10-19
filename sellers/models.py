from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()

STORE_STATUS_CHOICES = (
    ("pending", "Pendente"),
    ("approved", "Aprovada"),
    ("rejected", "Rejeitada"),
)


class Store(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name="store")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=STORE_STATUS_CHOICES, default="pending"
    )
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Loja"
        verbose_name_plural = "Lojas"

    def __str__(self):
        return self.name
