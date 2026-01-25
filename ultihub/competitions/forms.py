from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _


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
                    _("Registered: %(state)s") % {"state": application.get_state_display()}
                    if application
                    else _("Not registered")
                ),
                initial=bool(application),
                disabled=bool(application),
            )


class AddTeamsToTournamentForm(forms.Form):
    tournament = forms.ChoiceField(choices=[], label=_("Select tournament"))

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        related_tournaments = kwargs.pop("related_tournaments", [])
        super().__init__(*args, **kwargs)

        self.fields["tournament"].choices = [  # type: ignore
            (obj.id, f"{obj.name} ({obj.competition})") for obj in related_tournaments
        ]
