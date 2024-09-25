from django.core.exceptions import ValidationError


def _validate_cz_identification_number_checksum(value: str) -> bool:
    weights = [8, 7, 6, 5, 4, 3, 2]
    checksum = sum(int(value[i]) * weights[i] for i in range(7))
    remainder = checksum % 11
    check_digit = (11 - remainder) % 10
    return check_digit == int(value[-1])


def _validate_cz_account_number(number: str) -> bool:
    weight = [6, 3, 7, 9, 10, 5, 8, 4, 2, 1]
    number = number.zfill(10)
    checksum = sum(int(digit) * weight[i] for i, digit in enumerate(number))
    return checksum % 11 == 0


def validate_identification_number(value: str) -> None:
    if not value.isdigit():
        raise ValidationError("Identification number must contain only digits.")
    if len(value) != 8:
        raise ValidationError("Identification number must have exactly 8 digits.")
    if not _validate_cz_identification_number_checksum(value):
        raise ValidationError("Identification number has invalid checksum.")


def validate_account_number(value: str) -> None:
    parts = value.split("-")
    if len(parts) == 2:
        prefix, number = parts
    elif len(parts) == 1:
        prefix = ""
        number = parts[0]
    else:
        raise ValidationError("Account number has invalid format.")
    if prefix and (not prefix.isdigit() or len(prefix) > 6):
        raise ValidationError("Prefix must be empty or contain up to 6 digits.")
    if not number.isdigit() or not (2 <= len(number) <= 10):
        raise ValidationError("Account number must contain 2 to 10 digits.")
    if not _validate_cz_account_number(number):
        raise ValidationError("Account number has invalid checksum.")


def validate_bank_code(value: str) -> None:
    if not value.isdigit():
        raise ValidationError("Bank code must contain only digits.")
    if len(value) != 4:
        raise ValidationError("Bank code must have exactly 4 digits.")
