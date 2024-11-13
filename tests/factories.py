import factory.fuzzy
from clubs.models import Club, Team
from django.contrib.auth.models import User
from factory import SubFactory
from pytest_factoryboy import register
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
