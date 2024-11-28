from uuid import UUID

from core.helpers import get_club_id
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.timezone import now
from django.views.decorators.http import require_GET

from members.forms import MemberConfirmEmailForm, MemberForm
from members.models import CoachLicence, Member


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
    return render(request, "members/partials/member_form.html", {"form": form})


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
    return render(request, "members/confirm_email.html", {"form": form, "member": member})
