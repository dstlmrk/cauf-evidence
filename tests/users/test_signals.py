from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from users.models import Agent, NewAgentRequest
from users.signals import check_allowed_user

from tests.factories import AgentFactory, ClubFactory, UserFactory


class TestCheckAllowedUser:
    @patch("users.signals.get_user_managed_clubs")
    def test_updates_picture_url_for_existing_agent(self, mock_get_clubs):
        mock_get_clubs.return_value = MagicMock(first=MagicMock(return_value=None))
        user = UserFactory()
        agent = AgentFactory(user=user, picture_url="http://old-url.com/pic.jpg")

        mock_social_account = MagicMock()
        mock_social_account.get_avatar_url.return_value = "http://new-url.com/pic.jpg"

        request = MagicMock()

        with patch("users.signals.SocialAccount.objects.get", return_value=mock_social_account):
            check_allowed_user(sender=None, request=request, user=user)

        agent.refresh_from_db()
        assert agent.picture_url == "http://new-url.com/pic.jpg"

    @patch("users.signals.get_user_managed_clubs")
    @patch("users.signals.assign_agent_to_club")
    def test_creates_agent_from_new_agent_request(self, mock_assign, mock_get_clubs):
        mock_get_clubs.return_value = MagicMock(first=MagicMock(return_value=None))
        user = UserFactory(email="newuser@example.com")
        club = ClubFactory()
        inviter = UserFactory()
        NewAgentRequest.objects.create(
            email="newuser@example.com",
            club=club,
            invited_by=inviter,
            is_staff=True,
            is_superuser=False,
            is_primary=True,
        )

        mock_social_account = MagicMock()
        mock_social_account.get_avatar_url.return_value = "http://pic.com/avatar.jpg"

        request = MagicMock()

        with patch("users.signals.SocialAccount.objects.get", return_value=mock_social_account):
            check_allowed_user(sender=None, request=request, user=user)

        assert Agent.objects.filter(user=user).exists()
        user.refresh_from_db()
        assert user.is_staff is True

    @patch("users.signals.get_user_managed_clubs")
    @patch("users.signals.assign_agent_to_club")
    def test_assigns_agent_to_club_from_request(self, mock_assign, mock_get_clubs):
        mock_get_clubs.return_value = MagicMock(first=MagicMock(return_value=None))
        user = UserFactory(email="agent@example.com")
        club = ClubFactory()
        inviter = UserFactory()
        NewAgentRequest.objects.create(
            email="agent@example.com",
            club=club,
            invited_by=inviter,
            is_primary=True,
        )

        mock_social_account = MagicMock()
        mock_social_account.get_avatar_url.return_value = ""

        request = MagicMock()

        with patch("users.signals.SocialAccount.objects.get", return_value=mock_social_account):
            check_allowed_user(sender=None, request=request, user=user)

        mock_assign.assert_called_once_with(
            agent=user.agent,
            club=club,
            invited_by=inviter,
            is_primary=True,
        )

    @patch("users.signals.get_user_managed_clubs")
    def test_sets_session_club_when_user_manages_club(self, mock_get_clubs):
        from types import SimpleNamespace

        user = UserFactory()
        AgentFactory(user=user, picture_url="http://pic.com/pic.jpg")
        club = SimpleNamespace(id=42, name="Test Club")
        mock_get_clubs.return_value = MagicMock(first=MagicMock(return_value=club))

        mock_social_account = MagicMock()
        mock_social_account.get_avatar_url.return_value = "http://pic.com/pic.jpg"

        request = MagicMock()
        request.session = {}

        with patch("users.signals.SocialAccount.objects.get", return_value=mock_social_account):
            check_allowed_user(sender=None, request=request, user=user)

        assert request.session["club"] == {"id": 42, "name": "Test Club"}

    @patch("users.signals.get_user_managed_clubs")
    def test_sets_session_club_none_when_no_clubs(self, mock_get_clubs):
        user = UserFactory()
        AgentFactory(user=user, picture_url="http://pic.com/pic.jpg")
        mock_get_clubs.return_value = MagicMock(first=MagicMock(return_value=None))

        mock_social_account = MagicMock()
        mock_social_account.get_avatar_url.return_value = "http://pic.com/pic.jpg"

        request = MagicMock()
        request.session = {}

        with patch("users.signals.SocialAccount.objects.get", return_value=mock_social_account):
            check_allowed_user(sender=None, request=request, user=user)

        assert request.session["club"] is None


class TestNormalizeUserEmailSignal:
    def test_normalizes_email_to_lowercase_on_save(self):
        user = User(username="testuser", email="Test.User@Example.COM")
        user.save()

        user.refresh_from_db()
        assert user.email == "test.user@example.com"
