from typing import Any

from competitions.models import Season
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
        # Set default season to the newest one if no initial value is provided
        if not self.initial.get("season"):
            newest_season = Season.objects.order_by("-name").first()
            if newest_season:
                self.initial["season"] = newest_season
