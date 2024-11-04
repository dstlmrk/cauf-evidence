from django.contrib import admin

from finance.models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("pk", "club__name", "state", "type", "amount")
    ordering = ("-created_at",)
