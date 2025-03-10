# Generated by Django 5.1.1 on 2024-11-12 15:05

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("competitions", "0001_initial"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="competition",
            unique_together={("name", "season", "type", "division", "age_restriction")},
        ),
        migrations.AddField(
            model_name="competition",
            name="deposit",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Deposit (CZK) required to secure a spot in the competition",
                max_digits=10,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="competition",
            name="type",
            field=models.IntegerField(choices=[(1, "Outdoor"), (2, "Indoor"), (3, "Beach")]),
        ),
        migrations.CreateModel(
            name="CompetitionApplication",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("team_name", models.CharField(max_length=48)),
                (
                    "state",
                    models.IntegerField(
                        choices=[
                            (1, "Awaiting Payment"),
                            (2, "Paid"),
                            (3, "Accepted"),
                            (4, "Declined"),
                            (5, "Withdrawn"),
                        ],
                        default=1,
                    ),
                ),
                (
                    "competition",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to="competitions.competition"
                    ),
                ),
            ],
        ),
    ]
