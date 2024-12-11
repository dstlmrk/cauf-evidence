from django.contrib import admin

from finance.models import Invoice, InvoiceRelatedObject


class InvoiceRelatedObjectInline(admin.TabularInline):
    model = InvoiceRelatedObject
    fields = ("content_type", "object_id", "related_object")
    readonly_fields = ("related_object",)
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("pk", "club__name", "state", "type", "amount")
    ordering = ("-created_at",)
    inlines = [InvoiceRelatedObjectInline]
