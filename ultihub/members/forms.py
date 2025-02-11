from typing import Any

from clubs.models import Club
from core.helpers import SessionClub
from django import forms

from members.models import Member


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
            "street",
            "city",
            "house_number",
            "postal_code",
            "email",
            "default_jersey_number",
            "is_active",
        ]
        widgets = {
            "birth_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["birth_number"].label = "Birth number*"
        self.fields["birth_number"].help_text = ""
        self.fields["email"].required = True

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean() or {}
        if cleaned_data.get("citizenship") == "CZ":
            if not cleaned_data.get("birth_number"):
                self.add_error("birth_number", "This field is required for Czech citizens.")
        else:
            city = cleaned_data.get("city")
            house_number = cleaned_data.get("house_number")
            postal_code = cleaned_data.get("postal_code")
            if city or house_number or postal_code:
                error_msg = "This field is required if an address is provided."
                if not city:
                    self.add_error("city", error_msg)
                if not house_number:
                    self.add_error("house_number", error_msg)
                if not postal_code:
                    self.add_error("postal_code", error_msg)
        return cleaned_data


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


class TransferRequestForm(forms.Form):
    member_id = forms.IntegerField(widget=forms.HiddenInput())
    source_club = forms.ChoiceField(
        required=True,
        disabled=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    target_club = forms.ChoiceField(
        choices=[],
        required=True,
        disabled=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class TransferRequestFromMyClubForm(TransferRequestForm):
    def __init__(self, *args: Any, member: Member, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["member_id"].initial = member.id
        self.fields["source_club"].choices = [(member.club.id, member.club.name)]  # type: ignore
        self.fields["source_club"].initial = member.club.id
        self.fields["target_club"].disabled = False
        self.fields["target_club"].choices = [  # type: ignore
            (club.id, club.name) for club in Club.objects.exclude(id=member.club.id)
        ]


class TransferRequestToMyClubForm(TransferRequestForm):
    def __init__(
        self, *args: Any, member: Member, current_club: SessionClub, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.fields["member_id"].initial = member.id
        self.fields["source_club"].choices = [(member.club.id, member.club.name)]  # type: ignore
        self.fields["source_club"].initial = member.club.id
        self.fields["target_club"].choices = [(current_club.id, current_club.name)]  # type: ignore
        self.fields["target_club"].initial = current_club.id
