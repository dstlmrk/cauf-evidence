from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_GET


@require_GET
def homepage(request: HttpRequest) -> HttpResponse:
    return redirect("tournaments:tournaments")
