from django.core.validators import MinValueValidator
from django.db import models

from orders.models import SellerOrder


class CommissionConfig(models.Model):
    """Configuracao do percentual de comissao da plataforma KLYA.

    Mantida como registro unico para evitar hardcode espalhado pelas views.
    O percentual e provisorio (apenas desenvolvimento) enquanto nao houver
    uma política comercial definida.
    """

    name = models.CharField(max_length=100, default="padrao")
    rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0.05,
        validators=[MinValueValidator(0)],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.is_active:
            CommissionConfig.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active_rate(cls):
        config = cls.objects.filter(is_active=True).order_by("-updated_at").first()
        return config.rate if config else None

    class Meta:
        verbose_name = "Configuracao de comissao"
        verbose_name_plural = "Configuracoes de comissao"

    def __str__(self):
        return f"{self.name} - {self.rate * 100}%"


class Commission(models.Model):
    """Comissao da KLYA registrada no momento da compra, por pedido de vendedor.

    A taxa aplicada e copiada da configuracao vigente para preservar o
    histórico, mesmo que o percentual mude depois.
    """

    seller_order = models.OneToOneField(
        SellerOrder, on_delete=models.PROTECT, related_name="commission"
    )
    rate = models.DecimalField(
        max_digits=5, decimal_places=4, validators=[MinValueValidator(0)]
    )
    gross_amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    commission_amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    net_amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Comissao"
        verbose_name_plural = "Comissoes"

    def __str__(self):
        return f"Comissao {self.seller_order_id} - R$ {self.commission_amount}"
