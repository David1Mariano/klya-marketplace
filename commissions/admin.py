from django.contrib import admin

from .models import Commission, CommissionConfig


@admin.register(CommissionConfig)
class CommissionConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "rate", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "seller_order",
        "rate",
        "gross_amount",
        "commission_amount",
        "net_amount",
        "created_at",
    )
    list_filter = ("seller_order__store", "created_at")
    search_fields = ("seller_order__store__name",)
