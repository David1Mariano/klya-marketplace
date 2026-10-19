from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("<slug:slug>/<int:pk>/", views.product_detail, name="product_detail"),
    path("vendedor/meus-produtos/", views.seller_products, name="seller_products"),
    path("vendedor/produtos/novo/", views.product_create, name="product_create"),
    path("vendedor/produtos/<int:pk>/editar/", views.product_edit, name="product_edit"),
]
