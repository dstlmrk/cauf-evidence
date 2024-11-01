from django.urls import path

from clubs import views

app_name = "clubs"
urlpatterns = [
    # MEMBERS ------------------------------------------------------------
    path("<int:club_id>/members", views.members, name="members"),
    # TEAMS --------------------------------------------------------------
    path("<int:club_id>/team-list", views.team_list, name="team_list"),
    path("<int:club_id>/teams", views.teams, name="teams"),
    path("<int:club_id>/teams/<int:team_id>/edit", views.edit_team, name="edit_team"),
    path("<int:club_id>/teams/<int:team_id>/remove", views.remove_team, name="remove_team"),
    path("<int:club_id>/teams/add", views.add_team, name="add_team"),
    # SETTINGS -----------------------------------------------------------
    path("<int:club_id>/agent-list", views.agent_list, name="agent_list"),
    path("<int:club_id>/agents/add", views.add_agent, name="add_agent"),
    path("<int:club_id>/agents/remove", views.remove_agent, name="remove_agent"),
    path("<int:club_id>/settings", views.settings, name="settings"),
]
