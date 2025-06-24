from core.helpers import get_current_club_or_none
from django.http import HttpRequest

from clubs.models import ClubNotification


def notifications(request: HttpRequest) -> dict:
    if request.path.startswith("/admin/"):
        return {}

    club = get_current_club_or_none(request)
    if request.user.is_authenticated and club:
        new_notifications_count = ClubNotification.objects.filter(
            is_read=False,
            agent_at_club__agent_id=request.user.agent.id,
            agent_at_club__club_id=club.id,
        ).count()
    else:
        new_notifications_count = None

    return {"new_notifications_count": new_notifications_count}
