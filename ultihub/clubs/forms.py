from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from finance.clients.fakturoid import NotFoundError, fakturoid_client
from users.models import NewAgentRequest

from clubs.models import Club, Team
from clubs.services import (
    LOGO_ALLOWED_FORMATS,
    LOGO_MAX_ASPECT_RATIO,
    LOGO_MAX_BYTES,
    LOGO_MIN_SIZE,
)


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


LOGO_HELP_TEXT = f"Square PNG, JPEG or WebP, at least {LOGO_MIN_SIZE}x{LOGO_MIN_SIZE} px."


def validate_logo_image(logo: UploadedFile) -> UploadedFile:
    if logo.size and logo.size > LOGO_MAX_BYTES:
        raise ValidationError(f"The file is larger than {LOGO_MAX_BYTES // 1024 // 1024} MB.")

    if logo.image.format not in LOGO_ALLOWED_FORMATS:  # type: ignore[attr-defined]
        raise ValidationError("Only PNG, JPEG and WebP images are supported.")

    width, height = logo.image.size  # type: ignore[attr-defined]
    if min(width, height) < LOGO_MIN_SIZE:
        raise ValidationError(
            f"The image is only {min(width, height)} px on its shorter side,"
            f" at least {LOGO_MIN_SIZE} px is required."
        )

    if max(width, height) / min(width, height) > LOGO_MAX_ASPECT_RATIO:
        raise ValidationError(
            f"The image is {width}x{height} px. Crop it to a square before uploading it."
        )

    return logo


class ClubLogoForm(forms.Form):
    logo = forms.ImageField(label="New logo", help_text=LOGO_HELP_TEXT)

    def clean_logo(self) -> UploadedFile:
        return validate_logo_image(self.cleaned_data["logo"])


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
    logo = forms.ImageField(
        required=False,
        label="Replace logo",
        help_text=f"Takes effect immediately, without approval. {LOGO_HELP_TEXT}",
    )
    remove_logo = forms.BooleanField(
        required=False,
        label="Remove logo",
        help_text="Drops the logo in use as well as anything the club has waiting for approval",
    )

    class Meta:
        model = Club
        fields = "__all__"  # noqa: DJ007
        widgets = {
            "fakturoid_subject_id": forms.TextInput(),
        }

    def clean_logo(self) -> UploadedFile | None:
        logo = self.cleaned_data.get("logo")
        return validate_logo_image(logo) if logo else None

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean() or {}
        if cleaned_data.get("logo") and cleaned_data.get("remove_logo"):
            raise ValidationError(
                {"remove_logo": "Either replace the logo or remove it, not both at once."}
            )
        return cleaned_data

    def clean_fakturoid_subject_id(self) -> Any | None:
        value = self.cleaned_data.get("fakturoid_subject_id")
        if value and (not self.instance.pk or value != self.instance.fakturoid_subject_id):
            try:
                subject_data = fakturoid_client.get_subject_detail(value)
                self.instance._fakturoid_subject_name = subject_data["name"]
            except NotFoundError as ex:
                raise ValidationError("Subject with this ID does not exist in Fakturoid.") from ex
        return value


class CreateClubForm(ClubAdminForm):
    primary_agent_email = forms.EmailField(
        required=False,  # temporary solution
        help_text="Must be Google account",
    )

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        primary_agent_email = cleaned_data.get("primary_agent_email")
        team_name = cleaned_data["name"]
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
        return cleaned_data
