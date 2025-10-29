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
from django.urls import include, path

from ultihub import settings

logger = logging.getLogger(__name__)

admin.site.site_header = "ČAUF Admin"
admin.site.site_title = "ČAUF Admin"
admin.site.index_title = ""

urlpatterns = [
    path("", include("core.urls")),
    path("accounts/", include("allauth.urls")),
    path("admin/", admin.site.urls, name="admin"),
    path("api/", include("api.urls")),
    path("club/", include("clubs.urls")),
    path("competitions/", include("competitions.urls")),
    path("finance/", include("finance.urls")),
    path("international-tournaments/", include("international_tournaments.urls")),
    path("members/", include("members.urls")),
    path("tournaments/", include("tournaments.urls")),
    path("users/", include("users.urls")),
]

if settings.ENVIRONMENT != "test":
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns = [*urlpatterns] + debug_toolbar_urls()
