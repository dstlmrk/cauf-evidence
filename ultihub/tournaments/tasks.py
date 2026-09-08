import logging
from collections import defaultdict
from datetime import timedelta

import sentry_sdk
from clubs.models import Club
from clubs.services import notify_club
from django.db.models import Prefetch
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from huey import crontab
from huey.contrib.djhuey import db_periodic_task
from ultihub.settings import BASE_URL

from tournaments.models import MemberAtTournament, TeamAtTournament, Tournament

logger = logging.getLogger(__name__)

# How long before the roster deadline clubs get their reminder
REMINDER_HOURS = 12

NOTIFICATION_SUBJECT = "Blíží se uzávěrka soupisek"


def _roster_link(team_at_tournament: TeamAtTournament) -> str:
    path = reverse("tournaments:detail", args=(team_at_tournament.tournament_id,))
    return f"{BASE_URL}{path}?roster={team_at_tournament.pk}"


def _get_teams_by_club(tournament: Tournament) -> dict[Club, list[TeamAtTournament]]:
    teams_by_club: dict[Club, list[TeamAtTournament]] = defaultdict(list)

    for team_at_tournament in (
        TeamAtTournament.objects.filter(tournament=tournament)
        .select_related("application__team__club")
        .prefetch_related(
            Prefetch(
                "members",
                queryset=MemberAtTournament.objects.select_related("member").order_by(
                    "member__last_name", "member__first_name"
                ),
            )
        )
    ):
        teams_by_club[team_at_tournament.application.team.club].append(team_at_tournament)

    return teams_by_club


def _format_notification_message(
    tournament: Tournament, teams: list[TeamAtTournament], deadline: str
) -> str:
    """Short body for the in-app notification; the e-mail carries the full rosters."""
    list_items = format_html_join(
        "\n",
        '<li><a href="{}">{}</a> — hráčů na soupisce:&nbsp;{}</li>',
        (
            (_roster_link(team), team.application.team_name, len(team.members.all()))
            for team in teams
        ),
    )

    return format_html(
        "<p>Soupisky turnaje <b>{}</b> se zavírají <b>{}</b>."
        " Zkontroluj si je, po uzávěrce už je nelze upravit.</p>\n<ul>\n{}\n</ul>",
        tournament.name,
        deadline,
        list_items,
    )


def _render_email_body(tournament: Tournament, teams: list[TeamAtTournament], deadline: str) -> str:
    return render_to_string(
        "emails/roster_reminder.html",
        {
            "tournament": tournament,
            "deadline": deadline,
            "teams": [
                {
                    "name": team.application.team_name,
                    "roster_link": _roster_link(team),
                    "members": [
                        member_at_tournament.member for member_at_tournament in team.members.all()
                    ],
                }
                for team in teams
            ],
        },
    )


def _send_reminders_for_tournament(tournament: Tournament) -> None:
    deadline = timezone.localtime(tournament.rosters_deadline).strftime("%d.%m.%Y %H:%M")

    for club, teams in _get_teams_by_club(tournament).items():
        # Keep going for the remaining clubs; the tournament is marked as reminded either
        # way, so a single failing club cannot cause a second round of e-mails to everyone.
        try:
            notify_club(
                club=club,
                subject=NOTIFICATION_SUBJECT,
                message=_format_notification_message(tournament, teams, deadline),
                email_body=_render_email_body(tournament, teams, deadline),
            )
        except Exception as ex:
            logger.exception(
                "Failed to send roster deadline reminder to club %s for tournament %s",
                club.id,
                tournament.id,
            )
            sentry_sdk.capture_exception(ex)


@db_periodic_task(crontab(minute="0", hour="*"))
def send_roster_deadline_reminders() -> None:
    """
    Periodic task reminding clubs with a team at a tournament that its rosters are about
    to close. Runs hourly and notifies each club once, so a missed run only delays the
    reminder instead of dropping it.
    """
    logger.info("Start sending roster deadline reminders")

    now = timezone.now()
    reminder_threshold = now + timedelta(hours=REMINDER_HOURS)

    # A deadline moved further out starts over so clubs are reminded about the new date
    Tournament.objects.filter(
        rosters_deadline__gt=reminder_threshold,
        rosters_reminder_sent_at__isnull=False,
    ).update(rosters_reminder_sent_at=None)

    reminded = 0

    for tournament in Tournament.objects.filter(
        rosters_deadline__gt=now,
        rosters_deadline__lte=reminder_threshold,
        rosters_reminder_sent_at__isnull=True,
    ):
        # Process each tournament in isolation so a single failure cannot abort the whole run
        try:
            _send_reminders_for_tournament(tournament)
        except Exception as ex:
            logger.exception("Failed to send roster deadline reminders for %s", tournament.id)
            sentry_sdk.capture_exception(ex)
            continue

        Tournament.objects.filter(pk=tournament.pk).update(rosters_reminder_sent_at=timezone.now())
        reminded += 1

    logger.info("End sending roster deadline reminders, notified %d tournaments", reminded)
