from django.urls import path

from clubs import views

app_name = "clubs"
urlpatterns = [
    path("invoices", views.invoices, name="invoices"),
    # MEMBERS ------------------------------------------------------------
    path("member-list", views.member_list, name="member_list"),
    path("members", views.members, name="members"),
    path(
        "members/<int:member_id>/licence-list", views.coach_licence_list, name="coach_licence_list"
    ),
    path("members/<int:member_id>/edit", views.edit_member, name="edit_member"),
    path("members/add", views.add_member, name="add_member"),
    # TEAMS --------------------------------------------------------------
    path("team-list", views.team_list, name="team_list"),
    path("teams", views.teams, name="teams"),
    path("teams/<int:team_id>/edit", views.edit_team, name="edit_team"),
    path("teams/<int:team_id>/remove", views.remove_team, name="remove_team"),
    path("teams/add", views.add_team, name="add_team"),
    # SETTINGS -----------------------------------------------------------
    path("agent-list", views.agent_list, name="agent_list"),
    path("agents/add", views.add_agent, name="add_agent"),
    path("agents/remove", views.remove_agent, name="remove_agent"),
    path("settings", views.settings, name="settings"),
]
