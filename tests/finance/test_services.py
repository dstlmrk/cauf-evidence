from competitions.models import CompetitionFeeTypeEnum, Season
from finance.services import SeasonFeeData, calculate_season_fees

from tests.factories import MemberAtTournamentFactory, SeasonFactory
from tests.helpers import create_complete_competition


def test_calculate_season_fees():
    season = SeasonFactory()

    free_complete_competition = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.FREE,
    )
    discounted_complete_competition = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.DISCOUNTED,
    )
    regular_complete_competition = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.REGULAR,
    )

    member_1 = MemberAtTournamentFactory(
        tournament=regular_complete_competition["tournament"],
        team_at_tournament=regular_complete_competition["team_at_tournament"],
    ).member
    member_2 = MemberAtTournamentFactory(
        tournament=discounted_complete_competition["tournament"],
        team_at_tournament=discounted_complete_competition["team_at_tournament"],
    ).member
    member_3 = MemberAtTournamentFactory(
        tournament=free_complete_competition["tournament"],
        team_at_tournament=free_complete_competition["team_at_tournament"],
    ).member

    results = calculate_season_fees(Season.objects.last())
    assert len(results) == 2
    assert results == {
        member_1: SeasonFeeData(
            season.regular_fee,
            [regular_complete_competition["tournament"]],
            [],
        ),
        member_2: SeasonFeeData(
            season.discounted_fee,
            [],
            [discounted_complete_competition["tournament"]],
        ),
    }

    MemberAtTournamentFactory(
        tournament=regular_complete_competition["tournament"],
        team_at_tournament=regular_complete_competition["team_at_tournament"],
        member=member_2,
    )
    MemberAtTournamentFactory(
        tournament=discounted_complete_competition["tournament"],
        team_at_tournament=discounted_complete_competition["team_at_tournament"],
        member=member_3,
    )

    results = calculate_season_fees(Season.objects.last())
    assert len(results) == 3
    assert results == {
        member_1: SeasonFeeData(
            season.regular_fee,
            [regular_complete_competition["tournament"]],
            [],
        ),
        member_2: SeasonFeeData(
            season.regular_fee,
            [regular_complete_competition["tournament"]],
            [discounted_complete_competition["tournament"]],
        ),
        member_3: SeasonFeeData(
            season.discounted_fee,
            [],
            [discounted_complete_competition["tournament"]],
        ),
    }

    # Test filter
    results = calculate_season_fees(Season.objects.last(), club_id=member_1.club.id)
    assert len(results) == 1
    assert results == {
        member_1: SeasonFeeData(
            season.regular_fee,
            [regular_complete_competition["tournament"]],
            [],
        )
    }
