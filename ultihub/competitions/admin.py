import logging
from typing import Any

from clubs.models import Club
from django.contrib import admin, messages
from django.db import IntegrityError, transaction
from django.db.models import QuerySet, Subquery
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import URLPattern, path, reverse
from finance.tasks import (
    calculate_season_fees_and_generate_invoices,
    calculate_season_fees_for_check,
)
from members.tasks import generate_nsa_export
from tournaments.models import TeamAtTournament, Tournament

from competitions.enums import ApplicationStateEnum
from competitions.forms import AddTeamsToTournamentForm
from competitions.models import (
    AgeLimit,
    Competition,
    CompetitionApplication,
    Division,
    Season,
)

logger = logging.getLogger(__name__)


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "discounted_fee",
        "regular_fee",
        "fee_at_tournament",
        "min_allowed_age",
        "age_reference_date",
        "has_generated_invoices",
    )
    change_form_template = "admin/season_change_form.html"

    def has_generated_invoices(self, obj: Season) -> bool:
        return obj.invoices_generated_at is not None

    has_generated_invoices.boolean = True  # type: ignore

    def response_change(self, request: HttpRequest, obj: Season) -> HttpResponse:
        if "_generate-nsa-export" in request.POST:
            generate_nsa_export(request.user, obj, None)
            self.message_user(
                request, "The NSA export is being generated. Check your email for results."
            )
            return HttpResponseRedirect(".")
        if "_check-fees" in request.POST:
            calculate_season_fees_for_check(request.user, obj)
            self.message_user(
                request, "Fees calculation (for check) started. Check you email for results."
            )
            return HttpResponseRedirect(".")
        if "_generate-invoices" in request.POST:
            if self.has_generated_invoices(obj):
                self.message_user(request, "Invoices are already generated.", level=messages.ERROR)
            else:
                calculate_season_fees_and_generate_invoices(obj)
                self.message_user(
                    request, "It's going to take a while. All clubs will be notified."
                )
            return HttpResponseRedirect(".")
        return super().response_change(request, obj)

    def change_view(self, request: HttpRequest, object_id: str, form_url="", extra_context=None):  # type: ignore
        extra_context = extra_context or {}
        extra_context["clubs_without_subject_id"] = Club.objects.filter(
            fakturoid_subject_id__isnull=True
        )
        return super().change_view(request, object_id, form_url, extra_context=extra_context)


@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_female_allowed", "is_male_allowed")


@admin.register(AgeLimit)
class AgeLimitAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "m_min", "m_max", "f_min", "f_max")
    change_form_template = "admin/age_limit_change_form.html"


class TournamentInline(admin.TabularInline):
    model = Tournament
    extra = 1
    fields = ("name", "start_date", "end_date", "location", "rosters_deadline")
    show_change_link = True


class CompetitionApplicationInline(admin.TabularInline):
    model = CompetitionApplication
    extra = 0
    fields = ("club", "team_name", "state", "final_placement")
    readonly_fields = ("club",)

    @admin.display(description="Club")
    def club(self, obj: CompetitionApplication) -> str:
        return str(obj.team.club)


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_filter = ("season", "division", "age_limit", "environment")
    list_display = (
        "id",
        "season",
        "age_limit",
        "name",
        "division",
        "environment",
        "fee_type",
        "registration_deadline",
    )
    fields = (
        "season",
        "age_limit",
        "name",
        "division",
        "environment",
        "fee_type",
        "registration_deadline",
        "deposit",
        "description",
    )
    inlines = [TournamentInline, CompetitionApplicationInline]


class SeasonFilter(admin.SimpleListFilter):
    title = "Season"
    parameter_name = "competition__season"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple]:
        seasons = set(
            ca.competition.season
            for ca in model_admin.model.objects.select_related("competition").all()
        )
        return [(season.id, season.name) for season in seasons]

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        if self.value():
            return queryset.filter(competition__season=self.value())
        return queryset


@admin.register(CompetitionApplication)
class CompetitionApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "competition__season",
        "competition",
        "team_name",
        "team__club__name",
        "registrant_name",
        "state",
    )
    list_filter = (SeasonFilter, "competition", "state")
    ordering = ["-id"]
    show_facets = admin.ShowFacets.ALWAYS

    actions = ["approve", "decline", "add_teams_to_tournament"]

    def get_urls(self) -> list[URLPattern]:
        urls = super().get_urls()
        custom_urls = [
            path(
                "add-teams-to-tournament/",
                self.admin_site.admin_view(self.add_teams_to_tournament_view),
                name="add_teams_to_tournament",
            ),
        ]
        return custom_urls + urls

    @admin.display(description="Add teams to a tournament")
    def add_teams_to_tournament(self, request: HttpRequest, queryset: QuerySet) -> HttpResponse:
        if queryset.exclude(state=ApplicationStateEnum.ACCEPTED).exists():
            self.message_user(
                request, "Applications must be in ACCEPTED state", level=messages.ERROR
            )
            return HttpResponseRedirect(request.get_full_path())

        if queryset.values("competition").distinct().count() > 1:
            self.message_user(
                request, "Applications must be for the same competition", level=messages.ERROR
            )
            return HttpResponseRedirect(request.get_full_path())

        applications = ",".join(str(obj.id) for obj in queryset)
        return HttpResponseRedirect(f"add-teams-to-tournament/?ids={applications}")

    def add_teams_to_tournament_view(self, request: HttpRequest) -> HttpResponse:
        application_ids = request.GET.get("ids", "").split(",")

        related_tournaments = Tournament.objects.filter(
            competition_id__in=Subquery(
                CompetitionApplication.objects.filter(id__in=application_ids).values(
                    "competition_id"
                )
            )
        )

        if request.method == "POST":
            form = AddTeamsToTournamentForm(request.POST, related_tournaments=related_tournaments)

            if form.is_valid():
                tournament_id = form.cleaned_data["tournament"]
                team_at_tournament_instances = [
                    TeamAtTournament(
                        tournament_id=tournament_id,
                        application_id=application_id,
                    )
                    for application_id in application_ids
                ]

                try:
                    created_instances = TeamAtTournament.objects.bulk_create(
                        team_at_tournament_instances
                    )
                except IntegrityError:
                    self.message_user(
                        request,
                        "Some applications have already been added to the tournament",
                        level=messages.ERROR,
                    )
                    return HttpResponseRedirect(request.get_full_path())

                logger.info(
                    "Applications %s (%s) added to tournament %s",
                    application_ids,
                    len(created_instances),
                    tournament_id,
                )

                self.message_user(
                    request, f"Teams ({len(created_instances)}) have been added to the tournament"
                )
                return HttpResponseRedirect(
                    reverse("admin:competitions_competitionapplication_changelist")
                )
        else:
            form = AddTeamsToTournamentForm(related_tournaments=related_tournaments)

        return render(
            request,
            "admin/add_teams_to_tournament.html",
            {
                "form": form,
                "title": "Add teams to a tournament",
                "description": "Selected teams will be able to register players on rosters.",
            },
        )

    def competition_environment(self, obj: CompetitionApplication) -> str:
        return obj.competition.get_environment_display()

    @transaction.atomic
    @admin.display(description="Approve selected applications")
    def approve(self, request: HttpRequest, queryset: QuerySet) -> None:
        queryset.update(state=ApplicationStateEnum.ACCEPTED)
        self.message_user(request, "Applications approved")

    @admin.display(description="Decline selected applications")
    def decline(self, request: HttpRequest, queryset: QuerySet) -> None:
        queryset.update(state=ApplicationStateEnum.DECLINED)
        self.message_user(request, "Applications approved")
