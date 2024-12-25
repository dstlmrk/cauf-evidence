import logging

from django.db.models import Q
from tournaments.models import MemberAtTournament, Tournament

from members.models import Member, MemberSexEnum

logger = logging.getLogger(__name__)


def _get_already_assigned_members_ids(tournament: Tournament) -> list[int]:
    return list(
        MemberAtTournament.objects.filter(tournament=tournament).values_list("member_id", flat=True)
    )


def search(
    query: str, club_id: int, tournament: Tournament | None, limit: int = 20
) -> list[Member]:
    query_length = len(query)
    qs = Member.objects.select_related("club")

    if 0 < query_length < 3:
        return []

    query_filter = Q()

    if query_length >= 3:  # regular search for members over all clubs
        search_terms = query.split()

        if len(search_terms) == 2:
            first, second = search_terms
            query_filter |= (Q(first_name__icontains=first) & Q(last_name__icontains=second)) | (
                Q(first_name__icontains=second) & Q(last_name__icontains=first)
            )
        else:
            for term in search_terms:
                query_filter |= Q(first_name__icontains=term) | Q(last_name__icontains=term)

    else:  # search for members in the current club
        query_filter &= Q(club_id=club_id)
        query_filter &= Q(is_active=True)

        if tournament:
            division = tournament.competition.division
            season = tournament.competition.season

            if division.is_male_allowed != division.is_female_allowed:
                sex_filter = (
                    MemberSexEnum.MALE if division.is_male_allowed else MemberSexEnum.FEMALE
                )
                query_filter &= Q(sex=sex_filter)

            if "open" in division.name.lower():
                # Prefer men in open division
                qs = qs.order_by("-sex", "id")

            qs = qs.annotate_age(season.age_reference_date)  # type: ignore

            if age_limit := tournament.competition.age_limit:
                query_filter &= Q(
                    sex=MemberSexEnum.MALE,
                    age__range=(age_limit.m_min, age_limit.m_max),
                ) | Q(
                    sex=MemberSexEnum.FEMALE,
                    age__range=(age_limit.f_min, age_limit.f_max),
                )
            else:
                query_filter &= Q(age__gte=season.min_allowed_age)

            already_assigned_members_ids = _get_already_assigned_members_ids(tournament)
            if already_assigned_members_ids:
                query_filter &= ~Q(id__in=already_assigned_members_ids)

    # TODO: add higher weight to members who already played for the club in this competition
    return [member for member in qs.filter(query_filter)[:limit]]
