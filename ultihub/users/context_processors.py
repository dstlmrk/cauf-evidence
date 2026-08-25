from django.http import HttpRequest

from users.services import get_user_managed_clubs


def user_managed_clubs(request: HttpRequest) -> dict:
    if request.path.startswith("/admin/"):
        return {}

    clubs = list(get_user_managed_clubs(request.user))  # type: ignore
    selected_club_id = (request.session.get("club") or {}).get("id")

    return {
        "user_managed_clubs": clubs,
        # The selected club as a model instance, which the navbar needs for its logo
        "current_club": next((club for club in clubs if club.id == selected_club_id), None),
    }
