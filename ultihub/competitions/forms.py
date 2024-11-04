from typing import Any

from django import forms


class RegistrationForm(forms.Form):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        teams_with_applications = kwargs.pop("teams_with_applications", [])
        super().__init__(*args, **kwargs)
        for team in teams_with_applications:
            application = team.applications[0] if team.applications else None
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
