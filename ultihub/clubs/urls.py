from django.urls import path

from clubs import views

app_name = "clubs"
urlpatterns = [
    path("<int:club_id>/members", views.members, name="members"),
    path("<int:club_id>/settings", views.settings, name="settings"),
]
