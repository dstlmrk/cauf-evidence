from clubs.models import Club
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from users.forms import AgentForm


@login_required
@require_POST
def switch_club(request: HttpRequest) -> HttpResponse:
    club_id = request.POST.get("club_id")
    if not club_id:
        return HttpResponseBadRequest("Missing club_id")

    club = get_object_or_404(Club, id=club_id)
    if not request.user.has_perm("manage_club", club):
        return HttpResponse(status=403)

    request.session["club"] = {"id": club.id, "name": club.name}
    messages.success(request, "Club switched successfully")
    return HttpResponse(status=204, headers={"HX-Refresh": "true"})


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
