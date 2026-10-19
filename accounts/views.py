from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import SignUpForm


class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("accounts:profile")

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.instance
        login(self.request, user)
        messages.success(self.request, "Cadastro realizado com sucesso.")
        return response


@login_required
def profile(request):
    user = request.user
    store = None
    try:
        store = user.store
    except Exception:
        store = None

    can_request_store = True
    if store:
        can_request_store = False

    return render(
        request,
        "accounts/profile.html",
        {
            "user": user,
            "store": store,
            "can_request_store": can_request_store,
        },
    )


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Logout realizado com sucesso.")
    return redirect("core:home")
