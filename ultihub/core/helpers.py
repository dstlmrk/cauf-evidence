import csv
from dataclasses import dataclass
from io import StringIO

from django.http import HttpRequest


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
