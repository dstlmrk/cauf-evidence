from django.db.models import (
    Case,
    Count,
    Exists,
    IntegerField,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Value,
    When,
)
from tournaments.models import Tournament

from competitions.models import (
    ApplicationStateEnum,
    Competition,
    CompetitionApplication,
    CompetitionFeeTypeEnum,
)


def get_competitions_qs_with_related_data(
    club_id: int | None, competition_id: int | None = None
) -> QuerySet[Competition]:
    if competition_id:
        competitions_qs = Competition.objects.filter(id=competition_id)
    else:
        competitions_qs = Competition.objects.all()

    competitions_qs = (
        competitions_qs.select_related("age_limit", "season", "division")
        .prefetch_related(
            Prefetch(
                "tournaments",
                queryset=Tournament.objects.all().order_by("start_date", "name"),
                to_attr="prefetched_tournaments",
            ),
        )
        .annotate(
            application_count=Count("applications"),
            fee_at_tournament=Case(
                When(
                    fee_type=CompetitionFeeTypeEnum.REGULAR,
                    then="season__fee_at_tournament",
                ),
                default=Value(0),
                output_field=IntegerField(),
            ),
        )
        .order_by("-registration_deadline")
    )

    if club_id:
        competitions_qs = competitions_qs.annotate(
            club_application_without_invoice_count=Count(
                "applications",
                filter=Q(
                    applications__invoice__isnull=True,
                    applications__team__club_id=club_id,
                    applications__state=ApplicationStateEnum.AWAITING_PAYMENT,
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
