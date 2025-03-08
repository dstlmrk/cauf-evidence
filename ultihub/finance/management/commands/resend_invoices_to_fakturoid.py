import logging
from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone

from finance.models import Invoice, InvoiceStateEnum
from finance.services import create_invoice_in_fakturoid_and_save_data

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        logger.info("Start trying to resend invoices to Fakturoid")

        for invoice in Invoice.objects.filter(
            state=InvoiceStateEnum.DRAFT,
            created_at__lte=timezone.now() - timedelta(seconds=60),
        ):
            create_invoice_in_fakturoid_and_save_data(invoice)

        logger.info("End trying to resend invoices to Fakturoid")
