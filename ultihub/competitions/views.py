from clubs.models import Team
from core.helpers import get_club_id
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET

from competitions.forms import RegistrationForm
from competitions.models import (
    ApplicationStateEnum,
    Competition,
    CompetitionApplication,
    TeamAtTournament,
    Tournament,
)


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
    club_id = get_club_id(request)
    context = {}

    competitions_qs = (
        Competition.objects.select_related("age_restriction", "season", "division")
        .prefetch_related(
            Prefetch(
                "competitionapplication_set",
                queryset=CompetitionApplication.objects.select_related("team"),
                to_attr="applications",
            ),
        )
        .prefetch_related(
            Prefetch(
                "tournament_set",
                queryset=Tournament.objects.all().order_by("start_date", "name"),
                to_attr="tournaments",
            ),
        )
        .annotate(application_count=Count("competitionapplication"))
        .exclude(is_for_national_teams=True)
        .order_by("-pk")
    )

    if club_id:
        context["club_application_without_invoice_total"] = CompetitionApplication.objects.filter(
            team__club=club_id, invoice__isnull=True, state=ApplicationStateEnum.AWAITING_PAYMENT
        ).count()

        competitions_qs = competitions_qs.annotate(
            club_application_count=Count(
                "competitionapplication",
                filter=Q(
                    competitionapplication__team__club_id=club_id,
                ),
            ),
            club_application_without_invoice_count=Count(
                "competitionapplication",
                filter=Q(
                    competitionapplication__invoice__isnull=True,
                    competitionapplication__team__club_id=club_id,
                    competitionapplication__state=ApplicationStateEnum.AWAITING_PAYMENT,
                ),
            ),
            has_awaiting_payment=Exists(
                CompetitionApplication.objects.filter(
                    competition=OuterRef("pk"),
                    state=ApplicationStateEnum.AWAITING_PAYMENT,
                    team__club_id=club_id,
                )
            ),
        )

    return render(
        request,
        "competitions/competitions.html",
        context={
            "now": timezone.now(),
            "competitions": competitions_qs,
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
