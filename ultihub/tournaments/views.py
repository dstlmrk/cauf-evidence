import csv
import json
import logging
from typing import cast

from clubs.service import notify_club
from competitions.enums import EnvironmentEnum
from competitions.filters import TournamentFilterSet
from competitions.models import AgeLimit, Division, Season
from core.helpers import get_current_club, get_current_club_or_none
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import BooleanField, Count, Exists, OuterRef, Value
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from members.models import Member

from tournaments.forms import AddMemberToRosterForm, UpdateMemberToRosterForm
from tournaments.models import (
    MemberAtTournament,
    TeamAtTournament,
    Tournament,
)

logger = logging.getLogger(__name__)


@require_GET
def tournaments_view(request: HttpRequest) -> HttpResponse:
    club = get_current_club_or_none(request)

    # Build queryset with filters
    queryset = Tournament.objects.select_related(
        "competition",
        "competition__season",
        "competition__division",
        "competition__age_limit",
    ).prefetch_related(
        "winner_team__application",
        "sotg_winner_team__application",
    )

    # Set default season to the newest one if no season filter is applied
    query_params = request.GET.copy()
    if "season" not in query_params:
        newest_season = Season.objects.order_by("-name").first()
        if newest_season:
            query_params["season"] = str(newest_season.id)

    # Apply filters using FilterSet
    filter_set = TournamentFilterSet(query_params, queryset=queryset)
    queryset = filter_set.qs

    tournaments = queryset.annotate(
        team_count=Count("teams", distinct=True),
        member_count=Count("members", distinct=True),
        includes_my_club_team=Exists(
            TeamAtTournament.objects.filter(
                tournament=OuterRef("pk"), application__team__club_id=club.id
            )
        )
        if club
        else Value(False, output_field=BooleanField()),
    ).order_by("-start_date", "competition__division", "name")

    return render(
        request,
        "tournaments/tournaments.html",
        {
            "tournaments": tournaments,
            "seasons": Season.objects.all().order_by("-name"),
            "selected_season_id": query_params.get("season"),
            "environments": EnvironmentEnum.choices,
            "divisions": Division.objects.all().order_by("name"),
            "age_limits": AgeLimit.objects.all().order_by("name"),
        },
    )


@require_GET
def tournament_detail_view(request: HttpRequest, tournament_id: int) -> HttpResponse:
    tournament = get_object_or_404(
        Tournament.objects.select_related("competition").annotate(
            team_count=Count("teams", distinct=True),
            member_count=Count("members", distinct=True),
        ),
        pk=tournament_id,
    )
    return render(
        request,
        "tournaments/tournament_detail.html",
        {"tournament": tournament},
    )


@require_GET
def roster_dialog_view(request: HttpRequest, team_at_tournament_id: int) -> HttpResponse:
    team_at_tournament = get_object_or_404(TeamAtTournament, pk=team_at_tournament_id)
    return render(
        request,
        "tournaments/partials/roster_dialog.html",
        {
            "team_at_tournament": team_at_tournament,
            "members_at_tournament": MemberAtTournament.objects.select_related("member")
            .filter(team_at_tournament_id=team_at_tournament.id)
            .order_by("created_at"),
        },
    )


@login_required
def roster_dialog_add_form_view(request: HttpRequest, team_at_tournament_id: int) -> HttpResponse:
    team_at_tournament = get_object_or_404(
        TeamAtTournament.objects.select_related(
            "application",
            "application__team",
            "application__team__club",
            "tournament",
            "tournament__competition",
            "tournament__competition__season",
        ),
        pk=team_at_tournament_id,
    )

    current_club = get_current_club(request)
    if current_club.id != team_at_tournament.application.team.club_id:
        raise PermissionDenied()

    if request.method == "POST":
        form = AddMemberToRosterForm(
            request.POST,
            team_at_tournament=team_at_tournament,
        )

        if form.is_valid():
            # Use validated member from form (already loaded with age annotation)
            member = cast(Member, form.validated_member)
            MemberAtTournament.objects.create(
                tournament_id=team_at_tournament.tournament_id,
                team_at_tournament_id=team_at_tournament.id,
                member_id=member.id,
                jersey_number=member.default_jersey_number,
            )
            messages.success(request, "Member added successfully")

            if member.club != team_at_tournament.application.team.club:
                tournament = team_at_tournament.tournament

                notify_club(
                    club=member.club,
                    subject="Roster announcement",
                    message=(
                        "Your player <b>{}</b> has been registered on the <b>{}</b> roster"
                        ' for the <a href="{}">{}</a> tournament.'
                    ).format(
                        member.full_name,
                        team_at_tournament.application.team_name,
                        request.build_absolute_uri(
                            reverse("tournaments:detail", args=(tournament.pk,))
                        ),
                        tournament,
                    ),
                )

            response = HttpResponse(status=204)
            response["HX-Trigger"] = json.dumps(
                dict(
                    showRosterDialog=dict(teamAtTournamentId=team_at_tournament_id),
                    teamsListChanged=True,
                )
            )
            return response
    else:
        team_at_tournament = get_object_or_404(TeamAtTournament, pk=team_at_tournament_id)
        form = AddMemberToRosterForm()

    return render(
        request,
        "tournaments/partials/roster_dialog_add_form.html",
        {
            "team_at_tournament_id": team_at_tournament_id,
            "tournament_id": team_at_tournament.tournament_id,
            "form": form,
        },
    )


