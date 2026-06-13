from datetime import timedelta
from unittest.mock import patch

from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone

from competitions.enums import ApplicationStateEnum
from competitions.models import CompetitionApplication
from tests.factories import (
    ClubFactory,
    CompetitionApplicationFactory,
    CompetitionFactory,
    InvoiceFactory,
    TeamAtTournamentFactory,
    TeamFactory,
    TournamentFactory,
    UserFactory,
)


class TestRegistrationView:
    def test_creates_application_awaiting_payment(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        team = TeamFactory(club=club, is_primary=True)
        competition = CompetitionFactory(
            deposit=1000,
            registration_deadline=timezone.now() + timedelta(days=5),
        )
        TournamentFactory(competition=competition)
        client = logged_in_client(user, club)

        response = client.post(
            reverse("competitions:registration", args=[competition.id]),
            data={f"team_{team.id}": True},
        )

        assert response.status_code == 204
        app = CompetitionApplication.objects.get(team=team, competition=competition)
        assert app.state == ApplicationStateEnum.AWAITING_PAYMENT

    def test_creates_application_paid_when_no_deposit(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        team = TeamFactory(club=club, is_primary=True)
        competition = CompetitionFactory(
            deposit=0,
            registration_deadline=timezone.now() + timedelta(days=5),
        )
        TournamentFactory(competition=competition)
        client = logged_in_client(user, club)

        response = client.post(
            reverse("competitions:registration", args=[competition.id]),
            data={f"team_{team.id}": True},
        )

        assert response.status_code == 204
        app = CompetitionApplication.objects.get(team=team, competition=competition)
        assert app.state == ApplicationStateEnum.PAID

    def test_does_not_register_other_clubs_team(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        other_club = ClubFactory()
        team = TeamFactory(club=other_club)
        competition = CompetitionFactory(
            registration_deadline=timezone.now() + timedelta(days=5),
        )
        client = logged_in_client(user, club)

        response = client.post(
            reverse("competitions:registration", args=[competition.id]),
            data={f"team_{team.id}": True},
        )

        # Form only contains teams from current club, so other club's team field is ignored
        assert response.status_code == 204
        assert not CompetitionApplication.objects.filter(team=team).exists()

    def test_cannot_register_after_deadline(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        team = TeamFactory(club=club, is_primary=True)
        competition = CompetitionFactory(
            registration_deadline=timezone.now() - timedelta(days=1),
        )
        TournamentFactory(competition=competition)
        client = logged_in_client(user, club)

        response = client.post(
            reverse("competitions:registration", args=[competition.id]),
            data={f"team_{team.id}": True},
        )

        assert response.status_code == 403
        assert not CompetitionApplication.objects.filter(
            team=team, competition=competition
        ).exists()

    def test_duplicate_submit_returns_400_instead_of_500(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        team = TeamFactory(club=club, is_primary=True)
        competition = CompetitionFactory(
            registration_deadline=timezone.now() + timedelta(days=5),
        )
        TournamentFactory(competition=competition)
        client = logged_in_client(user, club)

        # Simulate the race where a concurrent submit already created the application:
        # the unique constraint rejects this insert and the view must surface a
        # friendly message with a 400, never a 500.
        with patch.object(CompetitionApplication.objects, "create", side_effect=IntegrityError):
            response = client.post(
                reverse("competitions:registration", args=[competition.id]),
                data={f"team_{team.id}": True},
            )

        assert response.status_code == 400


class TestCancelApplicationView:
    def test_cancels_own_application(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        team = TeamFactory(club=club)
        competition = CompetitionFactory(
            registration_deadline=timezone.now() + timedelta(days=5),
        )
        application = CompetitionApplicationFactory(
            competition=competition,
            team=team,
            state=ApplicationStateEnum.AWAITING_PAYMENT,
        )
        client = logged_in_client(user, club)

        response = client.post(reverse("competitions:cancel_application", args=[application.id]))

        assert response.status_code == 204
        assert not CompetitionApplication.objects.filter(pk=application.pk).exists()

    def test_cannot_cancel_closed_registration(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        team = TeamFactory(club=club)
        competition = CompetitionFactory(
            registration_deadline=timezone.now() - timedelta(days=1),
        )
        application = CompetitionApplicationFactory(
            competition=competition,
            team=team,
            state=ApplicationStateEnum.AWAITING_PAYMENT,
        )
        client = logged_in_client(user, club)

        response = client.post(reverse("competitions:cancel_application", args=[application.id]))

        assert response.status_code == 403

    def test_cannot_cancel_with_invoice(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        team = TeamFactory(club=club)
        competition = CompetitionFactory(
            registration_deadline=timezone.now() + timedelta(days=5),
        )
        invoice = InvoiceFactory(club=club)
        application = CompetitionApplicationFactory(
            competition=competition,
            team=team,
            state=ApplicationStateEnum.AWAITING_PAYMENT,
            invoice=invoice,
        )
        client = logged_in_client(user, club)

        response = client.post(reverse("competitions:cancel_application", args=[application.id]))

        assert response.status_code == 403

    def test_cannot_cancel_other_clubs_application(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        other_club = ClubFactory()
        team = TeamFactory(club=other_club)
        competition = CompetitionFactory(
            registration_deadline=timezone.now() + timedelta(days=5),
        )
        application = CompetitionApplicationFactory(
            competition=competition,
            team=team,
            state=ApplicationStateEnum.AWAITING_PAYMENT,
        )
        client = logged_in_client(user, club)

        response = client.post(reverse("competitions:cancel_application", args=[application.id]))

        assert response.status_code == 403

    def test_cannot_cancel_when_team_assigned_to_tournament(self, logged_in_client):
        user = UserFactory()
        club = ClubFactory()
        team = TeamFactory(club=club)
        competition = CompetitionFactory(
            registration_deadline=timezone.now() + timedelta(days=5),
        )
        application = CompetitionApplicationFactory(
            competition=competition,
            team=team,
            state=ApplicationStateEnum.PAID,
        )
        # Assigning the team to a tournament protects the application from deletion.
        TeamAtTournamentFactory(
            tournament=TournamentFactory(competition=competition),
            application=application,
        )
        client = logged_in_client(user, club)

        response = client.post(reverse("competitions:cancel_application", args=[application.id]))

        # The protected delete must surface a user-facing error, not an HTTP 500.
        assert response.status_code == 409
        assert CompetitionApplication.objects.filter(pk=application.pk).exists()
