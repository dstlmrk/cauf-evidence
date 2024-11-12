from core.models import AuditModel
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class CompetitionTypeEnum(models.IntegerChoices):
    OUTDOOR = 1, "Outdoor"
    INDOOR = 2, "Indoor"
    BEACH = 3, "Beach"


class ApplicationStateEnum(models.IntegerChoices):
    AWAITING_PAYMENT = 1, "Awaiting Payment"
    PAID = 2, "Paid"
    ACCEPTED = 3, "Accepted"
    DECLINED = 4, "Declined"
    WITHDRAWN = 5, "Withdrawn"


class Season(AuditModel):
    name = models.CharField(
        max_length=32,
        unique=True,
    )
    player_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    def __str__(self) -> str:
        return self.name


class Division(AuditModel):
    name = models.CharField(
        max_length=32,
        unique=True,
    )
    is_female_allowed = models.BooleanField(
        default=True,
    )
    is_male_allowed = models.BooleanField(
        default=True,
    )

    def __str__(self) -> str:
        return self.name


class AgeRestriction(AuditModel):
    name = models.CharField(
        max_length=32,
        unique=True,
    )
    min = models.PositiveSmallIntegerField(
        default=0,
        validators=[MaxValueValidator(99)],
    )
    max = models.PositiveSmallIntegerField(
        default=99,
        validators=[MaxValueValidator(99)],
    )

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValidationError("Min age must be less than or equal to max age.")


class Competition(AuditModel):
    name = models.CharField(
        max_length=48,
    )
    season = models.ForeignKey(
        Season,
        on_delete=models.PROTECT,
    )
    division = models.ForeignKey(
        Division,
        on_delete=models.PROTECT,
    )
    age_restriction = models.ForeignKey(
        AgeRestriction,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    is_for_national_teams = models.BooleanField(
        default=False,
    )
    type = models.IntegerField(
        choices=CompetitionTypeEnum.choices,
    )
    player_fee_per_tournament = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    is_exempted_from_season_fee = models.BooleanField(
        default=False,
    )
    deposit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Deposit (CZK) required to secure a spot in the competition",
    )
    registration_deadline = models.DateTimeField()

    class Meta:
        unique_together = ("name", "season", "type", "division", "age_restriction")

    def __str__(self) -> str:
        return f"<Competition({self.pk}, name={self.name})>"


class CompetitionApplication(AuditModel):
    team_name = models.CharField(  # copied name at the time of application
        max_length=48,
    )
    state = models.IntegerField(
        choices=ApplicationStateEnum.choices,
        default=ApplicationStateEnum.AWAITING_PAYMENT,
    )
    invoice = models.ForeignKey(
        "finance.Invoice",
        null=True,
        on_delete=models.PROTECT,
        related_name="applications",
    )
    competition = models.ForeignKey(
        Competition,
        on_delete=models.PROTECT,
    )
    team = models.ForeignKey(
        "clubs.Team", on_delete=models.PROTECT, related_name="competition_application"
    )
    registered_by = models.ForeignKey(
        User,
        null=False,
        on_delete=models.PROTECT,
    )

    class Meta:
        unique_together = ("competition", "team")

    def __str__(self) -> str:
        return (
            f"<CompetitionApplication({self.pk},"
            f" team_name={self.team_name}, competition={self.competition})>"
        )

    def registrant_name(self) -> str:
        return self.registered_by.get_full_name()
