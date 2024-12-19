from django import forms

from tournaments.models import MemberAtTournament


class AddMemberToRosterForm(forms.Form):
    member_id = forms.IntegerField(widget=forms.HiddenInput())


class UpdateMemberToRosterForm(forms.ModelForm):
    class Meta:
        model = MemberAtTournament
        fields = [
            "jersey_number",
            "is_captain",
            "is_coach",
        ]
