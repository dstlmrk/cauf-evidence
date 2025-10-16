from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from users.services import assign_or_invite_agent_to_club

from clubs.forms import ClubAdminForm, CreateClubForm
from clubs.models import Club, ClubNotification, Team


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "short_name",
        "city",
        "organization_name",
        "identification_number",
        "fakturoid_subject_id",
    )
    ordering = ("name",)

    def get_form(self, request, obj=None, **kwargs):  # type: ignore
        kwargs["form"] = CreateClubForm if obj is None else ClubAdminForm
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
        if hasattr(obj, "_fakturoid_subject_name"):
            msg = f'The club was paired with "{obj._fakturoid_subject_name}" in Fakturoid'
            self.message_user(request, msg, messages.SUCCESS)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "club__name", "is_primary", "is_active")
    ordering = ("club__name", "name")
    search_fields = ("name", "club__name")


@admin.register(ClubNotification)
class ClubNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "subject",
        "message",
        "is_read",
        "agent_at_club__agent__user__email",
        "agent_at_club__club__name",
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request)
        qs = qs.select_related(
            "agent_at_club",
            "agent_at_club__agent",
            "agent_at_club__agent__user",
            "agent_at_club__club",
        )
        return qs
