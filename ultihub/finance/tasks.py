import logging
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from clubs.models import Club
from clubs.service import notify_club
from competitions.models import ApplicationStateEnum, CompetitionApplication, Season
from core.helpers import create_csv
from core.tasks import send_email
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from huey import crontab
from huey.contrib.djhuey import db_periodic_task, db_task

from finance.clients.fakturoid import InvoiceDetails, fakturoid_client
from finance.models import Invoice, InvoiceStateEnum, InvoiceTypeEnum
from finance.services import (
    calculate_season_fees,
    create_invoice,
    create_invoice_in_fakturoid_and_save_data,
)

logger = logging.getLogger(__name__)


@transaction.atomic
def _update_invoice(invoice: Invoice, details: InvoiceDetails) -> None:
    status = details["status"]
    total = details["total"]
    due_on = details["due_on"]

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

    if due_on and invoice.fakturoid_due_on != due_on:
        invoice.fakturoid_due_on = due_on
        logger.info("Invoice %s due_on was updated to %s", invoice.id, due_on)

    invoice.save()


@db_periodic_task(crontab(minute="0", hour="5,17"))
def check_fakturoid_invoices() -> None:
    """
    Periodic task to check invoices in Fakturoid.
    Syncs status, total, and due_on from Fakturoid.
    """
    logger.info("Start regular check of invoices in Fakturoid")

    for invoice in Invoice.objects.filter(
        state=InvoiceStateEnum.OPEN,
        created_at__gte=timezone.now() - timedelta(days=180),
    ):
        details = fakturoid_client.get_invoice_details(
            invoice_id=invoice.fakturoid_invoice_id  # type: ignore
        )
        status = details["status"]
        if (
            status in ("paid", "cancelled", "uncollectible")
            or invoice.fakturoid_total != details["total"]
            or invoice.fakturoid_due_on != details["due_on"]
        ):
            _update_invoice(invoice, details)

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
@transaction.atomic
def calculate_season_fees_and_generate_invoices(
    season: Season, dry_run: bool = False, dry_run_user: User | None = None
) -> None:
    """
    Generate invoices for season fees.

    Args:
        season: The season to generate invoices for
        dry_run: If True, only simulate and send preview email (no DB changes)
        dry_run_user: Required when dry_run=True, user to send preview email to
    """
    if dry_run and dry_run_user is None:
        raise ValueError("dry_run_user is required when dry_run=True")

    logger.info(f"Calculating fees ({'dry-run' if dry_run else 'hot'}) for season {season.name}")

    if not dry_run:
        season = Season.objects.select_for_update().get(pk=season.pk)
        if season.invoices_generated_at is not None:
            logger.warning(
                f"Invoices for season {season.name} were already"
                f" generated at {season.invoices_generated_at}"
            )
            return

    season_ct = ContentType.objects.get_for_model(Season)
    invoices_data = []  # (club_name, club_id, amount) for clubs that will get invoices
    clubs_to_notification = []  # Club objects for notifications (hot mode only)
    total_amount = Decimal("0")

    for club in Club.objects.filter(fakturoid_subject_id__isnull=False).iterator():
        fees = calculate_season_fees(season, club.id)
        club_info = f"{club.name} ({club.id})"

        if (club_total := Decimal(sum([fee.amount for fee in fees.values()]))) <= 0:
            logger.info(
                f"Club {club.name} (ID: {club.id}) has no fees for season {season.name}, skipping"
            )
            continue

        if Invoice.objects.filter(
            club=club,
            type=InvoiceTypeEnum.SEASON_PLAYER_FEES,
            related_objects__content_type=season_ct,
            related_objects__object_id=season.id,
        ).exists():
            logger.info(
                f"Invoice for club {club_info} and season {season.name} already exists, skipping"
            )
            continue

        invoices_data.append((club.name, club.id, club_total))
        total_amount += club_total

        if dry_run:
            logger.info(
                f"Dry-run: Would create invoice for club {club_info}, amount: {club_total} CZK"
            )
        else:
            create_invoice(
                club,
                InvoiceTypeEnum.SEASON_PLAYER_FEES,
                [(f"Poplatky za sezónu {season.name}", club_total)],
                related_objects=[season],
            )
            clubs_to_notification.append(club)
            logger.info(f"Created invoice for club {club_info}, amount: {club_total} CZK")

    if dry_run:
        email = dry_run_user.email  # type: ignore
        _send_dry_run_email(email, season, invoices_data, total_amount)
        logger.info(
            f"Dry-run completed for season {season.name}. "
            f"Would create {len(invoices_data)} invoices, total: {total_amount} CZK. "
            f"Email sent to {email}"
        )
    else:
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
        logger.info(
            f"Invoice generation completed for season {season.name}. "
            f"Created {len(clubs_to_notification)} invoices, total: {total_amount} CZK"
        )


