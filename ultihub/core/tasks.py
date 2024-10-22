import logging

from django.core.mail import EmailMessage
from django_rq import job

from ultihub.settings import ENVIRONMENT

logger = logging.getLogger(__name__)


@job
def send_email(subject: str, body: str, to: list[str]) -> None:
    if ENVIRONMENT in ["prod", "dev"]:
        logger.info("Sending email to %s", to)
        EmailMessage(subject=subject, body=body, to=to).send()
        logger.info("Email sent to %s", to)
    else:
        logger.warning("Email to %s not sent due to environment", to)
