from typing import Any

from competitions.models import Season
from core.helpers import get_default_season
from django import forms


class SeasonFeesCheckForm(forms.Form):
    season = forms.ModelChoiceField(
        queryset=Season.objects.all(),
        label="Season",
        empty_label="Choose a season",
        widget=forms.Select(attrs={"class": "form-control"}),
        help_text="Select a season to calculate fees for.",
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if not self.initial.get("season"):
            default_season = get_default_season("competition")
            if default_season:
                self.initial["season"] = default_season
