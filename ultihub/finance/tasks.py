import logging

from clubs.models import Club
from competitions.models import Season
from core.helpers import create_csv
from core.tasks import send_email
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from django_rq import job
from members.models import Member

from finance.models import InvoiceTypeEnum
from finance.services import create_invoice

logger = logging.getLogger(__name__)


@job
@transaction.atomic()
def calculate_season_fees_for_check(user: User, season: Season) -> None:
    logger.info(f"Calculating fees (check) for season {season.name}")
    # TODO: Prepare data properly
    csv_data = create_csv(
        header=["Member", "Club", "Amount"],
        data=[["Jan Novak", "Prague Devils", "1000"]],
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
    clubs = Club.objects.all()
    for club in clubs:
        # TODO: calculate amount properly
        amount = season.regular_fee * Member.objects.filter(club=club).count()
        create_invoice(
            club.id, amount, InvoiceTypeEnum.ANNUAL_PLAYER_FEES, related_objects=[season]
        )
    season.invoices_generated_at = timezone.now()
    season.save()
    # TODO: send notification to all clubs
