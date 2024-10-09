from core.models import AuditModel
from django.core.validators import RegexValidator
from django.db import models

from clubs.validators import (
    validate_account_number,
    validate_bank_code,
    validate_identification_number,
)


class Organization(AuditModel):
    name = models.CharField(max_length=128, unique=True)
    identification_number = models.CharField(
        max_length=8,
        unique=True,
        validators=[validate_identification_number],
        help_text="IČO",
    )
    account_number = models.CharField(
        max_length=17,  # 6 digits for prefix, 10 digits for account number, 1 hyphen
        unique=True,
        validators=[validate_account_number],
    )
    bank_code = models.CharField(
        max_length=4,
        validators=[validate_bank_code],
    )
    street = models.CharField(max_length=128)
    city = models.CharField(max_length=128)
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
        max_length=50,
        default="Česká republika",
    )

    def __str__(self) -> str:
        return f"<Organization({self.pk}, name={self.name})>"


class Club(AuditModel):
    name = models.CharField(max_length=128)
    email = models.EmailField()
    website = models.URLField()
    city = models.CharField(max_length=128)
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE)

    class Meta:
        permissions = (("manage_club", "Can manage club"),)

    def __str__(self) -> str:
        return f"<Club({self.pk}, name={self.name})>"
