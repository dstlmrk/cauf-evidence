from uuid import UUID

from core.helpers import get_club_id
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.timezone import now
from django.views.decorators.http import require_GET, require_POST
from finance.models import Invoice
from users.models import AgentAtClub, NewAgentRequest
from users.services import (
    assign_or_invite_agent_to_club,
    unassign_or_cancel_agent_invite_from_club,
)

from clubs.forms import AddAgentForm, ClubForm, MemberConfirmEmailForm, MemberForm, TeamForm
from clubs.models import Club, CoachLicence, Member, Team


@login_required
def invoices(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "clubs/invoices.html",
        {"invoices": Invoice.objects.filter(club_id=get_club_id(request)).order_by("-pk")},
    )


@login_required
def members(request: HttpRequest) -> HttpResponse:
    return render(request, "clubs/members.html")


@login_required
@require_GET
def member_list(request: HttpRequest) -> HttpResponse:
    current_date = now().date()
    return render(
        request,
        "clubs/partials/member_list.html",
        {
            "members": Member.objects.filter(club_id=get_club_id(request)).annotate(
                has_coach_licence=Exists(
                    CoachLicence.objects.filter(
                        member=OuterRef("pk"),
                        valid_from__lte=current_date,
                        valid_to__gte=current_date,
                    )
                ),
            )
        },
    )


def confirm_email(request: HttpRequest, token: UUID) -> HttpResponse:
    member = get_object_or_404(Member, email_confirmation_token=token)
    if request.method == "POST":
        form = MemberConfirmEmailForm(request.POST, member=member)
        if form.is_valid():
            member.has_email_confirmed = True
            member.email_confirmation_token = None
            if form.cleaned_data.get("marketing_consent"):
                member.marketing_consent_given_at = now()
            member.save()
            messages.success(request, "You have confirmed your email")
            return HttpResponse(status=204, headers={"HX-Redirect": reverse("home")})
    else:
        form = MemberConfirmEmailForm(member=member)
    return render(request, "clubs/confirm_email.html", {"form": form, "member": member})


@login_required
def add_member(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = MemberForm(request.POST)
        if form.is_valid():
            form.instance.club_id = get_club_id(request)
            form.save()
            messages.success(request, "Confirmation email sent")
            return HttpResponse(status=204, headers={"HX-Trigger": "memberListChanged"})
    else:
        form = MemberForm()
    return render(request, "clubs/partials/member_form.html", {"form": form})


@login_required
def edit_member(request: HttpRequest, member_id: int) -> HttpResponse:
    member = get_object_or_404(Member, pk=member_id, club_id=get_club_id(request))
    if request.method == "POST":
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            messages.success(request, "Member updated successfully.")
            return HttpResponse(status=204, headers={"HX-Trigger": "memberListChanged"})
    else:
        form = MemberForm(instance=member)
    return render(request, "clubs/partials/member_form.html", {"form": form})


@login_required
@require_GET
def coach_licence_list(request: HttpRequest, member_id: int) -> HttpResponse:
    return render(
        request,
        "clubs/partials/coach_licence_list.html",
        {"coach_licences": CoachLicence.objects.filter(member_id=member_id).order_by("-valid_to")},
    )


@login_required
def teams(request: HttpRequest) -> HttpResponse:
    return render(request, "clubs/teams.html")


@login_required
def add_team(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = TeamForm(request.POST)
        if form.is_valid():
            form.instance.club_id = get_club_id(request)
            form.save()
            messages.success(request, "Team added successfully.")
            return HttpResponse(status=204, headers={"HX-Trigger": "teamListChanged"})
    else:
        form = TeamForm()
    return render(request, "clubs/partials/team_form.html", {"form": form})


@login_required
def edit_team(request: HttpRequest, team_id: int) -> HttpResponse:
    team = get_object_or_404(Team, pk=team_id, club_id=get_club_id(request), is_primary=False)
    if request.method == "POST":
        form = TeamForm(request.POST, instance=team)
        if form.is_valid():
            form.save()
            messages.success(request, "Team updated successfully.")
            return HttpResponse(status=204, headers={"HX-Trigger": "teamListChanged"})
    else:
        form = TeamForm(instance=team)
    return render(request, "clubs/partials/team_form.html", {"form": form})


@login_required
@require_POST
def remove_team(request: HttpRequest, team_id: int) -> HttpResponse:
    Team.objects.filter(id=team_id, club_id=get_club_id(request), is_primary=False).update(
        is_active=False
    )
    messages.success(request, "Team removed successfully.")
    return HttpResponse(status=204, headers={"HX-Trigger": "teamListChanged"})


@login_required
def team_list(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "clubs/partials/team_list.html",
        {"teams": Team.objects.filter(club_id=get_club_id(request), is_active=True)},
    )


@login_required
def settings(request: HttpRequest) -> HttpResponse:
    club = get_object_or_404(Club, pk=get_club_id(request))
    club_form = ClubForm(instance=club)

    if request.method == "POST" and "submit_club" in request.POST:
        club_form = ClubForm(request.POST, instance=club)
        if club_form.is_valid():
            club_form.save()

            # Sync navbar club name
            request.session["club"]["name"] = club_form.cleaned_data["name"]
            request.session.modified = True

            messages.success(request, "Club updated successfully.")
            return redirect("clubs:settings")

    return render(
        request,
        "clubs/settings.html",
        context={
            "club_form": club_form,
        },
    )


@login_required
def add_agent(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = AddAgentForm(request.POST)
        if form.is_valid():
            assign_or_invite_agent_to_club(
                email=form.cleaned_data["email"],
                club=get_object_or_404(Club, pk=get_club_id(request)),
                invited_by=request.user,  # type: ignore
            )
            messages.success(request, "Agent added successfully.")
            return HttpResponse(status=204, headers={"HX-Trigger": "agentListChanged"})
    else:
        form = AddAgentForm()
    return render(request, "clubs/partials/add_agent_form.html", {"form": form})


@login_required
@require_POST
def remove_agent(request: HttpRequest) -> HttpResponse:
    unassign_or_cancel_agent_invite_from_club(
        email=request.POST["email"],
        club=get_object_or_404(Club, pk=get_club_id(request)),
        kicked_out_by=request.user,  # type: ignore
    )
    messages.success(request, "Agent removed successfully.")
    return HttpResponse(status=204, headers={"HX-Trigger": "agentListChanged"})


@login_required
def agent_list(request: HttpRequest) -> HttpResponse:
    club = get_object_or_404(Club, pk=get_club_id(request))
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
        request, "clubs/partials/agent_list.html", {"agents": agents + new_agent_requests}
    )
