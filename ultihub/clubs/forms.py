from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from finance.clients.fakturoid import NotFoundError, fakturoid_client
from users.models import NewAgentRequest

from clubs.models import Club, Team


class ClubForm(forms.ModelForm):
    class Meta:
        model = Club
        fields = [
            "name",
            "email",
            "website",
            "city",
            "organization_name",
            "identification_number",
        ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["name"].disabled = True
        self.fields["organization_name"].disabled = True
        self.fields["identification_number"].disabled = True
        if self.instance.short_name:
            self.initial["name"] = f"{self.instance.name} ({self.instance.short_name})"

    def clean_name(self) -> str:
        return self.instance.name

    def clean_organization_name(self) -> str:
        return self.instance.organization_name

    def clean_identification_number(self) -> str:
        return self.instance.identification_number


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = [
            "name",
            "description",
        ]


class AddAgentForm(forms.Form):
    email = forms.EmailField(
        label=_("Email"),
        help_text=_("Requires an email that is linked to a Google Account."),
        max_length=48,
        required=True,
    )


class ClubAdminForm(forms.ModelForm):
    class Meta:
        model = Club
        fields = "__all__"  # noqa: DJ007
        widgets = {
            "fakturoid_subject_id": forms.TextInput(),
        }

    def clean_fakturoid_subject_id(self) -> Any | None:
        value = self.cleaned_data.get("fakturoid_subject_id")
        if value and (not self.instance.pk or value != self.instance.fakturoid_subject_id):
            try:
                subject_data = fakturoid_client.get_subject_detail(value)
                self.instance._fakturoid_subject_name = subject_data["name"]
            except NotFoundError as ex:
                raise ValidationError(
                    _("Subject with this ID does not exist in Fakturoid.")
                ) from ex
        return value


class CreateClubForm(ClubAdminForm):
    primary_agent_email = forms.EmailField(
        required=False,  # temporary solution
        help_text=_("Must be Google account"),
    )

    def clean(self) -> None:
        cleaned_data = super().clean()
        primary_agent_email = cleaned_data.get("primary_agent_email")  # type: ignore
        team_name = cleaned_data["name"]  # type: ignore
        if (
            primary_agent_email
            and NewAgentRequest.objects.filter(
                email=primary_agent_email,
                processed_at__isnull=True,
            ).exists()
        ):
            raise ValidationError(
                {"primary_agent_email": _("Agent with this email must log in first")},
            )
        if Team.objects.filter(name=team_name, is_active=True).exists():
            raise ValidationError(
                {"name": _("There is already an active team with this name")},
            )
