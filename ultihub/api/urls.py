from django.urls import path

from api.views import (
    ClubsView,
    CompetitionApplicationView,
    CompetitionsView,
    SeasonsView,
    TeamAtTournamentView,
    TeamsAtTournamentView,
)

app_name = "api"

urlpatterns = [
    path(
        "competitions",
        CompetitionsView.as_view(),
        name="competitions",
    ),
    path(
        "clubs",
        ClubsView.as_view(),
        name="clubs",
    ),
    path(
        "teams-at-tournament",
        TeamsAtTournamentView.as_view(),
        name="teams-at-tournament",
    ),
    path(
        "team-at-tournament/<int:pk>",
        TeamAtTournamentView.as_view(),
        name="team-at-tournament",
    ),
    path(
        "competition-application/<int:pk>",
        CompetitionApplicationView.as_view(),
        name="competition-application",
    ),
    path(
        "seasons",
        SeasonsView.as_view(),
        name="seasons",
    ),
]
