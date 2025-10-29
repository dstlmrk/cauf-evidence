from competitions.enums import CompetitionFeeTypeEnum, EnvironmentEnum
from core.models import AuditModel
from django.core.exceptions import ValidationError
from django.db import models
from django_countries.fields import CountryField

from international_tournaments.enums import InternationalTournamentTypeEnum


class InternationalTournament(AuditModel):
    name = models.CharField(max_length=48)
    season = models.ForeignKey(
        "competitions.Season",
        on_delete=models.PROTECT,
        related_name="international_tournaments",
    )
    date_from = models.DateField()
    date_to = models.DateField()
    city = models.CharField(max_length=48)
    country = CountryField()
    type = models.IntegerField(
        choices=InternationalTournamentTypeEnum.choices,
    )
    environment = models.IntegerField(
        choices=EnvironmentEnum.choices,
    )
    fee_type = models.IntegerField(
        choices=CompetitionFeeTypeEnum.choices,
    )
    teams: models.ManyToManyField = models.ManyToManyField(
        "clubs.Team",
        through="TeamAtInternationalTournament",
        related_name="international_tournaments",
    )

    class Meta:
        app_label = "international_tournaments"

    def __str__(self) -> str:
        return f"{self.name} ({self.city}, {self.country})"

    def clean(self) -> None:
        super().clean()
        if self.date_from > self.date_to:
            raise ValidationError({"date_from": "Start date cannot be after end date"})


class TeamAtInternationalTournament(AuditModel):
    tournament = models.ForeignKey(
        InternationalTournament,
        on_delete=models.PROTECT,
        related_name="team_participations",
    )
    team = models.ForeignKey(
        "clubs.Team",
        on_delete=models.PROTECT,
        related_name="international_tournament_participations",
    )
    age_limit = models.ForeignKey(
        "competitions.AgeLimit",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    division = models.ForeignKey(
        "competitions.Division",
        on_delete=models.PROTECT,
    )
    team_name = models.CharField(
        max_length=48,
        help_text="Team name at the time of participation (for historical purposes)",
    )
    final_placement = models.IntegerField(
        null=True,
        blank=True,
        help_text="Final placement at the tournament",
    )
    total_teams = models.IntegerField(
        null=True,
        blank=True,
        help_text="Total number of teams at the tournament in this division",
    )

    class Meta:
        unique_together = ("tournament", "team", "age_limit", "division")
        app_label = "international_tournaments"

    def __str__(self) -> str:
        return f"{self.team_name} at {self.tournament}"

    def clean(self) -> None:
        super().clean()
        if self.final_placement and self.total_teams:
            if self.final_placement > self.total_teams:
                raise ValidationError(
                    {"final_placement": "Final placement cannot be greater than total teams"}
                )
            if self.final_placement < 1:
                raise ValidationError({"final_placement": "Final placement must be at least 1"})
        if self.total_teams and self.total_teams < 1:
            raise ValidationError({"total_teams": "Total teams must be at least 1"})
