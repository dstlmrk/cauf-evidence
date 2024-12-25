from datetime import datetime, timedelta

import factory.fuzzy
from clubs.models import Club, Team
from competitions.models import (
    AgeLimit,
    Competition,
    CompetitionFeeTypeEnum,
    CompetitionTypeEnum,
    Division,
    Season,
)
from django.contrib.auth.models import User
from factory import SubFactory
from members.models import Member, MemberSexEnum
from pytest_factoryboy import register
from tournaments.models import Tournament
from users.models import Agent, AgentAtClub


@register
class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker("user_name")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Faker("email")
    is_staff = False


@register
class AgentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Agent

    picture_url = factory.Faker("image_url")
    user = SubFactory(UserFactory)


@register
class ClubFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Club

    name = factory.Faker("company")
    email = factory.Faker("email")
    website = factory.Faker("url")
    city = factory.Faker("city")
    organization_name = factory.Faker("company")


@register
class TeamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Team

    name = factory.fuzzy.FuzzyText()
    description = factory.fuzzy.FuzzyText()
    club = SubFactory(ClubFactory)


@register
class AgentAtClubFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AgentAtClub

    agent = SubFactory(AgentFactory)
    club = SubFactory(ClubFactory)
    invited_by = SubFactory(UserFactory)


@register
class MemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Member

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Faker("email")
    birth_date = factory.Faker("date_of_birth")
    sex = factory.fuzzy.FuzzyChoice(list(MemberSexEnum))


@register
class SeasonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Season

    name = 2025
    discounted_fee = 200
    regular_fee = 600
    fee_at_tournament = 60
    min_allowed_age = 14
    age_reference_date = factory.LazyAttribute(lambda obj: f"{obj.name}-12-31")


@register
class DivisionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Division


@register
class AgeLimitFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AgeLimit

    name = factory.Faker("word")
    m_min = f_min = 14
    m_max = f_max = 99


@register
class CompetitionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Competition

    name = factory.Faker("company")
    season = SubFactory(SeasonFactory)
    division = SubFactory(DivisionFactory)
    age_limit = None
    is_for_national_teams = False
    type = factory.fuzzy.FuzzyChoice(list(CompetitionTypeEnum))
    fee_type = CompetitionFeeTypeEnum.REGULAR
    deposit = factory.Faker("random_int", min=1000, max=2000)
    registration_deadline = factory.LazyFunction(lambda: datetime.now() + timedelta(days=2))


@register
class TournamentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tournament

    competition = SubFactory(CompetitionFactory)
    name = factory.Faker("company")
    start_date = factory.Faker("date_this_year")
    end_date = factory.LazyAttribute(lambda obj: obj.start_date + timedelta(days=2))
    location = factory.Faker("city")
    rosters_deadline = factory.LazyFunction(lambda: datetime.now() + timedelta(days=1))
