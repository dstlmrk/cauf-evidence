from typing import Any

from clients.fakturoid import NotFoundError, fakturoid_client
from django import forms
from django.core.exceptions import ValidationError
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
        if self.instance.short_name:
            self.initial["name"] = f"{self.instance.name} ({self.instance.short_name})"  # type: ignore


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = [
            "name",
            "description",
        ]


class AddAgentForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        help_text="Requires an email that is linked to a Google Account.",
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
                fakturoid_client.get_subject_detail(value)
            except NotFoundError as ex:
                raise ValidationError("Subject with this ID does not exist in Fakturoid.") from ex
        return value


class CreateClubForm(ClubAdminForm):
    primary_agent_email = forms.EmailField(
        required=False,  # temporary solution
        help_text="Must be Google account",
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
                {"primary_agent_email": "Agent with this email must log in first"},
            )
        if Team.objects.filter(name=team_name, is_active=True).exists():
            raise ValidationError(
                {"name": "There is already an active team with this name"},
            )
