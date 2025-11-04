from datetime import datetime, timedelta
from decimal import Decimal

import factory.fuzzy
from clubs.models import Club, Team
from competitions.enums import ApplicationStateEnum, CompetitionFeeTypeEnum, EnvironmentEnum
from competitions.models import (
    AgeLimit,
    Competition,
    CompetitionApplication,
    Division,
    Season,
)
from django.contrib.auth.models import User
from django.utils import timezone
from factory import SubFactory
from finance.models import Invoice, InvoiceTypeEnum
from international_tournaments.enums import InternationalTournamentTypeEnum
from international_tournaments.models import (
    InternationalTournament,
    MemberAtInternationalTournament,
    TeamAtInternationalTournament,
)
from members.models import Member, MemberSexEnum, Transfer, TransferStateEnum
from tournaments.models import MemberAtTournament, TeamAtTournament, Tournament
from users.models import Agent, AgentAtClub


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker("user_name")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Faker("email")
    is_staff = False


class AgentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Agent

    picture_url = factory.Faker("image_url")
    user = SubFactory(UserFactory)


class ClubFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Club

    name = factory.Faker("company")
    email = factory.Faker("email")
    website = factory.Faker("url")
    city = factory.Faker("city")
    organization_name = factory.Faker("company")
    identification_number = ""
    fakturoid_subject_id = None


class TeamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Team

    name = factory.fuzzy.FuzzyText()
    description = factory.fuzzy.FuzzyText()
    club = SubFactory(ClubFactory)


class AgentAtClubFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AgentAtClub

    agent = SubFactory(AgentFactory)
    club = SubFactory(ClubFactory)
    invited_by = SubFactory(UserFactory)


class MemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Member

    club = SubFactory(ClubFactory)
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Faker("email")
    birth_date = factory.Faker("date_of_birth", minimum_age=20, maximum_age=30)
    sex = factory.fuzzy.FuzzyChoice(list(MemberSexEnum))


class SeasonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Season
        django_get_or_create = ("name",)

    name = "2025"
    discounted_fee = Decimal(200)
    regular_fee = Decimal(600)
    fee_at_tournament = Decimal(60)
    min_allowed_age = 14
    age_reference_date = factory.LazyAttribute(
        lambda obj: datetime.strptime(f"{obj.name}-12-31", "%Y-%m-%d").date()
    )


class DivisionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Division

    name = factory.Faker("word")
    is_female_allowed = True
    is_male_allowed = True


class AgeLimitFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AgeLimit

    name = factory.Faker("word")
    m_min = f_min = 14
    m_max = f_max = 99


class CompetitionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Competition

    name = factory.Faker("company")
    season = SubFactory(SeasonFactory)
    division = SubFactory(DivisionFactory)
    age_limit = None
    environment = factory.fuzzy.FuzzyChoice(list(EnvironmentEnum))
    fee_type = CompetitionFeeTypeEnum.REGULAR
    deposit = factory.Faker("random_int", min=1000, max=2000)
    registration_deadline = factory.LazyFunction(lambda: timezone.now() + timedelta(days=2))


class TournamentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tournament

    competition = SubFactory(CompetitionFactory)
    name = factory.Faker("company")
    start_date = factory.Faker("date_this_year")
    end_date = factory.LazyAttribute(lambda obj: obj.start_date + timedelta(days=2))
    location = factory.Faker("city")
    rosters_deadline = factory.LazyFunction(lambda: timezone.now() + timedelta(days=1))


class CompetitionApplicationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CompetitionApplication

    team_name = factory.LazyAttribute(lambda obj: obj.team.club.name)
    competition = SubFactory(CompetitionFactory)
    state = ApplicationStateEnum.ACCEPTED
    registered_by = SubFactory(UserFactory)
    team = SubFactory(TeamFactory)


class TeamAtTournamentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TeamAtTournament

    tournament = SubFactory(TournamentFactory)
    application = SubFactory(CompetitionApplicationFactory)
    final_placement = None
    spirit_avg = None


class MemberAtTournamentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MemberAtTournament

    tournament = SubFactory(TournamentFactory)
    team_at_tournament = SubFactory(TeamAtTournamentFactory)
    member = SubFactory(MemberFactory)
    is_captain = False
    is_spirit_captain = False
    is_coach = False
    jersey_number = 10


class InvoiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invoice

    club = SubFactory(ClubFactory)
    type = InvoiceTypeEnum.COMPETITION_DEPOSIT
    original_amount = Decimal(2000)


class TransferFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Transfer

    member = SubFactory(MemberFactory)
    state = TransferStateEnum.REQUESTED
    source_club = factory.LazyAttribute(lambda obj: obj.member.club)
    target_club = SubFactory(ClubFactory)
    requesting_club = factory.LazyAttribute(lambda obj: obj.source_club)
    approving_club = factory.LazyAttribute(lambda obj: obj.target_club)
    requested_by = SubFactory(AgentFactory)


class InternationalTournamentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InternationalTournament

    name = factory.Faker("company")
    season = SubFactory(SeasonFactory)
    date_from = factory.Faker("date_this_year")
    date_to = factory.LazyAttribute(lambda obj: obj.date_from + timedelta(days=3))
    city = factory.Faker("city")
    country = "CZ"
    type = InternationalTournamentTypeEnum.NATIONAL_TEAM
    environment = factory.fuzzy.FuzzyChoice(list(EnvironmentEnum))
    fee_type = CompetitionFeeTypeEnum.REGULAR


class TeamAtInternationalTournamentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TeamAtInternationalTournament

    tournament = SubFactory(InternationalTournamentFactory)
    team = SubFactory(TeamFactory)
    age_limit = None
    division = SubFactory(DivisionFactory)
    team_name = factory.LazyAttribute(lambda obj: obj.team.name)


class MemberAtInternationalTournamentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MemberAtInternationalTournament

    tournament = factory.LazyAttribute(lambda obj: obj.team_at_tournament.tournament)
    team_at_tournament = SubFactory(TeamAtInternationalTournamentFactory)
    member = SubFactory(MemberFactory)
    is_captain = False
    is_spirit_captain = False
    is_coach = False
    jersey_number = 10
