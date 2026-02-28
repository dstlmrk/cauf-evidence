from unittest.mock import MagicMock

from django.test import override_settings

from core.context_processors import app_settings


class TestAppSettingsContextProcessor:
    def test_contains_sentry_dsn(self):
        with override_settings(SENTRY_DSN="https://key@sentry.io/123"):
            result = app_settings(MagicMock())
            assert result["SENTRY_DSN"] == "https://key@sentry.io/123"

    def test_contains_environment(self):
        with override_settings(ENVIRONMENT="production"):
            result = app_settings(MagicMock())
            assert result["ENVIRONMENT"] == "production"

    def test_empty_sentry_dsn(self):
        with override_settings(SENTRY_DSN=""):
            result = app_settings(MagicMock())
            assert result["SENTRY_DSN"] == ""

    def test_contains_national_team_club_id(self):
        result = app_settings(MagicMock())
        assert "NATIONAL_TEAM_CLUB_ID" in result

    def test_contains_app_settings_key(self):
        result = app_settings(MagicMock())
        assert "app_settings" in result


class TestSentryMetaTags:
    def test_meta_tags_rendered_in_html(self, client):
        with override_settings(
            SENTRY_DSN="https://key@sentry.io/123",
            ENVIRONMENT="staging",
        ):
            response = client.get("/faq")
            content = response.content.decode()
            assert '<meta name="sentry-dsn" content="https://key@sentry.io/123" />' in content
            assert '<meta name="environment" content="staging" />' in content

    def test_empty_sentry_dsn_renders_empty_meta(self, client):
        with override_settings(SENTRY_DSN="", ENVIRONMENT="test"):
            response = client.get("/faq")
            content = response.content.decode()
            assert '<meta name="sentry-dsn" content="" />' in content
