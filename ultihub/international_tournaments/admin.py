from django.contrib import admin

from international_tournaments.models import InternationalTournament, TeamAtInternationalTournament


class TeamAtInternationalTournamentInline(admin.TabularInline):
    model = TeamAtInternationalTournament
    extra = 1
    fields = ("team", "age_limit", "division")
    autocomplete_fields = ["team"]


@admin.register(InternationalTournament)
class InternationalTournamentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "season",
        "city",
        "country",
        "date_from",
        "date_to",
        "type",
        "environment",
    )
    list_filter = ("season", "type", "environment", "country")
    search_fields = ("name", "city")
    inlines = [TeamAtInternationalTournamentInline]
    fields = (
        "name",
        "season",
        "date_from",
        "date_to",
        "city",
        "country",
        "type",
        "environment",
        "fee_type",
    )

    def save_formset(self, request, form, formset, change):  # type: ignore
        instances = formset.save(commit=False)
        for instance in instances:
            if (
                isinstance(instance, TeamAtInternationalTournament)
                and not instance.team_name
                and instance.team
            ):
                instance.team_name = instance.team.name
            instance.save()
        formset.save_m2m()


@admin.register(TeamAtInternationalTournament)
class TeamAtInternationalTournamentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tournament",
        "team",
        "team_name",
        "age_limit",
        "division",
    )
    list_filter = ("tournament", "age_limit", "division")
    search_fields = ("team_name", "team__name", "tournament__name")
    autocomplete_fields = ["team", "tournament"]
