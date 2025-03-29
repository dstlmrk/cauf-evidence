import logging
from collections import Counter

from clubs.models import Club
from clubs.service import notify_club
from competitions.models import Season
from core.helpers import SessionClub, create_csv
from core.tasks import send_email
from django.db.models import Exists, OuterRef, Subquery
from django.utils import timezone
from django.utils.timezone import now
from tournaments.models import MemberAtTournament, Tournament
from users.models import Agent

from members.models import CoachLicence, Member, Transfer, TransferStateEnum

logger = logging.getLogger(__name__)


def create_transfer_request(
    agent: Agent, current_club: Club, member: Member, source_club: Club, target_club: Club
) -> None:
    if member.club != source_club:
        raise ValueError("Member is not in source club")
    if member.club == target_club:
        raise ValueError("Member is already in target club")

    approving_club = target_club if current_club == source_club else source_club

    Transfer.objects.create(
        member=member,
        source_club=source_club,
        target_club=target_club,
        requesting_club=current_club,
        approving_club=approving_club,
        requested_by=agent,
    )

    notify_club(
        club=approving_club,
        subject="Transfer request",
        message=f"You have been requested to approve the transfer of <b>{member.full_name}</b>.",
    )


def approve_transfer(agent: Agent, transfer: Transfer) -> None:
    if transfer.state != TransferStateEnum.REQUESTED:
        raise ValueError("Transfer must be in REQUESTED state to be approved")

    transfer.state = TransferStateEnum.PROCESSED
    transfer.approved_at = timezone.now()
    transfer.approved_by = agent
    transfer.save()

    transfer.member.club = transfer.target_club
    transfer.member.save()

    notify_club(
        club=transfer.requesting_club,
        subject="Transfer approved",
        message=f"Your request to transfer <b>{transfer.member.full_name}</b> has been approved.",
    )


def revoke_transfer(transfer: Transfer) -> None:
    if transfer.state != TransferStateEnum.REQUESTED:
        raise ValueError("Transfer must be in REQUESTED state to be canceled")

    transfer.state = TransferStateEnum.REVOKED
    transfer.save()

    notify_club(
        club=transfer.approving_club,
        subject="Transfer revoked",
        message=(
            f"The transfer of <b>{transfer.member.full_name}</b> has been revoked by requester."
        ),
    )


def reject_transfer(transfer: Transfer) -> None:
    if transfer.state != TransferStateEnum.REQUESTED:
        raise ValueError("Transfer must be in REQUESTED state to be rejected")

    transfer.state = TransferStateEnum.REJECTED
    transfer.save()

    notify_club(
        club=transfer.requesting_club,
        subject="Transfer rejected",
        message=(
            f"The transfer of <b>{transfer.member.full_name}</b> has been rejected by approver."
        ),
    )


def get_member_participation_counts_for_last_season() -> Counter[int]:
    last_season = Season.objects.last()
    tournament_lengths = {}
    for tournament in Tournament.objects.filter(competition__season=last_season):
        delta_days = (tournament.end_date - tournament.start_date).days + 1
        tournament_lengths[tournament.id] = delta_days
    member_participation: Counter[int] = Counter()
    for member_at_tournament in MemberAtTournament.objects.filter(
        tournament_id__in=tournament_lengths.keys()
    ):
        member_participation[member_at_tournament.member_id] += tournament_lengths[
            member_at_tournament.tournament.id
        ]
    return member_participation


def export_members_to_csv_for_nsa(agent: Agent, club: SessionClub) -> None:
    # https://rejstriksportu.cz/dashboard/public/dokumentace

    logger.info(f"Agent {agent.user.email} requested NSA export for {club.name}")
    current_date = now().date()
    data = []

    member_participation = get_member_participation_counts_for_last_season()

    for member in Member.objects.filter(club_id=club.id).annotate(
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
    ):
        data.append(
            [
                member.first_name,
                member.last_name,
                member.birth_number,
                member.citizenship.alpha3,
                member.birth_date.strftime("%d.%m.%Y"),
                "Ž" if member.sex == 1 else "M",
                member.city,
                member.street,
                member.house_number,
                member.postal_code,
                "1",
                member.created_at,
                "98.3",
                member_participation[member.id],
                "1" if member.has_coach_licence else "0",
                member.earliest_coach_licence_date if member.has_coach_licence else "",
                "98.3",
                member.club.identification_number,
            ]
        )

    csv_data = create_csv(
        header=[
            "JMENO",
            "PRIJMENI",
            "RODNE_CISLO",
            "OBCANSTVI",
            "DATUM_NAROZENI",
            "POHLAVI",
            "NAZEV_OBCE",
            "NAZEV_ULICE",
            "CISLO_POPISNE",
            "PSC",
            "SPORTOVEC",
            "SPORTOVCEM_OD",
            "SPORTOVEC_DRUH_SPORTU",
            "SPORTOVEC_UCAST_SOUTEZE_POCET",
            "TRENER",
            "TRENEREM_OD",
            "TRENER_DRUH_SPORTU",
            "SVAZ_ICO_SKTJ",
        ],
        data=data,
    )

    send_email(
        "NSA export",
        f"Hi. Here is the CSV export of all members in {club.name} for NSA.",
        to=[agent.user.email],
        csv_data=csv_data,
    )
    logger.info(f"NSA export sent to {agent.user.email}")
