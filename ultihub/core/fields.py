from typing import Any

from django.db import models

from core.validators import validate_email_domain_typos, validate_email_mx_record


class ValidatedEmailField(models.EmailField):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        orig_validators = kwargs.pop("validators", [])
        validators = list(orig_validators)

        if validate_email_domain_typos not in validators:
            validators.append(validate_email_domain_typos)
        if validate_email_mx_record not in validators:
            validators.append(validate_email_mx_record)

        kwargs["validators"] = validators
        super().__init__(*args, **kwargs)
