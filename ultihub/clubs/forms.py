from typing import Any

from django import forms

from clubs.models import Club, Organization


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = [
            "name",
            "identification_number",
            "account_number",
            "bank_code",
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
