from contextlib import contextmanager

import pytest
from django.test import Client
from pytest_factoryboy import register

from tests.factories import (
    AgeLimitFactory,
    AgentFactory,
    ClubFactory,
    CompetitionApplicationFactory,
    CompetitionFactory,
    DivisionFactory,
    InternationalTournamentFactory,
    InvoiceFactory,
    MemberAtInternationalTournamentFactory,
    MemberAtTournamentFactory,
    MemberFactory,
    SeasonFactory,
    TeamAtInternationalTournamentFactory,
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
register(InternationalTournamentFactory)
register(InvoiceFactory)
register(MemberAtInternationalTournamentFactory)
register(MemberAtTournamentFactory)
register(MemberFactory)
register(SeasonFactory)
register(TeamAtInternationalTournamentFactory)
register(TeamAtTournamentFactory)
register(TeamFactory)
register(TournamentFactory)
register(UserFactory)


@pytest.fixture(scope="function", autouse=True)
def enable_db_access_for_all_tests(db):
    pass


@pytest.fixture
def logged_in_client():
    def _make(user, club):
        from users.models import Agent

        if not Agent.objects.filter(user=user).exists():
            AgentFactory(user=user)
        client = Client()
        client.force_login(user)
        session = client.session
        session["club"] = {"id": club.id, "name": club.name}
        session.save()
        return client

    return _make


@contextmanager
def override_app_settings(**kwargs):
    """Context manager to temporarily override AppSettings values in tests.

    Usage:
        with override_app_settings(min_age_verification_required=False):
            # test code...
    """
    from core.models import AppSettings

    settings = AppSettings.get_solo()
    original = {key: getattr(settings, key) for key in kwargs}

    for key, value in kwargs.items():
        setattr(settings, key, value)
    settings.save()

    try:
        yield settings
    finally:
        for key, value in original.items():
            setattr(settings, key, value)
        settings.save()


def with_app_settings(**settings_kwargs):
    """Decorator to override AppSettings values for a test function.

    Usage:
        @with_app_settings(min_age_verification_required=False)
        def test_something(self, ...):
            # test code...
    """
    from functools import wraps

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with override_app_settings(**settings_kwargs):
                return func(*args, **kwargs)

        return wrapper

    return decorator
