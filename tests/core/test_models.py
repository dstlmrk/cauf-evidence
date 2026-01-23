from core.models import AppSettings


class TestAppSettings:
    def test_singleton_returns_same_instance(self):
        settings1 = AppSettings.get_solo()
        settings2 = AppSettings.get_solo()
        assert settings1.pk == settings2.pk

    def test_default_values(self):
        AppSettings.objects.all().delete()
        AppSettings.clear_cache()
        settings = AppSettings.get_solo()
        assert settings.email_required is False
        assert settings.email_verification_required is False
        assert settings.min_age_verification_required is False
        assert settings.team_management_enabled is False
        assert settings.transfers_enabled is False

    def test_can_update_and_persist(self):
        settings = AppSettings.get_solo()
        settings.email_required = True
        settings.transfers_enabled = True
        settings.save()

        refreshed = AppSettings.get_solo()
        assert refreshed.email_required is True
        assert refreshed.transfers_enabled is True
