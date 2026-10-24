from typing import Any

from django import forms
from django.db.models import QuerySet
from tournaments.models import MemberAtTournament

from competitions.models import Season


class RegistrationForm(forms.Form):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        teams_with_applications = kwargs.pop("teams_with_applications", [])
        super().__init__(*args, **kwargs)
        for team in teams_with_applications:
            application = team.prefetched_applications[0] if team.prefetched_applications else None
            self.fields[f"team_{team.pk}"] = forms.BooleanField(
                label=application.team_name if application else team.name,
                required=False,
                help_text=(
                    f"Registered: {application.get_state_display()}"
                    if application
                    else "Not registered"
                ),
                initial=bool(application),
                disabled=bool(application),
            )


class AddTeamsToTournamentForm(forms.Form):
    tournament = forms.ChoiceField(choices=[], label="Select tournament")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        related_tournaments = kwargs.pop("related_tournaments", [])
        super().__init__(*args, **kwargs)

        self.fields["tournament"].choices = [  # type: ignore
            (obj.id, f"{obj.name} ({obj.competition})") for obj in related_tournaments
        ]


class SeasonChangeConfirmForm(forms.ModelForm):
    """
    Issued season invoices are never recalculated, so moving played rosters into or out of
    an invoiced season has to be confirmed explicitly.
    """

    confirm_season_change = forms.BooleanField(
        required=False,
        label="Confirm season change",
        help_text=(
            "Required when rosters are moved into or out of a season"
            " whose invoices have already been generated."
        ),
    )

    def validate_season_change(
        self, old_season: Season, new_season: Season | None, rosters: QuerySet
    ) -> None:
        if new_season is None or new_season == old_season:
            return
        invoiced = [
            season.name for season in (old_season, new_season) if season.invoices_generated_at
        ]
        if invoiced and rosters.exists() and not self.cleaned_data.get("confirm_season_change"):
            self.add_error(
                "confirm_season_change",
                f"Invoices for season {' and '.join(invoiced)} have already been generated."
                " Moving the rosters changes which season their fees belong to,"
                " but the issued invoices will not be recalculated.",
            )


class CompetitionAdminForm(SeasonChangeConfirmForm):
    def clean(self) -> dict[str, Any] | None:
        cleaned_data = super().clean()
        if self.instance.pk:
            self.validate_season_change(
                self.instance.season,
                self.cleaned_data.get("season"),
                MemberAtTournament.objects.filter(tournament__competition=self.instance),
            )
        return cleaned_data
