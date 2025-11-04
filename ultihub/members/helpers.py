import logging
from collections import Counter

from clubs.models import Club
from clubs.service import notify_club
from competitions.models import Season
from django.utils import timezone
from international_tournaments.models import (
    InternationalTournament,
    MemberAtInternationalTournament,
)
from tournaments.models import MemberAtTournament, Tournament
from users.models import Agent

from members.models import Member, Transfer, TransferStateEnum

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


def get_member_participation_counts(season: Season) -> Counter[int]:
    # Calculate days for domestic tournaments
    tournament_lengths: dict[int, int] = {}
    for tournament in Tournament.objects.filter(competition__season=season):
        delta_days = (tournament.end_date - tournament.start_date).days + 1
        tournament_lengths[tournament.id] = delta_days

    # Calculate days for international tournaments
    international_tournament_lengths: dict[int, int] = {}
    for int_tournament in InternationalTournament.objects.filter(season=season):
        delta_days = (int_tournament.date_to - int_tournament.date_from).days + 1
        international_tournament_lengths[int_tournament.id] = delta_days

    # Sum up days for each member from domestic tournaments
    member_participation: Counter[int] = Counter()
    for member_at_tournament in MemberAtTournament.objects.filter(
        tournament_id__in=tournament_lengths.keys()
    ):
        member_participation[member_at_tournament.member_id] += tournament_lengths[
            member_at_tournament.tournament.id
        ]

    # Add days from international tournaments
    for member_at_int_tournament in MemberAtInternationalTournament.objects.filter(
        tournament_id__in=international_tournament_lengths.keys()
    ):
        member_participation[member_at_int_tournament.member_id] += (
            international_tournament_lengths[member_at_int_tournament.tournament.id]
        )

    return member_participation
