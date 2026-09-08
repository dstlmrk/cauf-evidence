from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tournaments", "0006_populate_tournament_winners"),
    ]

    operations = [
        migrations.AddField(
            model_name="tournament",
            name="rosters_reminder_sent_at",
            field=models.DateTimeField(
                blank=True,
                editable=False,
                help_text="When the reminder about the approaching rosters deadline was sent",
                null=True,
            ),
        ),
    ]
