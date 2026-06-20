import pytest
from django.urls import reverse
from members.models import FavouriteMember

from tests.factories import ClubFactory, MemberFactory, UserFactory


@pytest.mark.django_db
class TestToggleFavouriteMember:
    def test_first_toggle_creates_favourite(self, logged_in_client):
        club = ClubFactory()
        member = MemberFactory(club=club)
        user = UserFactory()
        client = logged_in_client(user, club)

        response = client.post(reverse("members:toggle_favourite", args=[member.id]))

        assert response.status_code == 204
        assert FavouriteMember.objects.filter(agent=user.agent, member=member).exists()

    def test_second_toggle_removes_favourite(self, logged_in_client):
        club = ClubFactory()
        member = MemberFactory(club=club)
        user = UserFactory()
        client = logged_in_client(user, club)

        client.post(reverse("members:toggle_favourite", args=[member.id]))
        client.post(reverse("members:toggle_favourite", args=[member.id]))

        assert not FavouriteMember.objects.filter(agent=user.agent, member=member).exists()

    def test_member_of_another_club_returns_404(self, logged_in_client):
        club = ClubFactory()
        other_member = MemberFactory(club=ClubFactory())
        client = logged_in_client(UserFactory(), club)

        response = client.post(reverse("members:toggle_favourite", args=[other_member.id]))

        assert response.status_code == 404
        assert not FavouriteMember.objects.filter(member=other_member).exists()

    def test_favourites_are_scoped_per_agent(self, logged_in_client):
        club = ClubFactory()
        member = MemberFactory(club=club)
        first_user = UserFactory()
        second_user = UserFactory()

        # Both clients also create an Agent for their user, so we can assert the
        # favourite belongs to the first agent only.
        first_client = logged_in_client(first_user, club)
        logged_in_client(second_user, club)

        first_client.post(reverse("members:toggle_favourite", args=[member.id]))

        assert FavouriteMember.objects.filter(agent=first_user.agent, member=member).exists()
        assert not FavouriteMember.objects.filter(agent=second_user.agent, member=member).exists()
