import logging
from datetime import date

from competitions.models import AgeLimit
from core.helpers import get_app_settings, get_club_id, get_current_club, get_default_season
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef, Q
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import now
from django.views.decorators.http import require_GET, require_POST
from finance.forms import SeasonFeesCheckForm
from finance.models import Invoice, InvoiceTypeEnum
from members.models import CoachLicence, FavouriteMember, Member, Transfer
from users.models import AgentAtClub, NewAgentRequest
from users.services import (
    NewAgentRequestAlreadyExistsError,
    assign_or_invite_agent_to_club,
    unassign_or_cancel_agent_invite_from_club,
)

from clubs.forms import AddAgentForm, ClubForm, ClubLogoForm, TeamForm
from clubs.models import Club, ClubLogo, ClubNotification, Team
from clubs.services import remove_club_logo, save_club_logo

logger = logging.getLogger(__name__)


@login_required
def invoices(request: HttpRequest) -> HttpResponse:
    invoices_qs = Invoice.objects.filter(club_id=get_club_id(request)).order_by("-pk")

    selected_type = request.GET.get("type")
    if selected_type and selected_type.isdigit():
        invoices_qs = invoices_qs.filter(type=selected_type)

    return render(
        request,
        "clubs/invoices.html",
        {
            "invoices": invoices_qs,
            "invoice_types": InvoiceTypeEnum.choices,
            "selected_type": selected_type,
        },
    )


@login_required
def transfers_view(request: HttpRequest) -> HttpResponse:
    current_club = get_current_club(request)
    return render(
        request,
        "clubs/transfers.html",
        {
            "transfers": Transfer.objects.filter(
                Q(source_club__id=current_club.id) | Q(target_club__id=current_club.id)
            ).select_related(
                "member",
                "source_club",
                "target_club",
                "requesting_club",
                "approving_club",
                "requested_by__user",
                "approved_by__user",
            ),
        },
    )


@login_required
def members(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "clubs/members.html",
        {
            "any_member_exists": Member.objects.filter(club_id=get_club_id(request)).exists(),
            "age_limits": AgeLimit.objects.all().order_by("name"),
            # The season whose reference date drives the age-category filter, shown
            # next to each category so it's clear what age is used.
            "age_season": get_default_season("competition"),
        },
    )


@login_required
def season_fees_view(request: HttpRequest) -> HttpResponse:
    return render(request, "clubs/season_fees.html", {"form": SeasonFeesCheckForm()})


@login_required
@require_GET
def member_list(request: HttpRequest) -> HttpResponse:
    current_date = now().date()
    # The age-category filter mirrors competition eligibility, which evaluates age
    # at the season's reference date (typically 31st December) rather than today —
    # so the filter matches the selections made later when building rosters. The
    # "current" season matches how the rest of the app resolves it; fall back to
    # the end of the current year when none exists.
    season = get_default_season("competition")
    age_reference_date = season.age_reference_date if season else date(current_date.year, 12, 31)
    return render(
        request,
        "clubs/partials/member_list.html",
        {
            "members": (
                Member.objects.filter(club_id=get_club_id(request))
                .annotate(
                    has_coach_licence=Exists(
                        CoachLicence.objects.filter(
                            member=OuterRef("pk"),
                            valid_from__lte=current_date,
                            valid_to__gte=current_date,
                        )
                    ),
                    # Favourites are per-agent; pin the current agent's favourites
                    # to the top of the default ordering.
                    is_favourite=Exists(
                        FavouriteMember.objects.filter(
                            agent=request.user.agent,  # type: ignore[union-attr]
                            member=OuterRef("pk"),
                        )
                    ),
                )
                .annotate_age(age_reference_date)  # type: ignore[attr-defined]
                .order_by("-is_favourite", "last_name", "first_name")
            )
        },
    )


@login_required
def teams_view(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "clubs/teams.html",
    )


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
def team_list_view(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "clubs/partials/team_list.html",
        {
            "teams": Team.objects.filter(club_id=get_club_id(request), is_active=True),
        },
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
            "club": club,
            "club_form": club_form,
            "logo_form": ClubLogoForm(),
            "pending_logo": ClubLogo.objects.filter(club=club, is_approved=False).first(),
        },
    )


