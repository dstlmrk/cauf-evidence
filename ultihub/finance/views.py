from core.helpers import get_club_id
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_POST

from finance.services import create_deposit_invoice


@require_POST
def invoices(request: HttpRequest) -> HttpResponse:
    create_deposit_invoice(get_club_id(request))
    messages.success(request, "The request has been successfully sent. Check your invoices.")
    return HttpResponse(status=204, headers={"HX-Refresh": "true"})
