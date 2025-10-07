from clubs.models import Club
from core.helpers import get_current_club
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from finance.forms import SeasonFeesCheckForm
from finance.services import calculate_season_fees, create_deposit_invoice


@require_POST
def invoices(request: HttpRequest) -> HttpResponse:
    club = get_object_or_404(Club, pk=get_current_club(request).id)

    if club.fakturoid_subject_id:
        create_deposit_invoice(club)
        messages.success(request, "The request has been successfully sent. Check your invoices.")
    else:
        messages.error(
            request, "Your club has no financial settings. Please contact the administrator."
        )

    return HttpResponse(status=204, headers={"HX-Refresh": "true"})


@require_POST
def season_fees_list_view(request: HttpRequest) -> HttpResponse:
    form = SeasonFeesCheckForm(request.POST)
    if form.is_valid():
        club = get_current_club(request)
        fees = calculate_season_fees(form.cleaned_data["season"], club.id)
        messages.success(request, "Season fees have been calculated")
        return render(
            request,
            "finance/partials/season_fees_list.html",
            {
                "season": form.cleaned_data["season"],
                "fees": sorted(fees.items(), key=lambda x: x[0].full_name),
                "total_amount": sum([fee.amount for fee in fees.values()]),
            },
        )
    else:
        messages.error(request, "Something went wrong")
        return HttpResponse(status=400)
