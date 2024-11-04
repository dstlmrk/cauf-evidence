from core.models import AuditModel
from django.core.validators import MinValueValidator
from django.db import models


class InvoiceStateEnum(models.IntegerChoices):
    DRAFT = 1
    SENT_TO_FAKTUROID = 2
    PAID = 3
    CANCELLED = 4


class InvoiceTypeEnum(models.IntegerChoices):
    COMPETITION_DEPOSIT = 1
    ANNUAL_PLAYER_FEES = 2


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
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    def __str__(self) -> str:
        return f"<Invoice({self.pk}, amount={self.amount})>"
