from typing import Any

from competitions.models import CompetitionFeeTypeEnum

from tests.factories import (
    CompetitionApplicationFactory,
    CompetitionFactory,
    DivisionFactory,
    SeasonFactory,
    TeamAtTournamentFactory,
    TournamentFactory,
)


def create_complete_competition(**kwargs: Any) -> dict:
    season = kwargs.get("season") or SeasonFactory()
    division = kwargs.get("division") or DivisionFactory()
    fee_type = kwargs.get("fee_type", CompetitionFeeTypeEnum.REGULAR)

    competition = CompetitionFactory(
        season=season,
        division=division,
        fee_type=fee_type,
    )
    tournament = TournamentFactory(
        competition=competition,
    )
    application = CompetitionApplicationFactory(
        competition=competition,
    )
    team_at_tournament = TeamAtTournamentFactory(
        tournament=tournament,
        application=application,
    )
    return {
        "competition": competition,
        "tournament": tournament,
        "application": application,
        "team_at_tournament": team_at_tournament,
    }
