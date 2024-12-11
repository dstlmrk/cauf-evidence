from django.contrib import admin, messages
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from finance.tasks import (
    calculate_season_fees_and_generate_invoices,
    calculate_season_fees_for_check,
)

from competitions.models import (
    AgeRestriction,
    Competition,
    CompetitionApplication,
    Division,
    Season,
    Tournament,
)


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ("name", "player_fee", "has_generated_invoices")
    change_form_template = "admin/season_change_form.html"

    def has_generated_invoices(self, obj: Season) -> bool:
        return obj.invoices_generated_at is not None

    has_generated_invoices.boolean = True  # type: ignore

    def response_change(self, request: HttpRequest, obj: Season) -> HttpResponse:
        if "_check-fees" in request.POST:
            calculate_season_fees_for_check.delay(request.user, obj)
            self.message_user(
                request, "Fees calculation (for check) started. Check you email for results."
            )
            return HttpResponseRedirect(".")
        if "_generate-invoices" in request.POST:
            if self.has_generated_invoices(obj):
                self.message_user(request, "Invoices are already generated.", level=messages.ERROR)
            else:
                calculate_season_fees_and_generate_invoices.delay(obj)
                self.message_user(
                    request, "It's going to take a while. All clubs will be notified."
                )
            return HttpResponseRedirect(".")
        return super().response_change(request, obj)


@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ("name", "is_female_allowed", "is_male_allowed")


@admin.register(AgeRestriction)
class AgeRestrictionAdmin(admin.ModelAdmin):
    list_display = ("name", "min", "max")


class TournamentInline(admin.TabularInline):
    model = Tournament
    extra = 1
    fields = ("name", "start_date", "end_date", "location")
    show_change_link = True


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display_links = ("name",)
    list_filter = ("season", "division", "age_restriction", "type")
    list_display = (
        "season",
        "age_restriction",
        "name",
        "division",
        "type",
        "registration_deadline",
    )
    fields = (
        "season",
        "age_restriction",
        "name",
        "division",
        "type",
        "is_for_national_teams",
        "player_fee_per_tournament",
        "is_exempted_from_season_fee",
        "registration_deadline",
        "deposit",
    )
    inlines = [TournamentInline]


@admin.register(CompetitionApplication)
class CompetitionApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "competition__season",
        "competition",
        "team_name",
        "team__club__name",
        "registrant_name",
        "state",
    )

    # def save_model(self, request, obj, form, change):  # type: ignore
    #     previous_state = self.model.objects.get(pk=obj.pk).state if change else None
    #     super().save_model(request, obj, form, change)
    #     if previous_state and previous_state != obj.state:
    #         if obj.state == ApplicationStateEnum.ACCEPTED:
    #             accept_team_to_competition(obj)
    #         elif previous_state == ApplicationStateEnum.ACCEPTED:
    #             reject_team_from_competition(obj)


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ("competition", "name", "start_date", "end_date", "location")
    ordering = ("-created_at",)
