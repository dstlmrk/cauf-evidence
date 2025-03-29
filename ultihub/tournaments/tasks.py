import logging
from datetime import datetime, time, timedelta

from core.tasks import send_email
from django.db.models import Count
from django.template.loader import render_to_string
from django.utils import timezone
from huey import crontab
from huey.contrib.djhuey import db_periodic_task

from tournaments.models import TeamAtTournament

logger = logging.getLogger(__name__)


# @db_periodic_task(crontab(minute="0", hour="14"))
@db_periodic_task(crontab(minute="*", hour="*"))
def send_roster_reminders() -> None:
    """
    Periodic task to send reminders to clubs about their rosters before deadline.
    """
    logger.info("Check coming roster deadlines and send reminders")

    today_16 = timezone.make_aware(datetime.combine(timezone.now(), time(16, 0)))
    tomorrow_16 = today_16 + timedelta(days=1)

    # TODO: posilam email pouze pokud jsou nejake takove turnaje
    #  musim nastavit are_reminders_sent na True
    #  poslat email vsem zastupcum klubu

    html_content = render_to_string(
        "emails/roster_reminder.html",
        {
            "rosters": [
                {
                    "tournament_name": team.tournament.name,
                    "team_name": team.application.team_name,
                    "roster_count": team.roster_count,
                    "roster_link": f"https://ultihub.cz/roster/{team.id}/",
                }
                for team in TeamAtTournament.objects.filter(
                    tournament__rosters_deadline__gte=today_16,
                    tournament__rosters_deadline__lt=tomorrow_16,
                    tournament__are_reminders_sent=False,
                )
                .select_related("tournament", "application")
                .annotate(roster_count=Count("members"))
            ]
        },
    )

    send_email("Roster reminder", html_content, to=["dstlmrk@gmail.com"])
