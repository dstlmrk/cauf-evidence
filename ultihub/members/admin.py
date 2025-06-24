import csv
from typing import Any

from django.contrib import admin
from django.db.models import Exists, OuterRef, QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils.timezone import localtime, now
from django_countries.fields import Country
from rangefilter.filters import DateRangeFilterBuilder
from tournaments.admin import MemberAtTournamentInline

# from members.helpers import get_member_participation_counts_for_last_season
from members.models import CoachLicence, Member, MemberSexEnum


class CitizenshipFilter(admin.SimpleListFilter):
    title = "Citizenship"
    parameter_name = "citizenship"

    _cached_lookups = None

    @classmethod
    def get_lookups(cls, model_admin: Any) -> list[tuple[str, str]]:
        if cls._cached_lookups is not None:
            return cls._cached_lookups  # type: ignore[unreachable]
        cls._cached_lookups = [
            (code, Country(code).name)
            for code in model_admin.model.objects.values_list("citizenship", flat=True).distinct()
            if code
        ]
        return cls._cached_lookups

    def lookups(self, request: HttpRequest, model_admin: Any) -> list:
        return self.get_lookups(model_admin)

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        if self.value():
            return queryset.filter(citizenship=self.value())
        return queryset

    @classmethod
    def clear_cache(cls) -> None:
        cls._cached_lookups = None


class CoachLicenceFilter(admin.SimpleListFilter):
    title = "Coach"
    parameter_name = "has_coach_licence"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list:
        return [("yes", "Yes"), ("no", "No")]

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        if self.value() == "yes":
            return queryset.filter(has_coach_licence=True)
        if self.value() == "no":
            return queryset.filter(has_coach_licence=False)
        return queryset


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "original_id",
        "club",
        "has_coach_licence",
        "first_name",
        "last_name",
        "birth_year",
        # "birth_number",
        # "sex_abbreviation",
        "citizenship_code",
        # "email",
        "has_email_confirmed",
        # "has_marketing_consent_given",
        "created_at_local_time",
        # "participation_count",
    )
    readonly_fields = [
        "email_confirmation_token",
        "email_confirmed_at",
        # "participation_count",
    ]

    actions = ["export_as_csv"]
    ordering = ["-id"]
    show_facets = admin.ShowFacets.ALWAYS
    inlines = [MemberAtTournamentInline]

    search_fields = ["first_name", "last_name", "email", "birth_number", "original_id"]
    list_filter = [
        "sex",
        ("birth_date", DateRangeFilterBuilder()),
        CitizenshipFilter,
        CoachLicenceFilter,
        "club__name",
    ]

    # def __init__(self, *args: Any, **kwargs: Any) -> None:
    #     super().__init__(*args, **kwargs)
    #     self.member_participation: dict = {}

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        # self.member_participation = get_member_participation_counts_for_last_season()

        CitizenshipFilter.clear_cache()
        current_date = now().date()
        return (
            super()
            .get_queryset(request)
            .select_related("club")
            .annotate(
                has_coach_licence=Exists(
                    CoachLicence.objects.filter(
                        member=OuterRef("pk"),
                        valid_from__lte=current_date,
                        valid_to__gte=current_date,
                    )
                ),
            )
        )

    # @admin.display(description="Participation count")
    # def participation_count(self, obj: Member) -> int:
    #     """
    #     Return the number of days the member has participated
    #     in tournaments in current season
    #     """
    #     return self.member_participation[obj.id]

    @admin.display(ordering="birth_date")
    def birth_year(self, obj: Member) -> str:
        return obj.birth_date.strftime("%Y")

    @admin.display(description="Citizenship")
    def citizenship_code(self, obj: Member) -> str:
        return obj.citizenship.code

    def club(self, obj: Member) -> str:
        return obj.club.short_name_or_name

    @admin.display(description="Created")
    def created_at_local_time(self, obj: Member) -> str:
        return localtime(obj.created_at).strftime("%Y/%m/%d %H:%M")

    @admin.display(description="Marketing consent", boolean=True)
    def has_marketing_consent_given(self, obj: Member) -> bool:
        return obj.marketing_consent_given_at is not None

    @admin.display(description="Coach", boolean=True)
    def has_coach_licence(self, obj: Member) -> bool:
        return obj.has_coach_licence  # type: ignore

    @admin.display(description="Confirmed email", boolean=True)
    def has_email_confirmed(self, obj: Member) -> bool:
        return obj.has_email_confirmed

    @admin.display(description="Sex")
    def sex_abbreviation(self, obj: Member) -> str:
        return "F" if obj.sex == MemberSexEnum.FEMALE else "M"

    @admin.display(description="Export selected")
    def export_as_csv(self, request: HttpRequest, queryset: QuerySet) -> HttpResponse:
        field_names = [
            "id",
            "club",
            "first_name",
            "last_name",
            "birth_date",
            "email",
            "sex",
            "citizenship",
            "birth_number",
            "street",
            "city",
            "house_number",
            "postal_code",
            "email_confirmed_at",
            "marketing_consent_given_at",
            "has_coach_licence",
            # "participation_count",
            "created_at",
        ]

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=members.csv"
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            writer.writerow(
                [
                    obj.id,
                    obj.club.name,
                    obj.first_name,
                    obj.last_name,
                    obj.birth_date,
                    obj.email,
                    MemberSexEnum(obj.sex).label,
                    obj.citizenship,
                    obj.birth_number,
                    obj.street,
                    obj.city,
                    obj.house_number,
                    obj.postal_code,
                    obj.email_confirmed_at,
                    obj.marketing_consent_given_at,
                    obj.has_coach_licence,
                    # self.member_participation[obj.id],
                    self.created_at_local_time(obj),
                ]
            )

        return response


@admin.register(CoachLicence)
class CoachLicenceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "member__first_name",
        "member__last_name",
        "member__club__name",
        "level",
        "valid_from",
        "valid_to",
        "is_valid",
    )

    @admin.display(boolean=True)
    def is_valid(self, obj: CoachLicence) -> bool:
        return obj.valid_from < now().date() < obj.valid_to

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request)
        qs = qs.select_related("member", "member__club")
        return qs
