from django_filters import ChoiceFilter, FilterSet, NumberFilter

from competitions.models import Competition, CompetitionTypeEnum


class CompetitionFilterSet(FilterSet):
    season = NumberFilter(field_name="season", lookup_expr="exact")
    type = ChoiceFilter(choices=CompetitionTypeEnum.choices)
    division = NumberFilter(field_name="division", lookup_expr="exact")
    age_limit = NumberFilter(field_name="age_limit", lookup_expr="exact")

    class Meta:
        model = Competition
        fields = ["season", "type", "division", "age_limit"]


class TournamentFilterSet(FilterSet):
    season = NumberFilter(field_name="competition__season", lookup_expr="exact")
    type = ChoiceFilter(field_name="competition__type", choices=CompetitionTypeEnum.choices)
    division = NumberFilter(field_name="competition__division", lookup_expr="exact")
    age_limit = NumberFilter(field_name="competition__age_limit", lookup_expr="exact")

    class Meta:
        model = Competition  # This is just for field definitions
        fields = ["season", "type", "division", "age_limit"]
