import logging
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from competitions.models import CompetitionApplication, CompetitionFeeTypeEnum, Season
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q, Sum
from members.models import Member
from tournaments.models import MemberAtTournament, Tournament

from finance.models import Invoice, InvoiceRelatedObject, InvoiceTypeEnum

logger = logging.getLogger(__name__)


@dataclass
class SeasonFeeData:
    # Season fee
    amount: Decimal
    # List of tournaments with regular fee
    regular_tournaments: list[Tournament]
    # List of tournaments with discounted fee
    discounted_tournaments: list[Tournament]


def create_invoice(
    club_id: int, amount: Decimal, type_: InvoiceTypeEnum, related_objects: list[Any] | None = None
) -> Invoice:
    invoice = Invoice.objects.create(club_id=club_id, amount=amount, type=type_)
    for related_object in related_objects or []:
        InvoiceRelatedObject.objects.create(
            invoice=invoice,
            content_type=ContentType.objects.get_for_model(related_object),
            object_id=related_object.id,
        )
    return invoice


@transaction.atomic
def create_deposit_invoice(club_id: int) -> None:
    """
    Create an invoice for the total deposit of all competition applications
    """
    applications_qs = (
        CompetitionApplication.objects.filter(
            team__club=club_id,
            invoice__isnull=True,
        )
        .select_related("competition")
        .select_for_update()
    )

    total_deposit = applications_qs.aggregate(
        total_deposit=Sum("competition__deposit"),
    )["total_deposit"]

    invoice = create_invoice(
        club_id,
        total_deposit,
        InvoiceTypeEnum.COMPETITION_DEPOSIT,
        related_objects=[application for application in applications_qs],
    )
    applications_qs.update(invoice=invoice)


def calculate_season_fees(
    season: Season, club_id: int | None = None
) -> dict[Member, SeasonFeeData]:
    fees: dict[Member, SeasonFeeData] = defaultdict(lambda: SeasonFeeData(Decimal(0), [], []))

    for amount, fee_type in [
        (season.discounted_fee, CompetitionFeeTypeEnum.DISCOUNTED),
        (season.regular_fee, CompetitionFeeTypeEnum.REGULAR),
    ]:
        members_at_tournaments = (
            MemberAtTournament.objects.filter(
                Q(tournament__competition__season=season),
                Q(tournament__competition__fee_type=fee_type),
                Q(member__club=club_id) if club_id else Q(),
            )
            .select_related("member")
            .prefetch_related("tournament__competition")
        )

        for member_at_tournament in members_at_tournaments:
            member = member_at_tournament.member
            fees[member].amount = amount
            getattr(fees[member], f"{fee_type.label.lower()}_tournaments").append(
                member_at_tournament.tournament
            )

    return fees
