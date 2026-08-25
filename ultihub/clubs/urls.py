from django.urls import path, re_path

from clubs import views

app_name = "clubs"
urlpatterns = [
    path("invoices", views.invoices, name="invoices"),
    path("transfers", views.transfers_view, name="transfers"),
    # MEMBERS ------------------------------------------------------------
    path("member-list", views.member_list, name="member_list"),
    path("members", views.members, name="members"),
    path("season-fees", views.season_fees_view, name="season_fees"),
    # TEAMS --------------------------------------------------------------
    path("team-list", views.team_list_view, name="team_list"),
    path("teams", views.teams_view, name="teams"),
    path("teams/<int:team_id>/edit", views.edit_team, name="edit_team"),
    path("teams/<int:team_id>/remove", views.remove_team, name="remove_team"),
    path("teams/add", views.add_team, name="add_team"),
    # SETTINGS -----------------------------------------------------------
    path("agent-list", views.agent_list, name="agent_list"),
    path("agents/add", views.add_agent, name="add_agent"),
    path("agents/remove", views.remove_agent, name="remove_agent"),
    path("settings", views.settings, name="settings"),
    path("logo/upload", views.upload_logo, name="upload_logo"),
    path("logo/remove", views.remove_logo, name="remove_logo"),
    path("logo/cancel-pending", views.cancel_pending_logo, name="cancel_pending_logo"),
    # The size is part of the pattern so the view can read the matching column directly
    re_path(
        r"^logos/(?P<club_id>\d+)/(?P<size>large|small)\.webp$",
        views.club_logo,
        name="club_logo",
    ),
    # OTHERS -------------------------------------------------------------
    path("notifications-dialog", views.notifications_dialog_view, name="notifications_dialog"),
]
