from django.urls import path

from competitions import views

app_name = "competitions"
urlpatterns = [
    path("", views.competitions, name="competitions"),
    path("<int:competition_id>/register", views.registration, name="registration"),
    path("<int:competition_id>/application-list", views.application_list, name="application_list"),
]
