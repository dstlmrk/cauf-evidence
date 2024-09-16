from django.contrib import admin
from django.http import HttpRequest

from users.models import NewAgentRequest


class BaseAdmin(admin.ModelAdmin):
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(NewAgentRequest)
class NewAgentRequestAdmin(BaseAdmin):
    list_display = ("email", "is_staff", "is_superuser", "created_at", "processed_at")
    search_fields = ("email",)
    list_filter = ("is_staff",)
    ordering = ("-created_at",)

    def get_readonly_fields(self, request: HttpRequest, obj=None) -> tuple:  # type: ignore
        fields = tuple(super().get_readonly_fields(request, obj))
        if obj:
            return ("email", "is_staff", "is_superuser", "processed_at") + fields
        else:
            return fields
