from django.urls import path

from rest_api.views import CompetitionView

app_name = "api"

urlpatterns = [
    path("competitions", CompetitionView.as_view()),
]
