from django import forms

from users.models import Agent


class AgentForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = [
            "has_email_notifications_enabled",
            "has_guest_players_notifications_enabled",
            "has_roster_reminders_enabled",
        ]