def _send_dry_run_email(
    email: str, season: Season, invoices_data: list[tuple[str, int, Decimal]], total_amount: Decimal
) -> None:
    """Send HTML preview email for dry-run mode using template."""
    body = render_to_string(
        "emails/season_fees_preview.html",
        {
            "season": season,
            "timestamp": timezone.now().strftime("%d.%m.%Y %H:%M:%S"),
            "invoices_data": invoices_data,
            "total_amount": total_amount,
        },
    )

    send_email(subject=f"Preview generování faktur - {season.name}", body=body, to=[email])


OVERDUE_REMINDER_DAYS = [1, 15, 30]


def _get_overdue_invoices_for_reminder() -> dict[Club, list[tuple[Invoice, int]]]:
    """
    Find invoices that are exactly 1, 15, or 30 days overdue.
    Returns dict: {club: [(invoice, days_overdue), ...]}
    """
    today = date.today()
    result: dict[Club, list[tuple[Invoice, int]]] = defaultdict(list)

    target_due_dates = [today - timedelta(days=d) for d in OVERDUE_REMINDER_DAYS]

    overdue_invoices = Invoice.objects.filter(
        state=InvoiceStateEnum.OPEN,
        fakturoid_due_on__in=target_due_dates,
    ).select_related("club")

    for invoice in overdue_invoices:
        assert invoice.fakturoid_due_on is not None  # Guaranteed by filter
        days_overdue = (today - invoice.fakturoid_due_on).days
        result[invoice.club].append((invoice, days_overdue))

    return result


def _format_overdue_reminder_message(invoices_data: list[tuple[Invoice, int]]) -> str:
    """Format HTML message listing overdue invoices for a club."""
    lines = ["<p>Následující faktury jsou po splatnosti:</p>", "<ul>"]

    for invoice, days_overdue in invoices_data:
        assert invoice.fakturoid_due_on is not None  # Guaranteed by caller
        amount = invoice.amount
        link = invoice.fakturoid_public_html_url
        due_date = invoice.fakturoid_due_on.strftime("%d.%m.%Y")

        lines.append(
            f'<li><a href="{link}">Faktura</a> - '
            f"{amount} Kč, splatnost {due_date} ({days_overdue} dnů po splatnosti)</li>"
        )

    lines.append("</ul>")
    lines.append("<p>Prosíme o úhradu co nejdříve.</p>")

    return "\n".join(lines)


@db_periodic_task(crontab(minute="0", hour="8"))
def send_overdue_invoice_reminders() -> None:
    """
    Send reminder notifications for overdue invoices.
    Runs daily at 8:00 AM.
    Sends reminders when invoices are exactly 1, 15, or 30 days overdue.
    One summary notification per club containing all overdue invoices.
    """
    logger.info("Start sending overdue invoice reminders")

    clubs_with_overdue = _get_overdue_invoices_for_reminder()

    for club, invoices_data in clubs_with_overdue.items():
        if not invoices_data:
            continue

        message = _format_overdue_reminder_message(invoices_data)

        notify_club(
            club=club,
            subject="Připomínka: Faktury po splatnosti",
            message=message,
        )

        logger.info(
            "Sent overdue reminder to club %s for %d invoices",
            club.name,
            len(invoices_data),
        )

    logger.info("End sending overdue invoice reminders, notified %d clubs", len(clubs_with_overdue))
