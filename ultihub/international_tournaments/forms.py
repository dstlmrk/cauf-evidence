from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from members.models import Member

from international_tournaments.models import MemberAtInternationalTournament


class AddMemberToInternationalRosterForm(forms.Form):
    member_id = forms.IntegerField(widget=forms.HiddenInput())

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.team_at_tournament = kwargs.pop("team_at_tournament", None)
        self.validated_member: Member | None = None  # Store validated member to avoid re-fetching
        super().__init__(*args, **kwargs)

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        if cleaned_data is None:
            return {}

        if self.team_at_tournament and cleaned_data.get("member_id"):
            tournament = self.team_at_tournament.tournament

            try:
                member = Member.objects.get(pk=cleaned_data["member_id"])
            except Member.DoesNotExist as err:
                raise ValidationError({"member_id": "Member not found"}) from err

            # Store for later use to avoid re-fetching
            self.validated_member = member

            # Check if member is already in this team at this tournament
            if MemberAtInternationalTournament.objects.filter(
                team_at_tournament=self.team_at_tournament, member=member
            ).exists():
                raise ValidationError({"member_id": "Member is already in this team roster"})

            # Check if member is already in another team at this tournament
            if roster_record := MemberAtInternationalTournament.objects.filter(
                tournament=tournament, member=member
            ).first():
                raise ValidationError(
                    {
                        "member_id": (
                            "Member is already in another team at this tournament: "
                            f"{roster_record.team_at_tournament.team_name}"
                        )
                    }
                )

        return cleaned_data


class UpdateMemberToInternationalRosterForm(forms.ModelForm):
    class Meta:
        model = MemberAtInternationalTournament
        fields = [
            "jersey_number",
            "is_captain",
            "is_spirit_captain",
            "is_coach",
        ]

    def clean(self) -> dict[str, Any] | None:
        cleaned_data = super().clean()
        is_captain = cleaned_data.get("is_captain") if cleaned_data else None
        is_spirit_captain = cleaned_data.get("is_spirit_captain") if cleaned_data else None
        jersey_number = cleaned_data.get("jersey_number") if cleaned_data else None

        team_at_tournament = self.instance.team_at_tournament

        if is_captain:
            existing_captains = MemberAtInternationalTournament.objects.filter(
                team_at_tournament=team_at_tournament,
                is_captain=True,
            ).exclude(pk=self.instance.pk)
            if existing_captains.exists():
                raise ValidationError({"is_captain": "Team already has a captain."})

        if is_spirit_captain:
            existing_spirit_captains = MemberAtInternationalTournament.objects.filter(
                team_at_tournament=team_at_tournament,
                is_spirit_captain=True,
            ).exclude(pk=self.instance.pk)
            if existing_spirit_captains.exists():
                raise ValidationError({"is_spirit_captain": "Team already has a spirit captain."})

        if jersey_number is not None:
            existing_jersey = MemberAtInternationalTournament.objects.filter(
                team_at_tournament=team_at_tournament,
                jersey_number=jersey_number,
            ).exclude(pk=self.instance.pk)
            if existing_jersey.exists():
                raise ValidationError(
                    {"jersey_number": f"Another player already has jersey number {jersey_number}."}
                )

        return cleaned_data
