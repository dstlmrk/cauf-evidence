from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from users.models import NewAgentRequest

from clubs.models import Club, Organization, Team


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = [
            "name",
            "identification_number",
            "street",
            "city",
            "postal_code",
            "country",
        ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["country"].disabled = True


class ClubForm(forms.ModelForm):
    class Meta:
        model = Club
        fields = [
            "name",
            "email",
            "website",
            "city",
        ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["name"].disabled = True


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


class CreateClubForm(forms.ModelForm):
    primary_agent_email = forms.EmailField(
        required=True,
        help_text="Must be Google account",
    )

    def clean(self) -> None:
        cleaned_data = super().clean()
        if NewAgentRequest.objects.filter(
            email=cleaned_data.get("primary_agent_email"),  # type: ignore
            processed_at__isnull=True,
        ).exists():
            raise ValidationError(
                {"primary_agent_email": "Agent with this email must log in first"}
            )

    class Meta:
        model = Club
        fields = ("name", "email", "website", "city", "primary_agent_email")
