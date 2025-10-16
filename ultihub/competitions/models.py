from decimal import Decimal

from core.models import AuditModel
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from competitions.enums import ApplicationStateEnum, CompetitionFeeTypeEnum, EnvironmentEnum


class Season(AuditModel):
    name = models.CharField(
        max_length=32,
        unique=True,
    )
    discounted_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal(0))],
    )
    regular_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal(0))],
    )
    fee_at_tournament = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal(0))],
    )
    invoices_generated_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    min_allowed_age = models.PositiveSmallIntegerField(
        help_text="Members younger than this age are not allowed to participate",
        validators=[MaxValueValidator(99)],
    )
    age_reference_date = models.DateField(
        help_text="Determining date for age calculation (typically 31st December)",
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


class AgeLimit(AuditModel):
    name = models.CharField(
        max_length=32,
        unique=True,
    )
    m_min = models.PositiveSmallIntegerField(
        default=14,
        validators=[MaxValueValidator(99)],
        verbose_name="Minimum age for men",
        help_text="Minimum age allowed (inclusive) for men",
    )
    m_max = models.PositiveSmallIntegerField(
        default=99,
        validators=[MaxValueValidator(99)],
        verbose_name="Maximum age for men",
        help_text="Maximum age allowed (inclusive) for men",
    )
    f_min = models.PositiveSmallIntegerField(
        default=14,
        validators=[MaxValueValidator(99)],
        verbose_name="Minimum age for women",
        help_text="Minimum age allowed (inclusive) for women",
    )
    f_max = models.PositiveSmallIntegerField(
        default=99,
        validators=[MaxValueValidator(99)],
        verbose_name="Maximum age for women",
        help_text="Maximum age allowed (inclusive) for women",
    )

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        if self.m_min > self.m_max or self.f_min > self.f_max:
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
    age_limit = models.ForeignKey(
        AgeLimit,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    environment = models.IntegerField(
        choices=EnvironmentEnum.choices,
    )
    fee_type = models.IntegerField(
        choices=CompetitionFeeTypeEnum.choices,
        help_text="FREE and DISCOUNTED cause no player fee to be charged",
    )
    deposit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal(0))],
        help_text="Deposit (CZK) required to secure a spot in the competition",
    )
    registration_deadline = models.DateTimeField()
    description = models.TextField(
        blank=True,
    )

    class Meta:
        unique_together = ("name", "season", "environment", "division", "age_limit")

    def __str__(self) -> str:
        name = f"BEACH {self.name}" if self.environment == EnvironmentEnum.BEACH else self.name
        return f"{name} {self.season} {str(self.division).upper()} {self.age_limit or ''}".strip()

    @property
    def has_open_registration(self) -> bool:
        return self.registration_deadline > timezone.now()

    def season_fee(self) -> Decimal:
        if self.fee_type == CompetitionFeeTypeEnum.REGULAR:
            return self.season.regular_fee
        if self.fee_type == CompetitionFeeTypeEnum.DISCOUNTED:
            return self.season.discounted_fee
        return Decimal(0)

    def player_fee(self) -> Decimal:
        if self.fee_type == CompetitionFeeTypeEnum.REGULAR:
            return self.season.fee_at_tournament
        return Decimal(0)


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
        blank=True,
        on_delete=models.PROTECT,
        related_name="applications",
    )
    competition = models.ForeignKey(
        Competition,
        on_delete=models.PROTECT,
        related_name="applications",
    )
    team = models.ForeignKey(
        "clubs.Team",
        on_delete=models.PROTECT,
        related_name="applications",
    )
    registered_by = models.ForeignKey(
        User,
        null=False,
        on_delete=models.PROTECT,
    )
    final_placement = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )

    class Meta:
        unique_together = ("competition", "team")

    def __str__(self) -> str:
        return f"{self.team_name} ({self.competition})"

    def registrant_name(self) -> str:
        return self.registered_by.get_full_name()
