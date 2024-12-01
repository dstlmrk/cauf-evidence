from clubs.models import Club
from django.utils import timezone
from users.models import Agent

from members.models import Member, Transfer, TransferStateEnum


def create_transfer_request(
    agent: Agent, current_club: Club, member: Member, source_club: Club, target_club: Club
) -> None:
    if member.club != source_club:
        raise ValueError("Member is not in source club")
    if member.club == target_club:
        raise ValueError("Member is already in target club")

    Transfer.objects.create(
        member=member,
        source_club=source_club,
        target_club=target_club,
        requesting_club=current_club,
        approving_club=target_club if current_club == source_club else source_club,
        requested_by=agent,
    )
    # TODO: send email/notification


def approve_transfer(agent: Agent, transfer: Transfer) -> None:
    if transfer.state != TransferStateEnum.REQUESTED:
        raise ValueError("Transfer must be in REQUESTED state to be approved")

    transfer.state = TransferStateEnum.PROCESSED
    transfer.approved_at = timezone.now()
    transfer.approved_by = agent
    transfer.save()

    transfer.member.club = transfer.target_club
    transfer.member.save()


def revoke_transfer(transfer: Transfer) -> None:
    if transfer.state != TransferStateEnum.REQUESTED:
        raise ValueError("Transfer must be in REQUESTED state to be canceled")

    transfer.state = TransferStateEnum.REVOKED
    transfer.save()
