import re
from datetime import datetime

from django.core.exceptions import ValidationError
from django.utils import timezone


def validate_czech_birth_number(value: str) -> None:
    value_cleaned = value.replace("/", "")

    if len(value_cleaned) not in [9, 10]:
        raise ValidationError("Birth number must have 9 or 10 digits.")

    if not re.match(r"^\d{6}/?\d{3,4}$", value):
        raise ValidationError("Invalid birth number format.")

    try:
        year = int(value_cleaned[:2])
        month = int(value_cleaned[2:4])
        day = int(value_cleaned[4:6])

        if month > 50:
            month -= 50

        if month > 70:
            month -= 70

        current_year = timezone.now().year % 100
        century = 1900 if year > current_year or len(value_cleaned) == 9 else 2000

        datetime(century + year, month, day)

    except ValueError as ex:
        raise ValidationError("Invalid birth number.") from ex

    if len(value_cleaned) == 10 and int(value_cleaned) % 11 != 0:
        raise ValidationError("Birth number is not divisible by 11.")


def validate_postal_code(value: str) -> None:
    if not value.isdigit() or len(value) != 5:
        raise ValidationError("Invalid postal code format.")
