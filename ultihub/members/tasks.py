import logging
from datetime import date

from clubs.models import Club
from competitions.models import Season
from core.helpers import create_csv
from core.tasks import send_email
from django.contrib.auth.models import User
from django.db.models import Exists, OuterRef, Subquery
from django.utils.timezone import now
from huey.contrib.djhuey import db_task

from members.helpers import get_member_participation_counts
from members.models import CoachLicence, Member

logger = logging.getLogger(__name__)


def _format_date(date_: date) -> str:
    """Format date as DD.MM.YYYY without leading zeros."""
    return f"{date_.day}.{date_.month}.{date_.year}"


@db_task()
def generate_nsa_export(user: User, season: Season, club: Club | None) -> None:
    # https://rejstriksportu.cz/dashboard/public/dokumentace

    logger.info(f"User {user.email} requested NSA export for {club.name if club else 'all clubs'}")
    current_date = now().date()

    logger.info("Calculating participation counts for active members")
    member_participation = get_member_participation_counts(season)
    logger.info(f"Participation counts calculated for {len(member_participation)} members")

    members_qs = Member.objects.filter(id__in=member_participation.keys()).annotate(
        has_coach_licence=Exists(
            CoachLicence.objects.filter(
                member=OuterRef("pk"),
                valid_from__lte=current_date,
                valid_to__gte=current_date,
            )
        ),
        earliest_coach_licence_date=Subquery(
            CoachLicence.objects.filter(member=OuterRef("pk"))
            .order_by("valid_from")
            .values("valid_from")[:1]
        ),
    )

    if club:
        members_qs = members_qs.filter(club=club)

    data = []
    for member in members_qs:
        data.append(
            [
                member.first_name,
                member.last_name,
                "",
                "",
                member.birth_number,
                member.citizenship.alpha3,
                _format_date(member.birth_date),
                "Ž" if member.sex == 1 else "M",
                member.city,
                "",
                member.street,
                member.house_number,
                "",
                member.postal_code,
                "1",
                _format_date(member.created_at),
                "",
                "98.3",
                "",
                member_participation[member.id],
                "1" if member.has_coach_licence else "0",
                member.earliest_coach_licence_date if member.has_coach_licence else "",
                "",
                "",
                "98.3",
                member.club.identification_number,
            ]
        )

    # fmt: off
    header = [
        "JMENO", "PRIJMENI", "TITUL_PRED", "TITUL_ZA",
        "RODNE_CISLO", "OBCANSTVI", "DATUM_NAROZENI", "POHLAVI",
        "NAZEV_OBCE", "NAZEV_CASTI_OBCE", "NAZEV_ULICE", "CISLO_POPISNE", "CISLO_ORIENTACNI", "PSC",
        "SPORTOVEC", "SPORTOVCEM_OD", "SPORTOVCEM_DO", "SPORTOVEC_DRUH_SPORTU", "SPORTOVEC_CETNOST",
        "SPORTOVEC_UCAST_SOUTEZE_POCET", "TRENER", "TRENEREM_OD", "TRENEREM_DO", "TRENER_CETNOST",
        "TRENER_DRUH_SPORTU", "SVAZ_ICO_SKTJ",
    ]
    # fmt: on

    csv_data = create_csv(header=header, data=data)

    if club:
        body = f"Hi. Here is the NSA export for the season {season.name} and club {club.name}."
    else:
        body = f"Hi. Here is the NSA export for the season {season.name}."

    send_email("NSA export", body=body, to=[user.email], csv_data=csv_data)
    logger.info(f"NSA export sent to {user.email}")
