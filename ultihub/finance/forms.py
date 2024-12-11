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
