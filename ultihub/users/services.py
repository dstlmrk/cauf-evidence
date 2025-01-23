from clubs.models import Club
from core.tasks import send_email
from django.contrib.auth.models import User
from django.db.models import QuerySet
from guardian.shortcuts import assign_perm, get_objects_for_user, remove_perm

from users.models import Agent, AgentAtClub, NewAgentRequest


def assign_agent_to_club(
    agent: Agent, club: Club, invited_by: User, is_primary: bool = False
) -> None:
    """
    Assign permission to agent to manage club
    """
    if not agent.user.has_perm("manage_club", club):
        AgentAtClub.objects.update_or_create(
            agent=agent,
            club=club,
            defaults=dict(is_active=True, is_primary=is_primary, invited_by=invited_by),
            create_defaults=dict(invited_by=invited_by, is_primary=is_primary),
        )
        assign_perm("manage_club", agent.user, club)


def unassign_agent_from_club(agent: Agent, club: Club) -> None:
    """
    Remove permission from agent to manage club
    """
    AgentAtClub.objects.filter(agent=agent, club=club).update(is_active=False)
    remove_perm("manage_club", agent.user, club)


def send_inviting_email(email: str, club: Club) -> None:
    send_email.delay(
        "Access to club granted",
        f"You have been granted access to {club.name}. Check it out at https://evidence.frisbee.cz\n",
        to=[email],
    )


def assign_or_invite_agent_to_club(
    email: str, club: Club, invited_by: User, is_primary: bool = False
) -> None:
    """
    Assign agent to club and invite him if he doesn't have an account in the app
    """
    if agent := Agent.objects.filter(user__email=email).first():
        if agent.user.has_perm("manage_club", club):
            return
        assign_agent_to_club(agent, club, invited_by, is_primary)
    else:
        NewAgentRequest.objects.create(
            email=email,
            is_staff=False,
            is_superuser=False,
            club=club,
            invited_by=invited_by,
            is_primary=is_primary,
        )

    send_inviting_email(email, club)


def unassign_or_cancel_agent_invite_from_club(email: str, club: Club) -> None:
    """
    Unassign agent from club or cancel pending invite
    """
    agent_at_club = AgentAtClub.objects.filter(agent__user__email=email, club=club).first()

    if agent_at_club:
        if agent_at_club.is_primary:
            raise ValueError("Cannot remove primary agent from club")
        if not agent_at_club.agent.user.has_perm("manage_club", club):
            raise ValueError("Cannot remove already removed agent from club")
        unassign_agent_from_club(agent_at_club.agent, club)
    else:
        NewAgentRequest.objects.filter(email=email, club=club, processed_at__isnull=True).delete()

    send_email.delay(
        "Access to club revoked",
        f"Your access to {club.name} has been revoked",
        to=[email],
    )


def get_user_managed_clubs(user: User) -> QuerySet[Club]:
    """
    Get all clubs that the user has manage_club permission for
    """
    return (
        get_objects_for_user(user, "clubs.manage_club", klass=Club)
        if user.is_authenticated
        else Club.objects.none()
    )
