from typing import Any

from django.contrib import admin
from django.http import HttpRequest
from guardian.admin import GuardedModelAdmin

from users.models import Agent, NewAgentRequest


@admin.register(NewAgentRequest)
class NewAgentRequestAdmin(admin.ModelAdmin):
    list_display = ("email", "is_staff", "is_superuser", "created_at", "processed_at")
    search_fields = ("email",)
    list_filter = ("is_staff",)
    ordering = ("-created_at",)

    def get_readonly_fields(self, request: HttpRequest, obj: Any | None = None) -> tuple:
        fields = tuple(super().get_readonly_fields(request, obj))
        if obj:
            return ("email", "is_staff", "is_superuser", "processed_at") + fields
        else:
            return fields


@admin.register(Agent)
class AgentAdmin(GuardedModelAdmin):
    list_display = ("user__email",)
    search_fields = ("user__email",)
    ordering = ("-pk",)
