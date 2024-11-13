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

from competitions.views import tournaments
from debug_toolbar.toolbar import debug_toolbar_urls
from django.contrib import admin
from django.urls import include, path

from ultihub import settings

logger = logging.getLogger(__name__)

urlpatterns = [
    path("", include("core.urls")),
    path("accounts/", include("allauth.urls")),
    path("admin/", admin.site.urls, name="admin"),
    path("api/", include("rest_api.urls")),
    path("club/", include("clubs.urls")),
    path("competitions/", include("competitions.urls")),
    path("django-rq/", include("django_rq.urls")),
    path("finance/", include("finance.urls")),
    path("tournaments/", tournaments, name="tournaments"),
    path("users/", include("users.urls")),
]

if settings.ENVIRONMENT != "test":
    urlpatterns = [*urlpatterns] + debug_toolbar_urls()
