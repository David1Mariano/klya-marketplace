from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from cart.cart import Cart

from .checkout import checkout as perform_checkout
from .models import Order, SellerOrder
from commissions.models import Commission
from payments.models import Payment


@login_required
def checkout_review(request):
    """Página de revisão da compra antes da finalização."""
    cart = Cart(request)

    if len(cart) == 0:
        messages.warning(request, "Seu carrinho está vazio.")
        return redirect("cart:cart_detail")

    from .checkout import build_checkout_summary

    summary = build_checkout_summary(cart)

    context = {
        "summary": summary,
        "cart": list(cart),
        "total": summary["total"],
    }
    return render(request, "orders/checkout_review.html", context)


@login_required
@require_POST
def checkout(request):
    """Finaliza o carrinho e cria os pedidos (atômico, com idempotência)."""
    order, error = perform_checkout(request)

    if error is not None:
        messages.error(request, error)
        return redirect("cart:cart_detail")

    if order is None:
        messages.error(request, "Não foi possível finalizar a compra.")
        return redirect("cart:cart_detail")

    messages.success(
        request,
        f"Pedido #{order.pk} criado com sucesso. Prossiga para o pagamento simulado.",
    )
    return redirect("orders:order_detail", pk=order.pk)


@login_required
def order_list(request):
    """Histórico de pedidos do comprador logado."""
    orders = Order.objects.filter(buyer=request.user).prefetch_related(
        "seller_orders__store"
    )
    return render(request, "orders/order_list.html", {"orders": orders})


@login_required
def order_detail(request, pk):
    """Detalhe de um pedido do comprador (apenas o próprio comprador)."""
    order = get_object_or_404(Order, pk=pk, buyer=request.user)
    seller_orders = order.seller_orders.select_related("store").prefetch_related(
        "items__product", "commission"
    )
    try:
        payment = order.payment
    except Payment.DoesNotExist:
        payment = None
    return render(
        request,
        "orders/order_detail.html",
        {
            "order": order,
            "seller_orders": seller_orders,
            "payment": payment,
        },
    )


@login_required
def seller_order_list(request):
    """Lista de pedidos recebidos pelo vendedor (apenas sua loja)."""
    try:
        store = request.user.store
    except Exception:
        store = None

    if not store:
        messages.warning(request, "Você não possui uma loja cadastrada.")
        return redirect("accounts:profile")

    seller_orders = (
        SellerOrder.objects.filter(store=store)
        .select_related("order__buyer", "store")
        .prefetch_related("items__product", "commission")
        .order_by("-created_at")
    )
    return render(
        request,
        "orders/seller_order_list.html",
        {"store": store, "seller_orders": seller_orders},
    )


@login_required
def seller_order_detail(request, pk):
    """Detalhe de um pedido de vendedor (apenas o vendedor responsável)."""
    try:
        store = request.user.store
    except Exception:
        store = None

    if not store:
        messages.warning(request, "Você não possui uma loja cadastrada.")
        return redirect("accounts:profile")

    seller_order = get_object_or_404(
        SellerOrder.objects.select_related("order__buyer", "store"),
        pk=pk,
        store=store,
    )
    items = seller_order.items.select_related("product").all()
    try:
        commission = seller_order.commission
    except Commission.DoesNotExist:
        commission = None

    return render(
        request,
        "orders/seller_order_detail.html",
        {
            "store": store,
            "seller_order": seller_order,
            "items": items,
            "commission": commission,
        },
    )
