import pytest
from pytest_factoryboy import register

from tests.factories import (
    AgeLimitFactory,
    AgentFactory,
    ClubFactory,
    CompetitionApplicationFactory,
    CompetitionFactory,
    DivisionFactory,
    InvoiceFactory,
    MemberFactory,
    SeasonFactory,
    TeamAtTournamentFactory,
    TeamFactory,
    TournamentFactory,
    UserFactory,
)

register(AgeLimitFactory)
register(AgentFactory)
register(ClubFactory)
register(CompetitionApplicationFactory)
register(CompetitionFactory)
register(DivisionFactory)
register(InvoiceFactory)
register(MemberFactory)
register(SeasonFactory)
register(TeamAtTournamentFactory)
register(TeamFactory)
register(TournamentFactory)
register(UserFactory)


@pytest.fixture(scope="function", autouse=True)
def enable_db_access_for_all_tests(db):
    pass
