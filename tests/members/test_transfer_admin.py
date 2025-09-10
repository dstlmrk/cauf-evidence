from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import HttpRequest
from django.test import RequestFactory
from members.admin import TransferAdmin
from members.models import Transfer, TransferStateEnum

from tests.factories import AgentFactory, MemberFactory, TransferFactory, UserFactory


class TestTransferAdmin:
    def setup_method(self):
        """Setup for each test method"""
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.admin = TransferAdmin(Transfer, self.site)

    def _create_request_with_user(self, user: User) -> HttpRequest:
        """Helper to create request with authenticated user"""
        request = self.factory.get("/admin/")
        request.user = user
        # Add messages framework (required for admin actions)
        request.session = {}
        messages = FallbackStorage(request)
        request._messages = messages
        return request

    def test_list_display_fields(self):
        """Test that admin shows correct fields in list view"""
        expected_fields = ("id", "transfer", "member_full_name", "state", "approved_at")
        assert self.admin.list_display == expected_fields

    def test_list_filters(self):
        """Test that admin has correct filters"""
        expected_filters = ["state", "created_at"]
        assert self.admin.list_filter == expected_filters

    def test_admin_actions_available(self):
        """Test that approve_transfers action is available"""
        assert "approve_transfers" in self.admin.actions

    def test_member_full_name_display(self):
        """Test member_full_name admin display method"""
        transfer = TransferFactory()
        result = self.admin.member_full_name(transfer)
        assert result == transfer.member.full_name

    def test_transfer_display(self):
        """Test transfer admin display method"""
        transfer = TransferFactory()
        result = self.admin.transfer(transfer)
        expected = f"{transfer.source_club} → {transfer.target_club}"
        assert result == expected

    def test_queryset_optimization(self):
        """Test that queryset uses select_related for optimization"""
        user = UserFactory(is_staff=True)
        request = self._create_request_with_user(user)

        queryset = self.admin.get_queryset(request)

        # Check that select_related was applied
        assert "member" in queryset.query.select_related
        assert "source_club" in queryset.query.select_related
        assert "target_club" in queryset.query.select_related
        assert "requesting_club" in queryset.query.select_related
        assert "approving_club" in queryset.query.select_related
        assert "requested_by" in queryset.query.select_related
        assert "approved_by" in queryset.query.select_related

    def test_readonly_permissions(self):
        """Test that admin is read-only (inherits from ReadOnlyModelAdmin)"""
        user = UserFactory(is_staff=True)
        request = self._create_request_with_user(user)

        # Test permissions
        assert not self.admin.has_add_permission(request)
        assert not self.admin.has_change_permission(request)
        assert not self.admin.has_delete_permission(request)

    @patch("members.admin.approve_transfer")
    def test_approve_transfers_action_success(self, mock_approve):
        """Test successful approval of transfers via admin action"""
        # Create user with agent
        user = UserFactory(is_staff=True)
        agent = AgentFactory(user=user)
        request = self._create_request_with_user(user)

        # Create transfers in REQUESTED state
        transfer1 = TransferFactory(state=TransferStateEnum.REQUESTED)
        transfer2 = TransferFactory(state=TransferStateEnum.REQUESTED)
        queryset = Transfer.objects.filter(id__in=[transfer1.id, transfer2.id])

        # Execute admin action
        self.admin.approve_transfers(request, queryset)

        # Verify approve_transfer was called for each transfer
        assert mock_approve.call_count == 2
        mock_approve.assert_any_call(agent=agent, transfer=transfer1)
        mock_approve.assert_any_call(agent=agent, transfer=transfer2)

    @patch("members.admin.approve_transfer")
    def test_approve_transfers_action_filters_by_state(self, mock_approve):
        """Test that admin action only processes REQUESTED transfers"""
        user = UserFactory(is_staff=True)
        agent = AgentFactory(user=user)
        request = self._create_request_with_user(user)

        # Create transfers in different states
        requested_transfer = TransferFactory(state=TransferStateEnum.REQUESTED)
        TransferFactory(state=TransferStateEnum.PROCESSED, approved_by=AgentFactory())
        TransferFactory(state=TransferStateEnum.REJECTED)

        queryset = Transfer.objects.all()

        # Execute admin action
        self.admin.approve_transfers(request, queryset)

        # Verify only REQUESTED transfer was processed
        mock_approve.assert_called_once_with(agent=agent, transfer=requested_transfer)

    @patch("members.admin.approve_transfer")
    def test_approve_transfers_action_handles_errors(self, mock_approve):
        """Test that admin action handles errors gracefully"""
        user = UserFactory(is_staff=True)
        agent = AgentFactory(user=user)
        request = self._create_request_with_user(user)

        transfer = TransferFactory(state=TransferStateEnum.REQUESTED)
        queryset = Transfer.objects.filter(id=transfer.id)

        # Mock approve_transfer to raise an exception
        mock_approve.side_effect = ValueError("Test error")

        # Execute admin action (should not raise exception)
        self.admin.approve_transfers(request, queryset)

        # Verify error was handled
        mock_approve.assert_called_once_with(agent=agent, transfer=transfer)

    def test_approve_transfers_action_requires_agent(self):
        """Test that admin action requires user to have agent"""
        # Create user without agent
        user = UserFactory(is_staff=True)
        request = self._create_request_with_user(user)

        transfer = TransferFactory(state=TransferStateEnum.REQUESTED)
        queryset = Transfer.objects.filter(id=transfer.id)

        # Execute admin action - should handle error gracefully
        self.admin.approve_transfers(request, queryset)

        # Check that error message was added
        messages = list(request._messages)
        assert len(messages) == 1
        assert "Error approving transfer" in str(messages[0])
        assert str(transfer.id) in str(messages[0])

    @patch("members.admin.approve_transfer")
    def test_approve_transfers_action_success_message(self, mock_approve):
        """Test that admin action shows success message"""
        user = UserFactory(is_staff=True)
        AgentFactory(user=user)
        request = self._create_request_with_user(user)

        transfer = TransferFactory(state=TransferStateEnum.REQUESTED)
        queryset = Transfer.objects.filter(id=transfer.id)

        # Execute admin action
        self.admin.approve_transfers(request, queryset)

        # Check that success message was added
        messages = list(request._messages)
        assert len(messages) == 1
        assert "1 transfers were approved" in str(messages[0])

    def test_approve_transfers_action_no_requested_transfers(self):
        """Test admin action when no REQUESTED transfers in queryset"""
        user = UserFactory(is_staff=True)
        AgentFactory(user=user)
        request = self._create_request_with_user(user)

        # Create only processed transfers
        TransferFactory(state=TransferStateEnum.PROCESSED, approved_by=AgentFactory())
        queryset = Transfer.objects.all()

        # Execute admin action
        self.admin.approve_transfers(request, queryset)

        # No success message should be shown
        messages = list(request._messages)
        assert len(messages) == 0


class TestTransferAdminIntegration:
    """Integration tests for transfer admin functionality"""

    @patch("members.helpers.notify_club")
    def test_full_transfer_approval_workflow(self, mock_notify):
        """Test complete transfer approval workflow through admin"""
        # Setup
        user = UserFactory(is_staff=True)
        agent = AgentFactory(user=user)
        factory = RequestFactory()
        site = AdminSite()
        admin = TransferAdmin(Transfer, site)

        # Create transfer
        member = MemberFactory()
        original_club = member.club
        transfer = TransferFactory(
            member=member, source_club=original_club, state=TransferStateEnum.REQUESTED
        )

        # Create admin request
        request = factory.get("/admin/")
        request.user = user
        request.session = {}
        messages = FallbackStorage(request)
        request._messages = messages

        # Execute admin action
        queryset = Transfer.objects.filter(id=transfer.id)
        admin.approve_transfers(request, queryset)

        # Verify complete workflow
        transfer.refresh_from_db()
        member.refresh_from_db()

        assert transfer.state == TransferStateEnum.PROCESSED
        assert transfer.approved_by == agent
        assert transfer.approved_at is not None
        assert member.club == transfer.target_club
        assert member.club != original_club

        # Verify notification was sent
        mock_notify.assert_called_once()
