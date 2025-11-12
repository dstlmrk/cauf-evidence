from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from competitions.models import ApplicationStateEnum, CompetitionFeeTypeEnum
from django.utils import timezone
from finance.models import Invoice, InvoiceStateEnum, InvoiceTypeEnum
from finance.services import create_invoice
from finance.tasks import (
    calculate_season_fees_and_generate_invoices,
    check_fakturoid_invoices,
    resend_invoices_to_fakturoid,
)

from tests.factories import (
    AgentAtClubFactory,
    AgentFactory,
    ClubFactory,
    InvoiceFactory,
    MemberAtTournamentFactory,
    SeasonFactory,
)
from tests.helpers import create_complete_competition


@pytest.mark.parametrize("club__fakturoid_subject_id", [999])
def test_command_resend_invoices_to_fakturoid_should_work_properly(club):
    invoice = InvoiceFactory(club=club)
    invoice.created_at = timezone.now() - timedelta(seconds=65)
    invoice.save()

    assert invoice.state == InvoiceStateEnum.DRAFT
    resend_invoices_to_fakturoid()
    invoice.refresh_from_db()
    assert invoice.state == InvoiceStateEnum.OPEN
    assert invoice.fakturoid_status == "open"


@pytest.mark.parametrize("club__fakturoid_subject_id", [999])
def test_command_resend_invoices_to_fakturoid_should_not_resend_invoices_younger_than_60_seconds(
    club,
):
    invoice = InvoiceFactory(club=club)
    invoice.created_at = timezone.now() - timedelta(seconds=55)
    invoice.save()

    assert invoice.state == InvoiceStateEnum.DRAFT
    resend_invoices_to_fakturoid()
    invoice.refresh_from_db()
    assert invoice.state == InvoiceStateEnum.DRAFT
    assert invoice.fakturoid_status == ""


@pytest.mark.parametrize(
    "status,expected_invoice_state,expected_application_state",
    [
        ("open", InvoiceStateEnum.OPEN, ApplicationStateEnum.AWAITING_PAYMENT),
        ("paid", InvoiceStateEnum.PAID, ApplicationStateEnum.PAID),
        ("cancelled", InvoiceStateEnum.CANCELED, ApplicationStateEnum.AWAITING_PAYMENT),
        ("uncollectible", InvoiceStateEnum.CANCELED, ApplicationStateEnum.AWAITING_PAYMENT),
    ],
)
@pytest.mark.parametrize("club__fakturoid_subject_id", [999])
@pytest.mark.parametrize("competition_application__state", [ApplicationStateEnum.AWAITING_PAYMENT])
def test_command_check_invoices_in_fakturoid_should_work_properly(
    status, expected_invoice_state, expected_application_state, club, competition_application
):
    invoice = create_invoice(
        club, InvoiceTypeEnum.COMPETITION_DEPOSIT, [("", 100)], [competition_application]
    )
    invoice.state = InvoiceStateEnum.OPEN
    invoice.fakturoid_status = "open"
    invoice.save()

    with patch(
        "finance.clients.fakturoid.fakturoid_client.get_invoice_status_and_total"
    ) as mock_get_invoice_status_and_total:
        mock_get_invoice_status_and_total.return_value = status, Decimal("100.1")
        check_fakturoid_invoices()
        invoice.refresh_from_db()
        assert invoice.state == expected_invoice_state
        assert invoice.fakturoid_status == status
        assert invoice.fakturoid_total == Decimal("100.1")

    competition_application.refresh_from_db()
    assert competition_application.state == expected_application_state


