import logging
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from clubs.models import Club
from competitions.models import (
    ApplicationStateEnum,
    CompetitionApplication,
    CompetitionFeeTypeEnum,
    Season,
)
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q
from members.models import Member
from tournaments.models import MemberAtTournament, Tournament

from finance.clients.fakturoid import UnexpectedResponse, fakturoid_client
from finance.models import Invoice, InvoiceRelatedObject, InvoiceStateEnum, InvoiceTypeEnum

logger = logging.getLogger(__name__)


@dataclass
class SeasonFeeData:
    # Season fee
    amount: Decimal
    # List of tournaments with regular fee
    regular_tournaments: list[Tournament]
    # List of tournaments with discounted fee
    discounted_tournaments: list[Tournament]


class NoSubjectIdError(Exception):
    pass


def create_invoice_in_fakturoid_and_save_data(invoice: Invoice) -> None:
    if not invoice.club.fakturoid_subject_id:
        raise NoSubjectIdError

    try:
        data = fakturoid_client.create_invoice(
            subject_id=invoice.club.fakturoid_subject_id,
            lines=invoice.lines,
        )
    except UnexpectedResponse as ex:
        logger.error(f"Failed to create invoice in Fakturoid: {ex}")
    else:
        invoice.fakturoid_invoice_id = data["invoice_id"]
        invoice.fakturoid_total = data["total"]
        invoice.fakturoid_status = data["status"]
        invoice.fakturoid_public_html_url = data["public_html_url"]
        invoice.state = InvoiceStateEnum.OPEN
        invoice.save()


def create_invoice(
    club: Club,
    type_: InvoiceTypeEnum,
    lines: list[tuple[str, Decimal]],
    related_objects: list[Any] | None = None,
) -> Invoice:
    """
    Create an invoice in the system and send it to Fakturoid.
    """
    # For cases when we need to try to create invoice in Fakturoid again (after a failure)
    serialized_lines = [{"name": name, "unit_price": f"{amount:.2f}"} for name, amount in lines]
    original_amount = sum(amount for _, amount in lines)

    invoice = Invoice.objects.create(
        club=club,
        type=type_,
        original_amount=original_amount,
        lines=serialized_lines,
    )

    for related_object in related_objects or []:
        InvoiceRelatedObject.objects.create(
            invoice=invoice,
            content_type=ContentType.objects.get_for_model(related_object),
            object_id=related_object.id,
        )

    create_invoice_in_fakturoid_and_save_data(invoice)

    logger.info(
        "Created invoice %s for club %s with total %s", invoice.pk, club.name, invoice.amount
    )

    return invoice


@transaction.atomic
def create_deposit_invoice(club: Club) -> bool:
    """
    Create an invoice for all competition applications.
    Returns False if there were no applications with deposit > 0.
    """
    applications_qs = (
        CompetitionApplication.objects.filter(
            state=ApplicationStateEnum.AWAITING_PAYMENT,
            team__club=club.id,
            invoice__isnull=True,
            competition__deposit__gt=0,
        )
        .select_related("competition")
        .select_for_update()
    )

    applications = list(applications_qs)

    if applications:
        invoice = create_invoice(
            club,
            InvoiceTypeEnum.COMPETITION_DEPOSIT,
            lines=[
                (
                    f"{str(application.competition)} - Startovné za {application.team_name}",
                    application.competition.deposit,
                )
                for application in applications
            ],
            related_objects=applications,
        )
        applications_qs.update(invoice=invoice)
        return True
    else:
        return False


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
