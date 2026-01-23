import pytest
from django.core.exceptions import ValidationError

from core.validators import validate_email_domain_typos


class TestValidateEmailDomainTypos:
    @pytest.mark.parametrize(
        "email,expected_suggestion",
        [
            ("user@gmail.cz", "@gmail.com"),
            ("user@gmai.com", "@gmail.com"),
            ("user@gmial.com", "@gmail.com"),
            ("user@gmail.con", "@gmail.com"),
            ("user@gmail.co", "@gmail.com"),
            ("user@gmail.comm", "@gmail.com"),
            ("user@seznam.co", "@seznam.cz"),
            ("user@seznma.cz", "@seznam.cz"),
            ("user@seznam.c", "@seznam.cz"),
            ("user@sezman.cz", "@seznam.cz"),
            ("user@sznam.cz", "@seznam.cz"),
        ],
    )
    def test_raises_validation_error_for_typo(self, email, expected_suggestion):
        with pytest.raises(ValidationError) as exc_info:
            validate_email_domain_typos(email)
        assert expected_suggestion in str(exc_info.value.message)

    @pytest.mark.parametrize(
        "email",
        [
            "user@gmail.com",
            "user@seznam.cz",
            "user@outlook.com",
            "user@email.cz",
            "user@company.org",
        ],
    )
    def test_valid_email_passes(self, email):
        validate_email_domain_typos(email)

    @pytest.mark.parametrize(
        "email",
        [
            "user@Gmail.Cz",
            "user@GMAIL.CZ",
            "user@Gmai.COM",
            "user@SEZNAM.CO",
        ],
    )
    def test_case_insensitive_matching(self, email):
        with pytest.raises(ValidationError):
            validate_email_domain_typos(email)
