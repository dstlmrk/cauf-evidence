from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from guardian.decorators import permission_required_or_403
from guardian.shortcuts import get_users_with_perms
from users.api import (
    assign_or_invite_agent_to_club,
    unassign_or_cancel_agent_invite_from_club,
)
from users.models import NewAgentRequest

from clubs.forms import AddAgentForm, ClubForm, OrganizationForm
from clubs.models import Club


@login_required
def members(request: HttpRequest, club_id: int) -> HttpResponse:
    # https://docs.djangoproject.com/en/5.1/intro/tutorial03/
    return render(request, "clubs/members.html", context={"club_id": club_id})


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
def add_agent_to_club(request: HttpRequest, club_id: int) -> HttpResponse:
    if request.method == "POST":
        form = AddAgentForm(request.POST)
        if form.is_valid():
            assign_or_invite_agent_to_club(
                email=form.cleaned_data["email"],
                club=get_object_or_404(Club, pk=club_id),
            )
            messages.success(request, "Agent added successfully.")
            return HttpResponse(status=204, headers={"HX-Trigger": "agentListChanged"})
    else:
        form = AddAgentForm()
    return render(request, "partials/add_agent_form.html", {"form": form})


@login_required
@permission_required_or_403("clubs.manage_club", (Club, "id", "club_id"))
@require_POST
def remove_agent_from_club(request: HttpRequest, club_id: int) -> HttpResponse:
    unassign_or_cancel_agent_invite_from_club(
        email=request.POST["email"],
        club=get_object_or_404(Club, pk=club_id),
    )
    messages.success(request, "Agent removed successfully.")
    return HttpResponse(status=200, headers={"HX-Trigger": "agentListChanged"})


@login_required
@permission_required_or_403("clubs.manage_club", (Club, "id", "club_id"))
def agent_list(request: HttpRequest, club_id: int) -> HttpResponse:
    club = get_object_or_404(Club, pk=club_id)
    agents = [
        {
            "email": user.email,
            "picture_url": user.agent.picture_url,
            "full_name": user.get_full_name(),
            "has_joined": True,
        }
        for user in get_users_with_perms(club, only_with_perms_in=["manage_club"])
    ]
    new_agent_requests = [
        {
            "email": new_agent_request.email,
            "invited_at": new_agent_request.created_at,
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
