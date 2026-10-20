from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from orders.models import Order, SellerOrder
from .models import Payment


TERMINAL_STATUSES = {
    Payment.Status.APPROVED,
    Payment.Status.CANCELLED,
    Payment.Status.FAILED,
}

ACTION_TO_STATUS = {
    "approve": Payment.Status.APPROVED,
    "cancel": Payment.Status.CANCELLED,
    "fail": Payment.Status.FAILED,
}


@login_required
def simulate_payment(request, pk):
    """Página de pagamento simulado para o pedido do comprador logado.

    Não coleta nem armazena dados reais de cartão. A aprovação é uma
    simulação que altera os estados do pedido e do pagamento.
    """
    order = get_object_or_404(Order, pk=pk, buyer=request.user)
    try:
        payment = order.payment
    except Payment.DoesNotExist:
        messages.error(request, "Este pedido não possui pagamento associado.")
        return redirect("orders:order_detail", pk=order.pk)

    seller_orders = order.seller_orders.select_related("store").all()

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action not in ACTION_TO_STATUS:
            messages.error(request, "Ação de pagamento inválida.")
            return redirect("payments:simulate", pk=order.pk)

        if payment.status in TERMINAL_STATUSES:
            messages.error(
                request,
                f"Este pagamento já foi processado ({payment.get_status_display()}).",
            )
            return redirect("orders:order_detail", pk=order.pk)

        new_status = ACTION_TO_STATUS[action]

        with transaction.atomic():
            payment.status = new_status
            payment.save()

            mapped_order_status = {
                Payment.Status.APPROVED: Order.Status.PAID,
                Payment.Status.CANCELLED: Order.Status.CANCELLED,
                Payment.Status.FAILED: Order.Status.FAILED,
            }[new_status]
            order.status = mapped_order_status
            order.save()

            SellerOrder.objects.filter(order=order).update(status=mapped_order_status)

        status_label = dict(Payment.Status.choices)[new_status]
        messages.success(
            request,
            f"Pagamento simulado: {status_label}. Pedido #{order.pk} atualizado.",
        )
        return redirect("orders:order_detail", pk=order.pk)

    return render(
        request,
        "payments/simulate.html",
        {
            "order": order,
            "payment": payment,
            "seller_orders": seller_orders,
            "is_terminal": payment.status in TERMINAL_STATUSES,
        },
    )
