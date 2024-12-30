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
        "<int:competition_id>/register",
        views.registration,
        name="registration",
    ),
    path(
        "<int:competition_id>/application-list",
        views.application_list,
        name="application_list",
    ),
    path(
        "<int:competition_id>/detail",
        views.competition_detail_view,
        name="competition_detail",
    ),
    path(
        "<int:application_id>/cancel",
        views.cancel_application_view,
        name="cancel_application",
    ),
    path(
        "<int:competition_id>/final-placements-dialog",
        views.competition_final_placements_dialog_view,
        name="competition_final_placements_dialog",
    ),
]
