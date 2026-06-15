from typing import Any

from clubs.models import Club, Team
from core.helpers import (
    get_current_club,
    get_current_club_or_none,
    get_filter_context_and_params,
)
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Prefetch, ProtectedError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from competitions.enums import ApplicationStateEnum
from competitions.filters import CompetitionFilterSet
from competitions.forms import RegistrationForm
from competitions.models import (
    Competition,
    CompetitionApplication,
)
from competitions.services import get_competitions_qs_with_related_data


def competitions(request: HttpRequest) -> HttpResponse:
    session_club = get_current_club_or_none(request)
    # The session may still reference a club that has since been deleted; fall back to
    # no club instead of raising a 500 so the public competitions page keeps rendering.
    club = Club.objects.filter(id=session_club.id).first() if session_club else None

    context: dict[str, Any] = {}

    if club:
        context["club_application_without_invoice_total"] = CompetitionApplication.objects.filter(
            team__club=club, invoice__isnull=True, state=ApplicationStateEnum.AWAITING_PAYMENT
        ).count()

    # Build queryset with filters
    competitions_qs = get_competitions_qs_with_related_data(club_id=club.id if club else None)

    # Default season + shared filter context for core/partials/competition_filters.html
    query_params, filter_context = get_filter_context_and_params(request)

    # Apply filters using FilterSet
    filter_set = CompetitionFilterSet(query_params, queryset=competitions_qs)
    competitions_qs = filter_set.qs

    return render(
        request,
        "competitions/competitions.html",
        context={
            # Skip the financial-settings gate locally so registration can be
            # exercised without a configured Fakturoid subject.
            "is_unset_fakturoid_id": bool(club and not club.fakturoid_subject_id)
            and not settings.DEBUG,
            "competitions": competitions_qs.annotate(
                has_final_placement=Exists(
                    CompetitionApplication.objects.filter(
                        competition_id=OuterRef("pk"),
                        final_placement__isnull=False,
                    )
                )
            ),
            **filter_context,
            **context,
        },
    )


@login_required
@transaction.atomic
def registration(request: HttpRequest, competition_id: int) -> HttpResponse:
    current_club = get_current_club(request)
    teams_with_applications = Team.objects.filter(club_id=current_club.id).prefetch_related(
        Prefetch(
            "applications",
            queryset=CompetitionApplication.objects.filter(competition_id=competition_id),
            to_attr="prefetched_applications",
        )
    )

    if request.method == "POST":
        competition = get_object_or_404(Competition, pk=competition_id)
        # Enforce the registration deadline on the server; the template only hides
        # the submit button, so a form opened before the deadline must not be accepted afterwards.
        if not competition.has_open_registration:
            raise PermissionDenied()
        form = RegistrationForm(request.POST, teams_with_applications=teams_with_applications)
        if form.is_valid():
            for checkbox_name, value in form.cleaned_data.items():
                team_id = int(checkbox_name.split("_")[1])
                team = teams_with_applications.get(pk=team_id)
                if team.club.id == current_club.id:
                    if value and not team.prefetched_applications:
                        try:
                            # A double submit can race past the prefetched-applications check
                            # above; the (competition, team) unique constraint then rejects the
                            # second insert. Wrap each create in a savepoint so one duplicate
                            # does not break the surrounding atomic transaction, and treat it as
                            # an already-registered team instead of returning a 500.
                            with transaction.atomic():
                                CompetitionApplication.objects.create(
                                    team_name=team.name,
                                    competition_id=competition_id,
                                    team=team,
                                    registered_by=request.user,  # type: ignore
                                    state=(
                                        ApplicationStateEnum.PAID
                                        if competition.deposit == 0
                                        else ApplicationStateEnum.AWAITING_PAYMENT
                                    ),
                                )
                        except IntegrityError:
                            messages.error(
                                request,
                                f"Team {team.name} is already registered for this tournament.",
                            )
                            return HttpResponse(status=400)
                else:
                    raise PermissionDenied()

            messages.success(
                request,
                (
                    "Your team has been registered for the tournament. "
                    "To finalize the registration, please confirm it above."
                ),
            )
            return HttpResponse(status=204, headers={"HX-Refresh": "true"})
    else:
        form = RegistrationForm(teams_with_applications=teams_with_applications)
    return render(request, "competitions/partials/registration_form.html", {"form": form})


@require_GET
def application_list(request: HttpRequest, competition_id: int) -> HttpResponse:
    competition = get_object_or_404(Competition, pk=competition_id)
    return render(
        request,
        "competitions/partials/application_list.html",
        {
            "competition": competition,
            "applications": CompetitionApplication.objects.filter(competition=competition)
            .select_related("team__club", "invoice")
            .order_by("created_at"),
        },
    )


@require_GET
def competition_detail_view(request: HttpRequest, competition_id: int) -> HttpResponse:
    club = get_current_club_or_none(request)
    competition = get_object_or_404(
        get_competitions_qs_with_related_data(
            club_id=club.id if club else None,
            competition_id=competition_id,
        )
    )
    return render(
        request,
        "competitions/partials/competition_detail.html",
        {"competition": competition},
    )


@login_required
@require_POST
def cancel_application_view(request: HttpRequest, application_id: int) -> HttpResponse:
    application = get_object_or_404(CompetitionApplication, pk=application_id)
    if (
        application.team.club.id == get_current_club(request).id
        and application.competition.has_open_registration
        and application.is_cancellable
    ):
        try:
            application.delete()
        except ProtectedError:
            # The team is already assigned to a tournament (TeamAtTournament has
            # on_delete=PROTECT), so the application cannot be removed anymore.
            messages.error(
                request,
                "Cannot cancel application: the team is already assigned to a tournament.",
            )
            return HttpResponse(status=409)
        messages.success(request, "The application has been cancelled.")
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})
    else:
        raise PermissionDenied()


@require_GET
def competition_final_placements_dialog_view(
    request: HttpRequest, competition_id: int
) -> HttpResponse:
    return render(
        request,
        "competitions/partials/competition_final_placements_dialog.html",
        {
            "competition": get_object_or_404(Competition, pk=competition_id),
            "competition_applications": CompetitionApplication.objects.select_related(
                "team", "team__club"
            )
            .filter(
                competition_id=competition_id,
            )
            .order_by("final_placement"),
        },
    )
