from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from tournaments.models import MemberAtTournament

from tests.factories import (
    ClubFactory,
    CompetitionApplicationFactory,
    CompetitionFactory,
    MemberAtTournamentFactory,
    MemberFactory,
    TeamAtTournamentFactory,
    TeamFactory,
    TournamentFactory,
    UserFactory,
)


def _create_tournament_setup(club, rosters_deadline=None):
    if rosters_deadline is None:
        rosters_deadline = timezone.now() + timedelta(days=2)
    team = TeamFactory(club=club)
    competition = CompetitionFactory()
    tournament = TournamentFactory(competition=competition, rosters_deadline=rosters_deadline)
    application = CompetitionApplicationFactory(competition=competition, team=team)
    team_at_tournament = TeamAtTournamentFactory(tournament=tournament, application=application)
    return team, tournament, application, team_at_tournament


class TestRemoveMemberFromRoster:
    def test_removes_member_when_roster_open(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        team, tournament, application, tat = _create_tournament_setup(club)
        member = MemberFactory(club=club)
        mat = MemberAtTournamentFactory(
            tournament=tournament, team_at_tournament=tat, member=member
        )
        client = logged_in_client(user, club)

        response = client.post(reverse("tournaments:remove_member_from_roster", args=[mat.id]))

        assert response.status_code == 200
        assert not MemberAtTournament.objects.filter(pk=mat.pk).exists()

    def test_returns_400_when_roster_closed(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        past_deadline = timezone.now() - timedelta(days=1)
        team, tournament, application, tat = _create_tournament_setup(
            club, rosters_deadline=past_deadline
        )
        member = MemberFactory(club=club)
        mat = MemberAtTournamentFactory(
            tournament=tournament, team_at_tournament=tat, member=member
        )
        client = logged_in_client(user, club)

        response = client.post(reverse("tournaments:remove_member_from_roster", args=[mat.id]))

        assert response.status_code == 400
        assert MemberAtTournament.objects.filter(pk=mat.pk).exists()

    def test_permission_denied_other_club(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        other_club = ClubFactory()
        team, tournament, application, tat = _create_tournament_setup(other_club)
        member = MemberFactory(club=other_club)
        mat = MemberAtTournamentFactory(
            tournament=tournament, team_at_tournament=tat, member=member
        )
        client = logged_in_client(user, club)

        response = client.post(reverse("tournaments:remove_member_from_roster", args=[mat.id]))

        assert response.status_code == 403


class TestRosterDialogAddFormView:
    def test_permission_denied_other_clubs_team(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        other_club = ClubFactory()
        _, _, _, tat = _create_tournament_setup(other_club)
        client = logged_in_client(user, club)

        response = client.get(reverse("tournaments:roster_dialog_add_form", args=[tat.id]))

        assert response.status_code == 403

    def test_get_renders_form_for_own_team(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        _, _, _, tat = _create_tournament_setup(club)
        client = logged_in_client(user, club)

        response = client.get(reverse("tournaments:roster_dialog_add_form", args=[tat.id]))

        assert response.status_code == 200


class TestRosterDialogUpdateFormView:
    def test_permission_denied_other_clubs_member(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        other_club = ClubFactory()
        _, tournament, _, tat = _create_tournament_setup(other_club)
        member = MemberFactory(club=other_club)
        mat = MemberAtTournamentFactory(
            tournament=tournament, team_at_tournament=tat, member=member
        )
        client = logged_in_client(user, club)

        response = client.get(reverse("tournaments:roster_dialog_update_form", args=[mat.id]))

        assert response.status_code == 403

    def test_returns_400_when_deadline_passed(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        past_deadline = timezone.now() - timedelta(days=1)
        _, tournament, _, tat = _create_tournament_setup(club, rosters_deadline=past_deadline)
        member = MemberFactory(club=club)
        mat = MemberAtTournamentFactory(
            tournament=tournament, team_at_tournament=tat, member=member
        )
        client = logged_in_client(user, club)

        response = client.post(
            reverse("tournaments:roster_dialog_update_form", args=[mat.id]),
            data={"jersey_number": 7, "is_captain": False, "is_spirit_captain": False},
        )

        assert response.status_code == 400

    def test_get_renders_form_for_own_club(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        _, tournament, _, tat = _create_tournament_setup(club)
        member = MemberFactory(club=club)
        mat = MemberAtTournamentFactory(
            tournament=tournament, team_at_tournament=tat, member=member
        )
        client = logged_in_client(user, club)

        response = client.get(reverse("tournaments:roster_dialog_update_form", args=[mat.id]))

        assert response.status_code == 200

    def test_post_updates_jersey_number(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        _, tournament, _, tat = _create_tournament_setup(club)
        member = MemberFactory(club=club)
        mat = MemberAtTournamentFactory(
            tournament=tournament, team_at_tournament=tat, member=member, jersey_number=10
        )
        client = logged_in_client(user, club)

        response = client.post(
            reverse("tournaments:roster_dialog_update_form", args=[mat.id]),
            data={"jersey_number": 42, "is_captain": False, "is_spirit_captain": False},
        )

        assert response.status_code == 204
        mat.refresh_from_db()
        assert mat.jersey_number == 42
