from clubs.models import Club
from competitions.models import ApplicationStateEnum, Competition, CompetitionApplication, Season
from django.db.models import Prefetch, QuerySet
from django_filters.rest_framework import CharFilter, DjangoFilterBackend, FilterSet
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.serializers import Serializer
from tournaments.models import MemberAtTournament, TeamAtTournament, Tournament

from .serializers import (
    ClubSerializer,
    CompetitionApplicationSerializer,
    CompetitionApplicationUpdateSerializer,
    CompetitionSerializer,
    SeasonSerializer,
    TeamAtTournamentSerializer,
    TeamAtTournamentUpdateSerializer,
)


class CompetitionsFilter(FilterSet):
    season = CharFilter(field_name="season__name", lookup_expr="icontains")

    class Meta:
        model = Competition
        fields = ["season"]


class CompetitionsView(ListAPIView):
    queryset = (
        Competition.objects.select_related("age_limit", "season", "division")
        .prefetch_related(
            Prefetch(
                "tournaments",
                queryset=Tournament.objects.all(),
                to_attr="prefetched_tournaments",
            ),
            Prefetch(
                "applications",
                queryset=CompetitionApplication.objects.select_related("team", "team__club").filter(
                    state=ApplicationStateEnum.ACCEPTED
                ),
                to_attr="prefetched_applications",
            ),
        )
        .order_by("-pk")
    )
    serializer_class = CompetitionSerializer
    filterset_class = CompetitionsFilter


class ClubsView(ListAPIView):
    queryset = Club.objects.all()
    serializer_class = ClubSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["id"]


class TeamsAtTournamentView(ListAPIView):
    serializer_class = TeamAtTournamentSerializer

    def get_queryset(self) -> QuerySet:
        tournament_id = self.request.GET.get("tournament_id")

        if not tournament_id:
            raise ValidationError({"tournament_id": "This parameter is required."})

        return (
            TeamAtTournament.objects.select_related("application", "application__team")
            .prefetch_related(
                Prefetch(
                    "members",
                    queryset=MemberAtTournament.objects.select_related("member"),
                    to_attr="prefetched_members",
                )
            )
            .filter(tournament_id=tournament_id)
        )


class HttpMethodPermissionsMixin:
    request: Request

    def get_permissions(self) -> list[BasePermission]:
        if self.request.method == "GET":
            return [AllowAny()]
        elif self.request.method == "PATCH":
            return [IsAuthenticated()]
        return super().get_permissions()  # type: ignore[misc]


class TeamAtTournamentView(HttpMethodPermissionsMixin, RetrieveUpdateAPIView):
    # Only GET and PATCH are exposed; PUT is intentionally excluded.
    http_method_names = ["get", "patch", "options", "head"]

    def get_queryset(self) -> QuerySet:
        return TeamAtTournament.objects.prefetch_related(
            Prefetch(
                "members",
                queryset=MemberAtTournament.objects.select_related("member"),
                to_attr="prefetched_members",
            )
        )

    def get_serializer_class(self) -> type[Serializer]:
        if self.request.method == "PATCH":
            return TeamAtTournamentUpdateSerializer
        return TeamAtTournamentSerializer


class CompetitionApplicationView(HttpMethodPermissionsMixin, RetrieveUpdateAPIView):
    # Only GET and PATCH are exposed; PUT is intentionally excluded.
    http_method_names = ["get", "patch", "options", "head"]
    queryset = CompetitionApplication.objects.all()

    def get_serializer_class(self) -> type[Serializer]:
        if self.request.method == "PATCH":
            return CompetitionApplicationUpdateSerializer
        return CompetitionApplicationSerializer


class SeasonsView(ListAPIView):
    queryset = Season.objects.all()
    serializer_class = SeasonSerializer
