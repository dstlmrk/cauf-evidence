import pytest
from clubs.models import Team
from django.core.exceptions import ValidationError


def test_cannot_exist_two_teams_with_same_name(team):
    with pytest.raises(ValidationError) as ex:
        Team.objects.create(name=team.name, club=team.club)
        assert ex.value.message_dict == {
            "name": ["There is already an active team with this name."]
        }
