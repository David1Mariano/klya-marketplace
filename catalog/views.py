from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProductForm
from .models import Category, Product


def product_list(request):
    products = (
        Product.objects.select_related("store", "category")
        .filter(
            status=Product.Status.PUBLISHED, store__status="approved", is_active=True
        )
        .order_by("-created_at")
    )

    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()

    if q:
        products = products.filter(Q(name__icontains=q) | Q(description__icontains=q))

    if category:
        products = products.filter(category_id=category)

    categories = Category.objects.all().order_by("name")

    context = {
        "products": products,
        "categories": categories,
        "q": q,
        "selected_category": category,
    }
    return render(request, "catalog/product_list.html", context)


def product_detail(request, slug, pk):
    product = get_object_or_404(
        Product.objects.select_related("store", "category"),
        pk=pk,
        slug=slug,
        status=Product.Status.PUBLISHED,
        store__status="approved",
        is_active=True,
    )
    return render(request, "catalog/product_detail.html", {"product": product})


@login_required
def seller_products(request):
    try:
        store = request.user.store
    except Exception:
        store = None

    if not store or store.status != "approved":
        messages.warning(
            request, "Você precisa de uma loja aprovada para gerenciar produtos."
        )
        return redirect("accounts:profile")

    products = (
        Product.objects.filter(store=store)
        .select_related("category")
        .order_by("-created_at")
    )
    return render(
        request, "catalog/seller_products.html", {"products": products, "store": store}
    )


@login_required
def product_create(request):
    try:
        store = request.user.store
    except Exception:
        store = None

    if not store or store.status != "approved":
        messages.warning(
            request, "Você precisa de uma loja aprovada para cadastrar produtos."
        )
        return redirect("accounts:profile")

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.store = store
            product.save()
            messages.success(request, "Produto cadastrado com sucesso.")
            return redirect("catalog:seller_products")
    else:
        form = ProductForm()

    return render(
        request, "catalog/product_form.html", {"form": form, "is_create": True}
    )


@login_required
def product_edit(request, pk):
    try:
        store = request.user.store
    except Exception:
        store = None

    if not store or store.status != "approved":
        messages.warning(
            request, "Você precisa de uma loja aprovada para editar produtos."
        )
        return redirect("accounts:profile")

    product = get_object_or_404(Product, pk=pk, store=store)

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Produto atualizado com sucesso.")
            return redirect("catalog:seller_products")
    else:
        form = ProductForm(instance=product)

    return render(
        request,
        "catalog/product_form.html",
        {"form": form, "is_create": False, "product": product},
    )
