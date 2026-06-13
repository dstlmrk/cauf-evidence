import pytest
from django.urls import reverse

from tests.factories import ClubFactory, UserFactory


@pytest.mark.django_db
class TestSearchView:
    def test_search_without_tournament_id_returns_200(self, logged_in_client):
        club = ClubFactory()
        client = logged_in_client(UserFactory(), club)

        response = client.get(reverse("members:search"), data={"q": "test"})

        assert response.status_code == 200
        assert "results" in response.json()

    def test_search_with_null_tournament_id_returns_200(self, logged_in_client):
        club = ClubFactory()
        client = logged_in_client(UserFactory(), club)

        response = client.get(
            reverse("members:search"), data={"q": "test", "tournament_id": "null"}
        )

        assert response.status_code == 200
