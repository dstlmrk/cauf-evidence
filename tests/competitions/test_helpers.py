from competitions.enums import CompetitionFeeTypeEnum
from competitions.helpers import get_clubs_without_subject_id_with_fees
from tests.factories import (
    ClubFactory,
    CompetitionFactory,
    InternationalTournamentFactory,
    MemberAtInternationalTournamentFactory,
    MemberAtTournamentFactory,
    MemberFactory,
    SeasonFactory,
    TournamentFactory,
)


class TestGetClubsWithoutSubjectIdWithFees:
    def test_club_without_subject_id_with_regular_tournament_is_included(self):
        season = SeasonFactory()
        club = ClubFactory(fakturoid_subject_id=None)
        member = MemberFactory(club=club)

        competition = CompetitionFactory(season=season, fee_type=CompetitionFeeTypeEnum.REGULAR)
        tournament = TournamentFactory(competition=competition)
        MemberAtTournamentFactory(member=member, tournament=tournament)

        result = get_clubs_without_subject_id_with_fees(season)

        assert club in result

    def test_club_without_subject_id_with_discounted_tournament_is_included(self):
        season = SeasonFactory()
        club = ClubFactory(fakturoid_subject_id=None)
        member = MemberFactory(club=club)

        competition = CompetitionFactory(season=season, fee_type=CompetitionFeeTypeEnum.DISCOUNTED)
        tournament = TournamentFactory(competition=competition)
        MemberAtTournamentFactory(member=member, tournament=tournament)

        result = get_clubs_without_subject_id_with_fees(season)

        assert club in result

    def test_club_without_subject_id_with_free_tournament_is_excluded(self):
        season = SeasonFactory()
        club = ClubFactory(fakturoid_subject_id=None)
        member = MemberFactory(club=club)

        competition = CompetitionFactory(season=season, fee_type=CompetitionFeeTypeEnum.FREE)
        tournament = TournamentFactory(competition=competition)
        MemberAtTournamentFactory(member=member, tournament=tournament)

        result = get_clubs_without_subject_id_with_fees(season)

        assert club not in result

    def test_club_with_subject_id_with_regular_tournament_is_excluded(self):
        season = SeasonFactory()
        club = ClubFactory(fakturoid_subject_id=12345)  # Has subject_id
        member = MemberFactory(club=club)

        competition = CompetitionFactory(season=season, fee_type=CompetitionFeeTypeEnum.REGULAR)
        tournament = TournamentFactory(competition=competition)
        MemberAtTournamentFactory(member=member, tournament=tournament)

        result = get_clubs_without_subject_id_with_fees(season)

        assert club not in result

    def test_club_without_subject_id_without_members_is_excluded(self):
        season = SeasonFactory()
        club = ClubFactory(fakturoid_subject_id=None)

        # Create a tournament but don't add any members from this club
        competition = CompetitionFactory(season=season, fee_type=CompetitionFeeTypeEnum.REGULAR)
        TournamentFactory(competition=competition)

        result = get_clubs_without_subject_id_with_fees(season)

        assert club not in result

    def test_club_without_subject_id_with_international_regular_tournament_is_included(self):
        season = SeasonFactory()
        club = ClubFactory(fakturoid_subject_id=None)
        member = MemberFactory(club=club)

        int_tournament = InternationalTournamentFactory(
            season=season, fee_type=CompetitionFeeTypeEnum.REGULAR
        )
        MemberAtInternationalTournamentFactory(member=member, tournament=int_tournament)

        result = get_clubs_without_subject_id_with_fees(season)

        assert club in result

    def test_club_without_subject_id_with_international_free_tournament_is_excluded(self):
        season = SeasonFactory()
        club = ClubFactory(fakturoid_subject_id=None)
        member = MemberFactory(club=club)

        int_tournament = InternationalTournamentFactory(
            season=season, fee_type=CompetitionFeeTypeEnum.FREE
        )
        MemberAtInternationalTournamentFactory(member=member, tournament=int_tournament)

        result = get_clubs_without_subject_id_with_fees(season)

        assert club not in result

    def test_club_with_both_free_and_paid_tournaments_is_included(self):
        season = SeasonFactory()
        club = ClubFactory(fakturoid_subject_id=None)
        member1 = MemberFactory(club=club)
        member2 = MemberFactory(club=club)

        # Member at FREE tournament
        free_competition = CompetitionFactory(season=season, fee_type=CompetitionFeeTypeEnum.FREE)
        free_tournament = TournamentFactory(competition=free_competition)
        MemberAtTournamentFactory(member=member1, tournament=free_tournament)

        # Member at REGULAR tournament
        paid_competition = CompetitionFactory(
            season=season, fee_type=CompetitionFeeTypeEnum.REGULAR
        )
        paid_tournament = TournamentFactory(competition=paid_competition)
        MemberAtTournamentFactory(member=member2, tournament=paid_tournament)

        result = get_clubs_without_subject_id_with_fees(season)

        assert club in result

    def test_only_clubs_from_specific_season_are_included(self):
        season_2025 = SeasonFactory(name="2025")
        season_2026 = SeasonFactory(name="2026")

        club_2025 = ClubFactory(fakturoid_subject_id=None)
        member_2025 = MemberFactory(club=club_2025)

        club_2026 = ClubFactory(fakturoid_subject_id=None)
        member_2026 = MemberFactory(club=club_2026)

        # Club with member in 2025 season
        competition_2025 = CompetitionFactory(
            season=season_2025, fee_type=CompetitionFeeTypeEnum.REGULAR
        )
        tournament_2025 = TournamentFactory(competition=competition_2025)
        MemberAtTournamentFactory(member=member_2025, tournament=tournament_2025)

        # Club with member in 2026 season
        competition_2026 = CompetitionFactory(
            season=season_2026, fee_type=CompetitionFeeTypeEnum.REGULAR
        )
        tournament_2026 = TournamentFactory(competition=competition_2026)
        MemberAtTournamentFactory(member=member_2026, tournament=tournament_2026)

        # Query for 2025 season only
        result = get_clubs_without_subject_id_with_fees(season_2025)

        assert club_2025 in result
        assert club_2026 not in result

    def test_empty_result_when_no_clubs_match_criteria(self):
        season = SeasonFactory()

        # Create clubs but none match criteria
        ClubFactory(fakturoid_subject_id=12345)  # Has subject_id
        ClubFactory(fakturoid_subject_id=None)  # No subject_id but no members

        result = get_clubs_without_subject_id_with_fees(season)

        assert result.count() == 0
