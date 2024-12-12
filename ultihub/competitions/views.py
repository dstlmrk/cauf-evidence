from clubs.models import Team
from core.helpers import get_current_club_or_none
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET

from competitions.forms import RegistrationForm
from competitions.models import (
    ApplicationStateEnum,
    CompetitionApplication,
    TeamAtTournament,
    Tournament,
)
from competitions.services import get_competitions_qs_with_related_data


@require_GET
def tournaments(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "competitions/tournaments.html",
        {
            "tournaments": Tournament.objects.select_related(
                "competition",
                "competition__season",
                "competition__division",
                "competition__age_restriction",
            ).order_by("start_date", "name"),
        },
    )


def competitions(request: HttpRequest) -> HttpResponse:
    club = get_current_club_or_none(request)
    context = {}

    if club:
        context["club_application_without_invoice_total"] = CompetitionApplication.objects.filter(
            team__club=club.id, invoice__isnull=True, state=ApplicationStateEnum.AWAITING_PAYMENT
        ).count()

    return render(
        request,
        "competitions/competitions.html",
        context={
            "now": timezone.now(),
            "competitions": get_competitions_qs_with_related_data(
                club_id=club.id if club else None
            ),
            **context,
        },
    )


@login_required
def registration(request: HttpRequest, competition_id: int) -> HttpResponse:
    club_id = request.session["club"]["id"]
    teams_with_applications = Team.objects.filter(club_id=club_id).prefetch_related(
        Prefetch(
            "competition_application",
            queryset=CompetitionApplication.objects.filter(competition_id=competition_id),
            to_attr="applications",
        )
    )

    if request.method == "POST":
        form = RegistrationForm(request.POST, teams_with_applications=teams_with_applications)
        if form.is_valid():
            for checkbox_name, value in form.cleaned_data.items():
                team_id = int(checkbox_name.split("_")[1])
                team = teams_with_applications.get(pk=team_id)
                if request.user.has_perm("manage_club", team.club):
                    if value and not team.applications:  # type: ignore
                        CompetitionApplication.objects.create(
                            team_name=team.name,
                            competition_id=competition_id,
                            team=team,
                            registered_by=request.user,  # type: ignore
                        )
                else:
                    raise PermissionDenied()

            messages.success(
                request,
                (
                    "Your team has been registered for the tournament."
                    " To finalize the registration, please generate"
                    " an invoice and complete the payment."
                ),
            )
            return HttpResponse(status=204, headers={"HX-Refresh": "true"})
    else:
        form = RegistrationForm(teams_with_applications=teams_with_applications)
    return render(request, "competitions/partials/registration_form.html", {"form": form})


@require_GET
def application_list(request: HttpRequest, competition_id: int) -> HttpResponse:
    return render(
        request,
        "competitions/partials/application_list.html",
        {
            "applications": CompetitionApplication.objects.filter(
                competition_id=competition_id
            ).order_by("created_at"),
        },
    )


@require_GET
def competition_detail_view(request: HttpRequest, competition_id: int) -> HttpResponse:
    club = get_current_club_or_none(request)
    return render(
        request,
        "competitions/partials/competition_detail.html",
        {
            "competition": get_competitions_qs_with_related_data(
                club_id=club.id if club else None,
                competition_id=competition_id,
            ).get(),
            "now": timezone.now(),
        },
    )


@require_GET
def standings_list(request: HttpRequest, tournament_id: int) -> HttpResponse:
    return render(
        request,
        "competitions/partials/standings_list.html",
        {
            "teams_at_tournament": (
                TeamAtTournament.objects.filter(tournament_id=tournament_id)
                .select_related("application", "application__team", "application__team__club")
                .order_by("final_placement")
            ),
        },
    )
