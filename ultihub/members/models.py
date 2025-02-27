import logging
import uuid
from datetime import date
from typing import Any

from core.models import AuditModel
from core.tasks import send_email
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, FloatField, Func, Manager, Q, QuerySet, UniqueConstraint, Value
from django_countries.fields import CountryField

from members.validators import (
    is_at_least_15,
    is_valid_birth_date_with_id,
    validate_czech_birth_number,
    validate_postal_code,
)
from ultihub.settings import FF_EMAIL_REQUIRED

logger = logging.getLogger(__name__)


class MemberSexEnum(models.IntegerChoices):
    FEMALE = 1, "Female"
    MALE = 2, "Male"


class CoachLicenceClassEnum(models.IntegerChoices):
    FIRST = 1, "First"
    SECOND = 2, "Second"
    THIRD = 3, "Third"


class TransferStateEnum(models.IntegerChoices):
    REQUESTED = 1, "Requested"
    PROCESSED = 2, "Processed"
    REVOKED = 3, "Revoked"
    REJECTED = 4, "Rejected"


class MemberQuerySet(QuerySet):
    def annotate_age(self, age_reference_date: date) -> QuerySet:
        return self.annotate(
            age=Func(
                Func(
                    Value(age_reference_date),
                    F("birth_date"),
                    function="AGE",
                ),
                function="DATE_PART",
                template="DATE_PART('year', %(expressions)s)",
                output_field=FloatField(),
            )
        )


class MemberManager(Manager):
    def get_queryset(self) -> MemberQuerySet:
        return MemberQuerySet(self.model, using=self._db)


class Member(AuditModel):
    club = models.ForeignKey(
        "clubs.Club",
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
    street = models.CharField(
        max_length=128,
        blank=True,
    )
    city = models.CharField(
        max_length=64,
        blank=True,
    )
    house_number = models.CharField(
        max_length=16,
        blank=True,
    )
    postal_code = models.CharField(
        max_length=5,
        blank=True,
        validators=[validate_postal_code],
    )
    email = models.EmailField(
        blank=True,
    )
    legal_guardian_email = models.EmailField(
        blank=True,
    )
    legal_guardian_first_name = models.CharField(
        max_length=32,
        blank=True,
    )
    legal_guardian_last_name = models.CharField(
        max_length=32,
        blank=True,
    )
    email_confirmation_token = models.UUIDField(
        null=True,
        editable=False,
    )
    email_confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    marketing_consent_given_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(
        default=True,
        help_text=(
            "If you no longer need the member, you can deactivate them."
            " This means they will not appear in selection lists for rosters, etc."
            " You can reactivate the member at any time."
        ),
    )
    default_jersey_number = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(99)]
    )
    original_id = models.CharField(
        max_length=32,
        blank=True,
    )

    objects = MemberManager()

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["original_id"],
                name="unique_original_id_non_null",
                condition=Q(original_id__isnull=False) & ~Q(original_id=""),
            ),
            UniqueConstraint(
                fields=["birth_number"],
                name="unique_birth_number_non_null",
                condition=Q(birth_number__isnull=False) & ~Q(birth_number=""),
            ),
        ]

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def legal_guardian_full_name(self) -> str:
        return f"{self.legal_guardian_first_name} {self.legal_guardian_last_name}".strip()

    @property
    def address(self) -> str:
        if not self.street:
            return ""
        return f"{self.street} {self.house_number}, {self.postal_code} {self.city}, Czech Republic"

    def __str__(self) -> str:
        return f"{self.full_name} ({self.club.short_name or self.club.name})"

    def clean(self) -> None:
        errors = {}

        if self.citizenship == "CZ":
            if self.birth_number:
                if not is_valid_birth_date_with_id(self.birth_date, self.birth_number):
                    errors["birth_number"] = "Invalid birth number or birth date"
            else:
                errors["birth_number"] = "Birth number is required for czech citizens"

            for field in ["street", "city", "house_number", "postal_code"]:
                if getattr(self, field):
                    errors[field] = "This field is required only for non-czech citizens"

        else:
            if self.street or self.city or self.house_number or self.postal_code:
                for field in ["street", "city", "house_number", "postal_code"]:
                    if not getattr(self, field):
                        errors[field] = "This field is required if an address is provided"

        if self.email and Member.objects.filter(email=self.email).exclude(pk=self.pk).exists():
            errors["email"] = "Member with this email already exists"

        if is_at_least_15(self.birth_date):
            if FF_EMAIL_REQUIRED and not self.email:
                errors["email"] = "This field is required"
        else:
            error_msg = "This field is required for children under 15"
            if FF_EMAIL_REQUIRED and not self.legal_guardian_email:
                errors["legal_guardian_email"] = error_msg
            for field in ["legal_guardian_first_name", "legal_guardian_last_name"]:
                if not getattr(self, field):
                    errors[field] = error_msg
        if (
            self.birth_number
            and Member.objects.filter(birth_number=self.birth_number).exclude(pk=self.pk).exists()
        ):
            errors["birth_number"] = "Member with this birth number already exists"
        if (
            self.email_confirmation_token
            and Member.objects.filter(email_confirmation_token=self.email_confirmation_token)
            .exclude(pk=self.pk)
            .exists()
        ):
            errors["email_confirmation_token"] = (
                "Member with this email confirmation token already exists"
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args: Any, **kwargs: Any) -> None:
        send_token = False

        email_field_name = "email" if is_at_least_15(self.birth_date) else "legal_guardian_email"
        email = getattr(self, email_field_name)

        if self.pk:
            old_email = (
                Member.objects.filter(pk=self.pk).values_list(email_field_name, flat=True).first()
            )
            if email != old_email:
                self.has_email_confirmed = False
                if email:
                    self.email_confirmation_token = uuid.uuid4()
                    send_token = True
                else:
                    self.email_confirmation_token = None
        else:
            if email:
                self.email_confirmation_token = uuid.uuid4()
                send_token = True

        super().save(*args, **kwargs)

        if send_token:
            link = (
                f"https://evidence.frisbee.cz/members/confirm-email/{self.email_confirmation_token}"
            )
            send_email.delay(
                "Please confirm your email",
                (
                    f"You have been registered as a member of {self.club.name}.\n"
                    f"Please confirm your email by clicking on the following link: {link}\n"
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


class Transfer(AuditModel):
    member = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name="transfers",
    )
    state = models.IntegerField(
        choices=TransferStateEnum.choices,
        default=TransferStateEnum.REQUESTED,
    )
    source_club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.PROTECT,
        related_name="outgoing_transfers",
    )
    target_club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.PROTECT,
        related_name="incoming_transfers",
    )
    requesting_club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.PROTECT,
        related_name="requested_transfers",
    )
    approving_club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.PROTECT,
        related_name="approved_transfers",
    )
    requested_by = models.ForeignKey(
        "users.Agent",
        on_delete=models.PROTECT,
        related_name="requested_transfers",
    )
    approved_by = models.ForeignKey(
        "users.Agent",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="approved_transfers",
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def clean(self) -> None:
        if self.source_club == self.target_club:
            raise ValidationError("Target club must be different from source club")
        if self.state == TransferStateEnum.PROCESSED and not self.approved_by:
            raise ValidationError("Approved by agent must be set")

        if (
            Transfer.objects.filter(
                member=self.member,
                state=TransferStateEnum.REQUESTED,
                source_club=self.source_club,
                target_club=self.target_club,
            )
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError("Member already has a pending transfer request")

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.clean()
        super().save(*args, **kwargs)
