from django.urls import path

from finance import views

app_name = "finance"
urlpatterns = [
    path("invoices", views.invoices, name="invoices"),
    path("seasonal-fees-list", views.seasonal_fees_list_view, name="seasonal_fees_list"),
]
