from dataclasses import dataclass

from django.http import HttpRequest


@dataclass
class SessionClub:
    id: int
    name: str


def get_club_id(request: HttpRequest) -> int:
    return get_current_club(request).id


def get_current_club(request: HttpRequest) -> SessionClub:
    return SessionClub(**request.session.get("club", {}))
