from django.http import HttpRequest

from core.helpers import get_app_settings


def app_settings(request: HttpRequest) -> dict:
    return {"app_settings": get_app_settings()}
