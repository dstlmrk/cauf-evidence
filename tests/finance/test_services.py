from unittest.mock import patch

import pytest
from competitions.models import CompetitionFeeTypeEnum, Season
from finance.clients.fakturoid import UnexpectedResponse
from finance.models import InvoiceRelatedObject, InvoiceStateEnum, InvoiceTypeEnum
from finance.services import (
    SeasonFeeData,
    calculate_season_fees,
    create_invoice,
    create_invoice_in_fakturoid_and_save_data,
)

from tests.factories import MemberAtTournamentFactory, SeasonFactory
from tests.helpers import create_complete_competition


@pytest.mark.parametrize("club__fakturoid_subject_id", [999])
def test_create_invoice(club, competition):
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
            related_objects=[competition],
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
def test_create_invoice_is_able_to_resend_invoice_to_fakturoid(club, competition):
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
            related_objects=[competition],
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
