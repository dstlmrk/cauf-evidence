import json

from clubs.service import notify_club
from core.helpers import get_current_club
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, OuterRef, Subquery
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


@require_GET
def tournaments_view(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "tournaments/tournaments.html",
        {
            "tournaments": Tournament.objects.select_related(
                "competition",
                "competition__season",
                "competition__division",
                "competition__age_limit",
            )
            .annotate(
                team_count=Count("teams", distinct=True),
                member_count=Count("members", distinct=True),
                winner_team=Subquery(
                    TeamAtTournament.objects.filter(
                        tournament=OuterRef("pk"), final_placement=1
                    ).values("application__team_name")[:1]
                ),
            )
            .order_by("-start_date", "competition__division", "name"),
        },
    )


@require_GET
def tournament_detail_view(request: HttpRequest, tournament_id: int) -> HttpResponse:
    return render(
        request,
        "tournaments/tournament_detail.html",
        {
            "tournament": Tournament.objects.select_related("competition")
            .annotate(
                team_count=Count("teams", distinct=True),
                member_count=Count("members", distinct=True),
            )
            .get(pk=tournament_id),
        },
    )


@require_GET
def roster_dialog_view(request: HttpRequest, team_at_tournament_id: int) -> HttpResponse:
    team_at_tournament = get_object_or_404(TeamAtTournament, pk=team_at_tournament_id)
    return render(
        request,
        "tournaments/partials/roster_dialog.html",
        {
            "team_at_tournament": team_at_tournament,
            "members_at_tournament": MemberAtTournament.objects.select_related("member").filter(
                team_at_tournament_id=team_at_tournament.id
            ),
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
        member = (
            Member.objects.select_related("club")
            .annotate_age(team_at_tournament.tournament.competition.season.age_reference_date)  # type: ignore
            .get(pk=request.POST["member_id"])
        )
        form = AddMemberToRosterForm(
            request.POST, tournament=team_at_tournament.tournament, member=member
        )

        if form.is_valid():
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
                        "Your player {} has been registered on the roster"
                        " of another club for this tournament: {} ({}).\n"
                        "Link: {}"
                    ).format(
                        member.full_name,
                        tournament.name,
                        team_at_tournament.application.team_name,
                        request.build_absolute_uri(
                            reverse("tournaments:detail", args=(tournament.pk,))
                        ),
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
    return render(
        request,
        "tournaments/partials/tournament_detail_teams_table.html",
        {
            "tournament": Tournament.objects.select_related("competition").get(pk=tournament_id),
            "teams_at_tournament": (
                TeamAtTournament.objects.filter(tournament_id=tournament_id)
                .select_related("application", "application__team", "application__team__club")
                .annotate(members_count_on_roster=Count("members"))
                .order_by("final_placement", "seeding")
            ),
        },
    )
