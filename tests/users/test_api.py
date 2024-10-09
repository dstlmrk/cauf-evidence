import pytest
from users.api import assign_or_invite_agent_to_club, unassign_or_cancel_agent_invite_from_club
from users.models import NewAgentRequest


@pytest.mark.django_db
def test_assigning_and_unassigning_agent_to_club(agent, club):
    # assign
    assert not agent.user.has_perm("manage_club", club)
    assign_or_invite_agent_to_club(email=agent.user.email, club=club)
    assert NewAgentRequest.objects.count() == 0
    assert agent.user.has_perm("manage_club", club)

    # unassign
    unassign_or_cancel_agent_invite_from_club(email=agent.user.email, club=club)
    assert not agent.user.has_perm("manage_club", club)


@pytest.mark.django_db
def test_inviting_and_invite_canceling_agent_to_club(club):
    # invite
    assign_or_invite_agent_to_club(email="new@email.cz", club=club)
    new_agent_requests = NewAgentRequest.objects.all()
    assert len(new_agent_requests) == 1
    assert new_agent_requests[0].email == "new@email.cz"
    assert new_agent_requests[0].club == club

    # cancel invite
    unassign_or_cancel_agent_invite_from_club(email="new@email.cz", club=club)
    assert NewAgentRequest.objects.count() == 0
