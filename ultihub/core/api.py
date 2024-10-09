from django.core.mail import EmailMessage

from ultihub.settings import ENVIRONMENT


def send_email(subject: str, body: str, to: list[str]) -> None:
    if ENVIRONMENT == "prod":
        EmailMessage(subject=subject, body=body, to=to).send()
