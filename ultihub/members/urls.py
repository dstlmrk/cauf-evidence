from django.urls import path

from members import views

app_name = "members"
urlpatterns = [
    path("<int:member_id>/licence-list", views.coach_licence_list, name="coach_licence_list"),
    path("<int:member_id>/edit", views.edit_member, name="edit_member"),
    path("add", views.add_member, name="add_member"),
    path("confirm-email/<uuid:token>", views.confirm_email, name="confirm_email"),
    path("search", views.search, name="search"),
    path("transfer-form", views.transfer_form, name="transfer_form"),
    path("approve-transfer", views.approve_transfer_view, name="approve_transfer"),
    path("revoke-transfer", views.revoke_transfer_view, name="revoke_transfer"),
]
