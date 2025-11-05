from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from members.helpers import (
    approve_transfer,
    cancel_competing_transfers,
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
            TransferStateEnum.CANCELLED,
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


class TestCancelCompetingTransfers:
    """Test automatic cancellation of competing transfers"""

    def test_cancel_competing_transfers_cancels_other_requested_transfers(self):
        """Test that other REQUESTED transfers for the same member are cancelled"""
        member = MemberFactory()
        club1 = ClubFactory()
        club2 = ClubFactory()
        club3 = ClubFactory()

        # Create multiple transfer requests for the same member
        transfer1 = TransferFactory(
            member=member, source_club=club1, target_club=club2, state=TransferStateEnum.REQUESTED
        )
        transfer2 = TransferFactory(
            member=member, source_club=club1, target_club=club3, state=TransferStateEnum.REQUESTED
        )
        transfer3 = TransferFactory(
            member=member, source_club=club2, target_club=club3, state=TransferStateEnum.REQUESTED
        )

        # Cancel competing transfers (keeping transfer1)
        cancel_competing_transfers(member, transfer1.id)

        # Check that transfer1 is still REQUESTED
        transfer1.refresh_from_db()
        assert transfer1.state == TransferStateEnum.REQUESTED

        # Check that other transfers are CANCELLED
        transfer2.refresh_from_db()
        assert transfer2.state == TransferStateEnum.CANCELLED

        transfer3.refresh_from_db()
        assert transfer3.state == TransferStateEnum.CANCELLED

    def test_cancel_competing_transfers_does_not_affect_final_state_transfers(self):
        """Test that transfers in final states (PROCESSED, REJECTED, REVOKED) are not affected"""
        member = MemberFactory()
        club1 = ClubFactory()
        club2 = ClubFactory()
        club3 = ClubFactory()
        club4 = ClubFactory()
        agent = AgentFactory()

        # Create transfers in different states
        transfer_requested = TransferFactory(
            member=member, source_club=club1, target_club=club2, state=TransferStateEnum.REQUESTED
        )
        transfer_processed = TransferFactory(
            member=member,
            source_club=club1,
            target_club=club3,
            state=TransferStateEnum.PROCESSED,
            approved_by=agent,
        )
        transfer_rejected = TransferFactory(
            member=member, source_club=club1, target_club=club4, state=TransferStateEnum.REJECTED
        )
        transfer_revoked = TransferFactory(
            member=member, source_club=club2, target_club=club4, state=TransferStateEnum.REVOKED
        )

        # Cancel competing transfers (keeping one that doesn't exist)
        cancel_competing_transfers(member, 999999)

        # Check that only REQUESTED transfer was cancelled
        transfer_requested.refresh_from_db()
        assert transfer_requested.state == TransferStateEnum.CANCELLED

        # Check that final state transfers are unchanged
        transfer_processed.refresh_from_db()
        assert transfer_processed.state == TransferStateEnum.PROCESSED

        transfer_rejected.refresh_from_db()
        assert transfer_rejected.state == TransferStateEnum.REJECTED

        transfer_revoked.refresh_from_db()
        assert transfer_revoked.state == TransferStateEnum.REVOKED

    @patch("members.helpers.notify_club")
    def test_approve_transfer_cancels_competing_transfers(self, mock_notify):
        """Test that approving a transfer automatically cancels other REQUESTED transfers"""
        agent = AgentFactory()
        source_club = ClubFactory()
        target_club1 = ClubFactory()
        target_club2 = ClubFactory()
        member = MemberFactory(club=source_club)

        # Create two transfer requests for the same member
        transfer1 = TransferFactory(
            member=member,
            source_club=source_club,
            target_club=target_club1,
            state=TransferStateEnum.REQUESTED,
        )
        transfer2 = TransferFactory(
            member=member,
            source_club=source_club,
            target_club=target_club2,
            state=TransferStateEnum.REQUESTED,
        )

        # Approve the first transfer
        approve_transfer(agent=agent, transfer=transfer1)

        # Check that transfer1 is PROCESSED
        transfer1.refresh_from_db()
        assert transfer1.state == TransferStateEnum.PROCESSED

        # Check that transfer2 was automatically CANCELLED
        transfer2.refresh_from_db()
        assert transfer2.state == TransferStateEnum.CANCELLED

        # Check that member was moved to target_club1
        member.refresh_from_db()
        assert member.club == target_club1

    def test_cancel_competing_transfers_with_no_other_transfers(self):
        """Test that cancel_competing_transfers works when there are no other transfers"""
        member = MemberFactory()
        transfer = TransferFactory(member=member, state=TransferStateEnum.REQUESTED)

        # Should not raise any errors
        cancel_competing_transfers(member, transfer.id)

        # Transfer should remain unchanged
        transfer.refresh_from_db()
        assert transfer.state == TransferStateEnum.REQUESTED

    def test_cancelled_state_in_parametrized_test(self):
        """Test that CANCELLED state is also a final state like PROCESSED, REJECTED, REVOKED"""
        transfer = TransferFactory()
        transfer.state = TransferStateEnum.CANCELLED
        transfer.save()

        agent = AgentFactory()

        # Should not be able to approve, revoke, or reject a CANCELLED transfer
        with pytest.raises(ValueError):
            approve_transfer(agent=agent, transfer=transfer)

        with pytest.raises(ValueError):
            revoke_transfer(transfer=transfer)

        with pytest.raises(ValueError):
            reject_transfer(transfer=transfer)