@patch("finance.services.fakturoid_client.create_invoice")
@patch("finance.tasks.notify_club")
def test_calculate_season_fees_and_generate_invoices_happy_path(
    mock_notify_club, mock_fakturoid_create
):
    """Test basic scenario with multiple clubs having fees"""
    # Mock Fakturoid API - return different IDs for each call
    invoice_counter = {"count": 0}

    def mock_create_invoice_response(*args, **kwargs):
        invoice_counter["count"] += 1
        return {
            "invoice_id": invoice_counter["count"],
            "total": Decimal("100"),
            "status": "open",
            "public_html_url": f"http://example.com/{invoice_counter['count']}",
        }

    mock_fakturoid_create.side_effect = mock_create_invoice_response

    season = SeasonFactory(regular_fee=Decimal("100"), discounted_fee=Decimal("50"))

    # Create 3 clubs with fakturoid_subject_id
    club1 = ClubFactory(fakturoid_subject_id=100)
    club2 = ClubFactory(fakturoid_subject_id=200)
    club3 = ClubFactory(fakturoid_subject_id=300)

    # Club 1: Regular tournament (100 CZK)
    regular_competition = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.REGULAR,
    )
    MemberAtTournamentFactory(
        tournament=regular_competition["tournament"],
        team_at_tournament=regular_competition["team_at_tournament"],
        member__club=club1,
    )

    # Club 2: Discounted tournament (50 CZK)
    discounted_competition = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.DISCOUNTED,
    )
    MemberAtTournamentFactory(
        tournament=discounted_competition["tournament"],
        team_at_tournament=discounted_competition["team_at_tournament"],
        member__club=club2,
    )

    # Club 3: Two members with regular fees (200 CZK total)
    MemberAtTournamentFactory(
        tournament=regular_competition["tournament"],
        team_at_tournament=regular_competition["team_at_tournament"],
        member__club=club3,
    )
    MemberAtTournamentFactory(
        tournament=regular_competition["tournament"],
        team_at_tournament=regular_competition["team_at_tournament"],
        member__club=club3,
    )

    # Run the task
    calculate_season_fees_and_generate_invoices(season)

    # Verify invoices were created
    assert Invoice.objects.count() == 3

    # Verify season was marked as invoices generated
    season.refresh_from_db()
    assert season.invoices_generated_at is not None

    # Verify notifications were sent to all 3 clubs
    assert mock_notify_club.call_count == 3


@patch("finance.services.fakturoid_client.create_invoice")
@patch("finance.tasks.notify_club")
@patch("finance.tasks.logger")
def test_calculate_season_fees_and_generate_invoices_duplicate_execution_protection(
    mock_logger, mock_notify_club, mock_fakturoid_create
):
    """Test that running the task twice doesn't create duplicate invoices"""
    mock_fakturoid_create.return_value = {
        "invoice_id": 1,
        "total": Decimal("100"),
        "status": "open",
        "public_html_url": "http://example.com/1",
    }

    season = SeasonFactory(regular_fee=Decimal("100"))
    club = ClubFactory(fakturoid_subject_id=100)

    regular_competition = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.REGULAR,
    )
    MemberAtTournamentFactory(
        tournament=regular_competition["tournament"],
        team_at_tournament=regular_competition["team_at_tournament"],
        member__club=club,
    )

    # First execution - should create invoice
    calculate_season_fees_and_generate_invoices(season)

    assert Invoice.objects.count() == 1
    assert mock_notify_club.call_count == 1

    season.refresh_from_db()
    first_invoices_generated_at = season.invoices_generated_at
    assert first_invoices_generated_at is not None

    # Second execution - should skip and log warning
    calculate_season_fees_and_generate_invoices(season)

    # No new invoices created
    assert Invoice.objects.count() == 1
    # No new notifications sent
    assert mock_notify_club.call_count == 1

    # Season timestamp unchanged
    season.refresh_from_db()
    assert season.invoices_generated_at == first_invoices_generated_at

    # Warning was logged
    mock_logger.warning.assert_called_once()
    warning_message = mock_logger.warning.call_args[0][0]
    assert "already generated" in warning_message
    assert season.name in warning_message


