"""
URL configuration for ultihub project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

import logging

from django.contrib import admin
from django.db import connection
from django.http import HttpRequest, HttpResponse
from django.urls import path

logger = logging.getLogger(__name__)


def index(request: HttpRequest) -> HttpResponse:
    cursor = connection.cursor()
    cursor.execute("select 1 from pg_tables;")
    return HttpResponse("Hello, world")


urlpatterns = [
    path("", index, name="index"),
    path("admin/", admin.site.urls),
]
