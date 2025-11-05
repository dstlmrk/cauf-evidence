from clubs.models import Club
from django.db.models import Exists, OuterRef, Q, QuerySet
from international_tournaments.models import MemberAtInternationalTournament
from tournaments.models import MemberAtTournament

from competitions.enums import CompetitionFeeTypeEnum
from competitions.models import Season


def get_clubs_without_subject_id_with_fees(season: Season) -> QuerySet[Club]:
    """
    Get clubs that should receive invoices but cannot because they lack FAKTUROID_SUBJECT_ID.

    Returns clubs that:
    - Do NOT have fakturoid_subject_id set
    - Have members at paid tournaments (fee_type != FREE) in the given season

    Args:
        season: The season to check for tournament participation

    Returns:
        QuerySet of Club objects without fakturoid_subject_id that have members at paid tournaments
    """
    return Club.objects.filter(fakturoid_subject_id__isnull=True).filter(
        Q(
            # Clubs with members at domestic paid tournaments
            Exists(
                MemberAtTournament.objects.filter(
                    member__club=OuterRef("pk"),
                    tournament__competition__season=season,
                ).exclude(tournament__competition__fee_type=CompetitionFeeTypeEnum.FREE)
            )
        )
        | Q(
            # Clubs with members at international paid tournaments
            Exists(
                MemberAtInternationalTournament.objects.filter(
                    member__club=OuterRef("pk"),
                    tournament__season=season,
                ).exclude(tournament__fee_type=CompetitionFeeTypeEnum.FREE)
            )
        )
    )
