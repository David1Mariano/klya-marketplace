from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalog.models import Product

from .cart import Cart


@login_required
def cart_detail(request):
    cart = Cart(request)

    valid_items = []
    changed = False
    for item in cart:
        product = item["product"]
        available = (
            product.status == Product.Status.PUBLISHED
            and product.is_active
            and product.store.status == "approved"
            and product.stock >= item["quantity"]
        )
        if not available:
            messages.warning(
                request,
                f"O produto '{product.name}' nao esta mais disponivel e foi removido do carrinho.",
            )
            cart.remove(product)
            changed = True
            continue
        valid_items.append(item)

    if changed:
        return redirect("cart:cart_detail")

    context = {
        "cart": valid_items,
        "total": cart.get_total_price(),
    }
    return render(request, "cart/cart_detail.html", context)


@login_required
@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, pk=product_id)

    if (
        product.status != Product.Status.PUBLISHED
        or not product.is_active
        or product.store.status != "approved"
    ):
        messages.error(request, "Este produto nao esta disponível para compra.")
        return redirect("catalog:product_detail", slug=product.slug, pk=product.pk)

    try:
        quantity = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        quantity = 1

    if quantity < 1:
        messages.error(request, "A quantidade deve ser um número positivo.")
        return redirect("catalog:product_detail", slug=product.slug, pk=product.pk)

    if quantity > product.stock:
        messages.error(
            request,
            f"Estoque insuficiente para '{product.name}'. Disponível: {product.stock}.",
        )
        return redirect("catalog:product_detail", slug=product.slug, pk=product.pk)

    cart = Cart(request)
    cart.add(product, quantity=quantity)
    messages.success(request, f"{quantity}x '{product.name}' adicionado ao carrinho.")
    return redirect("catalog:product_detail", slug=product.slug, pk=product.pk)


@login_required
@require_POST
def cart_update(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    cart = Cart(request)

    try:
        quantity = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        messages.error(request, "Quantidade inválida.")
        return redirect("cart:cart_detail")

    if quantity < 1:
        messages.error(request, "A quantidade deve ser um número positivo.")
        return redirect("cart:cart_detail")

    if quantity > product.stock:
        messages.error(
            request,
            f"Estoque insuficiente para '{product.name}'. Disponível: {product.stock}.",
        )
        return redirect("cart:cart_detail")

    cart.add(product, quantity=quantity, override_quantity=True)
    messages.success(request, f"Quantidade de '{product.name}' atualizada.")
    return redirect("cart:cart_detail")


@login_required
@require_POST
def cart_remove(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    cart = Cart(request)
    cart.remove(product)
    messages.success(request, f"'{product.name}' removido do carrinho.")
    return redirect("cart:cart_detail")
