from clubs.models import Club
from core.api import send_email
from django.contrib.auth.models import User
from django.db.models import QuerySet
from guardian.shortcuts import assign_perm, get_objects_for_user, remove_perm

from users.models import Agent, NewAgentRequest


def assign_agent_to_club(agent: Agent, club: Club) -> None:
    """
    Assign permission to agent to manage club
    """
    assign_perm("manage_club", agent.user, club)


def unassign_agent_from_club(agent: Agent, club: Club) -> None:
    """
    Remove permission from agent to manage club
    """
    remove_perm("manage_club", agent.user, club)


def assign_or_invite_agent_to_club(email: str, club: Club) -> None:
    """
    Assign agent to club and invite him if he doesn't have an account in the app
    """
    if agent := Agent.objects.filter(user__email=email).first():
        if agent.user.has_perm("manage_club", club):
            return
        assign_agent_to_club(agent, club)
    else:
        NewAgentRequest.objects.create(email=email, is_staff=False, is_superuser=False, club=club)
    # TODO: send email via dramatiq
    send_email("Access to club granted", f"You have been granted access to {club.name}", [email])


def unassign_or_cancel_agent_invite_from_club(email: str, club: Club) -> None:
    """
    Unassign agent from club or cancel pending invite
    """
    if agent := Agent.objects.filter(user__email=email).first():
        if not agent.user.has_perm("manage_club", club):
            return
        unassign_agent_from_club(agent, club)
    else:
        NewAgentRequest.objects.filter(email=email, club=club, processed_at__isnull=True).delete()
    # TODO: send email via dramatiq
    send_email("Access to club revoked", f"Your access to {club.name} has been revoked", [email])


def get_user_managed_clubs(user: User) -> QuerySet[Club]:
    """
    Get all clubs that the user has manage_club permission for
    """
    return (
        get_objects_for_user(user, "clubs.manage_club", klass=Club)
        if user.is_authenticated
        else Club.objects.none()
    )
