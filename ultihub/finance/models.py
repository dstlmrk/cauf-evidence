from decimal import Decimal

from core.models import AuditModel
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator
from django.db import models


class InvoiceStateEnum(models.IntegerChoices):
    """Internal state of the invoice"""

    DRAFT = 1  # Created in the system
    OPEN = 2  # Sent to Fakturoid
    PAID = 3  # Paid in Fakturoid
    CANCELED = 4  # Canceled in Fakturoid


class InvoiceTypeEnum(models.IntegerChoices):
    COMPETITION_DEPOSIT = 1
    SEASON_PLAYER_FEES = 2


class Invoice(AuditModel):
    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.PROTECT,
    )
    state = models.IntegerField(
        choices=InvoiceStateEnum.choices,
        default=InvoiceStateEnum.DRAFT,
    )
    type = models.IntegerField(
        choices=InvoiceTypeEnum.choices,
    )
    original_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal(0))],
    )
    lines = models.JSONField(
        default=list,
    )
    fakturoid_invoice_id = models.IntegerField(
        blank=True,
        null=True,
        unique=True,
    )
    fakturoid_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
    )
    fakturoid_status = models.CharField(
        max_length=16,
        blank=True,
    )
    fakturoid_public_html_url = models.URLField(
        blank=True,
    )
    fakturoid_due_on = models.DateField(
        blank=True,
        null=True,
    )

    def __str__(self) -> str:
        return f"<Invoice({self.pk}, amount={self.amount})>"

    @property
    def amount(self) -> Decimal:
        return self.fakturoid_total if self.fakturoid_total is not None else self.original_amount


class InvoiceRelatedObject(AuditModel):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="related_objects",
    )

    # Generic relation to any object (season, competition, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    related_object = GenericForeignKey("content_type", "object_id")
