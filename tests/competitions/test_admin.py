from django.contrib.admin.sites import AdminSite
from django.test import Client, RequestFactory
from django.urls import reverse

from competitions.admin import CompetitionApplicationAdmin
from competitions.models import CompetitionApplication
from tests.factories import CompetitionApplicationFactory, UserFactory


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
