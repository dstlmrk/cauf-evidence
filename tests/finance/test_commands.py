from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.utils import timezone
from finance.models import InvoiceStateEnum

from tests.factories import InvoiceFactory


@pytest.mark.parametrize("club__fakturoid_subject_id", [999])
def test_command_resend_invoices_to_fakturoid_should_work_properly(club):
    invoice = InvoiceFactory(club=club)
    invoice.created_at = timezone.now() - timedelta(seconds=65)
    invoice.save()

    assert invoice.state == InvoiceStateEnum.DRAFT
    call_command("resend_invoices_to_fakturoid")
    invoice.refresh_from_db()
    assert invoice.state == InvoiceStateEnum.OPEN
    assert invoice.fakturoid_status == "open"


@pytest.mark.parametrize("club__fakturoid_subject_id", [999])
def test_command_resend_invoices_to_fakturoid_should_not_resend_invoices_younger_than_60_seconds(
    club,
):
    invoice = InvoiceFactory(club=club)
    invoice.created_at = timezone.now() - timedelta(seconds=55)
    invoice.save()

    assert invoice.state == InvoiceStateEnum.DRAFT
    call_command("resend_invoices_to_fakturoid")
    invoice.refresh_from_db()
    assert invoice.state == InvoiceStateEnum.DRAFT
    assert invoice.fakturoid_status == ""


@pytest.mark.parametrize(
    "status,expected_state",
    [
        ("open", InvoiceStateEnum.OPEN),
        ("paid", InvoiceStateEnum.PAID),
        ("cancelled", InvoiceStateEnum.CANCELED),
        ("uncollectible", InvoiceStateEnum.CANCELED),
    ],
)
@pytest.mark.parametrize("club__fakturoid_subject_id", [999])
def test_command_check_invoices_in_fakturoid_should_work_properly(status, expected_state, club):
    invoice = InvoiceFactory(club=club, state=InvoiceStateEnum.OPEN, fakturoid_status="open")
    with patch(
        "finance.clients.fakturoid.fakturoid_client.get_invoice_status"
    ) as mock_get_invoice_status:
        mock_get_invoice_status.return_value = status
        call_command("check_invoices_in_fakturoid")
        invoice.refresh_from_db()
        assert invoice.state == expected_state
        assert invoice.fakturoid_status == status
