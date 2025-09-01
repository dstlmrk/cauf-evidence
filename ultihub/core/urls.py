from django.urls import path

from core import views

urlpatterns = [
    path("", views.homepage_view, name="home"),
    path("faq", views.faq_view, name="faq"),
    path("privacy-policy", views.privacy_policy_view, name="privacy_policy"),
]
