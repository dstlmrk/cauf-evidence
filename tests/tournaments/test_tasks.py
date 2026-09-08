from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone
from tournaments.tasks import send_roster_deadline_reminders

from tests.factories import (
    ClubFactory,
    CompetitionApplicationFactory,
    MemberAtTournamentFactory,
    TeamAtTournamentFactory,
    TeamFactory,
    TournamentFactory,
)


def _tournament_with_team(hours_to_deadline, club=None, tournament=None):
    """Tournament with one team of the given (or a new) club on it."""
    tournament = tournament or TournamentFactory(
        rosters_deadline=timezone.now() + timedelta(hours=hours_to_deadline)
    )
    team_at_tournament = TeamAtTournamentFactory(
        tournament=tournament,
        application=CompetitionApplicationFactory(
            competition=tournament.competition,
            team=TeamFactory(club=club or ClubFactory()),
        ),
    )
    return tournament, team_at_tournament


@patch("tournaments.tasks.notify_club")
def test_reminder_is_sent_12_hours_before_deadline(mock_notify_club):
    tournament, _ = _tournament_with_team(hours_to_deadline=11)

    send_roster_deadline_reminders()

    mock_notify_club.assert_called_once()
    assert tournament.name in mock_notify_club.call_args[1]["message"]
    tournament.refresh_from_db()
    assert tournament.rosters_reminder_sent_at is not None


@patch("tournaments.tasks.notify_club")
def test_reminder_is_not_sent_twice(mock_notify_club):
    _tournament_with_team(hours_to_deadline=11)

    send_roster_deadline_reminders()
    send_roster_deadline_reminders()

    mock_notify_club.assert_called_once()


@patch("tournaments.tasks.notify_club")
def test_delayed_run_still_sends_the_reminder(mock_notify_club):
    _tournament_with_team(hours_to_deadline=2)

    send_roster_deadline_reminders()

    mock_notify_club.assert_called_once()


@patch("tournaments.tasks.notify_club")
def test_reminder_is_not_sent_too_early(mock_notify_club):
    _tournament_with_team(hours_to_deadline=13)

    send_roster_deadline_reminders()

    mock_notify_club.assert_not_called()


@patch("tournaments.tasks.notify_club")
def test_reminder_is_not_sent_after_deadline(mock_notify_club):
    _tournament_with_team(hours_to_deadline=-1)

    send_roster_deadline_reminders()

    mock_notify_club.assert_not_called()


@patch("tournaments.tasks.notify_club")
def test_moved_deadline_starts_the_reminder_over(mock_notify_club):
    tournament, _ = _tournament_with_team(hours_to_deadline=11)

    send_roster_deadline_reminders()

    tournament.rosters_deadline = timezone.now() + timedelta(days=7)
    tournament.save()
    send_roster_deadline_reminders()
    tournament.refresh_from_db()
    assert tournament.rosters_reminder_sent_at is None

    tournament.rosters_deadline = timezone.now() + timedelta(hours=11)
    tournament.save()
    send_roster_deadline_reminders()

    assert mock_notify_club.call_count == 2
    tournament.refresh_from_db()
    assert tournament.rosters_reminder_sent_at is not None


@patch("tournaments.tasks.notify_club")
def test_club_with_two_teams_gets_a_single_notification(mock_notify_club):
    club = ClubFactory()
    tournament, first_team = _tournament_with_team(hours_to_deadline=11, club=club)
    _, second_team = _tournament_with_team(hours_to_deadline=11, club=club, tournament=tournament)

    send_roster_deadline_reminders()

    mock_notify_club.assert_called_once()
    message = mock_notify_club.call_args[1]["message"]
    assert first_team.application.team_name in message
    assert second_team.application.team_name in message


@patch("tournaments.tasks.notify_club")
def test_every_club_at_the_tournament_is_notified(mock_notify_club):
    tournament, _ = _tournament_with_team(hours_to_deadline=11)
    _tournament_with_team(hours_to_deadline=11, tournament=tournament)

    send_roster_deadline_reminders()

    assert mock_notify_club.call_count == 2


@patch("tournaments.tasks.notify_club")
def test_reminder_contains_roster_link_and_players(mock_notify_club):
    tournament, team_at_tournament = _tournament_with_team(hours_to_deadline=11)
    member_at_tournament = MemberAtTournamentFactory(
        tournament=tournament,
        team_at_tournament=team_at_tournament,
    )

    send_roster_deadline_reminders()

    call_kwargs = mock_notify_club.call_args[1]
    expected_link = f"/tournaments/{tournament.pk}/detail?roster={team_at_tournament.pk}"
    assert expected_link in call_kwargs["message"]
    assert expected_link in call_kwargs["email_body"]
    assert member_at_tournament.member.full_name in call_kwargs["email_body"]
    assert member_at_tournament.member.full_name not in call_kwargs["message"]


@patch("tournaments.tasks.notify_club")
def test_empty_roster_is_pointed_out_in_the_email(mock_notify_club):
    _tournament_with_team(hours_to_deadline=11)

    send_roster_deadline_reminders()

    assert "Soupiska je prázdná" in mock_notify_club.call_args[1]["email_body"]


@patch("tournaments.tasks.notify_club")
def test_tournament_without_teams_is_skipped(mock_notify_club):
    tournament = TournamentFactory(rosters_deadline=timezone.now() + timedelta(hours=11))

    send_roster_deadline_reminders()

    mock_notify_club.assert_not_called()
    tournament.refresh_from_db()
    assert tournament.rosters_reminder_sent_at is not None


@patch("tournaments.tasks.notify_club")
def test_failing_club_does_not_block_the_others(mock_notify_club):
    tournament, _ = _tournament_with_team(hours_to_deadline=11)
    _tournament_with_team(hours_to_deadline=11, tournament=tournament)
    mock_notify_club.side_effect = [Exception("boom"), None]

    send_roster_deadline_reminders()

    assert mock_notify_club.call_count == 2
    tournament.refresh_from_db()
    assert tournament.rosters_reminder_sent_at is not None
