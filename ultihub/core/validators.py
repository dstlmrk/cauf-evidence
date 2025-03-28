import re

from django.core.exceptions import ValidationError

COMMON_EMAIL_TYPOS = {
    r"@gmail\.cz$": "@gmail.com",
    r"@gmai\.com$": "@gmail.com",
    r"@gmial\.com$": "@gmail.com",
    r"@gmail\.con$": "@gmail.com",
    r"@gmail\.co$": "@gmail.com",
    r"@gmail\.comm$": "@gmail.com",
    r"@seznam\.co$": "@seznam.cz",
    r"@seznma\.cz$": "@seznam.cz",
    r"@seznam\.c$": "@seznam.cz",
    r"@sezman\.cz$": "@seznam.cz",
    r"@sznam\.cz$": "@seznam.cz",
}


def validate_email_domain_typos(value: str) -> None:
    for pattern, correct in COMMON_EMAIL_TYPOS.items():
        if re.search(pattern, value, re.IGNORECASE):
            raise ValidationError(
                f"Invalid email domain. Maybe you meant: {correct}",
                code="email_typo_detected",
            )
