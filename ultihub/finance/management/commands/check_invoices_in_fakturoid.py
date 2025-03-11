import logging
from datetime import timedelta
from typing import Any

from competitions.models import ApplicationStateEnum, CompetitionApplication
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from finance.clients.fakturoid import InvoiceStatus, fakturoid_client
from finance.models import Invoice, InvoiceStateEnum, InvoiceTypeEnum

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    @transaction.atomic
    def _update_invoice(self, invoice: Invoice, status: InvoiceStatus) -> None:
        if status == "paid":
            invoice.state = InvoiceStateEnum.PAID
            if invoice.type == InvoiceTypeEnum.COMPETITION_DEPOSIT:
                CompetitionApplication.objects.filter(
                    id__in=invoice.related_objects.filter(
                        content_type_id=ContentType.objects.get_for_model(CompetitionApplication).id
                    ).values_list("object_id", flat=True),
                    state=ApplicationStateEnum.AWAITING_PAYMENT,
                ).update(state=ApplicationStateEnum.PAID)
            logger.info("Invoice %s was paid", invoice.id)
        elif status in ("cancelled", "uncollectible"):
            invoice.state = InvoiceStateEnum.CANCELED
            logger.info("Invoice %s was canceled", invoice.id)
        invoice.fakturoid_status = status
        invoice.save()

    def handle(self, *args: Any, **options: Any) -> None:
        logger.info("Start regular check of invoices in Fakturoid")

        for invoice in Invoice.objects.filter(
            state=InvoiceStateEnum.OPEN,
            created_at__gte=timezone.now() - timedelta(days=180),
        ):
            status = fakturoid_client.get_invoice_status(invoice_id=invoice.fakturoid_invoice_id)  # type: ignore
            if status in ("paid", "cancelled", "uncollectible"):
                self._update_invoice(invoice, status)

        logger.info("End regular check of invoices in Fakturoid")
