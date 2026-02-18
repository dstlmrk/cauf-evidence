import logging
from typing import Any

from django.core.mail import EmailMessage
from django.core.management import call_command
from huey import crontab
from huey.contrib.djhuey import db_periodic_task, task

from ultihub.settings import ENVIRONMENT

logger = logging.getLogger(__name__)


class RetriableEmailError(Exception):
    """Raised when an email send fails but can be retried.

    Sentry ignores this exception — only the final failure (original exception)
    is reported.
    """


@task(retries=3, retry_delay=60, context=True)
def send_email(
    subject: str, body: str, to: list[str], csv_data: str | None = None, *, task: Any = None
) -> None:
    if ENVIRONMENT in ["prod"]:
        logger.info("Sending email to %s", to)
        email = EmailMessage(subject=subject, body=body, to=to)
        email.content_subtype = "html"
        if csv_data:
            email.attach("data.csv", csv_data, "text/csv")
        try:
            email.send()
        except Exception as exc:
            retries_left = task.retries if task else 0
            if retries_left > 0:
                logger.warning("Email to %s failed, %d retries remaining", to, retries_left)
                raise RetriableEmailError(
                    f"Email to {to} failed, {retries_left} retries remaining"
                ) from exc
            logger.exception("Email to %s failed after all retries", to)
            raise
        logger.info("Email sent to %s", to)
    else:
        logger.warning("Email to %s not sent due to environment", to)


@db_periodic_task(crontab(hour=3, minute=0))
def backup_database() -> None:
    """
    Periodic task to back up the database. It uploads the backup to Dropbox.
    It uses the `django-dbbackup` package.
    """
    if ENVIRONMENT == "prod":
        try:
            logger.info("Starting nightly dbbackup")
            call_command("dbbackup")
            logger.info("Backup done")
        except Exception as e:
            logger.exception("Backup failed: %s", e)
