from unittest.mock import patch

import pytest
from users.api import assign_or_invite_agent_to_club, unassign_or_cancel_agent_invite_from_club
from users.models import AgentAtClub, NewAgentRequest

from tests.factories import AgentAtClubFactory


@patch("core.tasks.send_email.delay")
def test_assigning_and_unassigning_agent_to_club(mocked_task, agent, club, user):
    # assign
    assert not agent.user.has_perm("manage_club", club)
    assign_or_invite_agent_to_club(email=agent.user.email, club=club, invited_by=user)
    assert NewAgentRequest.objects.count() == 0
    assert agent.user.has_perm("manage_club", club)
    assert mocked_task.call_count == 1
    agent_at_club = AgentAtClub.objects.first()
    assert agent_at_club.agent == agent
    assert agent_at_club.club == club
    assert agent_at_club.is_active

    # unassign
    unassign_or_cancel_agent_invite_from_club(email=agent.user.email, club=club)
    assert not agent.user.has_perm("manage_club", club)
    assert mocked_task.call_count == 2
    agent_at_club = AgentAtClub.objects.first()
    assert not agent_at_club.is_active


@patch("core.tasks.send_email.delay")
def test_inviting_and_invite_canceling_agent_to_club(mocked_task, club, user):
    # invite
    assign_or_invite_agent_to_club(email="new@email.cz", club=club, invited_by=user)
    new_agent_requests = NewAgentRequest.objects.all()
    assert len(new_agent_requests) == 1
    assert new_agent_requests[0].email == "new@email.cz"
    assert new_agent_requests[0].club == club
    assert new_agent_requests[0].invited_by == user
    assert mocked_task.call_count == 1

    # cancel invite
    unassign_or_cancel_agent_invite_from_club(email="new@email.cz", club=club)
    assert NewAgentRequest.objects.count() == 0
    assert mocked_task.call_count == 2


def test_cannot_remove_primary_agent():
    agent_at_club = AgentAtClubFactory(is_primary=True)
    with pytest.raises(ValueError) as ex:
        unassign_or_cancel_agent_invite_from_club(
            email=agent_at_club.agent.user.email,
            club=agent_at_club.club,
        )
        assert str(ex.value) == "Cannot remove primary agent from club"
