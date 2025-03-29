import logging

from django.core.mail import EmailMessage
from django.core.management import call_command
from huey import crontab
from huey.contrib.djhuey import db_periodic_task, task

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
