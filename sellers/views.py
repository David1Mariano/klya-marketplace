from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render

from .forms import StoreRequestForm, StoreReviewForm
from .models import Store


def is_admin(user):
    return user.is_staff or user.is_superuser


@login_required
def store_request(request):
    try:
        store = request.user.store
    except Exception:
        store = None

    if store:
        messages.warning(request, "Você já possui uma loja cadastrada.")
        return redirect("accounts:profile")

    if request.method == "POST":
        form = StoreRequestForm(request.POST)
        if form.is_valid():
            store = form.save(commit=False)
            store.owner = request.user
            store.status = "pending"
            store.save()
            messages.success(request, "Solicitação de loja enviada com sucesso.")
            return redirect("accounts:profile")
    else:
        form = StoreRequestForm()

    return render(request, "sellers/store_request.html", {"form": form})


@login_required
def dashboard(request):
    try:
        store = request.user.store
    except Exception:
        store = None
    return render(request, "sellers/dashboard.html", {"store": store})


@user_passes_test(is_admin, login_url="accounts:login")
def store_list(request):
    stores = Store.objects.filter(status="pending").select_related("owner")
    return render(request, "sellers/store_list.html", {"stores": stores})


@user_passes_test(is_admin, login_url="accounts:login")
def store_review(request, pk):
    store = get_object_or_404(Store.objects.select_related("owner"), pk=pk)
    if request.method == "POST":
        form = StoreReviewForm(request.POST, instance=store)
        if form.is_valid():
            form.save()
            messages.success(request, "Loja atualizada com sucesso.")
            return redirect("sellers:store_list")
    else:
        form = StoreReviewForm(instance=store)

    return render(request, "sellers/store_review.html", {"form": form, "store": store})


@login_required
def seller_dashboard(request):
    return dashboard(request)
