from typing import Any

from django.db import migrations, models
from django.utils import timezone


def backfill_token_created_at(apps: Any, schema_editor: Any) -> None:
    # Give existing pending confirmations a fresh 30-day window so the new
    # expiry rule does not immediately invalidate them.
    Member = apps.get_model("members", "Member")
    Member.objects.filter(email_confirmation_token__isnull=False).update(
        email_confirmation_token_created_at=timezone.now()
    )


class Migration(migrations.Migration):
    dependencies = [
        ("members", "0011_alter_transfer_state"),
    ]

    operations = [
        migrations.AddField(
            model_name="member",
            name="email_confirmation_token_created_at",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.RunPython(backfill_token_created_at, migrations.RunPython.noop),
    ]
