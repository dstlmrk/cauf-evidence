import logging
from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone

from finance.clients.fakturoid import fakturoid_client
from finance.models import Invoice, InvoiceStateEnum

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        logger.info("Start regular check of invoices in Fakturoid")

        for invoice in Invoice.objects.filter(
            state=InvoiceStateEnum.OPEN,
            created_at__gte=timezone.now() - timedelta(days=180),
        ):
            status = fakturoid_client.get_invoice_status(invoice_id=invoice.fakturoid_invoice_id)  # type: ignore
            if status in ("paid", "cancelled", "uncollectible"):
                if status == "paid":
                    invoice.state = InvoiceStateEnum.PAID
                    logger.info("Invoice %s was paid", invoice.id)
                else:
                    invoice.state = InvoiceStateEnum.CANCELED
                    logger.info("Invoice %s was canceled", invoice.id)
                invoice.fakturoid_status = status
                invoice.save()

        logger.info("End regular check of invoices in Fakturoid")
