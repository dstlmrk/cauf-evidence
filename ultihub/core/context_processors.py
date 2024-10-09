from django.http import HttpRequest

from ultihub import settings


def app_version_processor(request: HttpRequest) -> dict:
    return {"release_datetime": settings.RELEASE_DATETIME}
