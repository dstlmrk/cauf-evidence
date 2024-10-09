from django.urls import path

from clubs import views

app_name = "clubs"
urlpatterns = [
    path(
        "<int:club_id>/members",
        views.members,
        name="members",
    ),
    path(
        "<int:club_id>/settings",
        views.settings,
        name="settings",
    ),
    path(
        "<int:club_id>/agents",
        views.agent_list,
        name="agent_list",
    ),
    path(
        "<int:club_id>/agents/add",
        views.add_agent_to_club,
        name="add_agent_to_club",
    ),
    path(
        "<int:club_id>/agents/remove",
        views.remove_agent_from_club,
        name="remove_agent_from_club",
    ),
]
