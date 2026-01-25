import logging

from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialLogin
from django.contrib import messages
from django.http import HttpRequest
from django.shortcuts import redirect
from django.utils.translation import gettext as _

from users.models import Agent, NewAgentRequest

logger = logging.getLogger(__name__)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request: HttpRequest, sociallogin: SocialLogin) -> None:
        google_email = sociallogin.account.extra_data.get("email").lower()
        try:
            Agent.objects.filter(user__email=google_email, user__is_active=True).get()
            logger.info("User %s has logged in", google_email)
        except Agent.DoesNotExist:
            try:
                NewAgentRequest.objects.filter(email=google_email, processed_at=None).get()
                logger.info("User %s is invited to be agent and has logged in", google_email)
            except NewAgentRequest.DoesNotExist:
                logger.info("User %s is not allowed to log in", google_email)
                messages.error(request, _("Your email is not allowed to log in"))
                raise ImmediateHttpResponse(redirect("home")) from None
