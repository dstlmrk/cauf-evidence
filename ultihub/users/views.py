import re

from clubs.models import Club
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_POST


@require_POST
def switch_club(request: HttpRequest) -> HttpResponse:
    messages.success(request, "Club switched successfully.")
    club = Club.objects.get(id=request.POST["club_id"])
    if request.user.has_perm("manage_club", club):
        request.session["club"] = {"id": club.id, "name": club.name}
        redirect_url = re.sub(r"/clubs/\d+/", f"/clubs/{club.id}/", request.META["HTTP_REFERER"])
        return HttpResponse(status=200, headers={"HX-Redirect": redirect_url})
    else:
        return HttpResponse(status=403)
