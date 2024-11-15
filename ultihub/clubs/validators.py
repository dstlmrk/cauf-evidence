import re
from datetime import datetime

from django.core.exceptions import ValidationError


def _validate_cz_identification_number_checksum(value: str) -> bool:
    weights = [8, 7, 6, 5, 4, 3, 2]
    checksum = sum(int(value[i]) * weights[i] for i in range(7))
    remainder = checksum % 11
    check_digit = (11 - remainder) % 10
    return check_digit == int(value[-1])


def validate_identification_number(value: str) -> None:
    if not value.isdigit():
        raise ValidationError("Identification number must contain only digits.")
    if len(value) != 8:
        raise ValidationError("Identification number must have exactly 8 digits.")
    if not _validate_cz_identification_number_checksum(value):
        raise ValidationError("Identification number has invalid checksum.")


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

        current_year = datetime.now().year % 100
        century = 1900 if year > current_year or len(value_cleaned) == 9 else 2000

        datetime(century + year, month, day)

    except ValueError as ex:
        raise ValidationError("Invalid birth number.") from ex

    if len(value_cleaned) == 10 and int(value_cleaned) % 11 != 0:
        raise ValidationError("Birth number is not divisible by 11.")
