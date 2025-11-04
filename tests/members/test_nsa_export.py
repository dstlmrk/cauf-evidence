from datetime import date
from unittest.mock import patch

from competitions.models import CompetitionFeeTypeEnum
from members.helpers import get_member_participation_counts
from members.tasks import generate_nsa_export

from tests.factories import (
    InternationalTournamentFactory,
    MemberAtInternationalTournamentFactory,
    MemberAtTournamentFactory,
    SeasonFactory,
    TeamAtInternationalTournamentFactory,
    UserFactory,
)
from tests.helpers import create_complete_competition


def test_member_participation_counts_includes_international_tournaments():
    """Test that participation counts include both domestic and international tournaments"""
    season = SeasonFactory()

    # Create domestic tournament (3 days)
    domestic_competition = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.REGULAR,
    )
    domestic_tournament = domestic_competition["tournament"]
    domestic_tournament.start_date = date(2025, 1, 1)
    domestic_tournament.end_date = date(2025, 1, 3)  # 3 days
    domestic_tournament.save()

    # Create international tournament (2 days)
    international_tournament = InternationalTournamentFactory(
        season=season,
        date_from=date(2025, 2, 10),
        date_to=date(2025, 2, 11),  # 2 days
        fee_type=CompetitionFeeTypeEnum.REGULAR,
    )
    team_at_int_tournament = TeamAtInternationalTournamentFactory(
        tournament=international_tournament
    )

    # Create member who plays in both tournaments
    domestic_mat = MemberAtTournamentFactory(
        tournament=domestic_tournament,
        team_at_tournament=domestic_competition["team_at_tournament"],
    )
    member = domestic_mat.member

    MemberAtInternationalTournamentFactory(
        tournament=international_tournament,
        team_at_tournament=team_at_int_tournament,
        member=member,
    )

    # Calculate participation
    participation = get_member_participation_counts(season)

    # Member should have 3 + 2 = 5 days
    assert participation[member.id] == 5


def test_member_participation_counts_only_domestic():
    """Test participation counts with only domestic tournaments"""
    season = SeasonFactory()

    # Create domestic tournament (4 days)
    domestic_competition = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.REGULAR,
    )
    domestic_tournament = domestic_competition["tournament"]
    domestic_tournament.start_date = date(2025, 1, 1)
    domestic_tournament.end_date = date(2025, 1, 4)  # 4 days
    domestic_tournament.save()

    mat = MemberAtTournamentFactory(
        tournament=domestic_tournament,
        team_at_tournament=domestic_competition["team_at_tournament"],
    )

    participation = get_member_participation_counts(season)

    assert participation[mat.member.id] == 4


def test_member_participation_counts_only_international():
    """Test participation counts with only international tournaments"""
    season = SeasonFactory()

    # Create international tournament (3 days)
    international_tournament = InternationalTournamentFactory(
        season=season,
        date_from=date(2025, 2, 10),
        date_to=date(2025, 2, 12),  # 3 days
        fee_type=CompetitionFeeTypeEnum.REGULAR,
    )
    team_at_int_tournament = TeamAtInternationalTournamentFactory(
        tournament=international_tournament
    )

    mait = MemberAtInternationalTournamentFactory(
        tournament=international_tournament,
        team_at_tournament=team_at_int_tournament,
    )

    participation = get_member_participation_counts(season)

    assert participation[mait.member.id] == 3


def test_member_participation_multiple_tournaments():
    """Test member playing in multiple tournaments of each type"""
    season = SeasonFactory()

    # Create 2 domestic tournaments
    domestic1 = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.REGULAR,
    )
    domestic1["tournament"].start_date = date(2025, 1, 1)
    domestic1["tournament"].end_date = date(2025, 1, 2)  # 2 days
    domestic1["tournament"].save()

    domestic2 = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.REGULAR,
    )
    domestic2["tournament"].start_date = date(2025, 3, 1)
    domestic2["tournament"].end_date = date(2025, 3, 3)  # 3 days
    domestic2["tournament"].save()

    # Create 2 international tournaments
    int1 = InternationalTournamentFactory(
        season=season,
        date_from=date(2025, 4, 1),
        date_to=date(2025, 4, 2),  # 2 days
        fee_type=CompetitionFeeTypeEnum.REGULAR,
    )
    team_at_int1 = TeamAtInternationalTournamentFactory(tournament=int1)

    int2 = InternationalTournamentFactory(
        season=season,
        date_from=date(2025, 5, 1),
        date_to=date(2025, 5, 4),  # 4 days
        fee_type=CompetitionFeeTypeEnum.REGULAR,
    )
    team_at_int2 = TeamAtInternationalTournamentFactory(tournament=int2)

    # Create member who plays in all tournaments
    mat1 = MemberAtTournamentFactory(
        tournament=domestic1["tournament"],
        team_at_tournament=domestic1["team_at_tournament"],
    )
    member = mat1.member

    MemberAtTournamentFactory(
        tournament=domestic2["tournament"],
        team_at_tournament=domestic2["team_at_tournament"],
        member=member,
    )

    MemberAtInternationalTournamentFactory(
        tournament=int1, team_at_tournament=team_at_int1, member=member
    )

    MemberAtInternationalTournamentFactory(
        tournament=int2, team_at_tournament=team_at_int2, member=member
    )

    participation = get_member_participation_counts(season)

    # Total: 2 + 3 + 2 + 4 = 11 days
    assert participation[member.id] == 11


