from django.urls import path

from competitions import views

app_name = "competitions"
urlpatterns = [
    path(
        "",
        views.competitions,
        name="competitions",
    ),
    path(
        "get",
        views.json_competitions,
        name="json_competitions",
    ),
]
