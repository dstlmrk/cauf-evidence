from django.contrib import admin

from tournaments.models import MemberAtTournament, TeamAtTournament, Tournament


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = (
        "competition",
        "name",
        "start_date",
        "end_date",
        "location",
        "rosters_deadline",
    )
    ordering = ("-created_at",)


@admin.register(TeamAtTournament)
class TeamAtTournamentAdmin(admin.ModelAdmin):
    list_display = (
        "tournament",
        "application__team_name",
        "application__team__club",
        "final_placement",
        "spirit_avg",
    )

    list_display_links = ("application__team_name",)


@admin.register(MemberAtTournament)
class MemberAtTournamentAdmin(admin.ModelAdmin):
    list_display = (
        "tournament",
        "team_at_tournament__application__team_name",
        "member",
        "is_captain",
        "is_coach",
        "jersey_number",
    )

    list_filter = ("is_captain", "is_coach")
    show_facets = admin.ShowFacets.ALWAYS
    list_display_links = ("member",)
