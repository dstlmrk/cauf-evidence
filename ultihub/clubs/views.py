from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from guardian.decorators import permission_required_or_403
from users.api import (
    assign_or_invite_agent_to_club,
    unassign_or_cancel_agent_invite_from_club,
)
from users.models import AgentAtClub, NewAgentRequest

from clubs.forms import AddAgentForm, ClubForm, OrganizationForm, TeamForm
from clubs.models import Club, Team


@login_required
def members(request: HttpRequest, club_id: int) -> HttpResponse:
    # https://docs.djangoproject.com/en/5.1/intro/tutorial03/
    return render(request, "clubs/members.html", context={"club_id": club_id})


@login_required
@permission_required_or_403("clubs.manage_club", (Club, "id", "club_id"))
def teams(request: HttpRequest, club_id: int) -> HttpResponse:
    return render(request, "clubs/teams.html", {"club_id": club_id})


@login_required
@permission_required_or_403("clubs.manage_club", (Club, "id", "club_id"))
def add_team(request: HttpRequest, club_id: int) -> HttpResponse:
    if request.method == "POST":
        form = TeamForm(request.POST)
        if form.is_valid():
            form.instance.club_id = club_id
            form.save()
            messages.success(request, "Team added successfully.")
            return HttpResponse(status=204, headers={"HX-Trigger": "teamListChanged"})
    else:
        form = TeamForm()
    return render(request, "partials/team_form.html", {"form": form})


@login_required
@permission_required_or_403("clubs.manage_club", (Club, "id", "club_id"))
def edit_team(request: HttpRequest, club_id: int, team_id: int) -> HttpResponse:
    team = get_object_or_404(Team, pk=team_id, club_id=club_id, is_primary=False)
    if request.method == "POST":
        form = TeamForm(request.POST, instance=team)
        if form.is_valid():
            form.save()
            messages.success(request, "Team updated successfully.")
            return HttpResponse(status=204, headers={"HX-Trigger": "teamListChanged"})
    else:
        form = TeamForm(instance=team)
    return render(request, "partials/team_form.html", {"form": form})


@login_required
@permission_required_or_403("clubs.manage_club", (Club, "id", "club_id"))
@require_POST
def remove_team(request: HttpRequest, club_id: int, team_id: int) -> HttpResponse:
    Team.objects.filter(id=team_id, club_id=club_id, is_primary=False).update(is_active=False)
    messages.success(request, "Team removed successfully.")
    return HttpResponse(status=200, headers={"HX-Trigger": "teamListChanged"})


@login_required
@permission_required_or_403("clubs.manage_club", (Club, "id", "club_id"))
def team_list(request: HttpRequest, club_id: int) -> HttpResponse:
    return render(
        request,
        "partials/team_list.html",
        {"teams": Team.objects.filter(club_id=club_id, is_active=True), "club_id": club_id},
    )


@login_required
@permission_required_or_403("clubs.manage_club", (Club, "id", "club_id"))
def settings(request: HttpRequest, club_id: int) -> HttpResponse:
    club = get_object_or_404(Club, pk=club_id)

    club_form = ClubForm(instance=club)
    organization_form = OrganizationForm(instance=club.organization)

    if request.method == "POST":
        if "submit_club" in request.POST:
            club_form = ClubForm(request.POST, instance=club)
            if club_form.is_valid():
                club_form.save()

                # Sync navbar club name
                request.session["club"]["name"] = club_form.cleaned_data["name"]
                request.session.modified = True

                messages.success(request, "Club updated successfully.")
                return redirect("clubs:settings", club_id=club_id)

        elif "submit_organization" in request.POST:
            organization_form = OrganizationForm(data=request.POST, instance=club.organization)
            if organization_form.is_valid():
                organization_form.save()
                messages.success(request, "Organization updated successfully.")
                return redirect("clubs:settings", club_id=club_id)

    return render(
        request,
        "clubs/settings.html",
        context={
            "club_id": club_id,
            "club_form": club_form,
            "organization_form": organization_form,
        },
    )


@login_required
@permission_required_or_403("clubs.manage_club", (Club, "id", "club_id"))
def add_agent(request: HttpRequest, club_id: int) -> HttpResponse:
    if request.method == "POST":
        form = AddAgentForm(request.POST)
        if form.is_valid():
            assign_or_invite_agent_to_club(
                email=form.cleaned_data["email"],
                club=get_object_or_404(Club, pk=club_id),
                invited_by=request.user,  # type: ignore
            )
            messages.success(request, "Agent added successfully.")
            return HttpResponse(status=204, headers={"HX-Trigger": "agentListChanged"})
    else:
        form = AddAgentForm()
    return render(request, "partials/add_agent_form.html", {"form": form})


@login_required
@permission_required_or_403("clubs.manage_club", (Club, "id", "club_id"))
@require_POST
def remove_agent(request: HttpRequest, club_id: int) -> HttpResponse:
    unassign_or_cancel_agent_invite_from_club(
        email=request.POST["email"],
        club=get_object_or_404(Club, pk=club_id),
        kicked_out_by=request.user,  # type: ignore
    )
    messages.success(request, "Agent removed successfully.")
    return HttpResponse(status=200, headers={"HX-Trigger": "agentListChanged"})


@login_required
@permission_required_or_403("clubs.manage_club", (Club, "id", "club_id"))
def agent_list(request: HttpRequest, club_id: int) -> HttpResponse:
    club = get_object_or_404(Club, pk=club_id)
    agents_at_club = AgentAtClub.objects.filter(club=club, is_active=True)

    agents = [
        {
            "email": agent_at_club.agent.user.email,
            "picture_url": agent_at_club.agent.picture_url,
            "full_name": agent_at_club.agent.user.get_full_name(),
            "has_joined": True,
            "is_primary": agent_at_club.is_primary,
        }
        for agent_at_club in agents_at_club
    ]
    new_agent_requests = [
        {
            "email": new_agent_request.email,
            "invited_at": new_agent_request.created_at,
            "invited_by": new_agent_request.invited_by,
            "is_primary": new_agent_request.is_primary,
        }
        for new_agent_request in NewAgentRequest.objects.filter(
            club=club, processed_at__isnull=True
        )
    ]

    return render(
        request,
        "partials/agent_list.html",
        {
            "agents": agents + new_agent_requests,
            "club_id": club_id,
        },
    )