@login_required
@require_POST
def upload_logo(request: HttpRequest) -> HttpResponse:
    if not get_app_settings().club_logo_upload_enabled:
        raise Http404

    club = get_object_or_404(Club, pk=get_club_id(request))
    logo_form = ClubLogoForm(request.POST, request.FILES)

    if not logo_form.is_valid():
        for error in logo_form.errors["logo"]:
            messages.error(request, str(error))
        return redirect("clubs:settings")

    save_club_logo(club, logo_form.cleaned_data["logo"])
    messages.success(
        request,
        "Logo uploaded successfully. It will be used once the association approves it.",
    )
    return redirect("clubs:settings")


@login_required
@require_POST
def remove_logo(request: HttpRequest) -> HttpResponse:
    if not get_app_settings().club_logo_upload_enabled:
        raise Http404

    remove_club_logo(get_object_or_404(Club, pk=get_club_id(request)))
    messages.success(request, "Logo removed successfully.")
    return HttpResponse(status=204, headers={"HX-Refresh": "true"})


@login_required
@require_POST
def cancel_pending_logo(request: HttpRequest) -> HttpResponse:
    if not get_app_settings().club_logo_upload_enabled:
        raise Http404

    remove_club_logo(get_object_or_404(Club, pk=get_club_id(request)), pending_only=True)
    messages.success(request, "Upload cancelled successfully.")
    return HttpResponse(status=204, headers={"HX-Refresh": "true"})


@require_GET
def club_logo(request: HttpRequest, club_id: int, size: str) -> HttpResponse:
    """
    Serves the approved logo of a club. Deliberately public and cached hard: the URL carries
    the approval timestamp as a query parameter, so a logo taken into use is a new URL and
    the previous one can be considered immutable. Logos waiting for approval are never served
    here; they are previewed inline where they are reviewed.
    """
    logo = get_object_or_404(
        ClubLogo.objects.only(size),
        club_id=club_id,
        is_approved=True,
    )

    response = HttpResponse(getattr(logo, size), content_type="image/webp")
    response["Cache-Control"] = "public, max-age=31536000, immutable"
    return response


@login_required
def add_agent(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = AddAgentForm(request.POST)
        if form.is_valid():
            try:
                assign_or_invite_agent_to_club(
                    email=form.cleaned_data["email"],
                    club=get_object_or_404(Club, pk=get_club_id(request)),
                    invited_by=request.user,  # type: ignore
                )
                messages.success(request, "Agent added successfully.")
                return HttpResponse(status=204, headers={"HX-Trigger": "agentListChanged"})
            except NewAgentRequestAlreadyExistsError:
                messages.error(
                    request,
                    (
                        "The agent is already invited to the application."
                        " He must complete it before the next invitation."
                    ),
                )
                return HttpResponse(status=409)
    else:
        form = AddAgentForm()
    return render(request, "clubs/partials/add_agent_form.html", {"form": form})


@login_required
@require_POST
def remove_agent(request: HttpRequest) -> HttpResponse:
    try:
        unassign_or_cancel_agent_invite_from_club(
            email=request.POST["email"],
            club=get_object_or_404(Club, pk=get_club_id(request)),
        )
    except ValueError as ex:
        # The agent is already removed (e.g. double click) or is the primary
        # agent which cannot be removed at all.
        messages.error(request, str(ex))
        return HttpResponse(status=409)
    messages.success(request, "Agent removed successfully.")
    return HttpResponse(status=204, headers={"HX-Trigger": "agentListChanged"})


@login_required
def agent_list(request: HttpRequest) -> HttpResponse:
    club = get_object_or_404(Club, pk=get_club_id(request))
    agents_at_club = AgentAtClub.objects.filter(club=club, is_active=True).select_related(
        "agent__user"
    )

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


@login_required
def notifications_dialog_view(request: HttpRequest) -> HttpResponse:
    notifications_qs = ClubNotification.objects.filter(
        agent_at_club__agent_id=request.user.agent.id,  # type: ignore
        agent_at_club__club_id=get_current_club(request).id,
    ).order_by("-created_at")

    if request.method == "POST":
        notifications_qs.filter(is_read=False).update(is_read=True)
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})
    else:
        limit = 5
        unread_notifications_count = notifications_qs.filter(is_read=False).count()
        if unread_notifications_count > 0:
            notifications_qs = notifications_qs[: max(unread_notifications_count + 1, limit)]
        else:
            notifications_qs = notifications_qs[:limit]
        return render(
            request,
            "clubs/partials/notifications_dialog.html",
            {"notifications": notifications_qs},
        )
