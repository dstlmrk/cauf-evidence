import logging

from django.db.models import Count, Exists, OuterRef, Prefetch, Q, QuerySet
from tournaments.models import TeamAtTournament, Tournament

from competitions.models import (
    ApplicationStateEnum,
    Competition,
    CompetitionApplication,
)

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


def get_competitions_qs_with_related_data(
    club_id: int | None, competition_id: int | None = None
) -> QuerySet[Competition]:
    context = {}

    if competition_id:
        competitions_qs = Competition.objects.filter(id=competition_id)
    else:
        competitions_qs = Competition.objects.all()

    competitions_qs = (
        competitions_qs.select_related("age_restriction", "season", "division")
        .prefetch_related(
            Prefetch(
                "competitionapplication_set",
                queryset=CompetitionApplication.objects.select_related("team"),
                to_attr="applications",
            ),
        )
        .prefetch_related(
            Prefetch(
                "tournament_set",
                queryset=Tournament.objects.all().order_by("start_date", "name"),
                to_attr="tournaments",
            ),
        )
        .annotate(application_count=Count("competitionapplication"))
        .exclude(is_for_national_teams=True)
        .order_by("-registration_deadline")
    )

    if club_id:
        context["club_application_without_invoice_total"] = CompetitionApplication.objects.filter(
            team__club=club_id, invoice__isnull=True, state=ApplicationStateEnum.AWAITING_PAYMENT
        ).count()

        competitions_qs = competitions_qs.annotate(
            club_application_count=Count(
                "competitionapplication",
                filter=Q(
                    competitionapplication__team__club_id=club_id,
                ),
            ),
            club_application_without_invoice_count=Count(
                "competitionapplication",
                filter=Q(
                    competitionapplication__invoice__isnull=True,
                    competitionapplication__team__club_id=club_id,
                    competitionapplication__state=ApplicationStateEnum.AWAITING_PAYMENT,
                ),
            ),
            has_awaiting_payment=Exists(
                CompetitionApplication.objects.filter(
                    competition=OuterRef("pk"),
                    state=ApplicationStateEnum.AWAITING_PAYMENT,
                    team__club_id=club_id,
                )
            ),
        )

    return competitions_qs
