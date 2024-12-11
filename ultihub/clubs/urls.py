from django.urls import path

from clubs import views

app_name = "clubs"
urlpatterns = [
    path("invoices", views.invoices, name="invoices"),
    path("transfers", views.transfers, name="transfers"),
    # MEMBERS ------------------------------------------------------------
    path("member-list", views.member_list, name="member_list"),
    path("members", views.members, name="members"),
    path("seasonal-fees", views.seasonal_fees_view, name="seasonal_fees"),
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
