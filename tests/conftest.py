import pytest
from pytest_factoryboy import register

from tests.factories import AgentFactory, ClubFactory, OrganizationFactory, TeamFactory, UserFactory

register(AgentFactory)
register(ClubFactory)
register(OrganizationFactory)
register(UserFactory)
register(TeamFactory)


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    pass
