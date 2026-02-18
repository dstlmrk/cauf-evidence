from unittest.mock import patch

import dns.resolver
import pytest
from django.core.exceptions import ValidationError

from core.validators import validate_email_domain_typos, validate_email_mx_record


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


class TestValidateEmailMxRecord:
    @patch("core.validators.dns.resolver.resolve")
    def test_valid_domain_passes(self, mock_resolve):
        mock_resolve.return_value = ["mx.example.com"]
        validate_email_mx_record("user@example.com")
        mock_resolve.assert_called_once_with("example.com", "MX")

    @patch("core.validators.dns.resolver.resolve", side_effect=dns.resolver.NXDOMAIN)
    def test_nxdomain_raises_validation_error(self, mock_resolve):
        with pytest.raises(ValidationError, match="does not accept emails"):
            validate_email_mx_record("user@nonexistent-domain.xyz")

    @patch("core.validators.dns.resolver.resolve", side_effect=dns.resolver.NoAnswer)
    def test_no_answer_raises_validation_error(self, mock_resolve):
        with pytest.raises(ValidationError, match="does not accept emails"):
            validate_email_mx_record("user@no-mx.example.com")

    @patch("core.validators.dns.resolver.resolve", side_effect=dns.resolver.NoNameservers)
    def test_no_nameservers_raises_validation_error(self, mock_resolve):
        with pytest.raises(ValidationError, match="does not accept emails"):
            validate_email_mx_record("user@broken-ns.example.com")

    @patch(
        "core.validators.dns.resolver.resolve",
        side_effect=dns.resolver.LifetimeTimeout,
    )
    def test_timeout_raises_validation_error(self, mock_resolve):
        with pytest.raises(ValidationError, match="does not accept emails"):
            validate_email_mx_record("user@slow-domain.example.com")

    @patch("core.validators.dns.resolver.resolve", side_effect=OSError("Network error"))
    def test_unexpected_exception_passes_silently(self, mock_resolve):
        validate_email_mx_record("user@example.com")
