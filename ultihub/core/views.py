from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def homepage(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "core/homepage.html",
    )
