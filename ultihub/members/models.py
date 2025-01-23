import logging
import uuid
from datetime import date
from typing import Any

from core.models import AuditModel
from core.tasks import send_email
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, FloatField, Func, Manager, QuerySet, Value
from django_countries.fields import CountryField

from members.validators import validate_czech_birth_number, validate_postal_code

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
    default_jersey_number = models.IntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(99)]
    )

    objects = MemberManager()

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __str__(self) -> str:
        return f"{self.full_name} ({self.club.short_name or self.club.name})"

    def clean(self) -> None:
        if self.citizenship == "CZ" and not self.birth_number:
            raise ValidationError({"birth_number": "Birth number is required for czech citizens."})
        if self.citizenship != "CZ" and (self.city or self.house_number or self.postal_code):
            error_msg = "This field is required if an address is provided."
            if not self.city:
                raise ValidationError({"city": error_msg})
            if not self.house_number:
                raise ValidationError({"house_number": error_msg})
            if not self.postal_code:
                raise ValidationError({"postal_code": error_msg})
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
