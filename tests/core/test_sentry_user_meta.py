from django.test import Client
from django.urls import reverse


class TestSentryUserMeta:
    def test_authenticated_user_has_sentry_meta_tags(self, client: Client, user):
        client.force_login(user)
        response = client.get(reverse("faq"))
        content = response.content.decode()

        assert f'<meta name="sentry-user-id" content="{user.pk}" />' in content
        assert f'<meta name="sentry-user-email" content="{user.email}" />' in content

    def test_anonymous_user_has_no_sentry_meta_tags(self, client: Client):
        response = client.get(reverse("faq"))
        content = response.content.decode()

        assert "sentry-user-id" not in content
        assert "sentry-user-email" not in content
