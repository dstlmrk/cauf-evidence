from core.admin import AuditlogMixin
from django.contrib import admin, messages
from django.db.models import Prefetch, QuerySet
from django.http import HttpRequest
from django.utils.html import format_html
from users.services import assign_or_invite_agent_to_club

from clubs.forms import ClubAdminForm, CreateClubForm
from clubs.models import Club, ClubLogo, ClubNotification, Team
from clubs.services import (
    approve_club_logo,
    reject_club_logo,
    remove_club_logo,
    save_club_logo,
)


@admin.register(Club)
class ClubAdmin(AuditlogMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "logo_preview",
        "name",
        "short_name",
        "city",
        "organization_name",
        "identification_number",
        "fakturoid_subject_id",
    )
    ordering = ("name",)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                Prefetch(
                    "logos",
                    queryset=ClubLogo.objects.filter(is_approved=True).only("club", "small"),
                    to_attr="approved_logos",
                )
            )
        )

    @admin.display(description="Logo")
    def logo_preview(self, obj: Club) -> str:
        if not obj.approved_logos:  # type: ignore[attr-defined]
            return "—"
        return format_html(
            '<img src="{}" style="height: 2rem; width: 2rem; object-fit: contain;" />',
            obj.approved_logos[0].small_data_uri,  # type: ignore[attr-defined]
        )

    def get_form(self, request, obj=None, **kwargs):  # type: ignore
        kwargs["form"] = CreateClubForm if obj is None else ClubAdminForm
        return super().get_form(request, obj, **kwargs)

    def get_fields(self, request, obj=None):  # type: ignore
        fields = list(super().get_fields(request, obj))
        if obj is None or not obj.logos.exists():
            fields.remove("remove_logo")
        return fields

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
        if form.cleaned_data.get("remove_logo"):
            remove_club_logo(obj)
            self.message_user(request, "The club logo was removed.", messages.SUCCESS)
        elif uploaded_logo := form.cleaned_data.get("logo"):
            approve_club_logo(
                save_club_logo(obj, uploaded_logo),
                approved_by=getattr(request.user, "agent", None),
            )
            self.message_user(request, "The club logo was replaced.", messages.SUCCESS)

        if hasattr(obj, "_fakturoid_subject_name"):
            msg = f'The club was paired with "{obj._fakturoid_subject_name}" in Fakturoid'
            self.message_user(request, msg, messages.SUCCESS)


@admin.register(ClubLogo)
class ClubLogoAdmin(admin.ModelAdmin):
    list_display = ("id", "preview", "club", "is_approved", "created_at", "approved_at")
    list_filter = ("is_approved",)
    search_fields = ("club__name", "club__short_name")
    # Logos waiting for approval first, they are the ones that need attention
    ordering = ("is_approved", "created_at")
    actions = ("approve_logos", "reject_logos")
    readonly_fields = ("preview", "club", "is_approved", "approved_at", "approved_by")
    fields = readonly_fields

    def has_add_permission(self, request: HttpRequest) -> bool:
        # Logos are uploaded by the club, or through the club detail page
        return False

    @admin.display(description="Preview")
    def preview(self, obj: ClubLogo) -> str:
        return format_html(
            '<img src="{}" style="height: 5rem; width: 5rem; object-fit: contain;" />',
            obj.large_data_uri,
        )

    @admin.display(description="Approve selected logos")
    def approve_logos(self, request: HttpRequest, queryset: QuerySet) -> None:
        approved_by = getattr(request.user, "agent", None)
        for logo in queryset.filter(is_approved=False):
            approve_club_logo(logo, approved_by=approved_by)
        self.message_user(request, "The selected logos were approved.", messages.SUCCESS)

    @admin.display(description="Reject selected logos")
    def reject_logos(self, request: HttpRequest, queryset: QuerySet) -> None:
        for logo in queryset:
            reject_club_logo(logo)
        self.message_user(request, "The selected logos were rejected.", messages.SUCCESS)


@admin.register(Team)
class TeamAdmin(AuditlogMixin, admin.ModelAdmin):
    list_display = ("id", "name", "club__name", "is_primary", "is_active")
    ordering = ("club__name", "name")
    search_fields = ("name", "club__name")


@admin.register(ClubNotification)
class ClubNotificationAdmin(AuditlogMixin, admin.ModelAdmin):
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
