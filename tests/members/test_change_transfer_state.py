import pytest
from django.urls import reverse

from tests.factories import ClubFactory, TransferFactory, UserFactory


@pytest.mark.django_db
class TestChangeTransferStateView:
    def test_unknown_action_returns_400(self, logged_in_client):
        club = ClubFactory()
        transfer = TransferFactory()
        client = logged_in_client(UserFactory(), club)

        response = client.post(
            reverse("members:change_transfer_state"),
            data={"transfer_id": transfer.id, "action": "destroy"},
        )

        assert response.status_code == 400

    def test_missing_action_returns_400(self, logged_in_client):
        club = ClubFactory()
        transfer = TransferFactory()
        client = logged_in_client(UserFactory(), club)

        response = client.post(
            reverse("members:change_transfer_state"),
            data={"transfer_id": transfer.id},
        )

        assert response.status_code == 400
