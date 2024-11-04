from competitions.models import CompetitionApplication
from django.db import transaction
from django.db.models import Sum

from finance.models import Invoice, InvoiceTypeEnum


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
    total_deposit = applications_qs.aggregate(total_deposit=Sum("competition__deposit"))[
        "total_deposit"
    ]
    invoice = Invoice.objects.create(
        club_id=club_id, amount=total_deposit, type=InvoiceTypeEnum.COMPETITION_DEPOSIT
    )
    applications_qs.update(invoice=invoice)
