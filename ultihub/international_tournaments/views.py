import json
import logging
from functools import wraps
from typing import Any, cast

from competitions.enums import EnvironmentEnum
from competitions.models import AgeLimit, Division, Season
from core.helpers import get_current_club, get_current_club_or_none
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import BooleanField, Count, Exists, F, OuterRef, Prefetch, Q, Value
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST
from members.models import Member

from international_tournaments.enums import InternationalTournamentTypeEnum
from international_tournaments.forms import (
    AddMemberToInternationalRosterForm,
    UpdateMemberToInternationalRosterForm,
)
from international_tournaments.models import (
    InternationalTournament,
    MemberAtInternationalTournament,
    TeamAtInternationalTournament,
)

logger = logging.getLogger(__name__)


@require_GET
def international_tournaments_view(request: HttpRequest) -> HttpResponse:
    club = get_current_club_or_none(request)

    # Set default season to the newest one if no season filter is applied
    query_params = request.GET.copy()
    if "season" not in query_params:
        newest_season = Season.objects.order_by("-name").first()
        if newest_season:
            query_params["season"] = str(newest_season.id)

    # Get filter values
    division_id = query_params.get("division")
    age_limit_id = query_params.get("age_limit")

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
    season_id = query_params.get("season")
    if season_id:
        queryset = queryset.filter(season_id=season_id)

    environment = query_params.get("environment")
    if environment:
        queryset = queryset.filter(environment=environment)

    tournament_type = query_params.get("type")
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
            "selected_season_id": query_params.get("season"),
            "environments": EnvironmentEnum.choices,
            "tournament_types": InternationalTournamentTypeEnum.choices,
            "divisions": Division.objects.all().order_by("name"),
            "age_limits": AgeLimit.objects.all().order_by("name"),
        },
    )


def require_national_team_permission(view_func):  # type: ignore
    """
    Decorator to check if user has permission to manage international tournament rosters.
    User must be logged in and belong to the national team club.
    """

    @wraps(view_func)
    @login_required
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        current_club = get_current_club(request)
        if current_club.id != settings.NATIONAL_TEAM_CLUB_ID:
            raise PermissionDenied(
                "Only National Team club members can manage international rosters"
            )
        return view_func(request, *args, **kwargs)

    return wrapper


@require_GET
def international_roster_dialog_view(
    request: HttpRequest, team_at_tournament_id: int
) -> HttpResponse:
    team_at_tournament = get_object_or_404(
        TeamAtInternationalTournament.objects.select_related("division", "age_limit", "tournament"),
        pk=team_at_tournament_id,
    )
    return render(
        request,
        "international_tournaments/partials/international_roster_dialog.html",
        {
            "team_at_tournament": team_at_tournament,
            "members_at_tournament": MemberAtInternationalTournament.objects.select_related(
                "member", "member__club"
            )
            .filter(team_at_tournament_id=team_at_tournament.id)
            .order_by(F("jersey_number").asc(nulls_last=True)),
        },
    )


@require_national_team_permission
def international_roster_add_form_view(
    request: HttpRequest, team_at_tournament_id: int
) -> HttpResponse:
    team_at_tournament = get_object_or_404(
        TeamAtInternationalTournament.objects.select_related(
            "team",
            "team__club",
            "tournament",
        ),
        pk=team_at_tournament_id,
    )

    if request.method == "POST":
        form = AddMemberToInternationalRosterForm(
            request.POST,
            team_at_tournament=team_at_tournament,
        )

        if form.is_valid():
            # Use validated member from form
            member = cast(Member, form.validated_member)
            MemberAtInternationalTournament.objects.create(
                tournament_id=team_at_tournament.tournament_id,
                team_at_tournament_id=team_at_tournament.id,
                member_id=member.id,
                jersey_number=member.default_jersey_number,
            )
            messages.success(request, _("Member added successfully"))

            response = HttpResponse(status=204)
            response["HX-Trigger"] = json.dumps(
                dict(
                    showRosterDialog=dict(teamAtTournamentId=team_at_tournament_id),
                    teamsListChanged=True,
                )
            )
            return response
    else:
        form = AddMemberToInternationalRosterForm()

    return render(
        request,
        "international_tournaments/partials/international_roster_add_form.html",
        {
            "team_at_tournament_id": team_at_tournament_id,
            "tournament_id": team_at_tournament.tournament_id,
            "form": form,
        },
    )


@require_national_team_permission
def international_roster_update_form_view(
    request: HttpRequest, member_at_tournament_id: int
) -> HttpResponse:
    member_at_tournament = get_object_or_404(
        MemberAtInternationalTournament, pk=member_at_tournament_id
    )

    if request.method == "POST":
        form = UpdateMemberToInternationalRosterForm(request.POST, instance=member_at_tournament)

        if form.is_valid():
            form.save()
            messages.success(request, _("Member updated successfully"))
            response = HttpResponse(status=204)

            response["HX-Trigger"] = json.dumps(
                {
                    "showRosterDialog": {
                        "teamAtTournamentId": member_at_tournament.team_at_tournament.id
                    }
                }
            )
            return response
    else:
        form = UpdateMemberToInternationalRosterForm(instance=member_at_tournament)

    return render(
        request,
        "international_tournaments/partials/international_roster_update_form.html",
        {"form": form},
    )


@require_national_team_permission
@require_POST
def remove_member_from_international_roster_view(
    request: HttpRequest, member_at_tournament_id: int
) -> HttpResponse:
    member_at_tournament = get_object_or_404(
        MemberAtInternationalTournament, pk=member_at_tournament_id
    )

    team_at_tournament = member_at_tournament.team_at_tournament

    logger.info(
        "Removing member from international tournament roster; member=%s, team=%s, tournament=%s",
        member_at_tournament.member,
        member_at_tournament.team_at_tournament,
        member_at_tournament.tournament,
    )

    member_at_tournament.delete()
    messages.success(request, _("Member removed successfully"))

    response = render(
        request,
        "international_tournaments/partials/international_roster_dialog.html",
        {
            "team_at_tournament": team_at_tournament,
            "members_at_tournament": MemberAtInternationalTournament.objects.select_related(
                "member", "member__club"
            )
            .filter(team_at_tournament_id=team_at_tournament.id)
            .order_by(F("jersey_number").asc(nulls_last=True)),
        },
    )
    response["HX-Trigger"] = "teamsListChanged"
    return response
