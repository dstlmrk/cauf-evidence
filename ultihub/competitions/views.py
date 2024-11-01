from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from competitions.models import Competition


def competitions(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "competitions/competitions.html",
        context={
            "competitions": Competition.objects.select_related(
                "age_restriction", "season", "division"
            )
            .exclude(is_for_national_teams=True)
            .order_by("-pk")
            .all()
        },
    )
