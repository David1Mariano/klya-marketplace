from django import forms
from .models import Store


class StoreRequestForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ("name", "description")


class StoreReviewForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ("status", "rejection_reason")

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        reason = cleaned.get("rejection_reason")
        if status == "rejected" and not reason:
            self.add_error("rejection_reason", "Informe o motivo da rejeição.")
        return cleaned
