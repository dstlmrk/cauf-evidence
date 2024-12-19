from django.urls import path

from tournaments import views

app_name = "tournaments"


urlpatterns = [
    path(
        "",
        views.tournaments_view,
        name="tournaments",
    ),
    path(
        "<int:tournament_id>/detail",
        views.tournament_detail_view,
        name="detail",
    ),
    path(
        "team-at-tournament/<int:team_at_tournament_id>/roster-dialog",
        views.roster_dialog_view,
        name="roster_dialog",
    ),
    path(
        "team-at-tournament/<int:team_at_tournament_id>/add",
        views.roster_dialog_add_form_view,
        name="roster_dialog_add_form",
    ),
    path(
        "member-at-tournament/<int:member_at_tournament_id>/update",
        views.roster_dialog_update_form_view,
        name="roster_dialog_update_form",
    ),
    path(
        "member-at-tournament/<int:member_at_tournament_id>/remove",
        views.remove_member_from_roster_view,
        name="remove_member_from_roster",
    ),
    path(
        "tournaments/<int:tournament_id>/teams-table",
        views.teams_table_view,
        name="teams_table",
    ),
]
