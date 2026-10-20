from catalog.models import Product

CART_SESSION_KEY = "cart"
OPERATION_SESSION_KEY = "checkout_operation_id"


class Cart:
    """Carrinho de compras persistido na sessao do Django.

    Armazena apenas identificador do produto e quantidade. O preco e a
    disponibilidade sao sempre revalidados no servidor (catalogo/views e
    checkout), nunca confiando em valores enviados pelo navegador.

    O carrinho tambem guarda um identificador de operacao de checkout
    gerado pelo servidor, usado para garantir idempotencia e permitir
    nova tentativa apos cancelamento ou falha sem duplicar pedidos.
    """

    OPERATION_SESSION_KEY = "checkout_operation_id"

    def __init__(self, request):
        self.session = request.session
        self.cart = self.session.get(CART_SESSION_KEY, {})
        if not self.cart:
            self.cart = self.session[CART_SESSION_KEY] = {}

    def save(self):
        self.session.modified = True

    def __iter__(self):
        product_ids = [int(pid) for pid in self.cart.keys()]
        products = Product.objects.filter(id__in=product_ids)
        cart = self.cart.copy()
        for product in products:
            item = cart[str(product.id)].copy()
            item["product"] = product
            item["price"] = product.price
            item["subtotal"] = product.price * item["quantity"]
            yield item

    def __len__(self):
        return sum(item["quantity"] for item in self.cart.values())

    def add(self, product, quantity=1, override_quantity=False):
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {"quantity": 0}
        if override_quantity:
            self.cart[product_id]["quantity"] = quantity
        else:
            self.cart[product_id]["quantity"] += quantity
        self.save()

    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def clear(self):
        self.session.pop(CART_SESSION_KEY, None)
        self.session.pop(OPERATION_SESSION_KEY, None)
        self.save()

    def get_total_price(self):
        return sum(item["price"] * item["quantity"] for item in self)

    def get_operation_id(self):
        """Retorna o identificador de operacao armazenado na sessao."""
        return self.session.get(OPERATION_SESSION_KEY)

    def set_operation_id(self, operation_id):
        """Armazena o identificador de operacao na sessao."""
        self.session[OPERATION_SESSION_KEY] = operation_id
        self.save()

    def clear_operation_id(self):
        """Remove o identificador de operacao da sessao."""
        self.session.pop(OPERATION_SESSION_KEY, None)
        self.save()
