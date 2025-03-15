from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET


@require_GET
def homepage_view(request: HttpRequest) -> HttpResponse:
    return redirect("tournaments:tournaments")


@require_GET
def faq_view(request: HttpRequest) -> HttpResponse:
    return render(request, "core/faq.html")
