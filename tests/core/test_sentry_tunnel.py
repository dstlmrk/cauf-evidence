import json
from unittest.mock import MagicMock, patch

from django.test import Client
from django.urls import reverse

SENTRY_DSN = "https://key@o123.ingest.us.sentry.io/456"


class TestSentryTunnelView:
    @patch("core.views.requests.post")
    def test_forwards_envelope_to_sentry(self, mock_post: MagicMock, client: Client, settings):
        settings.SENTRY_DSN = SENTRY_DSN
        mock_post.return_value = MagicMock(status_code=200)

        envelope = (
            json.dumps({"dsn": SENTRY_DSN}).encode()
            + b"\n"
            + b'{"type":"event"}\n{"message":"test"}'
        )
        response = client.post(
            reverse("api:sentry_tunnel"), data=envelope, content_type="application/octet-stream"
        )

        assert response.status_code == 200
        mock_post.assert_called_once_with(
            "https://o123.ingest.us.sentry.io/api/456/envelope/",
            data=envelope,
            headers={"Content-Type": "application/x-sentry-envelope"},
            timeout=5,
        )
