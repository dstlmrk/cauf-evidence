from allauth.account.signals import user_logged_in
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.http import HttpRequest
from django.utils import timezone

from users.models import Agent, NewAgentRequest


@receiver(user_logged_in)
def check_allowed_user(sender: type, request: HttpRequest, user: User, **kwargs: dict) -> None:
    social_account = SocialAccount.objects.get(user=user, provider="google")
    google_picture = social_account.extra_data.get("picture")
    try:
        if user.agent.picture_url != google_picture:
            user.agent.picture_url = google_picture
            user.agent.save()
    except Agent.DoesNotExist:
        new_agent_request = NewAgentRequest.objects.filter(
            email=user.email, processed_at=None
        ).get()
        user.agent = Agent.objects.create(user=user, picture_url=google_picture)
        user.is_staff = new_agent_request.is_staff
        user.is_superuser = new_agent_request.is_superuser
        user.save()
        new_agent_request.processed_at = timezone.now()
        new_agent_request.save()

    # TODO: remove later
    request.session["club_id"] = 1
