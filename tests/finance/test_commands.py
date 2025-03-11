from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from competitions.models import ApplicationStateEnum
from django.core.management import call_command
from django.utils import timezone
from finance.models import InvoiceStateEnum, InvoiceTypeEnum
from finance.services import create_invoice

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
    "status,expected_invoice_state,expected_application_state",
    [
        ("open", InvoiceStateEnum.OPEN, ApplicationStateEnum.AWAITING_PAYMENT),
        ("paid", InvoiceStateEnum.PAID, ApplicationStateEnum.PAID),
        ("cancelled", InvoiceStateEnum.CANCELED, ApplicationStateEnum.AWAITING_PAYMENT),
        ("uncollectible", InvoiceStateEnum.CANCELED, ApplicationStateEnum.AWAITING_PAYMENT),
    ],
)
@pytest.mark.parametrize("club__fakturoid_subject_id", [999])
@pytest.mark.parametrize("competition_application__state", [ApplicationStateEnum.AWAITING_PAYMENT])
def test_command_check_invoices_in_fakturoid_should_work_properly(
    status, expected_invoice_state, expected_application_state, club, competition_application
):
    invoice = create_invoice(
        club, InvoiceTypeEnum.COMPETITION_DEPOSIT, [("", 100)], [competition_application]
    )
    invoice.state = InvoiceStateEnum.OPEN
    invoice.fakturoid_status = "open"
    invoice.save()

    with patch(
        "finance.clients.fakturoid.fakturoid_client.get_invoice_status_and_total"
    ) as mock_get_invoice_status_and_total:
        mock_get_invoice_status_and_total.return_value = status, Decimal("100.1")
        call_command("check_invoices_in_fakturoid")
        invoice.refresh_from_db()
        assert invoice.state == expected_invoice_state
        assert invoice.fakturoid_status == status
        assert invoice.fakturoid_total == Decimal("100.1")

    competition_application.refresh_from_db()
    assert competition_application.state == expected_application_state
