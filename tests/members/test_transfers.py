from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from members.helpers import (
    approve_transfer,
    create_transfer_request,
    reject_transfer,
    revoke_transfer,
)
from members.models import Transfer, TransferStateEnum

from tests.factories import AgentFactory, ClubFactory, MemberFactory, TransferFactory


class TestTransferModel:
    def test_transfer_creation(self):
        """Test basic transfer creation"""
        transfer = TransferFactory()

        assert transfer.state == TransferStateEnum.REQUESTED
        assert transfer.member.club == transfer.source_club
        assert transfer.source_club != transfer.target_club
        assert transfer.requesting_club == transfer.source_club
        assert transfer.approving_club == transfer.target_club

    def test_transfer_validation_same_clubs(self):
        """Test that transfer between same clubs is invalid"""
        club = ClubFactory()
        member = MemberFactory(club=club)

        transfer = Transfer(
            member=member,
            source_club=club,
            target_club=club,  # Same club
            requesting_club=club,
            approving_club=club,
            requested_by=AgentFactory(),
        )

        with pytest.raises(ValidationError, match="Target club must be different from source club"):
            transfer.clean()

    def test_transfer_validation_processed_without_approver(self):
        """Test that processed transfer requires approved_by"""
        transfer = Transfer(
            member=MemberFactory(),
            state=TransferStateEnum.PROCESSED,
            source_club=ClubFactory(),
            target_club=ClubFactory(),
            requesting_club=ClubFactory(),
            approving_club=ClubFactory(),
            requested_by=AgentFactory(),
            approved_by=None,
        )

        with pytest.raises(ValidationError, match="Approved by agent must be set"):
            transfer.clean()

    def test_duplicate_transfer_request_validation(self):
        """Test that duplicate transfer requests are not allowed"""
        transfer1 = TransferFactory()

        # Try to create identical transfer
        transfer2 = Transfer(
            member=transfer1.member,
            state=TransferStateEnum.REQUESTED,
            source_club=transfer1.source_club,
            target_club=transfer1.target_club,
            requesting_club=transfer1.requesting_club,
            approving_club=transfer1.approving_club,
            requested_by=transfer1.requested_by,
        )

        with pytest.raises(ValidationError, match="Member already has a pending transfer request"):
            transfer2.clean()

    def test_ordering_by_created_at_desc(self):
        """Test that transfers are ordered by creation date descending"""
        older_transfer = TransferFactory()
        newer_transfer = TransferFactory()

        transfers = list(Transfer.objects.all())
        assert transfers[0] == newer_transfer
        assert transfers[1] == older_transfer


