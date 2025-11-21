from argparse import ArgumentParser
from decimal import Decimal
from typing import Any

from competitions.enums import CompetitionFeeTypeEnum
from competitions.models import Competition
from django.core.management.base import BaseCommand, CommandError
from members.models import Member
from tournaments.models import MemberAtTournament


class Command(BaseCommand):
    help = (
        "Calculate total season fees for members who participated only in a specific "
        "competition (and no other competitions in the same season)"
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--competition-id",
            type=int,
            required=True,
            help="ID of the competition to check",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        competition_id = options["competition_id"]

        try:
            competition = Competition.objects.select_related("season").get(id=competition_id)
        except Competition.DoesNotExist as err:
            raise CommandError(f"Competition with ID {competition_id} does not exist") from err

        season = competition.season

        self.stdout.write(f"Competition: {competition}")
        self.stdout.write(f"Season: {season}")
        self.stdout.write("=" * 60)

        members_in_target_competition = set(
            MemberAtTournament.objects.filter(tournament__competition=competition).values_list(
                "member_id", flat=True
            )
        )

        members_in_other_competitions = set(
            MemberAtTournament.objects.filter(tournament__competition__season=season)
            .exclude(tournament__competition=competition)
            .values_list("member_id", flat=True)
        )

        members_only_in_target = members_in_target_competition - members_in_other_competitions

        if not members_only_in_target:
            self.stdout.write("\nNo members found who participated only in this competition.")
            return

        members = (
            Member.objects.filter(id__in=members_only_in_target)
            .select_related("club")
            .order_by("last_name", "first_name")
        )

        fee_per_member = self._get_fee_for_competition(competition)
        total_fee = Decimal(0)

        self.stdout.write(f"\nMembers who participated only in '{competition.name}':\n")

        for i, member in enumerate(members, 1):
            self.stdout.write(
                f"  {i:3}. {member.last_name} {member.first_name} ({member.club.name})"
            )
            total_fee += fee_per_member

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(f"Total members: {len(members_only_in_target)}")
        self.stdout.write(
            f"Fee per member: {fee_per_member} CZK (fee_type: {competition.get_fee_type_display()})"
        )
        self.stdout.write(f"Total fees: {total_fee} CZK")

    def _get_fee_for_competition(self, competition: Competition) -> Decimal:
        if competition.fee_type == CompetitionFeeTypeEnum.REGULAR:
            return competition.season.regular_fee
        elif competition.fee_type == CompetitionFeeTypeEnum.DISCOUNTED:
            return competition.season.discounted_fee
        return Decimal(0)
