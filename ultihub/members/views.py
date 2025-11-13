import logging
from typing import cast
from uuid import UUID

from clubs.models import Club
from competitions.models import Season
from core.helpers import get_current_club
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.timezone import now
from django.views.decorators.http import require_GET, require_POST
from tournaments.models import Tournament

from members.forms import (
    MemberConfirmEmailForm,
    MemberForm,
    TransferRequestForm,
    TransferRequestFromMyClubForm,
    TransferRequestToMyClubForm,
)
from members.helpers import (
    approve_transfer,
    create_transfer_request,
    notify_monitored_citizenship,
    reject_transfer,
    revoke_transfer,
)
from members.models import CoachLicence, Member, Transfer
from members.services import search as search_service
from members.tasks import generate_nsa_export

logger = logging.getLogger(__name__)


@login_required
def add_member(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = MemberForm(request.POST)
        if form.is_valid():
            form.instance.club_id = get_current_club(request).id
            form.save()
            notify_monitored_citizenship(form.instance)
            if form.instance.email or form.instance.legal_guardian_email:
                messages.success(request, "Confirmation email sent")
            else:
                messages.success(request, "Member created successfully")
            return HttpResponse(status=204, headers={"HX-Trigger": "memberListChanged"})
        else:
            messages.error(request, "Member not created")
    else:
        form = MemberForm()
    return render(request, "members/partials/member_form.html", {"form": form})


@login_required
def edit_member(request: HttpRequest, member_id: int) -> HttpResponse:
    member = get_object_or_404(Member, pk=member_id, club_id=get_current_club(request).id)
    if request.method == "POST":
        old_citizenship = member.citizenship.code
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            # Notify if citizenship was changed to monitored country
            if form.instance.citizenship.code != old_citizenship:
                notify_monitored_citizenship(form.instance)
            messages.success(request, "Member updated successfully.")
            return HttpResponse(status=204, headers={"HX-Trigger": "memberListChanged"})
        else:
            messages.error(request, "Member not updated")
    else:
        form = MemberForm(instance=member)
    return render(request, "members/partials/member_form.html", {"form": form})


@login_required
@require_GET
def coach_licence_list(request: HttpRequest, member_id: int) -> HttpResponse:
    return render(
        request,
        "members/partials/coach_licence_list.html",
        {"coach_licences": CoachLicence.objects.filter(member_id=member_id).order_by("-valid_to")},
    )


def confirm_email(request: HttpRequest, token: UUID) -> HttpResponse:
    member = get_object_or_404(Member, email_confirmation_token=token)
    if request.method == "POST":
        form = MemberConfirmEmailForm(request.POST, member=member)
        current_time = now()
        if form.is_valid():
            member.email_confirmed_at = current_time
            member.email_confirmation_token = None
            if form.cleaned_data.get("marketing_consent"):
                member.marketing_consent_given_at = current_time
            member.save()
            messages.success(request, "You have confirmed your email")
            return HttpResponse(status=204, headers={"HX-Redirect": reverse("home")})
    else:
        form = MemberConfirmEmailForm(member=member)
    return render(request, "members/confirm_email.html", {"form": form, "member": member})


@login_required
def search(request: HttpRequest) -> JsonResponse:
    current_club = get_current_club(request)
    query = request.GET.get("q", "").strip()
    tournament_id = request.GET.get("tournament_id")
    member_id = request.GET.get("member_id")

    if tournament_id == "null":
        tournament = None
    else:
        tournament = get_object_or_404(Tournament, pk=tournament_id)

    logger.info(
        f"Searching for members with query: {query},"
        f" tournament_id: {tournament_id}, member_id: {member_id}"
    )

    if member_id:
        # If member_id is provided, return that specific member
        try:
            members = [Member.objects.select_related("club").get(pk=member_id)]
        except Member.DoesNotExist:
            members = []
    else:
        members = search_service(query, current_club.id, tournament)

    return JsonResponse(
        {
            "results": [
                {
                    "id": member.id,
                    "full_name": f"{member.first_name} {member.last_name}",
                    "birth_year": member.birth_date.year,
                    "club": {
                        "id": member.club.id,
                        "name": member.club.name,
                    },
                    "default_jersey_number": member.default_jersey_number,
                    "flag": member.citizenship.unicode_flag,
                }
                for member in members
            ]
        }
    )


@login_required
def transfer_form(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form: TransferRequestFromMyClubForm | TransferRequestToMyClubForm | TransferRequestForm
        member_id = request.POST.get("member_id")
        current_club = get_current_club(request)

        if member_id:
            member = Member.objects.select_related("club").get(pk=member_id)
            if member.club.id == get_current_club(request).id:
                form = TransferRequestFromMyClubForm(request.POST, member=member)
            else:
                form = TransferRequestToMyClubForm(
                    request.POST, member=member, current_club=current_club
                )
            try:
                if form.is_valid():
                    create_transfer_request(
                        agent=request.user.agent,  # type: ignore
                        current_club=Club.objects.get(pk=current_club.id),
                        member=member,
                        source_club=Club.objects.get(pk=form.cleaned_data["source_club"]),
                        target_club=Club.objects.get(pk=form.cleaned_data["target_club"]),
                    )
                    messages.success(request, "Transfer request created")
                    # TODO: solve HTMX cases when the request fails (everywhere in the app)
                    #  I don't see error messages in the UI (or in the console)
                    return HttpResponse(status=204, headers={"HX-Refresh": "true"})
            except ValidationError as ex:
                messages.error(request, ex.message)
                form = TransferRequestForm()
        else:
            form = TransferRequestForm(request.POST)

        return render(request, "members/partials/transfer_form.html", {"form": form})

    else:
        member_id = request.GET.get("member_id")

        if member_id:
            member = Member.objects.select_related("club").get(pk=member_id)
            current_club = get_current_club(request)

            if member.club.id == current_club.id:
                form = TransferRequestFromMyClubForm(member=member)
            else:
                form = TransferRequestToMyClubForm(member=member, current_club=current_club)
        else:
            form = TransferRequestForm()

        return render(request, "members/partials/transfer_form.html", {"form": form})


@login_required
@require_POST
def change_transfer_state_view(request: HttpRequest) -> HttpResponse:
    transfer_id = request.POST.get("transfer_id")
    action = request.POST.get("action")
    transfer = get_object_or_404(Transfer, pk=transfer_id)

    if action in ["approve", "reject"]:
        if transfer.approving_club.id != get_current_club(request).id:
            return HttpResponse(status=403)
        if action == "approve":
            approve_transfer(agent=request.user.agent, transfer=transfer)  # type: ignore
            messages.success(request, "Transfer approved")
        else:
            reject_transfer(transfer=transfer)
            messages.success(request, "Transfer rejected")
    else:
        if transfer.requesting_club.id != get_current_club(request).id:
            return HttpResponse(status=403)
        revoke_transfer(transfer=transfer)
        messages.success(request, "Transfer revoked")

    return HttpResponse(status=204, headers={"HX-Refresh": "true"})


@login_required
@require_GET
def nsa_export_modal_view(request: HttpRequest) -> HttpResponse:
    seasons = Season.objects.all().order_by("-name")
    last_season = Season.objects.last()
    return render(
        request,
        "members/partials/nsa_export_modal.html",
        {"seasons": seasons, "last_season": last_season},
    )


@login_required
@require_POST
def export_members_csv_for_nsa_view(request: HttpRequest) -> HttpResponse:
    season_id = request.POST.get("season_id")

    if season_id:
        season = get_object_or_404(Season, pk=season_id)
    else:
        season = cast(Season, Season.objects.last())

    generate_nsa_export(
        user=request.user,
        season=season,
        club=Club.objects.get(id=get_current_club(request).id),
    )
    messages.success(
        request,
        (
            f"The process of exporting members for {season.name} season has started."
            " The file will be sent to your email."
        ),
    )
    return HttpResponse(status=204)
