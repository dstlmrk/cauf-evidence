import logging

from core.tasks import send_email
from users.models import AgentAtClub

from clubs.models import Club, ClubNotification

logger = logging.getLogger(__name__)


def notify_club(club: Club, subject: str, message: str) -> None:
    logger.info("Notifying club %s about %s", club.name, subject)

    club_agents = AgentAtClub.objects.filter(club=club, is_active=True)
    for agent_at_club in club_agents:
        ClubNotification.objects.create(
            agent_at_club=agent_at_club,
            subject=subject,
            message=message,
        )

    for agent_at_club in club_agents.filter(agent__has_email_notifications_enabled=True):
        send_email(subject, message, to=[agent_at_club.agent.user.email])
