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
