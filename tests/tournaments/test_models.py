from datetime import datetime
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone


class TestTournamentModel:
    """Test Tournament model validation"""

    @pytest.mark.parametrize(
        "deadline_datetime,expected_valid",
        [
            # Valid: deadline before first day
            (datetime(2025, 3, 3, 23, 59, 59), True),
            # Valid: deadline during first day
            (datetime(2025, 3, 4, 8, 0, 0), True),
            # Invalid: deadline after first day
            (datetime(2025, 3, 5, 8, 0, 0), False),
        ],
    )
    def test_rosters_deadline_validation(
        self, tournament_factory, deadline_datetime, expected_valid
    ):
        """Test that rosters_deadline must be within the first day of the tournament"""
        start_date = datetime(2025, 3, 4).date()
        end_date = datetime(2025, 3, 6).date()
        rosters_deadline = timezone.make_aware(deadline_datetime)

        tournament = tournament_factory.build(
            start_date=start_date,
            end_date=end_date,
            rosters_deadline=rosters_deadline,
        )

        if expected_valid:
            tournament.clean()
        else:
            with pytest.raises(ValidationError) as exc_info:
                tournament.clean()

            assert "rosters_deadline" in exc_info.value.error_dict
            assert "Roster deadline cannot be after the first day of the tournament" in str(
                exc_info.value.error_dict["rosters_deadline"]
            )


class TestTournamentWinners:
    """Test Tournament winner_team and sotg_winner_team automatic updates"""

    def test_winner_team_set_on_final_placement(
        self, tournament_factory, team_at_tournament_factory
    ):
        """Test that winner_team is set when a team gets final_placement=1"""
        tournament = tournament_factory()
        team1 = team_at_tournament_factory(tournament=tournament)
        team2 = team_at_tournament_factory(tournament=tournament)

        # Set team1 as winner
        team1.final_placement = 1
        team1.save()

        tournament.refresh_from_db()
        assert tournament.winner_team == team1

        # Change winner to team2
        team1.final_placement = 2
        team1.save()
        team2.final_placement = 1
        team2.save()

        tournament.refresh_from_db()
        assert tournament.winner_team == team2

    def test_sotg_winner_team_set_on_spirit_avg(
        self, tournament_factory, team_at_tournament_factory
    ):
        """Test that sotg_winner_team is set based on best spirit_avg"""
        tournament = tournament_factory()
        _team1 = team_at_tournament_factory(
            tournament=tournament, spirit_avg=Decimal("15.500"), final_placement=2
        )
        team2 = team_at_tournament_factory(
            tournament=tournament, spirit_avg=Decimal("16.200"), final_placement=1
        )
        team3 = team_at_tournament_factory(
            tournament=tournament, spirit_avg=Decimal("14.800"), final_placement=3
        )

        tournament.refresh_from_db()
        assert tournament.sotg_winner_team == team2  # Highest spirit_avg

        # Update team3 to have best spirit
        team3.spirit_avg = Decimal("17.000")
        team3.save()

        tournament.refresh_from_db()
        assert tournament.sotg_winner_team == team3

    def test_sotg_winner_tiebreaker_by_final_placement(
        self, tournament_factory, team_at_tournament_factory
    ):
        """Test that final_placement is used as tiebreaker when spirit_avg is equal"""
        tournament = tournament_factory()
        _team1 = team_at_tournament_factory(
            tournament=tournament, spirit_avg=Decimal("15.000"), final_placement=2
        )
        team2 = team_at_tournament_factory(
            tournament=tournament, spirit_avg=Decimal("15.000"), final_placement=1
        )

        tournament.refresh_from_db()
        # When spirit_avg is equal, team with better final_placement wins
        assert tournament.sotg_winner_team == team2

    def test_sotg_winner_none_when_no_spirit(self, tournament_factory, team_at_tournament_factory):
        """Test that sotg_winner_team is None when no team has spirit_avg"""
        tournament = tournament_factory()
        _team1 = team_at_tournament_factory(
            tournament=tournament, spirit_avg=None, final_placement=2
        )
        _team2 = team_at_tournament_factory(
            tournament=tournament, spirit_avg=None, final_placement=1
        )

        tournament.refresh_from_db()
        # When no team has spirit_avg, sotg_winner_team should be None
        assert tournament.sotg_winner_team is None

    def test_winner_cleared_when_team_deleted(self, tournament_factory, team_at_tournament_factory):
        """Test that winner_team is cleared when the winning team is deleted"""
        tournament = tournament_factory()
        team1 = team_at_tournament_factory(tournament=tournament, final_placement=1)
        _team2 = team_at_tournament_factory(tournament=tournament, final_placement=2)

        tournament.refresh_from_db()
        assert tournament.winner_team == team1

        # Delete winning team
        team1.delete()

        tournament.refresh_from_db()
        # Should now be team2 if they become winner, or None if no winner
        # In this case, no team has final_placement=1 anymore, so should be None
        assert tournament.winner_team is None

    def test_no_winner_when_no_teams(self, tournament_factory):
        """Test that winner_team is None when tournament has no teams"""
        tournament = tournament_factory()

        assert tournament.winner_team is None
        assert tournament.sotg_winner_team is None

    def test_update_winners_method(self, tournament_factory, team_at_tournament_factory):
        """Test that update_winners() method correctly recalculates winners"""
        tournament = tournament_factory()
        team1 = team_at_tournament_factory(
            tournament=tournament, final_placement=1, spirit_avg=Decimal("15.000")
        )
        team2 = team_at_tournament_factory(
            tournament=tournament, final_placement=2, spirit_avg=Decimal("16.000")
        )

        # Manually call update_winners
        tournament.update_winners()
        tournament.refresh_from_db()

        assert tournament.winner_team == team1  # final_placement=1
        assert tournament.sotg_winner_team == team2  # best spirit_avg
