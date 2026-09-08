from datetime import date

from competitions.models import CompetitionFeeTypeEnum
from django.urls import reverse

from tests.factories import (
    ClubFactory,
    InternationalTournamentFactory,
    MemberAtInternationalTournamentFactory,
    MemberAtTournamentFactory,
    MemberFactory,
    SeasonFactory,
    TeamAtInternationalTournamentFactory,
    UserFactory,
)
from tests.helpers import create_complete_competition


def _add_domestic_tournament(season, member, start, end, fee_type=CompetitionFeeTypeEnum.REGULAR):
    competition = create_complete_competition(season=season, fee_type=fee_type)
    tournament = competition["tournament"]
    tournament.start_date = start
    tournament.end_date = end
    tournament.save()
    MemberAtTournamentFactory(
        tournament=tournament,
        team_at_tournament=competition["team_at_tournament"],
        member=member,
    )
    return tournament


def _add_international_tournament(
    season, member, date_from, date_to, fee_type=CompetitionFeeTypeEnum.REGULAR
):
    tournament = InternationalTournamentFactory(
        season=season,
        date_from=date_from,
        date_to=date_to,
        fee_type=fee_type,
    )
    MemberAtInternationalTournamentFactory(
        tournament=tournament,
        team_at_tournament=TeamAtInternationalTournamentFactory(tournament=tournament),
        member=member,
    )
    return tournament


class TestSeasonFeesListView:
    def test_shows_days_from_domestic_and_international_tournaments(self, logged_in_client):
        season = SeasonFactory()
        club = ClubFactory()
        member = MemberFactory(club=club)
        _add_domestic_tournament(season, member, date(2025, 1, 1), date(2025, 1, 3))  # 3 days
        _add_international_tournament(season, member, date(2025, 2, 10), date(2025, 2, 11))  # 2

        client = logged_in_client(UserFactory(), club)
        response = client.post(reverse("finance:season_fees_list"), {"season": season.id})

        assert response.status_code == 200
        assert [(m.id, days) for m, _fee, days in response.context["fees"]] == [(member.id, 5)]

    def test_free_tournaments_are_counted_in_their_own_column_and_in_days(self, logged_in_client):
        """Days must match the NSA export, which counts every tournament the member played."""
        season = SeasonFactory()
        club = ClubFactory()
        member = MemberFactory(club=club)
        _add_domestic_tournament(season, member, date(2025, 1, 1), date(2025, 1, 2))  # 2 days
        _add_domestic_tournament(
            season,
            member,
            date(2025, 3, 1),
            date(2025, 3, 4),  # 4 days
            fee_type=CompetitionFeeTypeEnum.FREE,
        )

        client = logged_in_client(UserFactory(), club)
        response = client.post(reverse("finance:season_fees_list"), {"season": season.id})

        member_, fee, days = response.context["fees"][0]
        assert member_.id == member.id
        assert len(fee.regular_tournaments) == 1
        assert len(fee.free_tournaments) == 1
        assert days == 6

    def test_omits_members_who_only_played_free_tournaments(self, logged_in_client):
        season = SeasonFactory()
        club = ClubFactory()
        member = MemberFactory(club=club)
        _add_domestic_tournament(
            season,
            member,
            date(2025, 1, 1),
            date(2025, 1, 2),
            fee_type=CompetitionFeeTypeEnum.FREE,
        )

        client = logged_in_client(UserFactory(), club)
        response = client.post(reverse("finance:season_fees_list"), {"season": season.id})

        assert response.context["fees"] == []


class TestSeasonFeesMemberDetailView:
    def test_shows_days_per_tournament_and_total(self, logged_in_client):
        season = SeasonFactory()
        club = ClubFactory()
        member = MemberFactory(club=club)
        _add_domestic_tournament(season, member, date(2025, 1, 1), date(2025, 1, 3))  # 3 days
        _add_international_tournament(season, member, date(2025, 2, 10), date(2025, 2, 11))  # 2

        client = logged_in_client(UserFactory(), club)
        response = client.post(
            reverse("finance:season_fees_member_detail"),
            {"member_id": member.id, "season_id": season.id},
        )

        assert response.status_code == 200
        assert sorted(item["days"] for item in response.context["tournaments"]) == [2, 3]
        assert response.context["total_days"] == 5

    def test_single_day_tournament_counts_as_one_day(self, logged_in_client):
        season = SeasonFactory()
        club = ClubFactory()
        member = MemberFactory(club=club)
        _add_domestic_tournament(season, member, date(2025, 1, 1), date(2025, 1, 1))

        client = logged_in_client(UserFactory(), club)
        response = client.post(
            reverse("finance:season_fees_member_detail"),
            {"member_id": member.id, "season_id": season.id},
        )

        assert response.context["total_days"] == 1
