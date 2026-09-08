from django.apps import AppConfig


class TournamentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tournaments"

    def ready(self) -> None:
        from tournaments import signals, tasks  # noqa: F401
