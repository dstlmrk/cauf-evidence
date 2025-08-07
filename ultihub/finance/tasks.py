import logging
from datetime import timedelta
from decimal import Decimal

from clubs.models import Club
from clubs.service import notify_club
from competitions.models import ApplicationStateEnum, CompetitionApplication, Season
from core.helpers import create_csv
from core.tasks import send_email
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone
from huey import crontab
from huey.contrib.djhuey import db_periodic_task, db_task

from finance.clients.fakturoid import InvoiceStatus, fakturoid_client
from finance.models import Invoice, InvoiceStateEnum, InvoiceTypeEnum
from finance.services import (
    calculate_season_fees,
    create_invoice,
    create_invoice_in_fakturoid_and_save_data,
)

logger = logging.getLogger(__name__)


@transaction.atomic
def _update_invoice(invoice: Invoice, status: InvoiceStatus, total: Decimal) -> None:
    if invoice.fakturoid_status != status:
        invoice.fakturoid_status = status

        if status == "paid":
            invoice.state = InvoiceStateEnum.PAID

            if invoice.type == InvoiceTypeEnum.COMPETITION_DEPOSIT:
                CompetitionApplication.objects.filter(
                    id__in=invoice.related_objects.filter(
                        content_type_id=ContentType.objects.get_for_model(CompetitionApplication).id
                    ).values_list("object_id", flat=True),
                    state=ApplicationStateEnum.AWAITING_PAYMENT,
                ).update(state=ApplicationStateEnum.PAID)
            logger.info("Invoice %s was paid", invoice.id)

        elif status in ("cancelled", "uncollectible"):
            invoice.state = InvoiceStateEnum.CANCELED
            logger.info("Invoice %s was canceled", invoice.id)

    if invoice.fakturoid_total != total:
        invoice.fakturoid_total = total
        logger.info("Invoice %s total was updated to %s", invoice.id, total)

    invoice.save()


@db_periodic_task(crontab(minute="0", hour="5,17"))
def check_fakturoid_invoices() -> None:
    """
    Periodic task to check invoices in Fakturoid.
    """
    logger.info("Start regular check of invoices in Fakturoid")

    for invoice in Invoice.objects.filter(
        state=InvoiceStateEnum.OPEN,
        created_at__gte=timezone.now() - timedelta(days=180),
    ):
        status, total = fakturoid_client.get_invoice_status_and_total(
            invoice_id=invoice.fakturoid_invoice_id  # type: ignore
        )
        if status in ("paid", "cancelled", "uncollectible") or invoice.fakturoid_total != total:
            _update_invoice(invoice, status, total)

    logger.info("End regular check of invoices in Fakturoid")


@db_periodic_task(crontab(minute="*/15", hour="*"))
def resend_invoices_to_fakturoid() -> None:
    logger.info("Start trying to resend invoices to Fakturoid")

    for invoice in Invoice.objects.filter(
        state=InvoiceStateEnum.DRAFT,
        created_at__lte=timezone.now() - timedelta(seconds=60),
    ):
        create_invoice_in_fakturoid_and_save_data(invoice)

    logger.info("End trying to resend invoices to Fakturoid")


@db_task()
@transaction.atomic()
def calculate_season_fees_for_check(user: User, season: Season) -> None:
    logger.info(f"Calculating fees (check) for season {season.name}")

    fees = calculate_season_fees(season)

    csv_data = create_csv(
        header=["Member", "Club", "Amount", "Regular tournaments", "Discounted tournaments"],
        data=[
            [
                member.full_name,
                member.club.name,
                data.amount,
                ", ".join(str(tournament.id) for tournament in data.regular_tournaments),
                ", ".join(str(tournament.id) for tournament in data.discounted_tournaments),
            ]
            for member, data in fees.items()
        ],
    )

    send_email(
        "Fees calculation for check",
        (
            f"Hi. We have calculated fees for the season {season.name}."
            " Please check the attached CSV file."
        ),
        [user.email],
        csv_data=csv_data,
    )


@db_task()
@transaction.atomic()
def calculate_season_fees_and_generate_invoices(season: Season) -> None:
    logger.info(f"Calculating fees (hot) for season {season.name}")
    clubs_to_notification = []

    for club in Club.objects.filter(fakturoid_subject_id__isnull=False):
        fees = calculate_season_fees(season, club.id)
        total_amount = Decimal(sum([fee.amount for fee in fees.values()]))
        if total_amount > 0:
            create_invoice(
                club,
                InvoiceTypeEnum.SEASON_PLAYER_FEES,
                [(f"Poplatky za sezónu {season.name}", total_amount)],
                related_objects=[season],
            )
            clubs_to_notification.append(club)

    season.invoices_generated_at = timezone.now()
    season.save()

    for club in clubs_to_notification:
        notify_club(
            club=club,
            subject="Season fees generated",
            message=(
                f"Season fees for the season <b>{season.name}</b>"
                " have been generated. Check your invoices."
            ),
        )
