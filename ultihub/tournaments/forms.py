from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from members.models import MemberSexEnum

from tournaments.models import MemberAtTournament


class AddMemberToRosterForm(forms.Form):
    member_id = forms.IntegerField(widget=forms.HiddenInput())

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.tournament = kwargs.pop("tournament", None)
        self.member = kwargs.pop("member", None)
        super().__init__(*args, **kwargs)

    def clean(self) -> dict[str, Any] | None:
        cleaned_data = super().clean()

        if self.tournament:
            if self.tournament.rosters_deadline < timezone.now():
                raise ValidationError({"member_id": "The roster deadline has passed"})

            if self.member:
                if not self.member.has_email_confirmed:
                    raise ValidationError({"member_id": "Member has not confirmed email"})

                if (
                    self.member.sex == MemberSexEnum.MALE
                    and not self.tournament.competition.division.is_male_allowed
                ):
                    raise ValidationError({"member_id": "Men are not allowed in this division"})

                if (
                    self.member.sex == MemberSexEnum.FEMALE
                    and not self.tournament.competition.division.is_female_allowed
                ):
                    raise ValidationError({"member_id": "Women are not allowed in this division"})

                if roster_record := MemberAtTournament.objects.filter(
                    tournament_id=self.tournament.id, member_id=self.member.id
                ).first():
                    raise ValidationError(
                        {
                            "member_id": (
                                "Member is already in the roster: "
                                f"{roster_record.team_at_tournament.application.team_name}"
                            )
                        }
                    )

                if self.tournament.competition.age_limit:
                    if self.member.sex == MemberSexEnum.MALE and (
                        self.member.age < self.tournament.competition.age_limit.m_min
                        or self.member.age > self.tournament.competition.age_limit.m_max
                    ):
                        raise ValidationError(
                            {"member_id": "Member does not meet age requirements"}
                        )

                    if self.member.sex == MemberSexEnum.FEMALE and (
                        self.member.age < self.tournament.competition.age_limit.f_min
                        or self.member.age > self.tournament.competition.age_limit.f_max
                    ):
                        raise ValidationError(
                            {"member_id": "Member does not meet age requirements"}
                        )

                else:
                    if self.member.age < self.tournament.competition.season.min_allowed_age:
                        raise ValidationError(
                            {"member_id": "Member does not meet age requirements"}
                        )

        return cleaned_data


class UpdateMemberToRosterForm(forms.ModelForm):
    class Meta:
        model = MemberAtTournament
        fields = [
            "jersey_number",
            "is_captain",
            "is_spirit_captain",
            # "is_coach",
        ]

    def clean(self) -> dict[str, Any] | None:
        cleaned_data = super().clean()
        is_captain = cleaned_data.get("is_captain") if cleaned_data else None
        is_spirit_captain = cleaned_data.get("is_spirit_captain") if cleaned_data else None

        team_at_tournament = self.instance.team_at_tournament

        if is_captain:
            existing_captains = MemberAtTournament.objects.filter(
                team_at_tournament=team_at_tournament,
                is_captain=True,
            ).exclude(pk=self.instance.pk)
            if existing_captains.exists():
                raise ValidationError({"is_captain": "Team already has a captain."})

        if is_spirit_captain:
            existing_spirit_captains = MemberAtTournament.objects.filter(
                team_at_tournament=team_at_tournament,
                is_spirit_captain=True,
            ).exclude(pk=self.instance.pk)
            if existing_spirit_captains.exists():
                raise ValidationError({"is_spirit_captain": "Team already has a spirit captain."})

        return cleaned_data
