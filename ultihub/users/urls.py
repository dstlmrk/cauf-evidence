from django.urls import path

from users import views

app_name = "users"

urlpatterns = [
    path("switch-club", views.switch_club, name="switch_club"),
]
