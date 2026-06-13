from unittest.mock import MagicMock

import pytest
from allauth.core.exceptions import ImmediateHttpResponse
from users.adapters import SocialAccountAdapter
from users.models import NewAgentRequest

from tests.factories import AgentFactory, ClubFactory, UserFactory


def _make_sociallogin(email):
    """Build a minimal SocialLogin-like mock carrying the Google email."""
    sociallogin = MagicMock()
    sociallogin.account.extra_data = {"email": email}
    return sociallogin


class TestPreSocialLogin:
    def test_allows_existing_active_agent(self):
        user = UserFactory(email="agent@example.com", is_active=True)
        AgentFactory(user=user)
        adapter = SocialAccountAdapter()
        request = MagicMock()

        # Should not raise for an allowed, active agent.
        adapter.pre_social_login(request, _make_sociallogin("agent@example.com"))

        request.assert_not_called()

    def test_allows_active_agent_with_uppercase_google_email(self):
        # Google may return the email in a different case than stored.
        user = UserFactory(email="agent@example.com", is_active=True)
        AgentFactory(user=user)
        adapter = SocialAccountAdapter()
        request = MagicMock()

        adapter.pre_social_login(request, _make_sociallogin("Agent@Example.COM"))

    def test_rejects_inactive_agent_without_invite(self):
        user = UserFactory(email="inactive@example.com", is_active=False)
        AgentFactory(user=user)
        adapter = SocialAccountAdapter()
        request = MagicMock()

        with pytest.raises(ImmediateHttpResponse):
            adapter.pre_social_login(request, _make_sociallogin("inactive@example.com"))

    def test_allows_user_with_pending_invite(self):
        club = ClubFactory()
        inviter = UserFactory()
        NewAgentRequest.objects.create(
            email="invited@example.com",
            club=club,
            invited_by=inviter,
            processed_at=None,
        )
        adapter = SocialAccountAdapter()
        request = MagicMock()

        # Pending invite (processed_at=None) must allow the login.
        adapter.pre_social_login(request, _make_sociallogin("invited@example.com"))

    def test_allows_invite_case_insensitive(self):
        club = ClubFactory()
        inviter = UserFactory()
        NewAgentRequest.objects.create(
            email="invited@example.com",
            club=club,
            invited_by=inviter,
            processed_at=None,
        )
        adapter = SocialAccountAdapter()
        request = MagicMock()

        adapter.pre_social_login(request, _make_sociallogin("INVITED@example.com"))

    def test_rejects_already_processed_invite(self):
        from django.utils import timezone

        club = ClubFactory()
        inviter = UserFactory()
        NewAgentRequest.objects.create(
            email="processed@example.com",
            club=club,
            invited_by=inviter,
            processed_at=timezone.now(),
        )
        adapter = SocialAccountAdapter()
        request = MagicMock()

        # An already processed invite no longer grants access on its own.
        with pytest.raises(ImmediateHttpResponse):
            adapter.pre_social_login(request, _make_sociallogin("processed@example.com"))

    def test_rejects_unknown_email(self):
        adapter = SocialAccountAdapter()
        request = MagicMock()

        with pytest.raises(ImmediateHttpResponse):
            adapter.pre_social_login(request, _make_sociallogin("nobody@example.com"))
