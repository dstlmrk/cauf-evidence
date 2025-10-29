import logging

from competitions.enums import EnvironmentEnum
from competitions.models import AgeLimit, Division, Season
from core.helpers import get_current_club_or_none
from django.db.models import BooleanField, Count, Exists, OuterRef, Prefetch, Q, Value
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from international_tournaments.enums import InternationalTournamentTypeEnum
from international_tournaments.models import InternationalTournament, TeamAtInternationalTournament

logger = logging.getLogger(__name__)


@require_GET
def international_tournaments_view(request: HttpRequest) -> HttpResponse:
    club = get_current_club_or_none(request)

    # Get filter values
    division_id = request.GET.get("division")
    age_limit_id = request.GET.get("age_limit")

    # Build queryset with prefetch for teams, sorted by division, age_limit, and team_name
    # Apply filters on the prefetch queryset
    team_filters = Q()
    if division_id:
        team_filters &= Q(division_id=division_id)
    if age_limit_id:
        team_filters &= Q(age_limit_id=age_limit_id)

    sorted_participations = (
        TeamAtInternationalTournament.objects.filter(team_filters)
        .select_related("team__club", "division", "age_limit")
        .order_by("division__name", "age_limit__name", "team_name")
    )

    queryset = InternationalTournament.objects.select_related("season").prefetch_related(
        Prefetch("team_participations", queryset=sorted_participations)
    )

    # Apply filters on tournaments
    season_id = request.GET.get("season")
    if season_id:
        queryset = queryset.filter(season_id=season_id)

    environment = request.GET.get("environment")
    if environment:
        queryset = queryset.filter(environment=environment)

    tournament_type = request.GET.get("type")
    if tournament_type:
        queryset = queryset.filter(type=tournament_type)

    # Filter tournaments that have at least one team matching division/age_limit
    if division_id or age_limit_id:
        tournament_team_filters = Q()
        if division_id:
            tournament_team_filters &= Q(team_participations__division_id=division_id)
        if age_limit_id:
            tournament_team_filters &= Q(team_participations__age_limit_id=age_limit_id)
        queryset = queryset.filter(tournament_team_filters).distinct()

    tournaments = queryset.annotate(
        team_count=Count("teams", distinct=True),
        includes_my_club_team=Exists(
            TeamAtInternationalTournament.objects.filter(
                tournament=OuterRef("pk"), team__club_id=club.id
            )
        )
        if club
        else Value(False, output_field=BooleanField()),
    ).order_by("-date_from", "name")

    return render(
        request,
        "international_tournaments/international_tournaments.html",
        {
            "tournaments": tournaments,
            "seasons": Season.objects.all().order_by("-name"),
            "environments": EnvironmentEnum.choices,
            "tournament_types": InternationalTournamentTypeEnum.choices,
            "divisions": Division.objects.all().order_by("name"),
            "age_limits": AgeLimit.objects.all().order_by("name"),
        },
    )
