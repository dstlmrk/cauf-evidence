import pytest
from django.core.exceptions import ValidationError

from tests.factories import MemberFactory


class TestMemberEmailNormalization:
    def test_email_is_normalized_to_lowercase_on_save(self):
        member = MemberFactory(email="Jan.Novak@Seznam.CZ")

        member.refresh_from_db()
        assert member.email == "jan.novak@seznam.cz"

    def test_legal_guardian_email_is_normalized_to_lowercase_on_save(self):
        member = MemberFactory(legal_guardian_email="Parent@Example.COM")

        member.refresh_from_db()
        assert member.legal_guardian_email == "parent@example.com"

    def test_empty_email_is_left_untouched_on_save(self):
        member = MemberFactory(email="", legal_guardian_email="")

        member.refresh_from_db()
        assert member.email == ""
        assert member.legal_guardian_email == ""


class TestMemberDuplicateEmailIsCaseInsensitive:
    def test_clean_detects_duplicate_email_ignoring_case(self):
        MemberFactory(citizenship="US", email="jan@example.com")
        duplicate = MemberFactory.build(citizenship="US", email="Jan@example.com")

        with pytest.raises(ValidationError) as exc_info:
            duplicate.clean()

        assert "email" in exc_info.value.message_dict
