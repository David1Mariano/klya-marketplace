from django.contrib import admin

from .models import Order, OrderItem, SellerOrder


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class SellerOrderInline(admin.TabularInline):
    model = SellerOrder
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("pk", "buyer", "status", "total", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("buyer__username", "pk")
    inlines = (SellerOrderInline,)


@admin.register(SellerOrder)
class SellerOrderAdmin(admin.ModelAdmin):
    list_display = ("pk", "order", "store", "status", "subtotal", "created_at")
    list_filter = ("status", "store", "created_at")
    search_fields = ("store__name", "order__pk")
    inlines = (OrderItemInline,)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "seller_order",
        "product_name",
        "unit_price",
        "quantity",
        "subtotal",
    )
    list_filter = ("seller_order__store",)
    search_fields = ("product_name", "product_sku")