@login_required
def roster_dialog_update_form_view(
    request: HttpRequest, member_at_tournament_id: int
) -> HttpResponse:
    member_at_tournament = get_object_or_404(MemberAtTournament, pk=member_at_tournament_id)

    current_club = get_current_club(request)
    if current_club.id != member_at_tournament.team_at_tournament.application.team.club_id:
        raise PermissionDenied()

    if request.method == "POST":
        form = UpdateMemberToRosterForm(request.POST, instance=member_at_tournament)

        if not member_at_tournament.tournament.has_open_rosters:
            messages.error(request, "The roster deadline has passed")
            return HttpResponse(status=400)

        if form.is_valid():
            form.save()
            messages.success(request, "Member updated successfully")
            response = HttpResponse(status=204)

            response["HX-Trigger"] = (
                f'{{"showRosterDialog": {{"teamAtTournamentId":'
                f' "{member_at_tournament.team_at_tournament.id}"}}}}'
            )
            return response
    else:
        form = UpdateMemberToRosterForm(instance=member_at_tournament)
    return render(
        request,
        "tournaments/partials/roster_dialog_update_form.html",
        {"form": form},
    )


@login_required
@require_POST
def remove_member_from_roster_view(
    request: HttpRequest, member_at_tournament_id: int
) -> HttpResponse:
    member_at_tournament = get_object_or_404(MemberAtTournament, pk=member_at_tournament_id)

    current_club = get_current_club(request)
    if current_club.id != member_at_tournament.team_at_tournament.application.team.club_id:
        raise PermissionDenied()

    if not member_at_tournament.tournament.has_open_rosters:
        messages.error(request, "The roster deadline has passed")
        return HttpResponse(status=400)

    member_at_tournament.delete()
    logger.info(
        "Member removed from roster; member=%s, team=%s, tournament=%s",
        member_at_tournament.member,
        member_at_tournament.team_at_tournament,
        member_at_tournament.tournament,
    )
    messages.success(request, "Member removed successfully")

    response = render(
        request,
        "tournaments/partials/roster_dialog.html",
        {
            "team_at_tournament": member_at_tournament.team_at_tournament,
            "members_at_tournament": MemberAtTournament.objects.select_related("member").filter(
                team_at_tournament_id=member_at_tournament.team_at_tournament.id
            ),
        },
    )
    response["HX-Trigger"] = "teamsListChanged"
    return response


@require_GET
def teams_table_view(request: HttpRequest, tournament_id: int) -> HttpResponse:
    tournament = get_object_or_404(
        Tournament.objects.select_related("competition"),
        pk=tournament_id,
    )
    return render(
        request,
        "tournaments/partials/tournament_detail_teams_table.html",
        {
            "tournament": tournament,
            "teams_at_tournament": (
                TeamAtTournament.objects.filter(tournament_id=tournament_id)
                .select_related("application", "application__team", "application__team__club")
                .annotate(members_count_on_roster=Count("members"))
                .order_by("final_placement", "seeding")
            ),
        },
    )


@require_GET
def export_rosters_csv_view(request: HttpRequest, tournament_id: int) -> HttpResponse:
    """Export all rosters for a tournament as CSV. Staff/superuser only."""
    if not (request.user.is_staff or request.user.is_superuser):
        raise PermissionDenied()

    tournament = get_object_or_404(Tournament, pk=tournament_id)

    members_at_tournament = (
        MemberAtTournament.objects.filter(tournament=tournament)
        .select_related(
            "member",
            "team_at_tournament__application__team__club",
        )
        .order_by(
            "team_at_tournament__application__team__name",
            "member__last_name",
            "member__first_name",
        )
    )

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="rosters_{tournament_id}.csv"'
    response.write("\ufeff")  # BOM for Excel

    writer = csv.writer(response)
    writer.writerow(
        [
            "first_name",
            "last_name",
            "birth_date",
            "sex",
            "citizenship",
            "team",
            "club",
            "is_captain",
            "is_spirit_captain",
            "is_coach",
            "jersey_number",
        ]
    )

    for mat in members_at_tournament:
        writer.writerow(
            [
                mat.member.first_name,
                mat.member.last_name,
                mat.member.birth_date.strftime("%Y-%m-%d"),
                mat.member.get_sex_display(),
                mat.member.citizenship.code,
                mat.team_at_tournament.application.team_name,
                mat.team_at_tournament.application.team.club.name,
                mat.is_captain,
                mat.is_spirit_captain,
                mat.is_coach,
                mat.jersey_number or "",
            ]
        )

    return response
