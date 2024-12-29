import logging
from decimal import Decimal

from clubs.models import Club
from clubs.service import notify_club
from competitions.models import Season
from core.helpers import create_csv
from core.tasks import send_email
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from django_rq import job

from finance.models import InvoiceTypeEnum
from finance.services import calculate_season_fees, create_invoice

logger = logging.getLogger(__name__)


@job
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

    send_email.delay(
        "Fees calculation for check",
        (
            f"Hi. We have calculated fees for the season {season.name}."
            " Please check the attached CSV file."
        ),
        [user.email],
        csv_data=csv_data,
    )


@job
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
                f"Season fees for the season {season.name}"
                " have been generated. Check your invoices."
            ),
        )
