import logging
import re

import dns.resolver
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

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


def validate_email_mx_record(value: str) -> None:
    domain = value.rsplit("@", 1)[-1]
    try:
        dns.resolver.resolve(domain, "MX")
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        raise ValidationError(
            f"Email domain '{domain}' does not accept emails.",
            code="invalid_mx_record",
        ) from None
    except dns.resolver.LifetimeTimeout:
        raise ValidationError(
            f"Email domain '{domain}' does not accept emails.",
            code="invalid_mx_record",
        ) from None
    except Exception:
        logger.warning("MX record check failed for domain '%s', skipping validation", domain)


def validate_email_domain_typos(value: str) -> None:
    for pattern, correct in COMMON_EMAIL_TYPOS.items():
        if re.search(pattern, value, re.IGNORECASE):
            raise ValidationError(
                f"Invalid email domain. Maybe you meant: {correct}",
                code="email_typo_detected",
            )