@patch("finance.services.fakturoid_client.create_invoice")
@patch("finance.tasks.notify_club")
@patch("finance.tasks.logger")
def test_calculate_season_fees_and_generate_invoices_partial_failure_recovery(
    mock_logger, mock_notify_club, mock_fakturoid_create
):
    """
    Test idempotent invoice creation when task partially failed before.
    Simulates a scenario where some invoices were created but the task didn't complete.
    """
    # Mock Fakturoid to return different invoice IDs
    mock_fakturoid_create.side_effect = [
        {
            "invoice_id": 1,
            "total": Decimal("100"),
            "status": "open",
            "public_html_url": "http://example.com/1",
        },
        {
            "invoice_id": 2,
            "total": Decimal("100"),
            "status": "open",
            "public_html_url": "http://example.com/2",
        },
        {
            "invoice_id": 3,
            "total": Decimal("100"),
            "status": "open",
            "public_html_url": "http://example.com/3",
        },
    ]

    season = SeasonFactory(regular_fee=Decimal("100"))

    club1 = ClubFactory(fakturoid_subject_id=100)
    club2 = ClubFactory(fakturoid_subject_id=200)
    club3 = ClubFactory(fakturoid_subject_id=300)

    regular_competition = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.REGULAR,
    )

    # All three clubs have members with fees
    MemberAtTournamentFactory(
        tournament=regular_competition["tournament"],
        team_at_tournament=regular_competition["team_at_tournament"],
        member__club=club1,
    )
    MemberAtTournamentFactory(
        tournament=regular_competition["tournament"],
        team_at_tournament=regular_competition["team_at_tournament"],
        member__club=club2,
    )
    MemberAtTournamentFactory(
        tournament=regular_competition["tournament"],
        team_at_tournament=regular_competition["team_at_tournament"],
        member__club=club3,
    )

    # Simulate partial failure: invoices for club1 and club2 were already created
    # (e.g., previous run succeeded partially)
    create_invoice(
        club1,
        InvoiceTypeEnum.SEASON_PLAYER_FEES,
        [(f"Poplatky za sezónu {season.name}", Decimal("100"))],
        related_objects=[season],
    )
    create_invoice(
        club2,
        InvoiceTypeEnum.SEASON_PLAYER_FEES,
        [(f"Poplatky za sezónu {season.name}", Decimal("100"))],
        related_objects=[season],
    )

    assert Invoice.objects.count() == 2

    # Note: season.invoices_generated_at is still None (task didn't complete)
    assert season.invoices_generated_at is None

    # Run the task - should create only missing invoice for club3
    calculate_season_fees_and_generate_invoices(season)

    # Total 3 invoices (2 existing + 1 new)
    assert Invoice.objects.count() == 3

    # Verify all clubs have invoices
    assert Invoice.objects.filter(club=club1).count() == 1
    assert Invoice.objects.filter(club=club2).count() == 1
    assert Invoice.objects.filter(club=club3).count() == 1

    # Season now marked as complete
    season.refresh_from_db()
    assert season.invoices_generated_at is not None

    # Only 1 notification sent (for club3 which got new invoice)
    assert mock_notify_club.call_count == 1
    assert mock_notify_club.call_args[1]["club"] == club3

    # Logger should have info messages about skipping existing invoices
    info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
    skipped_messages = [msg for msg in info_calls if "already exists" in msg]
    assert len(skipped_messages) == 2  # club1 and club2 were skipped


