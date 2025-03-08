from datetime import timedelta

from django.core.management import call_command
from django.utils import timezone
from finance.models import InvoiceStateEnum

from tests.factories import ClubFactory, InvoiceFactory


def test_command_resend_invoices_to_fakturoid_should_work_properly():
    invoice = InvoiceFactory(club=ClubFactory(fakturoid_subject_id=999))
    invoice.created_at = timezone.now() - timedelta(seconds=65)
    invoice.save()

    assert invoice.state == InvoiceStateEnum.DRAFT
    call_command("resend_invoices_to_fakturoid")
    invoice.refresh_from_db()
    assert invoice.state == InvoiceStateEnum.OPEN
    assert invoice.fakturoid_status == "open"


def test_command_resend_invoices_to_fakturoid_should_not_resend_invoices_younger_than_60_seconds():
    invoice = InvoiceFactory(club=ClubFactory(fakturoid_subject_id=999))
    invoice.created_at = timezone.now() - timedelta(seconds=55)
    invoice.save()

    assert invoice.state == InvoiceStateEnum.DRAFT
    call_command("resend_invoices_to_fakturoid")
    invoice.refresh_from_db()
    assert invoice.state == InvoiceStateEnum.DRAFT
    assert invoice.fakturoid_status == ""


def test_command_check_invoices_in_fakturoid_should_work_properly():
    pass
