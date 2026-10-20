import uuid
from decimal import ROUND_HALF_UP, Decimal

from django.db import IntegrityError, transaction
from django.db.models import F

from cart.cart import Cart
from catalog.models import Product
from commissions.models import Commission, CommissionConfig
from orders.models import Order, OrderItem, SellerOrder
from payments.models import Payment

TERMINAL_STATUSES = {
    Order.Status.CANCELLED,
    Order.Status.FAILED,
}


def money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def build_checkout_summary(cart):
    """Monta o resumo da compra agrupando itens por loja.

    Retorna uma lista de dicionarios, um por loja, com:
      - store: objeto Store
      - items: lista de itens (product, quantity, unit_price, subtotal)
      - subtotal: total da loja
      - commission: valor da comissao da KLYA
      - net: valor liquido devido ao vendedor
    """
    rate = CommissionConfig.get_active_rate() or Decimal("0")
    stores = {}

    for item in cart:
        product = item["product"]
        store = product.store
        if store.pk not in stores:
            stores[store.pk] = {
                "store": store,
                "items": [],
                "subtotal": Decimal("0"),
            }
        unit_price = product.price
        subtotal = unit_price * item["quantity"]
        stores[store.pk]["items"].append(
            {
                "product": product,
                "quantity": item["quantity"],
                "unit_price": unit_price,
                "subtotal": subtotal,
            }
        )
        stores[store.pk]["subtotal"] += subtotal

    summary = []
    total = Decimal("0")
    for store_data in stores.values():
        subtotal = store_data["subtotal"]
        commission = money(subtotal * rate)
        net = money(subtotal - commission)
        store_data["commission"] = commission
        store_data["net"] = net
        total += subtotal
        summary.append(store_data)

    summary.sort(key=lambda s: s["store"].name)
    return {
        "stores": summary,
        "total": money(total),
        "rate": rate,
    }