@patch("finance.services.fakturoid_client.create_invoice")
@patch("finance.tasks.notify_club")
@patch("finance.tasks.logger")
def test_calculate_season_fees_and_generate_invoices_clubs_without_fees_and_without_fakturoid_id(
    mock_logger, mock_notify_club, mock_fakturoid_create
):
    """
    Test edge cases:
    - Club with fakturoid_subject_id but no fees (total_amount = 0)
    - Club without fakturoid_subject_id (should be skipped entirely)
    - Club with fees and fakturoid_subject_id (should get invoice)
    """
    mock_fakturoid_create.return_value = {
        "invoice_id": 1,
        "total": Decimal("100"),
        "status": "open",
        "public_html_url": "http://example.com/1",
    }

    season = SeasonFactory(regular_fee=Decimal("100"))

    # Club 1: Has fakturoid_subject_id and fees -> should get invoice
    club_with_fees = ClubFactory(fakturoid_subject_id=100)

    # Club 2: Has fakturoid_subject_id but no fees -> no invoice
    club_without_fees = ClubFactory(fakturoid_subject_id=200)

    # Club 3: Has fees but no fakturoid_subject_id -> skipped entirely
    club_without_fakturoid_id = ClubFactory(fakturoid_subject_id=None)

    regular_competition = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.REGULAR,
    )
    free_competition = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.FREE,
    )

    # Club 1: Regular tournament (has fees)
    MemberAtTournamentFactory(
        tournament=regular_competition["tournament"],
        team_at_tournament=regular_competition["team_at_tournament"],
        member__club=club_with_fees,
    )

    # Club 2: Only free tournament (no fees)
    MemberAtTournamentFactory(
        tournament=free_competition["tournament"],
        team_at_tournament=free_competition["team_at_tournament"],
        member__club=club_without_fees,
    )

    # Club 3: Regular tournament but no fakturoid_subject_id
    MemberAtTournamentFactory(
        tournament=regular_competition["tournament"],
        team_at_tournament=regular_competition["team_at_tournament"],
        member__club=club_without_fakturoid_id,
    )

    # Run the task
    calculate_season_fees_and_generate_invoices(season)

    # Only 1 invoice created (for club_with_fees)
    assert Invoice.objects.count() == 1
    assert Invoice.objects.filter(club=club_with_fees).exists()
    assert not Invoice.objects.filter(club=club_without_fees).exists()
    assert not Invoice.objects.filter(club=club_without_fakturoid_id).exists()

    # Only 1 notification sent
    assert mock_notify_club.call_count == 1
    assert mock_notify_club.call_args[1]["club"] == club_with_fees

    # Season marked as complete
    season.refresh_from_db()
    assert season.invoices_generated_at is not None

    # Logger should have info about club_without_fees being skipped (total = 0)
    info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
    no_fees_messages = [
        msg for msg in info_calls if "has no fees" in msg and club_without_fees.name in msg
    ]
    assert len(no_fees_messages) == 1


@patch("finance.tasks.notify_club")
def test_calculate_season_fees_and_generate_invoices_no_clubs_with_fees(mock_notify_club):
    """Test that task completes successfully when no clubs have fees"""
    season = SeasonFactory()

    # Create clubs but don't add any members to tournaments
    ClubFactory(fakturoid_subject_id=100)
    ClubFactory(fakturoid_subject_id=200)

    # Run the task
    calculate_season_fees_and_generate_invoices(season)

    # No invoices created
    assert Invoice.objects.count() == 0

    # No notifications sent
    assert mock_notify_club.call_count == 0

    # Season still marked as complete
    season.refresh_from_db()
    assert season.invoices_generated_at is not None


@patch("finance.services.fakturoid_client.create_invoice")
@patch("clubs.service.send_email")
def test_calculate_season_fees_and_generate_invoices_notifications_and_emails(
    mock_send_email, mock_fakturoid_create
):
    """Test that notifications are created and emails are sent correctly"""
    from clubs.models import ClubNotification

    mock_fakturoid_create.return_value = {
        "invoice_id": 1,
        "total": Decimal("100"),
        "status": "open",
        "public_html_url": "http://example.com/1",
    }

    season = SeasonFactory(regular_fee=Decimal("100"))
    club = ClubFactory(fakturoid_subject_id=100)

    # Create 3 agents for this club
    # Agent 1: Active, email notifications enabled
    agent1 = AgentFactory(has_email_notifications_enabled=True)
    agent_at_club1 = AgentAtClubFactory(club=club, agent=agent1, is_active=True)

    # Agent 2: Active, email notifications disabled
    agent2 = AgentFactory(has_email_notifications_enabled=False)
    agent_at_club2 = AgentAtClubFactory(club=club, agent=agent2, is_active=True)

    # Agent 3: Inactive, email notifications enabled (should not receive anything)
    agent3 = AgentFactory(has_email_notifications_enabled=True)
    agent_at_club3 = AgentAtClubFactory(club=club, agent=agent3, is_active=False)

    regular_competition = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.REGULAR,
    )
    MemberAtTournamentFactory(
        tournament=regular_competition["tournament"],
        team_at_tournament=regular_competition["team_at_tournament"],
        member__club=club,
    )

    # Run the task
    calculate_season_fees_and_generate_invoices(season)

    # Verify ClubNotifications were created for active agents only
    notifications = ClubNotification.objects.filter(agent_at_club__club=club)
    assert notifications.count() == 2  # agent1 and agent2 (both active)

    # Verify notification content
    notification1 = ClubNotification.objects.get(agent_at_club=agent_at_club1)
    assert notification1.subject == "Season fees generated"
    assert season.name in notification1.message
    assert "have been generated" in notification1.message

    notification2 = ClubNotification.objects.get(agent_at_club=agent_at_club2)
    assert notification2.subject == "Season fees generated"

    # Verify no notification for inactive agent
    assert not ClubNotification.objects.filter(agent_at_club=agent_at_club3).exists()

    # Verify emails were sent only to agent1 (has_email_notifications_enabled=True)
    assert mock_send_email.call_count == 1
    email_call = mock_send_email.call_args

    assert email_call[0][0] == "Season fees generated"  # subject
    assert season.name in email_call[0][1]  # message contains season name
    assert email_call[1]["to"] == [agent1.user.email]  # sent to correct email


