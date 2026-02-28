import pytest
from django.test import Client
from django.urls import reverse


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def staff_user(user_factory):
    return user_factory(is_staff=True)


@pytest.fixture
def superuser(user_factory):
    return user_factory(is_superuser=True)


@pytest.fixture
def regular_user(user_factory):
    return user_factory(is_staff=False, is_superuser=False)


class TestExportRostersModal:
    def test_staff_user_can_access(self, client, staff_user):
        client.force_login(staff_user)
        response = client.get(reverse("international_tournaments:export_rosters_modal"))
        assert response.status_code == 200

    def test_regular_user_gets_403(self, client, regular_user):
        client.force_login(regular_user)
        response = client.get(reverse("international_tournaments:export_rosters_modal"))
        assert response.status_code == 403


class TestExportRostersCsv:
    def test_staff_user_can_export(self, client, staff_user, season_factory):
        season = season_factory()
        client.force_login(staff_user)
        response = client.get(
            reverse("international_tournaments:export_rosters_csv"),
            {"season_id": season.id},
        )
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv; charset=utf-8"

    def test_superuser_can_export(self, client, superuser, season_factory):
        season = season_factory()
        client.force_login(superuser)
        response = client.get(
            reverse("international_tournaments:export_rosters_csv"),
            {"season_id": season.id},
        )
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv; charset=utf-8"

    def test_regular_user_gets_403(self, client, regular_user, season_factory):
        season = season_factory()
        client.force_login(regular_user)
        response = client.get(
            reverse("international_tournaments:export_rosters_csv"),
            {"season_id": season.id},
        )
        assert response.status_code == 403

    def test_missing_season_id_returns_400(self, client, staff_user):
        client.force_login(staff_user)
        response = client.get(reverse("international_tournaments:export_rosters_csv"))
        assert response.status_code == 400

    def test_nonexistent_season_returns_404(self, client, staff_user):
        client.force_login(staff_user)
        response = client.get(
            reverse("international_tournaments:export_rosters_csv"),
            {"season_id": 99999},
        )
        assert response.status_code == 404

    def test_csv_has_correct_headers(self, client, staff_user, season_factory):
        season = season_factory()
        client.force_login(staff_user)
        response = client.get(
            reverse("international_tournaments:export_rosters_csv"),
            {"season_id": season.id},
        )

        content = response.content.decode("utf-8-sig")
        lines = content.strip().split("\r\n")
        header = lines[0]

        expected_headers = (
            "season,tournament,type,location,date,team,division,age_restriction,"
            "first_name,last_name,birth_date,sex,citizenship,"
            "is_captain,is_spirit_captain,is_coach,jersey_number"
        )
        assert header == expected_headers

    def test_csv_contains_member_data(
        self,
        client,
        staff_user,
        member_at_international_tournament_factory,
        team_at_international_tournament_factory,
    ):
        team_at_tournament = team_at_international_tournament_factory()
        mat = member_at_international_tournament_factory(
            tournament=team_at_tournament.tournament,
            team_at_tournament=team_at_tournament,
            is_captain=True,
            jersey_number=7,
        )

        client.force_login(staff_user)
        response = client.get(
            reverse("international_tournaments:export_rosters_csv"),
            {"season_id": team_at_tournament.tournament.season.id},
        )

        content = response.content.decode("utf-8-sig")
        lines = content.strip().split("\r\n")

        assert len(lines) == 2  # header + 1 member

        data_line = lines[1]
        assert mat.member.first_name in data_line
        assert mat.member.last_name in data_line
        assert mat.member.birth_date.strftime("%Y-%m-%d") in data_line
        assert "True" in data_line  # is_captain
        assert "7" in data_line  # jersey_number

    def test_export_empty_season(self, client, staff_user, season_factory):
        season = season_factory()
        client.force_login(staff_user)
        response = client.get(
            reverse("international_tournaments:export_rosters_csv"),
            {"season_id": season.id},
        )

        assert response.status_code == 200
        content = response.content.decode("utf-8-sig")
        lines = content.strip().split("\r\n")
        assert len(lines) == 1  # only header

    def test_content_disposition_header(self, client, staff_user, season_factory):
        season = season_factory()
        client.force_login(staff_user)
        response = client.get(
            reverse("international_tournaments:export_rosters_csv"),
            {"season_id": season.id},
        )

        assert "Content-Disposition" in response
        assert (
            f'filename="international_rosters_{season.name}.csv"' in response["Content-Disposition"]
        )
