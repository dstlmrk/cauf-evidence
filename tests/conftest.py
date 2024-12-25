import pytest
from pytest_factoryboy import register

from tests.factories import AgentFactory, ClubFactory, TeamFactory, TournamentFactory, UserFactory

register(AgentFactory)
register(ClubFactory)
register(UserFactory)
register(TeamFactory)
register(TournamentFactory)


@pytest.fixture(scope="function", autouse=True)
def enable_db_access_for_all_tests(db):
    pass
