from unittest.mock import patch

from django.conf import settings
from members.helpers import notify_monitored_citizenship

from tests.factories import MemberFactory


@patch("members.helpers.send_email")
def test_notification_sent_for_russian_member(mock_send_email):
    """Test that notification is sent for member with Russian citizenship"""
    member = MemberFactory(citizenship="RU")
    notify_monitored_citizenship(member)

    assert mock_send_email.called
    assert mock_send_email.call_count == 1

    notification_call = mock_send_email.call_args_list[0]
    subject = notification_call[1]["subject"]
    body = notification_call[1]["body"]
    to = notification_call[1]["to"]

    assert "Notifikace" in subject
    assert "Objevil se hráč" in subject
    assert member.club.name in body
    assert member.first_name in body
    assert member.last_name in body
    assert member.birth_date.strftime("%d.%m.%Y") in body
    assert to == [settings.MEMBER_NOTIFICATION_EMAIL]


@patch("members.helpers.send_email")
def test_notification_sent_for_belarusian_member(mock_send_email):
    """Test that notification is sent for member with Belarusian citizenship"""
    member = MemberFactory(citizenship="BY")
    notify_monitored_citizenship(member)

    assert mock_send_email.called
    assert mock_send_email.call_count == 1

    notification_call = mock_send_email.call_args_list[0]
    subject = notification_call[1]["subject"]
    to = notification_call[1]["to"]

    assert "Notifikace" in subject
    assert "Objevil se hráč" in subject
    assert to == [settings.MEMBER_NOTIFICATION_EMAIL]


@patch("members.helpers.send_email")
def test_no_notification_for_czech_member(mock_send_email):
    """Test that no notification is sent for member with Czech citizenship"""
    member = MemberFactory(citizenship="CZ")
    notify_monitored_citizenship(member)

    assert not mock_send_email.called, "No notification should be sent for Czech members"


@patch("members.helpers.send_email")
def test_no_notification_for_other_citizenship(mock_send_email):
    """Test that no notification is sent for members with other citizenships"""
    member = MemberFactory(citizenship="US")
    notify_monitored_citizenship(member)

    assert not mock_send_email.called, "No notification should be sent for other citizenships"


@patch("members.helpers.send_email")
def test_notification_contains_all_required_fields(mock_send_email):
    """Test that notification email contains all required information"""
    member = MemberFactory(citizenship="RU", first_name="Ivan", last_name="Petrov")
    notify_monitored_citizenship(member)

    notification_call = mock_send_email.call_args_list[0]
    body = notification_call[1]["body"]

    # Check all required fields are present
    assert member.club.name in body, "Club name should be in notification"
    assert "Ivan" in body, "First name should be in notification"
    assert "Petrov" in body, "Last name should be in notification"
    assert member.birth_date.strftime("%d.%m.%Y") in body, "Birth date should be in notification"