@patch("finance.tasks.send_email")
@patch("finance.tasks.notify_club")
def test_calculate_season_fees_dry_run_does_not_create_invoices_or_notifications(
    mock_notify_club, mock_send_email
):
    """Test that dry-run does not create invoices, notifications, or modify season"""
    season = SeasonFactory(regular_fee=Decimal("100"), discounted_fee=Decimal("50"))
    user = AgentFactory().user

    # Create clubs with different scenarios
    club1 = ClubFactory(fakturoid_subject_id=100, name="Club With Fakturoid")
    club2 = ClubFactory(fakturoid_subject_id=200, name="Club Two")
    club3 = ClubFactory(fakturoid_subject_id=None, name="Club Without Fakturoid")

    # Club 1: Regular tournament (100 CZK)
    regular_competition = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.REGULAR,
    )
    MemberAtTournamentFactory(
        tournament=regular_competition["tournament"],
        team_at_tournament=regular_competition["team_at_tournament"],
        member__club=club1,
    )

    # Club 2: Discounted tournament (50 CZK)
    discounted_competition = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.DISCOUNTED,
    )
    MemberAtTournamentFactory(
        tournament=discounted_competition["tournament"],
        team_at_tournament=discounted_competition["team_at_tournament"],
        member__club=club2,
    )

    # Club 3: Regular tournament but no fakturoid_subject_id
    MemberAtTournamentFactory(
        tournament=regular_competition["tournament"],
        team_at_tournament=regular_competition["team_at_tournament"],
        member__club=club3,
    )

    # Run dry-run
    calculate_season_fees_and_generate_invoices(season=season, dry_run=True, dry_run_user=user)

    # Verify NO invoices were created
    assert Invoice.objects.count() == 0

    # Verify season was NOT marked as invoices generated
    season.refresh_from_db()
    assert season.invoices_generated_at is None

    # Verify NO club notifications were sent
    assert mock_notify_club.call_count == 0

    # Verify email was sent to the admin user
    assert mock_send_email.call_count == 1
    email_call = mock_send_email.call_args

    # Check email subject
    assert f"Preview generování faktur - {season.name}" in email_call[1]["subject"]

    # Check email recipient
    assert email_call[1]["to"] == [user.email]

    # Check email body contains expected information (plain text format)
    email_body = email_call[1]["body"]
    assert season.name in email_body
    assert "- Club With Fakturoid (ID:" in email_body
    assert "- Club Two (ID:" in email_body
    assert "100 CZK" in email_body  # Club 1 amount
    assert "50 CZK" in email_body  # Club 2 amount


@patch("finance.tasks.send_email")
def test_calculate_season_fees_dry_run_works_even_if_invoices_already_generated(mock_send_email):
    """Test that dry-run works even if invoices were already generated"""
    season = SeasonFactory(regular_fee=Decimal("100"))
    user = AgentFactory().user

    # Mark season as already having invoices generated
    season.invoices_generated_at = timezone.now()
    season.save()

    club = ClubFactory(fakturoid_subject_id=100)

    regular_competition = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.REGULAR,
    )
    MemberAtTournamentFactory(
        tournament=regular_competition["tournament"],
        team_at_tournament=regular_competition["team_at_tournament"],
        member__club=club,
    )

    # Run dry-run - should work despite invoices_generated_at being set
    calculate_season_fees_and_generate_invoices(season=season, dry_run=True, dry_run_user=user)

    # Email should still be sent
    assert mock_send_email.call_count == 1
