from core.helpers import get_club_id, get_current_club
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from members.models import Member

from finance.forms import SeasonFeesCheckForm
from finance.services import create_deposit_invoice


@require_POST
def invoices(request: HttpRequest) -> HttpResponse:
    create_deposit_invoice(get_club_id(request))
    messages.success(request, "The request has been successfully sent. Check your invoices.")
    return HttpResponse(status=204, headers={"HX-Refresh": "true"})


@require_POST
def season_fees_list_view(request: HttpRequest) -> HttpResponse:
    form = SeasonFeesCheckForm(request.POST)
    if form.is_valid():
        members = Member.objects.filter(club_id=get_current_club(request).id)
        messages.success(request, "Season fees have been calculated")
        return render(
            request,
            "finance/partials/season_fees_list.html",
            {
                "season": form.cleaned_data["season"],
                "total_amount": 999,
                "members": members,
            },
        )
    else:
        messages.error(request, "Something went wrong")
        return HttpResponse(status=400)
