from decimal import Decimal
from unittest.mock import patch

import pytest
from competitions.models import ApplicationStateEnum, CompetitionFeeTypeEnum, Season
from finance.clients.fakturoid import UnexpectedResponse
from finance.models import Invoice, InvoiceRelatedObject, InvoiceStateEnum, InvoiceTypeEnum
from finance.services import (
    SeasonFeeData,
    calculate_season_fees,
    create_deposit_invoice,
    create_invoice,
    create_invoice_in_fakturoid_and_save_data,
)

from tests.factories import (
    CompetitionApplicationFactory,
    CompetitionFactory,
    InternationalTournamentFactory,
    MemberAtInternationalTournamentFactory,
    MemberAtTournamentFactory,
    SeasonFactory,
    TeamAtInternationalTournamentFactory,
    TeamFactory,
)
from tests.helpers import create_complete_competition


@pytest.mark.parametrize("club__fakturoid_subject_id", [999])
def test_create_invoice(club, competition_application):
    with patch("finance.clients.fakturoid.fakturoid_client.create_invoice") as mock_create_invoice:
        mock_create_invoice.return_value = {
            "invoice_id": 1,
            "status": "open",
            "total": 200,
            "public_html_url": "https://example.com/invoice",
        }
        invoice = create_invoice(
            club=club,
            type_=InvoiceTypeEnum.COMPETITION_DEPOSIT,
            lines=(("First line", 100), ("Second line", 100)),
            related_objects=[competition_application],
        )

        assert invoice.club == club
        assert invoice.type == InvoiceTypeEnum.COMPETITION_DEPOSIT
        assert invoice.original_amount == 200
        assert invoice.lines == [
            {"name": "First line", "unit_price": "100.00"},
            {"name": "Second line", "unit_price": "100.00"},
        ]

        assert InvoiceRelatedObject.objects.filter(invoice=invoice).count() == 1

        assert invoice.fakturoid_invoice_id == 1
        assert invoice.fakturoid_total == 200
        assert invoice.fakturoid_status == "open"
        assert invoice.fakturoid_public_html_url == "https://example.com/invoice"
        assert invoice.state == InvoiceStateEnum.OPEN


@pytest.mark.parametrize("club__fakturoid_subject_id", [999])
def test_create_invoice_is_able_to_resend_invoice_to_fakturoid(club, competition_application):
    with patch("finance.clients.fakturoid.fakturoid_client.create_invoice") as mock_create_invoice:
        mock_create_invoice.side_effect = [
            UnexpectedResponse(),
            {
                "invoice_id": 1,
                "status": "open",
                "total": 200,
                "public_html_url": "https://example.com/invoice",
            },
        ]

        invoice = create_invoice(
            club=club,
            type_=InvoiceTypeEnum.COMPETITION_DEPOSIT,
            lines=(("First line", 100), ("Second line", 100)),
            related_objects=[competition_application],
        )

        assert invoice.club == club
        assert invoice.type == InvoiceTypeEnum.COMPETITION_DEPOSIT
        assert invoice.original_amount == 200
        assert invoice.lines == [
            {"name": "First line", "unit_price": "100.00"},
            {"name": "Second line", "unit_price": "100.00"},
        ]

        assert InvoiceRelatedObject.objects.filter(invoice=invoice).count() == 1

        assert invoice.state == InvoiceStateEnum.DRAFT
        assert invoice.fakturoid_invoice_id is None

        # the logic in the command resend_invoices_to_fakturoid
        create_invoice_in_fakturoid_and_save_data(invoice)

        assert invoice.fakturoid_invoice_id == 1
        assert invoice.fakturoid_total == 200
        assert invoice.fakturoid_status == "open"
        assert invoice.fakturoid_public_html_url == "https://example.com/invoice"
        assert invoice.state == InvoiceStateEnum.OPEN


