import logging
from decimal import Decimal
from typing import Any

from competitions.models import CompetitionApplication
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Sum

from finance.models import Invoice, InvoiceRelatedObject, InvoiceTypeEnum

logger = logging.getLogger(__name__)


def create_invoice(
    club_id: int, amount: Decimal, type_: InvoiceTypeEnum, related_objects: list[Any] | None = None
) -> Invoice:
    invoice = Invoice.objects.create(club_id=club_id, amount=amount, type=type_)
    for related_object in related_objects or []:
        InvoiceRelatedObject.objects.create(
            invoice=invoice,
            content_type=ContentType.objects.get_for_model(related_object),
            object_id=related_object.id,
        )
    return invoice


@transaction.atomic
def create_deposit_invoice(club_id: int) -> None:
    """
    Create an invoice for the total deposit of all competition applications
    """
    applications_qs = (
        CompetitionApplication.objects.filter(
            team__club=club_id,
            invoice__isnull=True,
        )
        .select_related("competition")
        .select_for_update()
    )

    total_deposit = applications_qs.aggregate(
        total_deposit=Sum("competition__deposit"),
    )["total_deposit"]

    invoice = create_invoice(
        club_id,
        total_deposit,
        InvoiceTypeEnum.COMPETITION_DEPOSIT,
        related_objects=[application for application in applications_qs],
    )
    applications_qs.update(invoice=invoice)
