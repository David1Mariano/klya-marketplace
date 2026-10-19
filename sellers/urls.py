from django.urls import path
from . import views

app_name = "sellers"

urlpatterns = [
    path("solicitar/", views.store_request, name="store_request"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("painel/", views.seller_dashboard, name="seller_dashboard"),
    path("admin/lojas/pendentes/", views.store_list, name="store_list"),
    path("admin/lojas/<int:pk>/analisar/", views.store_review, name="store_review"),
]
