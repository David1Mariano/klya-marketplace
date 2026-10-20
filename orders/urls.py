from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("checkout/revisar/", views.checkout_review, name="checkout_review"),
    path("checkout/finalizar/", views.checkout, name="checkout"),
    path("meus-pedidos/", views.order_list, name="order_list"),
    path("meus-pedidos/<int:pk>/", views.order_detail, name="order_detail"),
    path("vendedor/meus-pedidos/", views.seller_order_list, name="seller_order_list"),
    path(
        "vendedor/meus-pedidos/<int:pk>/",
        views.seller_order_detail,
        name="seller_order_detail",
    ),
]
