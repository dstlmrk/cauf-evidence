from pytest_factoryboy import register

from tests.factories import AgentFactory, ClubFactory, OrganizationFactory, UserFactory

register(AgentFactory)
register(ClubFactory)
register(OrganizationFactory)
register(UserFactory)
