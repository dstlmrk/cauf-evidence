from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from competitions.models import Competition


def competitions(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "competitions/competitions.html",
        context={"competitions": Competition.objects.all()},
    )


@require_GET
def json_competitions(request: HttpRequest) -> JsonResponse:
    return JsonResponse(
        {
            "data": [
                {
                    "name": competition.name,
                    "season": competition.season.name,
                }
                for competition in Competition.objects.all()
            ]
        }
    )
