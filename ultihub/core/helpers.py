import csv
import json
from dataclasses import dataclass
from io import StringIO
from typing import Any

from django.http import HttpRequest, HttpResponse, QueryDict

from core.models import AppSettings


@dataclass
class SessionClub:
    id: int
    name: str


def get_club_id(request: HttpRequest) -> int:
    return get_current_club(request).id


def get_current_club(request: HttpRequest) -> SessionClub:
    return SessionClub(**request.session.get("club", {}))


def get_current_club_or_none(request: HttpRequest) -> SessionClub | None:
    try:
        return get_current_club(request)
    except TypeError:
        return None


def get_filter_context_and_params(
    request: HttpRequest,
) -> tuple[QueryDict, dict[str, Any]]:
    """
    Shared "default season + competition filters" logic used by the tournaments,
    international tournaments and competitions list views.

    Returns a copy of the request GET params with the season defaulted to the
    newest season (when no season filter is provided) and the context dict
    consumed by ``core/partials/competition_filters.html``.
    """
    # Imported locally to avoid a circular import (competitions.models imports core.models).
    from competitions.enums import EnvironmentEnum
    from competitions.models import AgeLimit, Division, Season

    # Set default season to the newest one if no season filter is applied
    query_params = request.GET.copy()
    if "season" not in query_params:
        newest_season = Season.objects.order_by("-name").first()
        if newest_season:
            query_params["season"] = str(newest_season.id)

    filter_context: dict[str, Any] = {
        "seasons": Season.objects.all().order_by("-name"),
        "selected_season_id": query_params.get("season"),
        "environments": EnvironmentEnum.choices,
        "divisions": Division.objects.all().order_by("name"),
        "age_limits": AgeLimit.objects.all().order_by("name"),
    }

    return query_params, filter_context


def hx_trigger_response(*, status: int = 204, **events: Any) -> HttpResponse:
    """
    Build an ``HttpResponse`` with a JSON-encoded ``HX-Trigger`` header.

    Each keyword argument is an HTMX event name mapped to its detail payload, e.g.
    ``hx_trigger_response(teamsListChanged=True)`` yields ``{"teamsListChanged": true}``.
    """
    response = HttpResponse(status=status)
    response["HX-Trigger"] = json.dumps(dict(events))
    return response


def get_app_settings() -> AppSettings:
    return AppSettings.get_solo()


def create_csv(header: list[str], data: list[list]) -> str:
    csv_buffer = StringIO()
    csv_buffer.write("\ufeff")  # BOM (Byte Order Mark) to support Excel
    csv_writer = csv.writer(csv_buffer)

    csv_writer.writerow(header)

    for item in data:
        csv_writer.writerow(item)

    csv_data = csv_buffer.getvalue()
    csv_buffer.close()

    return csv_data
