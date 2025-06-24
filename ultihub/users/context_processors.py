from django.http import HttpRequest

from users.services import get_user_managed_clubs


def user_managed_clubs(request: HttpRequest) -> dict:
    if request.path.startswith("/admin/"):
        return {}

    return {
        "user_managed_clubs": get_user_managed_clubs(
            request.user  # type: ignore
        )
    }
