from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from competitions.enums import ApplicationStateEnum
from competitions.models import CompetitionApplication
from tests.factories import (
    ClubFactory,
    CompetitionApplicationFactory,
    CompetitionFactory,
    InvoiceFactory,
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
