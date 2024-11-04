from django.contrib import admin

from competitions.models import (
    AgeRestriction,
    Competition,
    Division,
    Season,
)


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ("name", "player_fee")


@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ("name", "is_female_allowed", "is_male_allowed")


@admin.register(AgeRestriction)
class AgeRestrictionAdmin(admin.ModelAdmin):
    list_display = ("name", "min", "max")


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display_links = ("name",)
    list_filter = ("season", "division", "age_restriction", "type")
    list_display = (
        "season",
        "name",
        "division",
        "age_restriction",
        "type",
        "is_for_national_teams",
        "player_fee_per_tournament",
        "is_exempted_from_season_fee",
        "registration_deadline",
        "deposit",
    )
    fields = (
        "season",
        "name",
        "division",
        "age_restriction",
        "type",
        "is_for_national_teams",
        "player_fee_per_tournament",
        "is_exempted_from_season_fee",
        "registration_deadline",
        "deposit",
    )


# @admin.register(CompetitionApplication)
# class CompetitionApplicationAdmin(admin.ModelAdmin):
#     pass
