from datetime import date
from typing import cast

from clubs.models import Club
from core.helpers import get_current_club
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from members.models import Member
from tournaments.models import MemberAtTournament

from finance.forms import SeasonFeesCheckForm
from finance.services import calculate_season_fees, create_deposit_invoice


@require_POST
def invoices(request: HttpRequest) -> HttpResponse:
    club = get_object_or_404(Club, pk=get_current_club(request).id)

    if club.fakturoid_subject_id:
        invoice_created = create_deposit_invoice(club)
        message = "The request has been successfully sent."
        if invoice_created:
            message += " Check your invoices."
        messages.success(request, message)
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


@require_POST
def season_fees_member_detail_view(request: HttpRequest) -> HttpResponse:
    from competitions.models import Season
    from international_tournaments.models import MemberAtInternationalTournament

    member_id = request.POST.get("member_id", "")
    season_id = request.POST.get("season_id", "")

    member = get_object_or_404(Member, pk=member_id)
    season = get_object_or_404(Season, pk=season_id)

    # Get all domestic tournaments for this member in this season
    members_at_tournaments = (
        MemberAtTournament.objects.filter(
            member=member,
            tournament__competition__season=season,
        )
        .select_related(
            "tournament",
            "tournament__competition",
            "tournament__competition__division",
            "tournament__competition__age_limit",
            "team_at_tournament__application",
        )
        .order_by("-tournament__start_date")
    )

    tournaments_data = []
    for mat in members_at_tournaments:
        tournaments_data.append(
            {
                "tournament": mat.tournament,
                "team_name": mat.team_at_tournament.application.team_name,
                "fee_type": mat.tournament.competition.fee_type,
                "date": mat.tournament.start_date,
                "is_international": False,
                "competition": mat.tournament.competition,
                "division": mat.tournament.competition.division,
                "age_limit": mat.tournament.competition.age_limit,
                "location": mat.tournament.location,
                "date_from": mat.tournament.start_date,
                "date_to": mat.tournament.end_date,
            }
        )

    # Get all international tournaments for this member in this season
    members_at_international_tournaments = (
        MemberAtInternationalTournament.objects.filter(
            member=member,
            tournament__season=season,
        )
        .select_related(
            "tournament",
            "team_at_tournament",
            "team_at_tournament__division",
            "team_at_tournament__age_limit",
        )
        .order_by("-tournament__date_from")
    )

    for mait in members_at_international_tournaments:
        tournaments_data.append(
            {
                "tournament": mait.tournament,
                "team_name": mait.team_at_tournament.team_name,
                "fee_type": mait.tournament.fee_type,
                "date": mait.tournament.date_from,
                "is_international": True,
                "tournament_type": mait.tournament.get_type_display(),
                "division": mait.team_at_tournament.division,
                "age_limit": mait.team_at_tournament.age_limit,
                "location": f"{mait.tournament.city}, {mait.tournament.country.name}",
                "date_from": mait.tournament.date_from,
                "date_to": mait.tournament.date_to,
            }
        )

    # Sort all tournaments by date (most recent first)
    tournaments_data.sort(key=lambda x: cast(date, x["date"]) or date.min, reverse=True)

    return render(
        request,
        "finance/partials/season_fees_member_detail_modal.html",
        {
            "member": member,
            "season": season,
            "tournaments": tournaments_data,
        },
    )
