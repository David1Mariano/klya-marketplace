from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from catalog.models import Product
from sellers.models import Store

User = get_user_model()


class Order(models.Model):
    """Pedido principal do comprador.

    Representa a compra como um todo, independente do numero de vendedores
    envolvidos. Os valores sao registrados no servidor e preservam o
    histórico da compra (não mudam se o vendedor editar o produto depois).
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Aguardando pagamento")
        PAID = "paid", _("Pago (simulação)")
        CANCELLED = "cancelled", _("Cancelado")
        FAILED = "failed", _("Falha na simulação")

    buyer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    idempotency_key = models.CharField(
        max_length=255, unique=True, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"

    def __str__(self):
        return f"Pedido {self.pk} - {self.buyer.username}"

    def seller_orders_total(self):
        total = sum(
            (so.subtotal for so in self.seller_orders.all()),
            self._meta.get_field("total").default,
        )
        return total


class SellerOrder(models.Model):
    """Pedido referente a um único vendedor dentro de um pedido principal."""

    class Status(models.TextChoices):
        PENDING = "pending", _("Aguardando pagamento")
        PAID = "paid", _("Pago (simulação)")
        CANCELLED = "cancelled", _("Cancelado")
        FAILED = "failed", _("Falha na simulação")

    order = models.ForeignKey(
        Order, on_delete=models.PROTECT, related_name="seller_orders"
    )
    store = models.ForeignKey(
        Store, on_delete=models.PROTECT, related_name="seller_orders"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Pedido do vendedor"
        verbose_name_plural = "Pedidos do vendedor"
        unique_together = ("order", "store")

    def __str__(self):
        return f"Pedido vendedor {self.pk} - {self.store.name}"


class OrderItem(models.Model):
    """Item de um pedido de vendedor, com preço e nome registrados na compra."""

    seller_order = models.ForeignKey(
        SellerOrder, on_delete=models.PROTECT, related_name="items"
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="order_items"
    )
    product_name = models.CharField(max_length=255)
    product_sku = models.CharField(max_length=255, blank=True)
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    quantity = models.PositiveIntegerField(default=1)
    subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )

    class Meta:
        verbose_name = "Item do pedido"
        verbose_name_plural = "Itens do pedido"

    def __str__(self):
        return f"{self.quantity}x {self.product_name}"

    def save(self, *args, **kwargs):
        if not self.product_name:
            self.product_name = self.product.name
        if not self.product_sku:
            self.product_sku = self.product.slug
        self.subtotal = self.unit_price * self.quantity
        super().save(*args, **kwargs)
