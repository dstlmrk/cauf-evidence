import pytest
from pytest_factoryboy import register

from tests.factories import AgentFactory, ClubFactory, TeamFactory, UserFactory

register(AgentFactory)
register(ClubFactory)
register(UserFactory)
register(TeamFactory)


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    pass
