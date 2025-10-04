from typing import Any

from django.db import migrations
from django.db.migrations.state import StateApps


def create_default_settings(apps: StateApps, schema_editor: Any) -> None:
    AppSettings = apps.get_model("core", "AppSettings")
    AppSettings.objects.get_or_create(
        id=1,
        defaults={
            "email_required": False,
            "email_verification_required": True,
            "min_age_verification_required": True,
            "team_management_enabled": False,
            "transfers_enabled": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_default_settings),
    ]