@patch("members.tasks.send_email")
def test_nsa_export_excludes_free_only_players(mock_send_email):
    """Test that NSA export excludes members who only played in free tournaments"""
    season = SeasonFactory()
    user = UserFactory()

    # Create free tournament
    free_competition = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.FREE,
    )

    # Create regular tournament
    regular_competition = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.REGULAR,
    )

    # Member 1: only plays in free tournaments
    free_member = MemberAtTournamentFactory(
        tournament=free_competition["tournament"],
        team_at_tournament=free_competition["team_at_tournament"],
    ).member

    # Member 2: plays in regular tournaments
    regular_member = MemberAtTournamentFactory(
        tournament=regular_competition["tournament"],
        team_at_tournament=regular_competition["team_at_tournament"],
    ).member

    # Generate export
    generate_nsa_export(user, season, None)

    # Get CSV data from mock
    assert mock_send_email.called
    csv_data = mock_send_email.call_args[1]["csv_data"]

    # Parse CSV
    lines = csv_data.strip().split("\n")
    # Skip header
    data_lines = lines[1:]

    # Check that regular member is in export
    regular_member_in_export = any(
        regular_member.first_name in line and regular_member.last_name in line
        for line in data_lines
    )
    assert regular_member_in_export, "Regular member should be in export"

    # Check that free-only member is NOT in export
    free_member_in_export = any(
        free_member.first_name in line and free_member.last_name in line for line in data_lines
    )
    assert not free_member_in_export, "Free-only member should NOT be in export"


@patch("members.tasks.send_email")
def test_nsa_export_includes_discounted_players(mock_send_email):
    """Test that NSA export includes members who played in discounted tournaments"""
    season = SeasonFactory()
    user = UserFactory()

    # Create discounted tournament
    discounted_competition = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.DISCOUNTED,
    )

    discounted_member = MemberAtTournamentFactory(
        tournament=discounted_competition["tournament"],
        team_at_tournament=discounted_competition["team_at_tournament"],
    ).member

    # Generate export
    generate_nsa_export(user, season, None)

    # Get CSV data from mock
    assert mock_send_email.called
    csv_data = mock_send_email.call_args[1]["csv_data"]

    # Parse CSV
    lines = csv_data.strip().split("\n")
    data_lines = lines[1:]

    # Check that discounted member is in export
    discounted_member_in_export = any(
        discounted_member.first_name in line and discounted_member.last_name in line
        for line in data_lines
    )
    assert discounted_member_in_export, "Member with discounted fee should be in export"


@patch("members.tasks.send_email")
def test_nsa_export_csv_format(mock_send_email):
    """Test that NSA export CSV has correct format and structure"""
    season = SeasonFactory()
    user = UserFactory()

    # Create regular tournament
    regular_competition = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.REGULAR,
    )
    regular_competition["tournament"].start_date = date(2025, 1, 1)
    regular_competition["tournament"].end_date = date(2025, 1, 3)  # 3 days
    regular_competition["tournament"].save()

    MemberAtTournamentFactory(
        tournament=regular_competition["tournament"],
        team_at_tournament=regular_competition["team_at_tournament"],
    )

    # Generate export
    generate_nsa_export(user, season, None)

    # Get CSV data from mock
    assert mock_send_email.called
    csv_data = mock_send_email.call_args[1]["csv_data"]

    # Parse CSV
    lines = csv_data.strip().split("\n")

    # Check header
    header = lines[0]
    assert "JMENO" in header
    assert "PRIJMENI" in header
    assert "SPORTOVEC_UCAST_SOUTEZE_POCET" in header
    assert "SVAZ_ICO_SKTJ" in header

    # Check that we have at least one data row
    assert len(lines) > 1

    # Check that participation count is in the CSV (column 20)
    # Split by delimiter and verify structure
    data_row = lines[1]
    # CSV should have 26 columns (comma-separated)
    columns = data_row.split(",")
    assert len(columns) == 26, f"Expected 26 columns, got {len(columns)}"

    # Column 20 (index 19) should contain participation count
    # Should be 3 days for our test member
    participation_col = columns[19]
    assert "3" in participation_col or participation_col == "3"


@patch("members.tasks.send_email")
def test_nsa_export_with_international_tournaments(mock_send_email):
    """Test that NSA export correctly counts days from international tournaments"""
    season = SeasonFactory()
    user = UserFactory()

    # Create domestic regular tournament (2 days)
    domestic = create_complete_competition(
        season=season,
        fee_type=CompetitionFeeTypeEnum.REGULAR,
    )
    domestic["tournament"].start_date = date(2025, 1, 1)
    domestic["tournament"].end_date = date(2025, 1, 2)  # 2 days
    domestic["tournament"].save()

    # Create international regular tournament (3 days)
    international = InternationalTournamentFactory(
        season=season,
        date_from=date(2025, 2, 10),
        date_to=date(2025, 2, 12),  # 3 days
        fee_type=CompetitionFeeTypeEnum.REGULAR,
    )
    team_at_int = TeamAtInternationalTournamentFactory(tournament=international)

    # Member plays in both
    mat = MemberAtTournamentFactory(
        tournament=domestic["tournament"],
        team_at_tournament=domestic["team_at_tournament"],
    )
    member = mat.member

    MemberAtInternationalTournamentFactory(
        tournament=international, team_at_tournament=team_at_int, member=member
    )

    # Generate export
    generate_nsa_export(user, season, None)

    # Get CSV data from mock
    assert mock_send_email.called
    csv_data = mock_send_email.call_args[1]["csv_data"]

    # Parse CSV
    lines = csv_data.strip().split("\n")
    data_lines = lines[1:]

    # Find member's row
    member_row = None
    for line in data_lines:
        if member.first_name in line and member.last_name in line:
            member_row = line
            break

    assert member_row is not None, "Member should be in export"

    # Check participation count (column 20, index 19)
    columns = member_row.split(",")
    participation = columns[19]
    # Should be 2 + 3 = 5 days
    assert "5" in participation or participation == "5"
