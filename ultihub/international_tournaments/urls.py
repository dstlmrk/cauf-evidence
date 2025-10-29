from django.urls import path

from international_tournaments import views

app_name = "international_tournaments"


urlpatterns = [
    path(
        "",
        views.international_tournaments_view,
        name="international_tournaments",
    ),
]
