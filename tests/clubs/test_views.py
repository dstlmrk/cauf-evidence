from unittest.mock import patch

from clubs.models import ClubNotification, Team
from django.test import Client
from django.urls import reverse

from tests.factories import AgentAtClubFactory, AgentFactory, ClubFactory, TeamFactory, UserFactory


class TestAddTeam:
    def test_get_renders_form(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        client = logged_in_client(user, club)

        response = client.get(reverse("clubs:add_team"))

        assert response.status_code == 200

    def test_post_creates_team(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        client = logged_in_client(user, club)

        response = client.post(
            reverse("clubs:add_team"),
            data={"name": "New Team", "description": "A team"},
        )

        assert response.status_code == 204
        assert Team.objects.filter(name="New Team", club=club).exists()

    def test_unauthenticated_redirects(self):
        client = Client()
        response = client.get(reverse("clubs:add_team"))
        assert response.status_code == 302


class TestEditTeam:
    def test_can_edit_non_primary_team(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        team = TeamFactory(club=club, is_primary=False, name="OldName")
        client = logged_in_client(user, club)

        response = client.post(
            reverse("clubs:edit_team", args=[team.id]),
            data={"name": "NewName", "description": "Updated"},
        )

        assert response.status_code == 204
        team.refresh_from_db()
        assert team.name == "NewName"

    def test_cannot_edit_primary_team(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        team = TeamFactory(club=club, is_primary=True)
        client = logged_in_client(user, club)

        response = client.get(reverse("clubs:edit_team", args=[team.id]))

        assert response.status_code == 404

    def test_cannot_edit_other_clubs_team(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        other_club = ClubFactory()
        team = TeamFactory(club=other_club, is_primary=False)
        client = logged_in_client(user, club)

        response = client.get(reverse("clubs:edit_team", args=[team.id]))

        assert response.status_code == 404


class TestRemoveTeam:
    def test_deactivates_non_primary_team(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        team = TeamFactory(club=club, is_primary=False, is_active=True)
        client = logged_in_client(user, club)

        response = client.post(reverse("clubs:remove_team", args=[team.id]))

        assert response.status_code == 204
        team.refresh_from_db()
        assert team.is_active is False

    def test_cannot_remove_primary_team(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        team = TeamFactory(club=club, is_primary=True, is_active=True)
        client = logged_in_client(user, club)

        client.post(reverse("clubs:remove_team", args=[team.id]))

        team.refresh_from_db()
        assert team.is_active is True


class TestAddAgent:
    @patch("clubs.views.assign_or_invite_agent_to_club")
    def test_post_calls_service(self, mock_assign, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        client = logged_in_client(user, club)

        response = client.post(
            reverse("clubs:add_agent"),
            data={"email": "new@example.com"},
        )

        assert response.status_code == 204
        mock_assign.assert_called_once()

    @patch("clubs.views.assign_or_invite_agent_to_club")
    def test_duplicate_invite_returns_409(self, mock_assign, logged_in_client):
        from users.services import NewAgentRequestAlreadyExistsError

        mock_assign.side_effect = NewAgentRequestAlreadyExistsError()
        user = UserFactory()
        club = ClubFactory()
        client = logged_in_client(user, club)

        response = client.post(
            reverse("clubs:add_agent"),
            data={"email": "existing@example.com"},
        )

        assert response.status_code == 409


class TestRemoveAgent:
    @patch("clubs.views.unassign_or_cancel_agent_invite_from_club")
    def test_removes_agent(self, mock_unassign, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        client = logged_in_client(user, club)

        response = client.post(
            reverse("clubs:remove_agent"),
            data={"email": "agent@example.com"},
        )

        assert response.status_code == 204
        mock_unassign.assert_called_once()


class TestNotificationsDialog:
    def test_get_shows_notifications(self, logged_in_client):
        user = UserFactory()
        agent = AgentFactory(user=user)
        club = ClubFactory()
        agent_at_club = AgentAtClubFactory(agent=agent, club=club, is_active=True)
        ClubNotification.objects.create(
            agent_at_club=agent_at_club, subject="Test", message="Hello"
        )
        client = logged_in_client(user, club)

        response = client.get(reverse("clubs:notifications_dialog"))

        assert response.status_code == 200

    def test_post_marks_as_read(self, logged_in_client):
        user = UserFactory()
        agent = AgentFactory(user=user)
        club = ClubFactory()
        agent_at_club = AgentAtClubFactory(agent=agent, club=club, is_active=True)
        notification = ClubNotification.objects.create(
            agent_at_club=agent_at_club, subject="Test", message="Hello", is_read=False
        )
        client = logged_in_client(user, club)

        response = client.post(reverse("clubs:notifications_dialog"))

        assert response.status_code == 204
        notification.refresh_from_db()
        assert notification.is_read is True

    def test_unauthenticated_redirects(self):
        client = Client()
        response = client.get(reverse("clubs:notifications_dialog"))
        assert response.status_code == 302
