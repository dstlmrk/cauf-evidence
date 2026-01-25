from typing import Any

from core.helpers import get_app_settings
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from members.models import Member, MemberSexEnum

from tournaments.models import MemberAtTournament


class AddMemberToRosterForm(forms.Form):
    member_id = forms.IntegerField(widget=forms.HiddenInput())

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.team_at_tournament = kwargs.pop("team_at_tournament", None)
        self.validated_member: Member | None = None  # Store validated member to avoid re-fetching
        super().__init__(*args, **kwargs)

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        if cleaned_data is None:
            return {}

        app_settings = get_app_settings()

        if self.team_at_tournament and cleaned_data.get("member_id"):
            tournament = self.team_at_tournament.tournament
            if tournament.rosters_deadline < timezone.now():
                raise ValidationError({"member_id": _("The roster deadline has passed")})

            # Load member with age annotation for efficient age validation
            member = (
                Member.objects.get_queryset()
                .annotate_age(tournament.competition.season.age_reference_date)
                .get(pk=cleaned_data["member_id"])
            )

            # Store for later use to avoid re-fetching
            self.validated_member = member

            if member:
                if app_settings.email_verification_required and not member.has_email_confirmed:
                    raise ValidationError({"member_id": _("Member has not confirmed email")})

                if (
                    member.sex == MemberSexEnum.MALE
                    and not tournament.competition.division.is_male_allowed
                ):
                    raise ValidationError({"member_id": _("Men are not allowed in this division")})

                if (
                    member.sex == MemberSexEnum.FEMALE
                    and not tournament.competition.division.is_female_allowed
                ):
                    raise ValidationError(
                        {"member_id": _("Women are not allowed in this division")}
                    )

                if roster_record := MemberAtTournament.objects.filter(
                    tournament_id=tournament.id, member_id=member.id
                ).first():
                    raise ValidationError(
                        {
                            "member_id": _("Member is already in the roster: %(team_name)s")
                            % {"team_name": roster_record.team_at_tournament.application.team_name}
                        }
                    )

                if tournament.competition.age_limit:
                    if member.sex == MemberSexEnum.MALE and (
                        (
                            app_settings.min_age_verification_required
                            and member.age < tournament.competition.age_limit.m_min
                        )
                        or member.age > tournament.competition.age_limit.m_max
                    ):
                        raise ValidationError(
                            {"member_id": _("Member does not meet age requirements")}
                        )

                    if member.sex == MemberSexEnum.FEMALE and (
                        (
                            app_settings.min_age_verification_required
                            and member.age < tournament.competition.age_limit.f_min
                        )
                        or member.age > tournament.competition.age_limit.f_max
                    ):
                        raise ValidationError(
                            {"member_id": _("Member does not meet age requirements")}
                        )

                else:
                    if (
                        app_settings.min_age_verification_required
                        and member.age < tournament.competition.season.min_allowed_age
                    ):
                        raise ValidationError(
                            {"member_id": _("Member does not meet age requirements")}
                        )

                # Check nationality ratio (minimum 51% Czech citizens)
                current_roster = MemberAtTournament.objects.filter(
                    team_at_tournament=self.team_at_tournament
                ).select_related("member")

                # Count current nationality split
                czech_count = sum(1 for mat in current_roster if mat.member.citizenship == "CZ")
                foreign_count = len(current_roster) - czech_count

                # Add the new member to counts
                if member.citizenship == "CZ":
                    czech_count += 1
                else:
                    foreign_count += 1

                total_count = czech_count + foreign_count

                # Check ratio (minimum 51% Czech citizens)
                if total_count > 0:
                    czech_percentage = (czech_count / total_count) * 100
                    if czech_percentage < 51:
                        msg = _("Nationality ratio: at least 51% must be Czech citizens")
                        raise ValidationError({"member_id": msg})

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
                raise ValidationError({"is_captain": _("Team already has a captain.")})

        if is_spirit_captain:
            existing_spirit_captains = MemberAtTournament.objects.filter(
                team_at_tournament=team_at_tournament,
                is_spirit_captain=True,
            ).exclude(pk=self.instance.pk)
            if existing_spirit_captains.exists():
                raise ValidationError(
                    {"is_spirit_captain": _("Team already has a spirit captain.")}
                )

        return cleaned_data
