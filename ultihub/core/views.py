from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def index(request: HttpRequest) -> HttpResponse:
    return render(request, "core/index.html", {"users": User.objects.all()})