def test_calculate_season_fees():
    season = SeasonFactory()

    free_complete_competition = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.FREE,
    )
    discounted_complete_competition = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.DISCOUNTED,
    )
    regular_complete_competition = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.REGULAR,
    )

    member_1 = MemberAtTournamentFactory(
        tournament=regular_complete_competition["tournament"],
        team_at_tournament=regular_complete_competition["team_at_tournament"],
    ).member
    member_2 = MemberAtTournamentFactory(
        tournament=discounted_complete_competition["tournament"],
        team_at_tournament=discounted_complete_competition["team_at_tournament"],
    ).member
    member_3 = MemberAtTournamentFactory(
        tournament=free_complete_competition["tournament"],
        team_at_tournament=free_complete_competition["team_at_tournament"],
    ).member

    results = calculate_season_fees(Season.objects.last())
    assert len(results) == 2
    assert results == {
        member_1: SeasonFeeData(
            season.regular_fee,
            [regular_complete_competition["tournament"]],
            [],
        ),
        member_2: SeasonFeeData(
            season.discounted_fee,
            [],
            [discounted_complete_competition["tournament"]],
        ),
    }

    MemberAtTournamentFactory(
        tournament=regular_complete_competition["tournament"],
        team_at_tournament=regular_complete_competition["team_at_tournament"],
        member=member_2,
    )
    MemberAtTournamentFactory(
        tournament=discounted_complete_competition["tournament"],
        team_at_tournament=discounted_complete_competition["team_at_tournament"],
        member=member_3,
    )

    results = calculate_season_fees(Season.objects.last())
    assert len(results) == 3
    assert results == {
        member_1: SeasonFeeData(
            season.regular_fee,
            [regular_complete_competition["tournament"]],
            [],
        ),
        member_2: SeasonFeeData(
            season.regular_fee,
            [regular_complete_competition["tournament"]],
            [discounted_complete_competition["tournament"]],
        ),
        member_3: SeasonFeeData(
            season.discounted_fee,
            [],
            [discounted_complete_competition["tournament"]],
        ),
    }

    # Test filter
    results = calculate_season_fees(Season.objects.last(), club_id=member_1.club.id)
    assert len(results) == 1
    assert results == {
        member_1: SeasonFeeData(
            season.regular_fee,
            [regular_complete_competition["tournament"]],
            [],
        )
    }


@pytest.mark.parametrize("club__fakturoid_subject_id", [999])
def test_create_deposit_invoice_with_zero_deposit(club):
    """Test that no invoice is created when all applications have deposit = 0"""
    competition = CompetitionFactory(deposit=Decimal("0"))
    team = TeamFactory(club=club)
    CompetitionApplicationFactory(
        competition=competition,
        team=team,
        state=ApplicationStateEnum.AWAITING_PAYMENT,
        invoice=None,
    )

    with patch("finance.clients.fakturoid.fakturoid_client.create_invoice"):
        result = create_deposit_invoice(club)

    assert result is False
    assert Invoice.objects.count() == 0


@pytest.mark.parametrize("club__fakturoid_subject_id", [999])
def test_create_deposit_invoice_with_positive_deposit(club):
    """Test that invoice is created when applications have deposit > 0"""
    competition = CompetitionFactory(deposit=Decimal("500"))
    team = TeamFactory(club=club)
    application = CompetitionApplicationFactory(
        competition=competition,
        team=team,
        state=ApplicationStateEnum.AWAITING_PAYMENT,
        invoice=None,
    )

    with patch("finance.clients.fakturoid.fakturoid_client.create_invoice") as mock_create_invoice:
        mock_create_invoice.return_value = {
            "invoice_id": 1,
            "status": "open",
            "total": 500,
            "public_html_url": "https://example.com/invoice",
        }
        result = create_deposit_invoice(club)

    assert result is True
    assert Invoice.objects.count() == 1
    invoice = Invoice.objects.first()
    assert invoice.original_amount == 500
    application.refresh_from_db()
    assert application.invoice == invoice


