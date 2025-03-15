from django.urls import path

from core import views

urlpatterns = [
    path("", views.homepage_view, name="home"),
    path("faq", views.faq_view, name="faq"),
]
