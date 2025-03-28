from django.urls import path

from finance import views

app_name = "finance"
urlpatterns = [
    path("invoices", views.invoices, name="invoices"),
    path("season-fees-list", views.season_fees_list_view, name="season_fees_list"),
]
