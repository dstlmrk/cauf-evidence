from django.http import HttpRequest


def get_club_id(request: HttpRequest) -> int:
    return request.session.get("club", {}).get("id")
