from unittest.mock import patch

from django.urls import reverse
from users.services import NewAgentRequestAlreadyExistsError

from tests.factories import ClubFactory, TransferFactory, UserFactory

HTMX_HEADERS = {"HX-Request": "true"}


@patch("core.middleware.sentry_sdk.capture_message")
class TestSilentHtmxErrorReporting:
    def test_silent_4xx_is_reported(self, mock_capture, logged_in_client):
        client = logged_in_client(UserFactory(), ClubFactory())

        response = client.post(
            reverse("members:change_transfer_state"),
            data={"transfer_id": TransferFactory().id},
            headers=HTMX_HEADERS,
        )

        assert response.status_code == 400
        mock_capture.assert_called_once_with(
            "Silent HTMX error response 400 from members:change_transfer_state", level="error"
        )

    @patch("clubs.views.assign_or_invite_agent_to_club")
    def test_4xx_with_message_is_not_reported(self, mock_assign, mock_capture, logged_in_client):
        mock_assign.side_effect = NewAgentRequestAlreadyExistsError()
        client = logged_in_client(UserFactory(), ClubFactory())

        response = client.post(
            reverse("clubs:add_agent"),
            data={"email": "existing@example.com"},
            headers=HTMX_HEADERS,
        )

        assert response.status_code == 409
        assert "messages" in response.headers["HX-Trigger"]
        mock_capture.assert_not_called()

    def test_non_htmx_request_is_not_reported(self, mock_capture, logged_in_client):
        client = logged_in_client(UserFactory(), ClubFactory())

        response = client.post(
            reverse("members:change_transfer_state"),
            data={"transfer_id": TransferFactory().id},
        )

        assert response.status_code == 400
        mock_capture.assert_not_called()
