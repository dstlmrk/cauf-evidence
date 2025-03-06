from decimal import Decimal

from core.models import AuditModel
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Tournament(AuditModel):
    competition = models.ForeignKey(
        "competitions.Competition",
        on_delete=models.PROTECT,
        related_name="tournaments",
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

    @property
    def has_open_rosters(self) -> bool:
        return self.rosters_deadline > timezone.now()


class TeamAtTournament(AuditModel):
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.PROTECT,
        related_name="teams",
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
        validators=[MinValueValidator(Decimal(0)), MaxValueValidator(Decimal(20))],
    )
    seeding = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )

    class Meta:
        unique_together = (
            ("tournament", "application"),
            ("tournament", "seeding"),
        )
        app_label = "tournaments"

    def __str__(self) -> str:
        return f"{self.application.team_name}"


class MemberAtTournament(AuditModel):
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.PROTECT,
        related_name="members",
    )
    team_at_tournament = models.ForeignKey(
        TeamAtTournament,
        on_delete=models.PROTECT,
        related_name="members",
    )
    member = models.ForeignKey(
        "members.Member",
        on_delete=models.PROTECT,
    )
    is_captain = models.BooleanField(
        default=False,
        verbose_name="Captain",
        help_text="Only one captain per team is allowed",
    )
    is_spirit_captain = models.BooleanField(
        default=False,
        verbose_name="Spirit captain",
        help_text="Only one spirit captain per team is allowed",
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

    def __str__(self) -> str:
        return f"{self.member}"
