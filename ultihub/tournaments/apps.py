from django.apps import AppConfig


class TournamentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tournaments"

    def ready(self):
        from tournaments.scheduler import schedule_hello_world_task
        schedule_hello_world_task()
