from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("simular/<int:pk>/", views.simulate_payment, name="simulate"),
]
