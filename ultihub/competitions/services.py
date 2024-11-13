import logging

from competitions.models import CompetitionApplication, TeamAtTournament, Tournament

logger = logging.getLogger(__name__)


def accept_team_to_competition(application: CompetitionApplication) -> None:
    tournaments = Tournament.objects.filter(competition=application.competition)
    team_at_tournament_instances = [
        TeamAtTournament(
            tournament=tournament,
            application=application,
        )
        for tournament in tournaments
    ]
    created_instances = TeamAtTournament.objects.bulk_create(team_at_tournament_instances)
    logger.info(
        "Created %s TeamAtTournament instances for team %s",
        len(created_instances),
        application.team.id,
    )


def reject_team_from_competition(application: CompetitionApplication) -> None:
    deleted_rows, _ = TeamAtTournament.objects.filter(
        tournament__competition=application.competition,
        application=application,
    ).delete()
    logger.info(
        "Deleted %s TeamAtTournament instances for team %s",
        deleted_rows,
        application.team.id,
    )
