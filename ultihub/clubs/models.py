import uuid
from typing import Any

from core.models import AuditModel
from core.tasks import send_email
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django_countries.fields import CountryField
from users.adapters import logger

from clubs.validators import validate_czech_birth_number, validate_identification_number


class MemberSexEnum(models.IntegerChoices):
    FEMALE = 1, "Female"
    MALE = 2, "Male"


class CoachLicenceClassEnum(models.IntegerChoices):
    FIRST = 1, "First"
    SECOND = 2, "Second"
    THIRD = 3, "Third"


class Club(AuditModel):
    name = models.CharField(
        max_length=48,
        help_text="Only administrators can change this field",
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

    class Meta:
        permissions = (("manage_club", "Can manage club"),)

    def __str__(self) -> str:
        return f"<Club({self.pk}, name={self.name})>"

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


class Member(AuditModel):
    club = models.ForeignKey(
        Club,
        on_delete=models.PROTECT,
    )
    first_name = models.CharField(
        max_length=32,
        null=False,
    )
    last_name = models.CharField(
        max_length=32,
        null=False,
    )
    birth_date = models.DateField(
        null=False,
    )
    sex = models.IntegerField(
        choices=MemberSexEnum.choices,
    )
    citizenship = CountryField(
        default="CZ",
    )
    birth_number = models.CharField(
        max_length=10,
        blank=True,
        validators=[validate_czech_birth_number],
        help_text="Required for czech citizens",
    )
    address = models.CharField(
        max_length=128,
        blank=True,
        help_text="Required for non-czech citizens",
    )
    email = models.EmailField(
        blank=True,
        help_text="Member has to confirm this email",
    )
    email_confirmation_token = models.UUIDField(
        null=True,
        editable=False,
    )
    has_email_confirmed = models.BooleanField(
        default=False,
    )
    marketing_consent_given_at = models.DateTimeField(
        null=True,
    )
    is_active = models.BooleanField(
        default=True,
        help_text=(
            "If you no longer need the member, you can deactivate them."
            " This means they will not appear in selection lists for rosters, etc."
            " You can reactivate the member at any time."
        ),
    )
    is_favourite = models.BooleanField(
        default=False,
    )
    default_jersey_number = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(99)]
    )

    def clean(self) -> None:
        if self.birth_number and self.citizenship != "CZ":
            raise ValidationError({"birth_number": "Birth number is only for czech citizens."})
        if self.address and self.citizenship == "CZ":
            raise ValidationError({"address": "Address is only for non-czech citizens."})
        if self.email and Member.objects.filter(email=self.email).exclude(pk=self.pk).exists():
            raise ValidationError({"email": "Member with this email already exists."})
        if (
            self.birth_number
            and Member.objects.filter(birth_number=self.birth_number).exclude(pk=self.pk).exists()
        ):
            raise ValidationError({"birth_number": "Member with this birth number already exists."})
        if (
            self.email_confirmation_token
            and Member.objects.filter(email_confirmation_token=self.email_confirmation_token)
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError(
                {
                    "email_confirmation_token": (
                        "Member with this email confirmation token already exists."
                    )
                }
            )

    def save(self, *args: Any, **kwargs: Any) -> None:
        send_token = False

        if self.pk:
            old_email = Member.objects.filter(pk=self.pk).values_list("email", flat=True).first()
            if self.email != old_email:
                self.has_email_confirmed = False
                if self.email:
                    self.email_confirmation_token = uuid.uuid4()
                    send_token = True
                else:
                    self.email_confirmation_token = None
        else:
            if self.email:
                self.email_confirmation_token = uuid.uuid4()
                send_token = True

        super().save(*args, **kwargs)

        if send_token:
            link = f"https://evidence.frisbee.cz/confirm-email/{self.email_confirmation_token}"
            send_email.delay(
                "Please confirm your email",
                (
                    f"You have been registered as a member of {self.club.name}.\n"
                    f" Please confirm your email by clicking on the following link:\n{link}"
                ),
                to=[self.email],
            )
            logger.info(
                "Confirmation token %s sent to %s", self.email_confirmation_token, self.email
            )


class CoachLicence(AuditModel):
    member = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
    )
    level = models.IntegerField(
        choices=CoachLicenceClassEnum.choices,
    )
    valid_from = models.DateField(
        null=False,
    )
    valid_to = models.DateField(
        null=False,
    )

    def clean(self) -> None:
        if self.valid_from > self.valid_to:
            raise ValidationError(
                {"valid_to": "Valid to date must be greater than valid from date."}
            )
