from django.urls import path

from finance import views

app_name = "finance"
urlpatterns = [
    path("invoices", views.invoices, name="invoices"),
]
