from tournaments.models import TeamAtTournament

from competitions.services import accept_team_to_competition, reject_team_from_competition
from tests.factories import (
    CompetitionApplicationFactory,
    CompetitionFactory,
    TeamAtTournamentFactory,
    TeamFactory,
    TournamentFactory,
)


class TestAcceptTeamToCompetition:
    def test_creates_team_at_tournament_for_all_tournaments(self):
        competition = CompetitionFactory()
        t1 = TournamentFactory(competition=competition)
        t2 = TournamentFactory(competition=competition)
        team = TeamFactory()
        application = CompetitionApplicationFactory(competition=competition, team=team)

        accept_team_to_competition(application)

        assert TeamAtTournament.objects.filter(application=application).count() == 2
        assert TeamAtTournament.objects.filter(tournament=t1, application=application).exists()
        assert TeamAtTournament.objects.filter(tournament=t2, application=application).exists()

    def test_no_instances_when_no_tournaments(self):
        competition = CompetitionFactory()
        team = TeamFactory()
        application = CompetitionApplicationFactory(competition=competition, team=team)

        accept_team_to_competition(application)

        assert TeamAtTournament.objects.filter(application=application).count() == 0

    def test_creates_for_single_tournament(self):
        competition = CompetitionFactory()
        tournament = TournamentFactory(competition=competition)
        team = TeamFactory()
        application = CompetitionApplicationFactory(competition=competition, team=team)

        accept_team_to_competition(application)

        tat = TeamAtTournament.objects.get(application=application)
        assert tat.tournament == tournament


class TestRejectTeamFromCompetition:
    def test_deletes_all_team_at_tournament_for_application(self):
        competition = CompetitionFactory()
        t1 = TournamentFactory(competition=competition)
        t2 = TournamentFactory(competition=competition)
        team = TeamFactory()
        application = CompetitionApplicationFactory(competition=competition, team=team)
        TeamAtTournamentFactory(tournament=t1, application=application)
        TeamAtTournamentFactory(tournament=t2, application=application)

        reject_team_from_competition(application)

        assert TeamAtTournament.objects.filter(application=application).count() == 0

    def test_does_not_delete_other_applications(self):
        competition = CompetitionFactory()
        tournament = TournamentFactory(competition=competition)
        team1 = TeamFactory()
        team2 = TeamFactory()
        app1 = CompetitionApplicationFactory(competition=competition, team=team1)
        app2 = CompetitionApplicationFactory(competition=competition, team=team2)
        TeamAtTournamentFactory(tournament=tournament, application=app1)
        TeamAtTournamentFactory(tournament=tournament, application=app2)

        reject_team_from_competition(app1)

        assert TeamAtTournament.objects.filter(application=app1).count() == 0
        assert TeamAtTournament.objects.filter(application=app2).count() == 1
