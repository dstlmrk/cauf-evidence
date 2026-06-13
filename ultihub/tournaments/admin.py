from core.admin import AuditlogMixin
from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from tournaments.models import MemberAtTournament, TeamAtTournament, Tournament


class TeamAtTournamentInline(admin.TabularInline):
    model = TeamAtTournament
    extra = 0
    fields = ("team_name", "seeding", "final_placement", "spirit_avg")
    readonly_fields = ("team_name",)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).select_related("application__team__club")

    @admin.display(description="Team name")
    def team_name(self, obj: TeamAtTournament) -> str:
        return f"{obj.application.team_name} ({obj.application.team.club})"


class MemberAtTournamentInline(admin.TabularInline):
    model = MemberAtTournament
    extra = 0
    fields = ("tournament", "team_name", "is_captain", "is_coach", "jersey_number")
    readonly_fields = ("tournament", "team_name")

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return (
            super()
            .get_queryset(request)
            .select_related("tournament", "team_at_tournament__application")
        )

    @admin.display(description="Team name")
    def team_name(self, obj: MemberAtTournament) -> str:
        return f"{obj.team_at_tournament.application.team_name}"


@admin.register(Tournament)
class TournamentAdmin(AuditlogMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "competition",
        "name",
        "start_date",
        "end_date",
        "location",
        "rosters_deadline",
        "winner_team",
        "sotg_winner_team",
    )
    list_select_related = ("competition", "winner_team", "sotg_winner_team")
    readonly_fields = ("winner_team", "sotg_winner_team")
    ordering = ("-created_at",)
    inlines = [TeamAtTournamentInline]


@admin.register(TeamAtTournament)
class TeamAtTournamentAdmin(AuditlogMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "tournament",
        "application__team_name",
        "application__team__club",
        "final_placement",
        "spirit_avg",
    )

    inlines = [MemberAtTournamentInline]


@admin.register(MemberAtTournament)
class MemberAtTournamentAdmin(AuditlogMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "tournament__name",
        "tournament__competition",
        "team_at_tournament__application__team_name",
        "member",
        "is_captain",
        "is_coach",
        "jersey_number",
    )

    list_filter = ("tournament__competition__season", "is_captain", "is_coach")
    search_fields = (
        "member__first_name",
        "member__last_name",
        "member__email",
        "member__birth_number",
        "team_at_tournament__application__team_name",
        "tournament__name",
        "tournament__competition__name",
    )
    show_facets = admin.ShowFacets.ALWAYS
