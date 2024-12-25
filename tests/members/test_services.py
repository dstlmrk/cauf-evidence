from unittest.mock import patch

import pytest
from members.models import MemberSexEnum
from members.services import search

from tests.factories import (
    AgeLimitFactory,
    ClubFactory,
    CompetitionFactory,
    DivisionFactory,
    MemberFactory,
    TournamentFactory,
)


@pytest.fixture
def prepared_members():
    club = ClubFactory()
    return club, [
        # Regular man
        MemberFactory(club=club, sex=MemberSexEnum.MALE, birth_date="2006-01-01"),
        # Regular woman
        MemberFactory(club=club, sex=MemberSexEnum.FEMALE, birth_date="2005-12-31"),
        # Regular woman
        MemberFactory(club=club, sex=MemberSexEnum.FEMALE, birth_date="2003-12-31"),
        # Too young woman but junior
        MemberFactory(club=club, sex=MemberSexEnum.FEMALE, birth_date="2013-12-31"),
        # Regular man
        MemberFactory(club=club, sex=MemberSexEnum.MALE, birth_date="2010-06-06"),
        # Too young man and neither regular member nor junior
        MemberFactory(club=club, sex=MemberSexEnum.MALE, birth_date="2014-01-01"),
        # A regular woman from different club
        MemberFactory(club=ClubFactory(), sex=MemberSexEnum.FEMALE, birth_date="1990-01-01"),
        # Inactive member
        MemberFactory(
            club=club, sex=MemberSexEnum.FEMALE, birth_date="1990-01-01", is_active=False
        ),
    ]


def test_search_returns_women(prepared_members):
    club = prepared_members[0]
    members = prepared_members[1]

    tournament = TournamentFactory(
        competition=CompetitionFactory(
            division=DivisionFactory(
                name="Women",
                is_male_allowed=False,
                is_female_allowed=True,
            ),
        )
    )

    result = search("", club, tournament)

    assert len(result) == 2
    assert set(result) == {members[1], members[2]}


def test_search_prefers_men_in_open_division(prepared_members):
    club = prepared_members[0]
    members = prepared_members[1]

    tournament = TournamentFactory(
        competition=CompetitionFactory(
            division=DivisionFactory(
                name="Open",
                is_male_allowed=True,
                is_female_allowed=True,
            ),
        )
    )

    result = search("", club, tournament)
    assert len(result) == 4
    assert result == [members[0], members[4], members[1], members[2]]


def test_search_does_not_return_players_already_in_tournament(prepared_members):
    club = prepared_members[0]
    members = prepared_members[1]

    tournament = TournamentFactory(
        competition=CompetitionFactory(
            division=DivisionFactory(
                name="Women",
                is_male_allowed=False,
                is_female_allowed=True,
            ),
        )
    )

    with patch(
        "members.services._get_already_assigned_members_ids",
        return_value=[
            members[1].id,
        ],
    ):
        result = search("", club, tournament)

    assert len(result) == 1
    assert set(result) == {members[2]}


def test_search_should_return_properly_old_members(prepared_members):
    club = prepared_members[0]
    members = prepared_members[1]

    tournament = TournamentFactory(
        competition=CompetitionFactory(
            division=DivisionFactory(
                name="Mixed",
                is_male_allowed=True,
                is_female_allowed=True,
            ),
            age_limit=AgeLimitFactory(
                name="U20",
                m_min=12,
                m_max=19,
                f_min=12,
                f_max=19,
            ),
        )
    )

    result = search("", club, tournament)
    assert len(result) == 3
    assert set(result) == {members[0], members[3], members[4]}


def test_search_should_ignore_global_min_age_when_age_limit_exists(club):
    MemberFactory(club=club, sex=MemberSexEnum.MALE, birth_date="2000-01-01")
    master = MemberFactory(club=club, sex=MemberSexEnum.MALE, birth_date="1990-01-01")

    tournament = TournamentFactory(
        competition=CompetitionFactory(
            division=DivisionFactory(
                name="Open",
                is_male_allowed=True,
                is_female_allowed=True,
            ),
            age_limit=AgeLimitFactory(
                name="Masters",
                m_min=33,
                m_max=99,
                f_min=30,
                f_max=99,
            ),
        )
    )

    result = search("", club, tournament)
    assert len(result) == 1
    assert set(result) == {master}