class TestTransferHelpers:
    @patch("members.helpers.notify_club")
    def test_create_transfer_request_success(self, mock_notify):
        """Test successful transfer request creation"""
        agent = AgentFactory()
        source_club = ClubFactory()
        target_club = ClubFactory()
        member = MemberFactory(club=source_club)

        create_transfer_request(
            agent=agent,
            current_club=source_club,
            member=member,
            source_club=source_club,
            target_club=target_club,
        )

        transfer = Transfer.objects.get(member=member)
        assert transfer.state == TransferStateEnum.REQUESTED
        assert transfer.source_club == source_club
        assert transfer.target_club == target_club
        assert transfer.requesting_club == source_club
        assert transfer.approving_club == target_club
        assert transfer.requested_by == agent

        # Check notification was sent
        mock_notify.assert_called_once_with(
            club=target_club,
            subject="Transfer request",
            message=(
                f"You have been requested to approve the transfer of <b>{member.full_name}</b>."
            ),
        )

    def test_create_transfer_request_member_wrong_club(self):
        """Test transfer request fails if member is not in source club"""
        agent = AgentFactory()
        source_club = ClubFactory()
        target_club = ClubFactory()
        wrong_club = ClubFactory()
        member = MemberFactory(club=wrong_club)  # Member is in wrong club

        with pytest.raises(ValueError, match="Member is not in source club"):
            create_transfer_request(
                agent=agent,
                current_club=source_club,
                member=member,
                source_club=source_club,
                target_club=target_club,
            )

    def test_create_transfer_request_member_already_in_target_club(self):
        """Test transfer request fails if member is already in target club"""
        agent = AgentFactory()
        club = ClubFactory()
        member = MemberFactory(club=club)

        with pytest.raises(ValueError, match="Member is already in target club"):
            create_transfer_request(
                agent=agent, current_club=club, member=member, source_club=club, target_club=club
            )

    @patch("members.helpers.notify_club")
    def test_approve_transfer_success(self, mock_notify):
        """Test successful transfer approval"""
        agent = AgentFactory()
        source_club = ClubFactory()
        target_club = ClubFactory()
        member = MemberFactory(club=source_club)
        transfer = TransferFactory(
            member=member,
            source_club=source_club,
            target_club=target_club,
            state=TransferStateEnum.REQUESTED,
        )

        approve_transfer(agent=agent, transfer=transfer)

        transfer.refresh_from_db()
        member.refresh_from_db()

        # Check transfer state updated
        assert transfer.state == TransferStateEnum.PROCESSED
        assert transfer.approved_by == agent
        assert transfer.approved_at is not None

        # Check member moved to target club
        assert member.club == target_club

        # Check notification sent
        mock_notify.assert_called_once_with(
            club=transfer.requesting_club,
            subject="Transfer approved",
            message=f"Your request to transfer <b>{member.full_name}</b> has been approved.",
        )

    def test_approve_transfer_wrong_state(self):
        """Test approval fails if transfer is not in REQUESTED state"""
        agent = AgentFactory()
        transfer = TransferFactory(state=TransferStateEnum.PROCESSED, approved_by=AgentFactory())

        with pytest.raises(ValueError, match="Transfer must be in REQUESTED state to be approved"):
            approve_transfer(agent=agent, transfer=transfer)

    @patch("members.helpers.notify_club")
    def test_revoke_transfer_success(self, mock_notify):
        """Test successful transfer revocation"""
        transfer = TransferFactory(state=TransferStateEnum.REQUESTED)

        revoke_transfer(transfer=transfer)

        transfer.refresh_from_db()
        assert transfer.state == TransferStateEnum.REVOKED

        # Check notification sent
        mock_notify.assert_called_once_with(
            club=transfer.approving_club,
            subject="Transfer revoked",
            message=(
                f"The transfer of <b>{transfer.member.full_name}</b> has been revoked by requester."
            ),
        )

    def test_revoke_transfer_wrong_state(self):
        """Test revocation fails if transfer is not in REQUESTED state"""
        transfer = TransferFactory(state=TransferStateEnum.PROCESSED, approved_by=AgentFactory())

        with pytest.raises(ValueError, match="Transfer must be in REQUESTED state to be canceled"):
            revoke_transfer(transfer=transfer)

    @patch("members.helpers.notify_club")
    def test_reject_transfer_success(self, mock_notify):
        """Test successful transfer rejection"""
        transfer = TransferFactory(state=TransferStateEnum.REQUESTED)

        reject_transfer(transfer=transfer)

        transfer.refresh_from_db()
        assert transfer.state == TransferStateEnum.REJECTED

        # Check notification sent
        mock_notify.assert_called_once_with(
            club=transfer.requesting_club,
            subject="Transfer rejected",
            message=(
                f"The transfer of <b>{transfer.member.full_name}</b> has been rejected by approver."
            ),
        )

    def test_reject_transfer_wrong_state(self):
        """Test rejection fails if transfer is not in REQUESTED state"""
        transfer = TransferFactory(state=TransferStateEnum.PROCESSED, approved_by=AgentFactory())

        with pytest.raises(ValueError, match="Transfer must be in REQUESTED state to be rejected"):
            reject_transfer(transfer=transfer)


class TestTransferStateTransitions:
    """Test all possible state transitions"""

    def test_requested_to_processed_valid(self):
        """Test REQUESTED -> PROCESSED is valid"""
        transfer = TransferFactory(state=TransferStateEnum.REQUESTED)
        agent = AgentFactory()

        approve_transfer(agent=agent, transfer=transfer)

        transfer.refresh_from_db()
        assert transfer.state == TransferStateEnum.PROCESSED

    def test_requested_to_revoked_valid(self):
        """Test REQUESTED -> REVOKED is valid"""
        transfer = TransferFactory(state=TransferStateEnum.REQUESTED)

        revoke_transfer(transfer=transfer)

        transfer.refresh_from_db()
        assert transfer.state == TransferStateEnum.REVOKED

    def test_requested_to_rejected_valid(self):
        """Test REQUESTED -> REJECTED is valid"""
        transfer = TransferFactory(state=TransferStateEnum.REQUESTED)

        reject_transfer(transfer=transfer)

        transfer.refresh_from_db()
        assert transfer.state == TransferStateEnum.REJECTED

    @pytest.mark.parametrize(
        "invalid_state",
        [
            TransferStateEnum.PROCESSED,
            TransferStateEnum.REVOKED,
            TransferStateEnum.REJECTED,
        ],
    )
    def test_invalid_state_transitions(self, invalid_state):
        """Test that transfers in final states cannot be changed"""
        transfer = TransferFactory()
        transfer.state = invalid_state
        if invalid_state == TransferStateEnum.PROCESSED:
            transfer.approved_by = AgentFactory()
        transfer.save()

        agent = AgentFactory()

        with pytest.raises(ValueError):
            approve_transfer(agent=agent, transfer=transfer)

        with pytest.raises(ValueError):
            revoke_transfer(transfer=transfer)

        with pytest.raises(ValueError):
            reject_transfer(transfer=transfer)
