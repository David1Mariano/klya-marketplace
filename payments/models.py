from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from orders.models import Order


class Payment(models.Model):
    """Pagamento simulado. Nenhum dado real de cartao é coletado ou armazenado."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Aguardando pagamento")
        APPROVED = "approved", _("Aprovado (simulação)")
        CANCELLED = "cancelled", _("Cancelado")
        FAILED = "failed", _("Falha na simulação")

    order = models.OneToOneField(
        Order, on_delete=models.PROTECT, related_name="payment"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    method = models.CharField(max_length=50, default="simulado")
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pagamento"
        verbose_name_plural = "Pagamentos"

    def __str__(self):
        return f"Pagamento {self.order_id} - {self.status}"
