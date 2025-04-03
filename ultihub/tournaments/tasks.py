import logging
from collections import defaultdict
from datetime import datetime, time, timedelta

from clubs.service import notify_club
from django.db.models import Count
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from huey import crontab
from huey.contrib.djhuey import db_periodic_task

from tournaments.models import TeamAtTournament, Tournament
from ultihub.settings import BASE_URL

logger = logging.getLogger(__name__)


@db_periodic_task(crontab(minute="0", hour="14"))
def send_roster_reminders() -> None:
    """
    Periodic task to send reminders to clubs about their rosters before deadline.
    """
    logger.info("Check coming roster deadlines and send reminders")

    today_16 = timezone.make_aware(datetime.combine(timezone.now(), time(16, 0)))
    tomorrow_16 = today_16 + timedelta(days=1)

    tournaments_qs = Tournament.objects.filter(
        rosters_deadline__gte=today_16,
        rosters_deadline__lt=tomorrow_16,
        are_reminders_sent=False,
    )

    if not tournaments_qs.exists():
        logger.info("No tournaments with upcoming roster deadlines")
        return

    teams_by_club = defaultdict(list)
    tournaments_by_club = defaultdict(set)

    for team_at_tournament in (
        TeamAtTournament.objects.filter(tournament__in=tournaments_qs)
        .select_related("tournament", "application", "application__team")
        .annotate(roster_count=Count("members"))
    ):
        club = team_at_tournament.application.team.club
        tournaments_by_club[club].add(team_at_tournament.tournament)
        teams_by_club[club].append(
            {
                "tournament_name": str(team_at_tournament.tournament),
                "deadline": team_at_tournament.tournament.rosters_deadline,
                "team_name": team_at_tournament.application.team_name,
                "roster_count": team_at_tournament.roster_count,
                "roster_link": "{base_url}{path}?roster={team_at_tournament_id}".format(
                    base_url=BASE_URL,
                    path=reverse("tournaments:detail", args=(team_at_tournament.tournament.pk,)),
                    team_at_tournament_id=team_at_tournament.id,
                ),
            }
        )

    for club, data in teams_by_club.items():
        if club.id != 8:  # Terrible Monkeys:
            continue

        notify_club(
            club,
            "Roster reminder",
            "The roster deadline is approaching. Check teams: <ul>{}</ul>".format(
                "".join(
                    [
                        (
                            f'<li><a href="{x['roster_link']}">{x['team_name']}</a>'
                            f' at {x['tournament_name']}<br>'
                            f'Players on roster:&nbsp;{x['roster_count']},'
                            f' Deadline:&nbsp;{x['deadline']:%d.%m.%Y %H:%M}</li>'
                        )
                        for x in teams_by_club[club]
                    ]
                )
            ),
            render_to_string("emails/roster_reminder.html", {"rosters": data}),
        )

    tournaments_qs.update(are_reminders_sent=True)
    logger.info("Tournaments are marked as reminders sent. Finished.")
