from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("pk", "order", "status", "method", "amount", "created_at")
    list_filter = ("status", "method", "created_at")
    search_fields = ("order__pk",)
