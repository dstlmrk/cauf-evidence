from typing import Any

from core.models import AuditModel
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models

from clubs.validators import validate_identification_number


class Club(AuditModel):
    name = models.CharField(
        max_length=48,
        help_text="Only administrators can change this value",
    )
    short_name = models.CharField(
        max_length=4,
        blank=True,
        help_text="Short name of the club (2-4 characters)",
        validators=[MinLengthValidator(2)],
    )
    email = models.EmailField(
        blank=True,
        help_text="Contact email of the club",
    )
    website = models.URLField(
        blank=True,
        help_text="URL of the club's website",
    )
    city = models.CharField(
        max_length=64,
        blank=True,
        help_text="City where the club is located",
    )
    organization_name = models.CharField(
        max_length=64,
        blank=True,
        help_text="Name of the organization with legal entity status",
    )
    identification_number = models.CharField(
        max_length=8,
        blank=True,
        validators=[validate_identification_number],
        help_text="Company identification number",
    )
    fakturoid_subject_id = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="ID of the subject in Fakturoid. The club cannot be invoiced without this ID.",
    )

    class Meta:
        permissions = (("manage_club", "Can manage club"),)

    def __str__(self) -> str:
        return self.short_name or self.name

    def clean(self) -> None:
        if self.organization_name and (
            Club.objects.filter(organization_name=self.organization_name)
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError(
                {"organization_name": "Club with this organization name already exists."}
            )

        if self.identification_number and (
            Club.objects.filter(identification_number=self.identification_number)
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError(
                {"identification_number": "Club with this identification number already exists."}
            )


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

    class Meta:
        ordering = ["name"]

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


class ClubNotification(AuditModel):
    agent_at_club = models.ForeignKey("users.AgentAtClub", on_delete=models.PROTECT)
    subject = models.CharField(max_length=64)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"<ClubNotification({self.pk}, agent={self.agent_at_club})>"
