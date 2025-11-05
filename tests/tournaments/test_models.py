from datetime import datetime

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone


class TestTournamentModel:
    """Test Tournament model validation"""

    @pytest.mark.parametrize(
        "deadline_datetime,expected_valid",
        [
            # Valid: deadline before first day
            (datetime(2025, 3, 3, 23, 59, 59), True),
            # Valid: deadline during first day
            (datetime(2025, 3, 4, 8, 0, 0), True),
            # Invalid: deadline after first day
            (datetime(2025, 3, 5, 8, 0, 0), False),
        ],
    )
    def test_rosters_deadline_validation(
        self, tournament_factory, deadline_datetime, expected_valid
    ):
        """Test that rosters_deadline must be within the first day of the tournament"""
        start_date = datetime(2025, 3, 4).date()
        end_date = datetime(2025, 3, 6).date()
        rosters_deadline = timezone.make_aware(deadline_datetime)

        tournament = tournament_factory.build(
            start_date=start_date,
            end_date=end_date,
            rosters_deadline=rosters_deadline,
        )

        if expected_valid:
            tournament.clean()
        else:
            with pytest.raises(ValidationError) as exc_info:
                tournament.clean()

            assert "rosters_deadline" in exc_info.value.error_dict
            assert "Roster deadline cannot be after the first day of the tournament" in str(
                exc_info.value.error_dict["rosters_deadline"]
            )
