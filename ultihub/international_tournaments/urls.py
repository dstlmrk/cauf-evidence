from django.urls import path

from international_tournaments import views

app_name = "international_tournaments"


urlpatterns = [
    path(
        "",
        views.international_tournaments_view,
        name="international_tournaments",
    ),
    path(
        "team-at-tournament/<int:team_at_tournament_id>/roster-dialog",
        views.international_roster_dialog_view,
        name="roster_dialog",
    ),
    path(
        "team-at-tournament/<int:team_at_tournament_id>/add",
        views.international_roster_add_form_view,
        name="roster_add",
    ),
    path(
        "member-at-tournament/<int:member_at_tournament_id>/update",
        views.international_roster_update_form_view,
        name="roster_update",
    ),
    path(
        "member-at-tournament/<int:member_at_tournament_id>/remove",
        views.remove_member_from_international_roster_view,
        name="roster_remove",
    ),
]
