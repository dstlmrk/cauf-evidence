from typing import Any

from django.db import models

from core.validators import validate_email_domain_typos


class ValidatedEmailField(models.EmailField):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        orig_validators = kwargs.pop("validators", [])
        validators = list(orig_validators)

        if validate_email_domain_typos not in validators:
            validators.append(validate_email_domain_typos)

        kwargs["validators"] = validators
        super().__init__(*args, **kwargs)
