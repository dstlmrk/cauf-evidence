import json
import logging
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

logger = logging.getLogger(__name__)


@require_GET
def homepage_view(request: HttpRequest) -> HttpResponse:
    return redirect("tournaments:tournaments")


@require_GET
def faq_view(request: HttpRequest) -> HttpResponse:
    return render(request, "core/faq.html")


@require_GET
def privacy_policy_view(request: HttpRequest) -> HttpResponse:
    return render(request, "core/privacy-policy.html")


@csrf_exempt
@require_POST
def sentry_tunnel_view(request: HttpRequest) -> HttpResponse:
    if not settings.SENTRY_DSN:
        return HttpResponse(status=404)

    try:
        body = request.body
        header_line = body.split(b"\n", 1)[0]
        header = json.loads(header_line)
    except (json.JSONDecodeError, IndexError):
        return HttpResponse("Invalid envelope", status=400)

    dsn = header.get("dsn")
    if not dsn:
        return HttpResponse("Missing DSN in envelope header", status=400)

    try:
        parsed_dsn = urlparse(dsn)
        parsed_allowed = urlparse(settings.SENTRY_DSN)
    except ValueError:
        return HttpResponse("Invalid DSN", status=400)

    project_id = parsed_dsn.path.strip("/")
    allowed_project_id = parsed_allowed.path.strip("/")

    if parsed_dsn.hostname != parsed_allowed.hostname or project_id != allowed_project_id:
        return HttpResponse("Forbidden", status=403)

    upstream_url = f"https://{parsed_dsn.hostname}/api/{project_id}/envelope/"

    try:
        resp = requests.post(
            upstream_url,
            data=body,
            headers={"Content-Type": "application/x-sentry-envelope"},
            timeout=5,
        )
    except requests.RequestException:
        logger.exception("Failed to forward envelope to Sentry")
        return HttpResponse("Upstream error", status=502)

    return HttpResponse(status=resp.status_code)
