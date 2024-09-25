from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from clubs.forms import ClubForm, OrganizationForm
from clubs.models import Club


@login_required
def members(request: HttpRequest, club_id: int) -> HttpResponse:
    # https://docs.djangoproject.com/en/5.1/intro/tutorial03/
    return render(request, "clubs/members.html", context={"club_id": club_id})


@login_required
def settings(request: HttpRequest, club_id: int) -> HttpResponse:
    # TODO: Add permissions
    club = get_object_or_404(Club, pk=club_id)

    club_form = ClubForm(instance=club)
    organization_form = OrganizationForm(instance=club.organization)

    if request.method == "POST":
        if "submit_club" in request.POST:
            club_form = ClubForm(request.POST, instance=club)
            if club_form.is_valid():
                club_form.save()
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