@pytest.mark.parametrize("club__fakturoid_subject_id", [999])
def test_create_deposit_invoice_with_mixed_deposits(club):
    """Test that only applications with deposit > 0 are included in invoice"""
    competition_with_deposit = CompetitionFactory(deposit=Decimal("500"))
    competition_without_deposit = CompetitionFactory(deposit=Decimal("0"))
    team = TeamFactory(club=club)

    app_with_deposit = CompetitionApplicationFactory(
        competition=competition_with_deposit,
        team=team,
        state=ApplicationStateEnum.AWAITING_PAYMENT,
        invoice=None,
    )
    app_without_deposit = CompetitionApplicationFactory(
        competition=competition_without_deposit,
        team=team,
        state=ApplicationStateEnum.AWAITING_PAYMENT,
        invoice=None,
    )

    with patch("finance.clients.fakturoid.fakturoid_client.create_invoice") as mock_create_invoice:
        mock_create_invoice.return_value = {
            "invoice_id": 1,
            "status": "open",
            "total": 500,
            "public_html_url": "https://example.com/invoice",
        }
        result = create_deposit_invoice(club)

    assert result is True
    assert Invoice.objects.count() == 1
    invoice = Invoice.objects.first()
    assert invoice.original_amount == 500

    app_with_deposit.refresh_from_db()
    app_without_deposit.refresh_from_db()

    # Application with deposit should have invoice
    assert app_with_deposit.invoice == invoice
    # Application without deposit should not have invoice
    assert app_without_deposit.invoice is None


def test_calculate_season_fees_with_international_tournaments():
    """Test that international tournaments are included in season fees calculation"""
    season = SeasonFactory()

    # Create domestic tournament
    regular_complete_competition = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.REGULAR,
    )

    # Create international tournaments with different fee types
    regular_international_tournament = InternationalTournamentFactory(
        season=season,
        fee_type=CompetitionFeeTypeEnum.REGULAR,
    )
    discounted_international_tournament = InternationalTournamentFactory(
        season=season,
        fee_type=CompetitionFeeTypeEnum.DISCOUNTED,
    )
    free_international_tournament = InternationalTournamentFactory(
        season=season,
        fee_type=CompetitionFeeTypeEnum.FREE,
    )

    # Create team participations for international tournaments
    regular_team_at_int_tournament = TeamAtInternationalTournamentFactory(
        tournament=regular_international_tournament
    )
    discounted_team_at_int_tournament = TeamAtInternationalTournamentFactory(
        tournament=discounted_international_tournament
    )
    free_team_at_int_tournament = TeamAtInternationalTournamentFactory(
        tournament=free_international_tournament
    )

    # Create members at domestic tournament
    member_1 = MemberAtTournamentFactory(
        tournament=regular_complete_competition["tournament"],
        team_at_tournament=regular_complete_competition["team_at_tournament"],
    ).member

    # Create members at international tournaments
    member_2 = MemberAtInternationalTournamentFactory(
        tournament=regular_international_tournament,
        team_at_tournament=regular_team_at_int_tournament,
    ).member
    member_3 = MemberAtInternationalTournamentFactory(
        tournament=discounted_international_tournament,
        team_at_tournament=discounted_team_at_int_tournament,
    ).member
    member_4 = MemberAtInternationalTournamentFactory(
        tournament=free_international_tournament,
        team_at_tournament=free_team_at_int_tournament,
    ).member

    # Calculate fees
    results = calculate_season_fees(season)

    # Should only include members with regular or discounted fees (not free)
    assert len(results) == 3

    # Member 1 played in domestic regular tournament
    assert member_1 in results
    assert results[member_1].amount == season.regular_fee
    assert regular_complete_competition["tournament"] in results[member_1].regular_tournaments
    assert len(results[member_1].discounted_tournaments) == 0

    # Member 2 played in international regular tournament
    assert member_2 in results
    assert results[member_2].amount == season.regular_fee
    assert regular_international_tournament in results[member_2].regular_tournaments
    assert len(results[member_2].discounted_tournaments) == 0

    # Member 3 played in international discounted tournament
    assert member_3 in results
    assert results[member_3].amount == season.discounted_fee
    assert len(results[member_3].regular_tournaments) == 0
    assert discounted_international_tournament in results[member_3].discounted_tournaments

    # Member 4 played in free tournament, should not be included
    assert member_4 not in results

    # Test that member playing in both domestic and international tournaments gets correct fee
    MemberAtInternationalTournamentFactory(
        tournament=discounted_international_tournament,
        team_at_tournament=discounted_team_at_int_tournament,
        member=member_1,
    )

    results = calculate_season_fees(season)
    assert len(results) == 3
    # Member 1 now has both regular (domestic) and discounted (international) tournaments
    # Should be charged regular fee (higher priority)
    assert results[member_1].amount == season.regular_fee
    assert regular_complete_competition["tournament"] in results[member_1].regular_tournaments
    assert discounted_international_tournament in results[member_1].discounted_tournaments
