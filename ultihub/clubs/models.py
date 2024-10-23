from typing import Any

from core.models import AuditModel
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from clubs.validators import (
    validate_account_number,
    validate_bank_code,
    validate_identification_number,
)


class Club(AuditModel):
    name = models.CharField(
        max_length=48,
    )
    email = models.EmailField(
        help_text="Contact email of the club",
    )
    website = models.URLField(
        help_text="URL of the club's website",
    )
    city = models.CharField(
        max_length=64,
        help_text="City where the club is located",
    )

    class Meta:
        permissions = (("manage_club", "Can manage club"),)

    def __str__(self) -> str:
        return f"<Club({self.pk}, name={self.name})>"


class Organization(AuditModel):
    name = models.CharField(
        max_length=64,
        unique=True,
    )
    identification_number = models.CharField(
        max_length=8,
        unique=True,
        validators=[validate_identification_number],
        help_text="Company identification number",
    )
    account_number = models.CharField(
        max_length=17,  # 6 digits for prefix, 10 digits for account number, 1 hyphen
        blank=True,
        validators=[validate_account_number],
    )
    bank_code = models.CharField(
        max_length=4,
        blank=True,
        validators=[validate_bank_code],
    )
    street = models.CharField(
        max_length=64,
    )
    city = models.CharField(
        max_length=64,
    )
    postal_code = models.CharField(
        max_length=6,
        validators=[
            RegexValidator(
                regex=r"^\d{3}\s?\d{2}$",
                message="Postal code must be in format XXXXX or XXX XX.",
            )
        ],
    )
    country = models.CharField(
        max_length=32,
        default="Česká republika",
    )
    club = models.OneToOneField(
        Club,
        on_delete=models.PROTECT,
    )

    def __str__(self) -> str:
        return f"<Organization({self.pk}, name={self.name})>"


class Team(AuditModel):
    name = models.CharField(
        max_length=48,
    )
    description = models.CharField(
        max_length=64,
        blank=True,
        help_text="Only for club internal purposes",
    )
    is_active = models.BooleanField(
        default=True,
    )
    is_primary = models.BooleanField(
        default=False,
    )
    club = models.ForeignKey(
        Club,
        on_delete=models.PROTECT,
    )

    def __str__(self) -> str:
        return f"<Team({self.pk}, name={self.name})>"

    def clean(self) -> None:
        if (
            self.is_active
            and Team.objects.filter(name=self.name, is_active=True).exclude(pk=self.pk).exists()
        ):
            raise ValidationError({"name": "There is already an active team with this name."})

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)