def checkout(request):
    """Finaliza o carrinho criando os pedidos, missoes e pagamento.

    Toda a operacao ocorre dentro de uma transacao atomica. Os produtos
    sao bloqueados com select_for_update() para evitar vendas concorrentes
    acima do estoque disponivel. A idempotencia e garantida por um
    identificador de operacao (operation_id) gerado pelo servidor e
    armazenado na sessao do Django:

    - Repeticoes da mesma operacao (mesmo operation_id) retornam o pedido
      existente, sem duplicar pedidos, itens, missoes ou desconto de
      estoque.
    - Se o pedido associado a operacao estiver em estado terminal
      (cancelado ou falhou), o operation_id e renovado no servidor e um
      novo pedido e criado, preservando o pedido anterior e seu historico.
    - O cliente nao escolhe a chave de idempotencia; ela e gerada e
      controlada pelo servidor.

    Estados reconhecidos:
    * repeticao da operacao atual: mesmo operation_id, pedido existente
      (qualquer status) -> retorna o pedido existente
    * nova operacao apos cancelamento/falha: operation_id renovado,
      novo pedido criado, pedido anterior preservado
    * pedido ainda em processamento (PENDING/PAID): mesmo operation_id,
      retorna o pedido existente
    * falha de validacao ou transacao: rollback, carrinho mantido na
      sessao, nenhum pedido criado
    """
    user = request.user
    cart = Cart(request)

    if len(cart) == 0:
        return None, "Seu carrinho está vazio."

    summary = build_checkout_summary(cart)

    # Validacao de estoque e disponibilidade antes de iniciar a transacao.
    for store_data in summary["stores"]:
        for item in store_data["items"]:
            product = item["product"]
            if (
                product.status != product.Status.PUBLISHED
                or not product.is_active
                or product.store.status != "approved"
            ):
                return None, f"O produto '{product.name}' não está mais disponível."
            if product.stock < item["quantity"]:
                return None, (
                    f"Estoque insuficiente para '{product.name}'. "
                    f"Disponível: {product.stock}."
                )

    # Identificador de operacao gerado pelo servidor, armazenado na sessao.
    operation_id = cart.get_operation_id()
    if operation_id is None:
        operation_id = str(uuid.uuid4())
        cart.set_operation_id(operation_id)

    idempotency_key = f"checkout:{user.pk}:{operation_id}"

    # Verificacao idempotente FORA da transacao.
    existing = (
        Order.objects.filter(idempotency_key=idempotency_key)
        .select_related("payment")
        .first()
    )
    if existing is not None:
        if existing.status in TERMINAL_STATUSES:
            # Pedido anterior em estado terminal: renovar o operation_id
            # no servidor e criar um novo pedido. O cliente nao controla
            # essa renovacao.
            operation_id = str(uuid.uuid4())
            cart.set_operation_id(operation_id)
            idempotency_key = f"checkout:{user.pk}:{operation_id}"
        else:
            # Pedido ainda em processamento ou pago: retorna o existente.
            return existing, None

    created_order = None
    try:
        with transaction.atomic():
            # Cria o pedido principal.
            created_order = Order.objects.create(
                buyer=user,
                status=Order.Status.PENDING,
                total=summary["total"],
                idempotency_key=idempotency_key,
            )

            # Bloqueia as linhas dos produtos para evitar vendas concorrentes.
            product_ids_in_cart = [
                item["product"].pk
                for store_data in summary["stores"]
                for item in store_data["items"]
            ]
            locked_products = {
                p.pk: p
                for p in (
                    Product.objects.select_for_update().filter(
                        pk__in=product_ids_in_cart
                    )
                )
            }

            # Revalida estoque dentro da transacao apos o bloqueio.
            for store_data in summary["stores"]:
                for item in store_data["items"]:
                    product = locked_products[item["product"].pk]
                    if (
                        product.status != product.Status.PUBLISHED
                        or not product.is_active
                        or product.store.status != "approved"
                    ):
                        raise ValueError(
                            f"O produto '{product.name}' não está mais disponível."
                        )
                    if product.stock < item["quantity"]:
                        raise ValueError(
                            f"Estoque insuficiente para '{product.name}'. "
                            f"Disponível: {product.stock}."
                        )

            # Cria pedidos por vendedor, itens, missoes e desconta estoque.
            for store_data in summary["stores"]:
                store = store_data["store"]
                seller_order = SellerOrder.objects.create(
                    order=created_order,
                    store=store,
                    subtotal=store_data["subtotal"],
                    status=SellerOrder.Status.PENDING,
                )

                for item in store_data["items"]:
                    product = locked_products[item["product"].pk]
                    OrderItem.objects.create(
                        seller_order=seller_order,
                        product=product,
                        unit_price=product.price,
                        quantity=item["quantity"],
                    )

                    # Desconta estoque (baixa) no momento da finalizacao.
                    Product.objects.filter(pk=product.pk).update(
                        stock=F("stock") - item["quantity"]
                    )

                # Registra a misso da KLYA para este pedido de vendedor.
                rate = summary["rate"]
                gross = store_data["subtotal"]
                commission = money(gross * rate)
                net = money(gross - commission)
                Commission.objects.create(
                    seller_order=seller_order,
                    rate=rate,
                    gross_amount=gross,
                    commission_amount=commission,
                    net_amount=net,
                )

            # Cria o pagamento simulado em estado pendente.
            Payment.objects.create(
                order=created_order,
                amount=created_order.total,
                status=Payment.Status.PENDING,
            )
    except ValueError as exc:
        # Erro de validacao dentro da transacao: rollback automatico,
        # carrinho e operation_id mantidos na sessao.
        return None, str(exc)
    except IntegrityError:
        # Condicao de corrida: outra requisicao ja criou o pedido com essa
        # chave. A transacao foi desfeita ao sair do bloco with (rollback
        # automatico). Consulta FORA da transacao invalida.
        order = Order.objects.filter(idempotency_key=idempotency_key).first()
        if order is not None:
            return order, None
        # Violação de integridade nao relacionada à chave de idempotencia:
        # propaga sem mascarar.
        raise

    # Sucesso real da transacao: limpa o carrinho e o operation_id apenas
    # agora, fora da transacao (a sessao Django nao participa da
    # transacao do banco de dados).
    cart.clear()
    return created_order, None
