from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from users.models import NewAgentRequest

from clubs.models import Club, Member, Team


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


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = [
            "name",
            "description",
        ]


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            "first_name",
            "last_name",
            "birth_date",
            "sex",
            "citizenship",
            "birth_number",
            "address",
            "email",
            "default_jersey_number",
            "is_active",
        ]
        widgets = {
            "birth_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }


class MemberConfirmEmailForm(forms.Form):
    data_ok = forms.BooleanField(
        label="All information about me is correct",
        required=True,
        help_text=(
            "If not, please contact the club administrator, wait for"
            " the data to be corrected, and then reopen this link."
        ),
        initial=False,
    )
    basic_consent = forms.BooleanField(
        label="I agree to the processing of my personal data",
        required=True,
        initial=True,
    )
    marketing_consent = forms.BooleanField(
        label="I agree to receive newsletters and marketing materials",
        required=False,
        initial=True,
    )

    def __init__(self, *args: Any, member: Member | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if member and member.marketing_consent_given_at:
            self.fields.pop("marketing_consent")


class AddAgentForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        help_text="Requires an email that is linked to a Google Account.",
        max_length=48,
        required=True,
    )


class CreateClubForm(forms.ModelForm):
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

    class Meta:
        model = Club
        fields = (
            "name",
            "email",
            "website",
            "city",
            "organization_name",
            "identification_number",
            "primary_agent_email",
        )
