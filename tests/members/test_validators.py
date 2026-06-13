from datetime import date

import pytest
from django.core.exceptions import ValidationError
from members.validators import (
    is_valid_birth_date_with_id,
    validate_czech_birth_number,
)


class TestValidateCzechBirthNumber:
    @pytest.mark.parametrize(
        "birth_number",
        [
            "9501150010",  # man, standard month (01)
            "9551150004",  # woman, +50 month (51)
            "9521150001",  # man, +20 month (21) - day sequence exhausted, since 2004
            "9571150006",  # woman, +70 month (71) - day sequence exhausted, since 2004
            "9532150001",  # man, +20 month (32 -> December)
        ],
    )
    def test_valid_birth_number_passes(self, birth_number):
        validate_czech_birth_number(birth_number)

    @pytest.mark.parametrize(
        "birth_number",
        [
            "9513150005",  # month 13 - out of range
            "9520150004",  # month 20 - between standard and +20 ranges
            "9533150003",  # month 33 - above +20 range
            "9550150005",  # month 50 - just below +50 range
            "9563150002",  # month 63 - above +50 range
            "9570150007",  # month 70 - just below +70 range
            "9583150001",  # month 83 - above +70 range
            "9500150009",  # month 00
        ],
    )
    def test_invalid_month_raises(self, birth_number):
        with pytest.raises(ValidationError):
            validate_czech_birth_number(birth_number)


class TestIsValidBirthDateWithId:
    @pytest.mark.parametrize(
        "birth_number,birth_date",
        [
            ("9501150010", date(1995, 1, 15)),  # man, standard month
            ("9551150004", date(1995, 1, 15)),  # woman, +50 month
            ("9521150001", date(1995, 1, 15)),  # man, +20 month
            ("9571150006", date(1995, 1, 15)),  # woman, +70 month
        ],
    )
    def test_matching_birth_date_returns_true(self, birth_number, birth_date):
        assert is_valid_birth_date_with_id(birth_date, birth_number) is True

    def test_mismatched_birth_date_returns_false(self):
        assert is_valid_birth_date_with_id(date(1995, 2, 15), "9521150001") is False
