from django.contrib import admin
from users.services import assign_or_invite_agent_to_club

from clubs.forms import CreateClubForm
from clubs.models import Club, Organization, Team


class OrganizationInline(admin.StackedInline):
    model = Organization
    can_delete = False
    min_num = 1
    readonly_fields = ("country",)
    fieldsets = (
        (
            None,
            {
                "description": "The following fields pertain to organization information.",
                "fields": (
                    "name",
                    "identification_number",
                    "account_number",
                    "bank_code",
                    "street",
                    "city",
                    "postal_code",
                    "country",
                ),
            },
        ),
    )


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "email")
    ordering = ("name",)
    inlines = (OrganizationInline,)
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
            Team.objects.create(
                club=obj,
                is_primary=True,
                name=obj.name,
            )
            assign_or_invite_agent_to_club(
                club=obj,
                is_primary=True,
                email=form.cleaned_data["primary_agent_email"],
                invited_by=request.user,
            )
