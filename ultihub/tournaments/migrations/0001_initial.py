# Generated by Django 5.1.1 on 2024-12-23 15:12

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("competitions", "0007_competition_description"),
        ("members", "0004_remove_member_address_member_city_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Tournament",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=48)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("location", models.CharField(max_length=128)),
                ("rosters_deadline", models.DateTimeField()),
                (
                    "competition",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to="competitions.competition"
                    ),
                ),
            ],
            options={
                "unique_together": {("competition", "name")},
            },
        ),
        migrations.CreateModel(
            name="TeamAtTournament",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "final_placement",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(1)],
                    ),
                ),
                (
                    "spirit_avg",
                    models.DecimalField(
                        blank=True,
                        decimal_places=3,
                        max_digits=5,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(20),
                        ],
                    ),
                ),
                (
                    "application",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="competitions.competitionapplication",
                    ),
                ),
                (
                    "tournament",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to="tournaments.tournament"
                    ),
                ),
            ],
            options={
                "unique_together": {("tournament", "application")},
            },
        ),
        migrations.CreateModel(
            name="MemberAtTournament",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_captain", models.BooleanField(default=False, verbose_name="Captain")),
                ("is_coach", models.BooleanField(default=False, verbose_name="Coach")),
                (
                    "jersey_number",
                    models.IntegerField(
                        blank=True,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(99),
                        ],
                    ),
                ),
                (
                    "member",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to="members.member"
                    ),
                ),
                (
                    "team_at_tournament",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="tournaments.teamattournament",
                    ),
                ),
                (
                    "tournament",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to="tournaments.tournament"
                    ),
                ),
            ],
            options={
                "unique_together": {("team_at_tournament", "member"), ("tournament", "member")},
            },
        ),
    ]
