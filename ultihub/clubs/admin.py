from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from users.services import assign_or_invite_agent_to_club

from clubs.forms import CreateClubForm
from clubs.models import Club, ClubNotification, Team


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name", "city", "organization_name", "identification_number")
    ordering = ("name",)
    add_form = CreateClubForm

    def get_form(self, request, obj=None, **kwargs):  # type: ignore
        if obj is None:
            kwargs["form"] = self.add_form
        return super().get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):  # type: ignore
        if change:
            super().save_model(request, obj, form, change)
        else:
            super().save_model(request, obj, form, change)
            Team.objects.create(club=obj, is_primary=True, name=obj.name)
            Team.objects.create(club=obj, name=f"{obj.name} B")
            if primary_agent_email := form.cleaned_data.get("primary_agent_email"):
                assign_or_invite_agent_to_club(
                    club=obj,
                    is_primary=True,
                    email=primary_agent_email,
                    invited_by=request.user,
                )


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "club__name", "is_primary", "is_active")


@admin.register(ClubNotification)
class ClubNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "subject",
        "message",
        "is_read",
        "agent_at_club__agent__user__email",
        "agent_at_club__club__name",
    )
    list_display_links = ("subject",)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request)
        qs = qs.select_related(
            "agent_at_club",
            "agent_at_club__agent",
            "agent_at_club__agent__user",
            "agent_at_club__club",
        )
        return qs
