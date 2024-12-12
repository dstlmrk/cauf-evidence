from django.contrib import admin
from users.services import assign_or_invite_agent_to_club

from clubs.forms import CreateClubForm
from clubs.models import Club, Team


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "organization_name", "identification_number")
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
