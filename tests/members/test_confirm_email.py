from datetime import timedelta

from django.test import Client
from django.urls import reverse
from django.utils.timezone import now
from members.models import EMAIL_CONFIRMATION_TOKEN_VALIDITY

from tests.factories import MemberFactory


class TestConfirmEmail:
    def test_fresh_token_renders_page(self):
        member = MemberFactory()
        client = Client()

        response = client.get(
            reverse("members:confirm_email", args=[member.email_confirmation_token])
        )

        assert response.status_code == 200

    def test_expired_token_returns_404(self):
        member = MemberFactory()
        member.email_confirmation_token_created_at = (
            now() - EMAIL_CONFIRMATION_TOKEN_VALIDITY - timedelta(days=1)
        )
        member.save()
        client = Client()

        response = client.get(
            reverse("members:confirm_email", args=[member.email_confirmation_token])
        )

        assert response.status_code == 404
