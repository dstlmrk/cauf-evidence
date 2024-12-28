from decimal import Decimal

import pytest
from competitions.models import CompetitionApplication, CompetitionTypeEnum
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from tournaments.models import TeamAtTournament

from tests.factories import (
    CompetitionApplicationFactory,
    CompetitionFactory,
    DivisionFactory,
    MemberAtTournamentFactory,
    TournamentFactory,
)
from tests.helpers import create_complete_competition


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def api_token(user):
    return Token.objects.create(user=user)


def test_get_competitions(api_client):
    competition = CompetitionFactory(
        name="HMČR",
        type=CompetitionTypeEnum.OUTDOOR,
        division=DivisionFactory(name="Open"),
    )
    tournament = TournamentFactory(
        competition=competition,
        name="Kvalifikace Západ",
    )
    application = CompetitionApplicationFactory(
        competition=competition,
        team_name="Veselá rota B",
    )

    response = api_client.get(reverse("api:competitions"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [
        {
            "id": competition.id,
            "name": "HMČR",
            "type": "Outdoor",
            "division": "Open",
            "age_limit": None,
            "season": "2025",
            "tournaments": [
                {
                    "id": tournament.id,
                    "name": "Kvalifikace Západ",
                    "start_date": tournament.start_date.strftime("%Y-%m-%d"),
                    "end_date": tournament.end_date.strftime("%Y-%m-%d"),
                    "location": tournament.location,
                },
            ],
            "accepted_applications": [
                {
                    "id": application.id,
                    "team_name": "Veselá rota B",
                    "final_placement": None,
                },
            ],
        }
    ]


@pytest.mark.parametrize("club__identification_number", ["08057508"])
def test_get_clubs(api_client, club):
    response = api_client.get(reverse("api:clubs"))
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [
        {
            "id": club.id,
            "name": club.name,
            "short_name": club.short_name,
            "email": club.email,
            "website": club.website,
            "city": club.city,
            "organization_name": club.organization_name,
            "identification_number": "08057508",
        },
    ]


def test_get_teams_at_tournament(api_client):
    # Missing tournament_id parameter
    response = api_client.get(reverse("api:teams-at-tournament"))
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    complete_competition = create_complete_competition()
    tournament = complete_competition["tournament"]
    application = complete_competition["application"]
    team_at_tournament = complete_competition["team_at_tournament"]

    member_at_tournament = MemberAtTournamentFactory(
        tournament=tournament,
        team_at_tournament=team_at_tournament,
    )

    response = api_client.get(reverse("api:teams-at-tournament"), {"tournament_id": tournament.id})
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [
        {
            "id": member_at_tournament.team_at_tournament.id,
            "team_name": application.team_name,
            "final_placement": None,
            "spirit_avg": None,
            "members": [
                {
                    "is_captain": False,
                    "is_spirit_captain": False,
                    "is_coach": False,
                    "jersey_number": 10,
                    "member": {
                        "id": member_at_tournament.member.id,
                        "full_name": member_at_tournament.member.full_name,
                        "birth_year": member_at_tournament.member.birth_date.year,
                    },
                },
            ],
        },
    ]


def test_get_team_at_tournament(api_client, team_at_tournament):
    response = api_client.get(reverse("api:team-at-tournament", args=[team_at_tournament.pk]))
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "id": team_at_tournament.id,
        "team_name": team_at_tournament.application.team_name,
        "final_placement": None,
        "spirit_avg": None,
        "members": [],
    }


def test_patch_team_at_tournament(api_token, api_client, team_at_tournament):
    # Without token in header
    response = api_client.patch(reverse("api:team-at-tournament", args=[team_at_tournament.pk]))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    response = api_client.patch(
        reverse("api:team-at-tournament", args=[team_at_tournament.pk]),
        data={"final_placement": 99, "spirit_avg": "10.123"},
        HTTP_AUTHORIZATION=f"Token {api_token.key}",
    )
    assert response.status_code == status.HTTP_200_OK

    team_at_tournament = TeamAtTournament.objects.get(pk=team_at_tournament.pk)
    assert team_at_tournament.final_placement == 99
    assert team_at_tournament.spirit_avg == Decimal("10.123")


def test_get_competition_application(api_client, competition_application):
    response = api_client.get(
        reverse("api:competition-application", args=[competition_application.pk])
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "id": competition_application.id,
        "team_name": competition_application.team_name,
        "final_placement": None,
    }


def test_patch_competition_application(api_token, api_client, competition_application):
    # Without token in header
    response = api_client.patch(
        reverse("api:competition-application", args=[competition_application.pk])
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    response = api_client.patch(
        reverse("api:competition-application", args=[competition_application.pk]),
        data={"final_placement": 98},
        HTTP_AUTHORIZATION=f"Token {api_token.key}",
    )
    assert response.status_code == status.HTTP_200_OK

    competition_application = CompetitionApplication.objects.get(pk=competition_application.pk)
    assert competition_application.final_placement == 98
