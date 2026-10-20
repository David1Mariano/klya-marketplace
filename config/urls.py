from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("contas/", include("accounts.urls")),
    path("vendedores/", include("sellers.urls")),
    path("catalogo/", include("catalog.urls")),
    path("carrinho/", include("cart.urls")),
    path("pedidos/", include("orders.urls")),
    path("pagamentos/", include("payments.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
