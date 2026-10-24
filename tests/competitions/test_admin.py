from datetime import datetime, timedelta

from django.contrib.admin.sites import AdminSite
from django.forms.models import model_to_dict
from django.test import Client, RequestFactory
from django.urls import reverse
from django.utils import timezone
from international_tournaments.admin import InternationalTournamentAdmin
from tournaments.admin import TournamentAdmin

from competitions.admin import CompetitionAdmin, CompetitionApplicationAdmin
from competitions.models import CompetitionApplication
from tests.factories import (
    CompetitionApplicationFactory,
    CompetitionFactory,
    InternationalTournamentFactory,
    MemberAtInternationalTournamentFactory,
    MemberAtTournamentFactory,
    SeasonFactory,
    TeamAtInternationalTournamentFactory,
    TournamentFactory,
    UserFactory,
)


class TestCompetitionApplicationAdmin:
    def test_changelist_renders_season_column(self):
        application = CompetitionApplicationFactory()
        user = UserFactory(is_staff=True, is_superuser=True)
        client = Client()
        client.force_login(user)

        response = client.get(reverse("admin:competitions_competitionapplication_changelist"))

        assert response.status_code == 200
        assert str(application.competition.season) in response.content.decode()

    def test_season_display(self):
        application = CompetitionApplicationFactory()
        model_admin = CompetitionApplicationAdmin(CompetitionApplication, AdminSite())

        assert model_admin.season(application) == str(application.competition.season)

    def test_queryset_uses_select_related(self):
        model_admin = CompetitionApplicationAdmin(CompetitionApplication, AdminSite())
        request = RequestFactory().get("/admin/")
        request.user = UserFactory(is_staff=True, is_superuser=True)

        queryset = model_admin.get_queryset(request)

        assert queryset.query.select_related == {
            "competition": {"season": {}},
            "team": {"club": {}},
            "registered_by": {},
        }


class TestSeasonChangeConfirmation:
    def _admin_form(self, admin_class, obj, **changes):
        request = RequestFactory().get("/admin/")
        request.user = UserFactory(is_staff=True, is_superuser=True)
        form_class = admin_class(type(obj), AdminSite()).get_form(request, obj)
        data = {**model_to_dict(obj), **changes}
        # Admin renders datetimes as split date and time inputs
        for name, value in list(data.items()):
            if isinstance(value, datetime):
                local = timezone.localtime(value)
                data[f"{name}_0"], data[f"{name}_1"] = local.date(), local.time()
        return form_class(data=data, instance=obj)

    def _competition_with_rosters(self, season):
        competition = CompetitionFactory(season=season)
        MemberAtTournamentFactory(tournament=TournamentFactory(competition=competition))
        return competition

    def _tournament_with_rosters(self, season):
        # The default roster deadline is tomorrow, so the tournament must start later
        tournament = TournamentFactory(
            competition=CompetitionFactory(season=season),
            start_date=timezone.localdate() + timedelta(days=7),
        )
        MemberAtTournamentFactory(tournament=tournament)
        return tournament

    def test_moving_rosters_out_of_invoiced_season_requires_confirmation(self):
        competition = self._competition_with_rosters(
            SeasonFactory(name="2024", invoices_generated_at=timezone.now())
        )

        form = self._admin_form(CompetitionAdmin, competition, season=SeasonFactory(name="2026").pk)

        assert not form.is_valid()
        assert "season 2024 have already been generated" in str(
            form.errors["confirm_season_change"]
        )

    def test_moving_rosters_into_invoiced_season_requires_confirmation(self):
        invoiced = SeasonFactory(name="2024", invoices_generated_at=timezone.now())
        competition = self._competition_with_rosters(SeasonFactory(name="2026"))

        form = self._admin_form(CompetitionAdmin, competition, season=invoiced.pk)

        assert not form.is_valid()
        assert "confirm_season_change" in form.errors

    def test_confirmed_move_is_valid(self):
        competition = self._competition_with_rosters(
            SeasonFactory(name="2024", invoices_generated_at=timezone.now())
        )

        form = self._admin_form(
            CompetitionAdmin,
            competition,
            season=SeasonFactory(name="2026").pk,
            confirm_season_change=True,
        )

        assert form.is_valid(), form.errors

    def test_move_without_rosters_needs_no_confirmation(self):
        competition = CompetitionFactory(
            season=SeasonFactory(name="2024", invoices_generated_at=timezone.now())
        )

        form = self._admin_form(CompetitionAdmin, competition, season=SeasonFactory(name="2026").pk)

        assert form.is_valid(), form.errors

    def test_move_between_not_invoiced_seasons_needs_no_confirmation(self):
        competition = self._competition_with_rosters(SeasonFactory(name="2024"))

        form = self._admin_form(CompetitionAdmin, competition, season=SeasonFactory(name="2026").pk)

        assert form.is_valid(), form.errors

    def test_moving_tournament_to_competition_in_invoiced_season_requires_confirmation(self):
        tournament = self._tournament_with_rosters(SeasonFactory(name="2026"))
        target = CompetitionFactory(
            season=SeasonFactory(name="2024", invoices_generated_at=timezone.now())
        )

        form = self._admin_form(TournamentAdmin, tournament, competition=target.pk)

        assert not form.is_valid()
        assert "confirm_season_change" in form.errors

    def test_moving_tournament_within_season_needs_no_confirmation(self):
        season = SeasonFactory(name="2024", invoices_generated_at=timezone.now())
        tournament = self._tournament_with_rosters(season)

        form = self._admin_form(
            TournamentAdmin, tournament, competition=CompetitionFactory(season=season).pk
        )

        assert form.is_valid(), form.errors

    def test_moving_international_tournament_out_of_invoiced_season_requires_confirmation(
        self,
    ):
        tournament = InternationalTournamentFactory(
            season=SeasonFactory(name="2024", invoices_generated_at=timezone.now())
        )
        MemberAtInternationalTournamentFactory(
            team_at_tournament=TeamAtInternationalTournamentFactory(tournament=tournament)
        )

        form = self._admin_form(
            InternationalTournamentAdmin, tournament, season=SeasonFactory(name="2026").pk
        )

        assert not form.is_valid()
        assert "confirm_season_change" in form.errors
