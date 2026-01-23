from unittest.mock import patch

from clubs.models import ClubNotification
from clubs.service import notify_club

from tests.factories import AgentAtClubFactory, AgentFactory, ClubFactory


class TestNotifyClub:
    def test_creates_notifications_for_active_agents(self):
        club = ClubFactory()
        agent1 = AgentFactory()
        agent2 = AgentFactory()
        AgentAtClubFactory(agent=agent1, club=club, is_active=True)
        AgentAtClubFactory(agent=agent2, club=club, is_active=True)

        with patch("clubs.service.send_email"):
            notify_club(club, "Test Subject", "Test Message")

        assert ClubNotification.objects.filter(agent_at_club__club=club).count() == 2

    def test_does_not_notify_inactive_agents(self):
        club = ClubFactory()
        active_agent = AgentFactory()
        inactive_agent = AgentFactory()
        AgentAtClubFactory(agent=active_agent, club=club, is_active=True)
        AgentAtClubFactory(agent=inactive_agent, club=club, is_active=False)

        with patch("clubs.service.send_email"):
            notify_club(club, "Test Subject", "Test Message")

        assert ClubNotification.objects.filter(agent_at_club__club=club).count() == 1
        notification = ClubNotification.objects.get()
        assert notification.agent_at_club.agent == active_agent

    @patch("clubs.service.send_email")
    def test_sends_email_only_to_agents_with_notifications_enabled(self, mock_send_email):
        club = ClubFactory()
        agent_with_email = AgentFactory(has_email_notifications_enabled=True)
        agent_without_email = AgentFactory(has_email_notifications_enabled=False)
        AgentAtClubFactory(agent=agent_with_email, club=club, is_active=True)
        AgentAtClubFactory(agent=agent_without_email, club=club, is_active=True)

        notify_club(club, "Test Subject", "Test Message")

        mock_send_email.assert_called_once_with(
            "Test Subject", "Test Message", to=[agent_with_email.user.email]
        )

    @patch("clubs.service.send_email")
    def test_no_email_when_all_have_notifications_disabled(self, mock_send_email):
        club = ClubFactory()
        agent = AgentFactory(has_email_notifications_enabled=False)
        AgentAtClubFactory(agent=agent, club=club, is_active=True)

        notify_club(club, "Test Subject", "Test Message")

        mock_send_email.assert_not_called()

    @patch("clubs.service.send_email")
    def test_handles_club_with_no_agents(self, mock_send_email):
        club = ClubFactory()

        notify_club(club, "Test Subject", "Test Message")

        assert ClubNotification.objects.count() == 0
        mock_send_email.assert_not_called()
