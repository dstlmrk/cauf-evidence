import re
from datetime import date, datetime

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


def is_at_least_15(birth_date: date | str) -> bool:
    if isinstance(birth_date, str):
        birth_date = datetime.strptime(birth_date, "%Y-%m-%d").date()
    today = date.today()
    age = (
        today.year
        - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )
    return age >= 15


def is_valid_birth_date_with_id(birth_date: date, id_number: str) -> bool:
    try:
        id_cleaned = id_number.replace("/", "")
        id_year = int(id_cleaned[:2])
        id_month = int(id_cleaned[2:4])
        id_day = int(id_cleaned[4:6])

        if id_month > 50:
            id_month -= 50

        current_year = date.today().year % 100
        full_year = 1900 + id_year if id_year > current_year else 2000 + id_year

        return birth_date == date(full_year, id_month, id_day)
    except ValueError:
        return False
