from typing import Any

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
