from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("", views.cart_detail, name="cart_detail"),
    path("adicionar/<int:product_id>/", views.cart_add, name="cart_add"),
    path("atualizar/<int:product_id>/", views.cart_update, name="cart_update"),
    path("remover/<int:product_id>/", views.cart_remove, name="cart_remove"),
]
