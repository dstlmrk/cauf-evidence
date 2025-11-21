from decimal import Decimal
from io import StringIO

import pytest
from competitions.enums import CompetitionFeeTypeEnum
from django.core.management import call_command
from django.core.management.base import CommandError

from tests.factories import (
    ClubFactory,
    CompetitionApplicationFactory,
    CompetitionFactory,
    MemberAtTournamentFactory,
    MemberFactory,
    TeamAtTournamentFactory,
    TeamFactory,
    TournamentFactory,
)


class TestCompetitionOnlyFeesCommand:
    """Tests for the competition_only_fees management command."""

    def test_member_only_in_target_competition_is_included(self, season_factory):
        """Member who participated only in target competition should be included."""
        season = season_factory(name="2025", regular_fee=Decimal("600"))
        competition = CompetitionFactory(
            season=season,
            fee_type=CompetitionFeeTypeEnum.REGULAR,
        )
        tournament = TournamentFactory(competition=competition)
        club = ClubFactory()
        team = TeamFactory(club=club)
        application = CompetitionApplicationFactory(competition=competition, team=team)
        team_at_tournament = TeamAtTournamentFactory(tournament=tournament, application=application)
        member = MemberFactory(club=club, first_name="Jan", last_name="Novak")
        MemberAtTournamentFactory(
            tournament=tournament,
            team_at_tournament=team_at_tournament,
            member=member,
        )

        out = StringIO()
        call_command(
            "competition_only_fees",
            competition_id=competition.id,
            stdout=out,
        )
        output = out.getvalue()

        assert "Novak Jan" in output
        assert "Total members: 1" in output
        assert "Total fees: 600" in output

    def test_member_in_multiple_competitions_is_excluded(self, season_factory):
        """Member who participated in multiple competitions should be excluded."""
        season = season_factory(name="2025")
        competition1 = CompetitionFactory(season=season, name="EDGE")
        competition2 = CompetitionFactory(season=season, name="Liga")

        tournament1 = TournamentFactory(competition=competition1)
        tournament2 = TournamentFactory(competition=competition2)

        club = ClubFactory()
        team = TeamFactory(club=club)

        application1 = CompetitionApplicationFactory(competition=competition1, team=team)
        application2 = CompetitionApplicationFactory(competition=competition2, team=team)

        team_at_tournament1 = TeamAtTournamentFactory(
            tournament=tournament1, application=application1
        )
        team_at_tournament2 = TeamAtTournamentFactory(
            tournament=tournament2, application=application2
        )

        member = MemberFactory(club=club, first_name="Petr", last_name="Svoboda")
        MemberAtTournamentFactory(
            tournament=tournament1,
            team_at_tournament=team_at_tournament1,
            member=member,
        )
        MemberAtTournamentFactory(
            tournament=tournament2,
            team_at_tournament=team_at_tournament2,
            member=member,
        )

        out = StringIO()
        call_command(
            "competition_only_fees",
            competition_id=competition1.id,
            stdout=out,
        )
        output = out.getvalue()

        assert "Svoboda Petr" not in output
        assert "No members found" in output

    def test_correct_fee_calculation_discounted(self, season_factory):
        """Should use discounted fee for DISCOUNTED fee type."""
        season = season_factory(name="2025", discounted_fee=Decimal("200"))
        competition = CompetitionFactory(
            season=season,
            fee_type=CompetitionFeeTypeEnum.DISCOUNTED,
        )
        tournament = TournamentFactory(competition=competition)
        club = ClubFactory()
        team = TeamFactory(club=club)
        application = CompetitionApplicationFactory(competition=competition, team=team)
        team_at_tournament = TeamAtTournamentFactory(tournament=tournament, application=application)
        member = MemberFactory(club=club)
        MemberAtTournamentFactory(
            tournament=tournament,
            team_at_tournament=team_at_tournament,
            member=member,
        )

        out = StringIO()
        call_command(
            "competition_only_fees",
            competition_id=competition.id,
            stdout=out,
        )
        output = out.getvalue()

        assert "Fee per member: 200" in output
        assert "Total fees: 200" in output
        assert "Discounted" in output

    def test_correct_fee_calculation_free(self, season_factory):
        """Should return 0 for FREE fee type."""
        season = season_factory(name="2025")
        competition = CompetitionFactory(
            season=season,
            fee_type=CompetitionFeeTypeEnum.FREE,
        )
        tournament = TournamentFactory(competition=competition)
        club = ClubFactory()
        team = TeamFactory(club=club)
        application = CompetitionApplicationFactory(competition=competition, team=team)
        team_at_tournament = TeamAtTournamentFactory(tournament=tournament, application=application)
        member = MemberFactory(club=club)
        MemberAtTournamentFactory(
            tournament=tournament,
            team_at_tournament=team_at_tournament,
            member=member,
        )

        out = StringIO()
        call_command(
            "competition_only_fees",
            competition_id=competition.id,
            stdout=out,
        )
        output = out.getvalue()

        assert "Fee per member: 0" in output
        assert "Total fees: 0" in output

    def test_empty_result_when_no_qualifying_members(self, season_factory):
        """Should show appropriate message when no members qualify."""
        season = season_factory(name="2025")
        competition = CompetitionFactory(season=season)

        out = StringIO()
        call_command(
            "competition_only_fees",
            competition_id=competition.id,
            stdout=out,
        )
        output = out.getvalue()

        assert "No members found" in output

    def test_invalid_competition_id_raises_error(self):
        """Should raise CommandError for non-existent competition."""
        with pytest.raises(CommandError, match="Competition with ID 99999 does not exist"):
            call_command(
                "competition_only_fees",
                competition_id=99999,
            )

    def test_multiple_members_only_in_target_competition(self, season_factory):
        """Should correctly count and sum fees for multiple qualifying members."""
        season = season_factory(name="2025", regular_fee=Decimal("600"))
        competition = CompetitionFactory(
            season=season,
            fee_type=CompetitionFeeTypeEnum.REGULAR,
        )
        tournament = TournamentFactory(competition=competition)
        club = ClubFactory()
        team = TeamFactory(club=club)
        application = CompetitionApplicationFactory(competition=competition, team=team)
        team_at_tournament = TeamAtTournamentFactory(tournament=tournament, application=application)

        for i in range(3):
            member = MemberFactory(club=club, first_name=f"Player{i}", last_name="Test")
            MemberAtTournamentFactory(
                tournament=tournament,
                team_at_tournament=team_at_tournament,
                member=member,
            )

        out = StringIO()
        call_command(
            "competition_only_fees",
            competition_id=competition.id,
            stdout=out,
        )
        output = out.getvalue()

        assert "Total members: 3" in output
        assert "Total fees: 1800" in output
