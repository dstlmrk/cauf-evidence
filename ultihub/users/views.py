from clubs.models import Club
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from users.forms import AgentForm


@login_required
@require_POST
def switch_club(request: HttpRequest) -> HttpResponse:
    messages.success(request, "Club switched successfully")
    club = Club.objects.get(id=request.POST["club_id"])
    if request.user.has_perm("manage_club", club):
        request.session["club"] = {"id": club.id, "name": club.name}
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})
    else:
        return HttpResponse(status=403)


@login_required
def profile_view(request: HttpRequest) -> HttpResponse:
    agent = request.user.agent  # type: ignore
    if request.method == "POST":
        form = AgentForm(request.POST, instance=agent)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully")
    else:
        form = AgentForm(instance=agent)
    return render(request, "users/profile.html", {"form": form})
