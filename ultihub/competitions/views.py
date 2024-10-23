from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from competitions.models import Competition


def competitions(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "competitions/competitions.html",
        context={"competitions": Competition.objects.all()},
    )
