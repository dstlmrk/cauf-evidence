from django.contrib.messages import get_messages
from django.test import Client
from django.urls import reverse
from guardian.shortcuts import assign_perm

from tests.factories import ClubFactory, UserFactory


class TestSwitchClub:
    def test_missing_club_id_returns_400(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        client = logged_in_client(user, club)

        response = client.post(reverse("users:switch_club"))

        assert response.status_code == 400

    def test_unknown_club_returns_404(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        client = logged_in_client(user, club)

        response = client.post(
            reverse("users:switch_club"),
            data={"club_id": 999999},
        )

        assert response.status_code == 404

    def test_without_permission_returns_403_and_no_message(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        other_club = ClubFactory()
        client = logged_in_client(user, club)

        response = client.post(
            reverse("users:switch_club"),
            data={"club_id": other_club.id},
        )

        assert response.status_code == 403
        assert list(get_messages(response.wsgi_request)) == []
        # Session must keep the originally selected club.
        assert client.session["club"]["id"] == club.id

    def test_valid_switch_succeeds(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        target_club = ClubFactory()
        assign_perm("manage_club", user, target_club)
        client = logged_in_client(user, club)

        response = client.post(
            reverse("users:switch_club"),
            data={"club_id": target_club.id},
        )

        assert response.status_code == 204
        assert response.headers["HX-Refresh"] == "true"
        assert client.session["club"]["id"] == target_club.id
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        assert "Club switched successfully" in messages

    def test_unauthenticated_redirects(self):
        client = Client()
        response = client.post(reverse("users:switch_club"))
        assert response.status_code == 302
