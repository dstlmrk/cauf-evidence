from core.models import AuditModel
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Tournament(AuditModel):
    competition = models.ForeignKey(
        "competitions.Competition",
        on_delete=models.PROTECT,
    )
    name = models.CharField(max_length=48)
    start_date = models.DateField()
    end_date = models.DateField()
    location = models.CharField(max_length=128)
    rosters_deadline = models.DateTimeField()

    class Meta:
        unique_together = ("competition", "name")
        app_label = "tournaments"

    def __str__(self) -> str:
        return f"{self.name} ({self.competition})"


class TeamAtTournament(AuditModel):
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.PROTECT,
    )
    application = models.ForeignKey(
        "competitions.CompetitionApplication",
        on_delete=models.PROTECT,
    )
    final_placement = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )
    spirit_avg = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
    )

    class Meta:
        unique_together = ("tournament", "application")
        app_label = "tournaments"


class MemberAtTournament(AuditModel):
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.PROTECT,
    )
    team_at_tournament = models.ForeignKey(
        TeamAtTournament,
        on_delete=models.PROTECT,
    )
    member = models.ForeignKey(
        "members.Member",
        on_delete=models.PROTECT,
    )
    is_captain = models.BooleanField(
        default=False,
        verbose_name="Captain",
    )
    is_coach = models.BooleanField(
        default=False,
        verbose_name="Coach",
    )
    jersey_number = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(99)],
    )

    class Meta:
        unique_together = (
            ("tournament", "member"),
            ("team_at_tournament", "member"),
        )
