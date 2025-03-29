import logging

from django.core.mail import EmailMessage
from huey.contrib.djhuey import task

from ultihub.settings import ENVIRONMENT

logger = logging.getLogger(__name__)


@task()
def send_email(subject: str, body: str, to: list[str], csv_data: str | None = None) -> None:
    if ENVIRONMENT in ["prod"]:
        logger.info("Sending email to %s", to)
        email = EmailMessage(subject=subject, body=body, to=to)
        email.content_subtype = "html"
        if csv_data:
            email.attach("data.csv", csv_data, "text/csv")
        email.send()
        logger.info("Email sent to %s", to)
    else:
        logger.warning("Email to %s not sent due to environment", to)
