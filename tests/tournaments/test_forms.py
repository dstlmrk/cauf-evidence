from unittest.mock import patch

from django.utils import timezone
from members.models import MemberSexEnum
from tournaments.forms import AddMemberToRosterForm


class TestAddMemberToRosterForm:
    """Test nationality ratio validation in AddMemberToRosterForm"""

    @patch("tournaments.forms.FF_MIN_AGE_VERIFICATION_REQUIRED", False)
    def test_nationality_ratio_allowed_with_enough_czech_members(
        self, member_factory, team_at_tournament_factory, member_at_tournament_factory
    ):
        """Test that foreign member can be added when Czech ratio remains >= 51%"""
        # Setup: team with 3 Czech members (will be 75% Czech after adding foreign member)
        team_at_tournament = team_at_tournament_factory(
            tournament__rosters_deadline=timezone.now() + timezone.timedelta(days=1)
        )

        # Create 3 Czech members already on roster
        for _ in range(3):
            czech_member = member_factory(citizenship="CZ", email_confirmed_at=timezone.now())
            member_at_tournament_factory(
                team_at_tournament=team_at_tournament,
                tournament=team_at_tournament.tournament,
                member=czech_member,
            )

        # Try to add a foreign member
        foreign_member = member_factory(
            citizenship="US",
            sex=MemberSexEnum.MALE,
            club=team_at_tournament.application.team.club,
            email_confirmed_at=timezone.now(),
        )

        form = AddMemberToRosterForm(
            data={"member_id": foreign_member.id},
            member=foreign_member,
            team_at_tournament=team_at_tournament,
        )

        assert form.is_valid()

    @patch("tournaments.forms.FF_MIN_AGE_VERIFICATION_REQUIRED", False)
    def test_nationality_ratio_rejected_when_too_many_foreigners(
        self, member_factory, team_at_tournament_factory, member_at_tournament_factory
    ):
        """Test that foreign member is rejected when Czech ratio would drop below 51%"""
        # Setup: team with 1 Czech member (would be 33% Czech after adding foreign member)
        team_at_tournament = team_at_tournament_factory(
            tournament__rosters_deadline=timezone.now() + timezone.timedelta(days=1)
        )

        # Create 1 Czech member already on roster
        czech_member = member_factory(citizenship="CZ", email_confirmed_at=timezone.now())
        member_at_tournament_factory(
            team_at_tournament=team_at_tournament,
            tournament=team_at_tournament.tournament,
            member=czech_member,
        )

        # Create 1 foreign member already on roster
        existing_foreign = member_factory(citizenship="US", email_confirmed_at=timezone.now())
        member_at_tournament_factory(
            team_at_tournament=team_at_tournament,
            tournament=team_at_tournament.tournament,
            member=existing_foreign,
        )

        # Try to add another foreign member (would make it 1 Czech, 2 foreign = 33% Czech)
        new_foreign_member = member_factory(
            citizenship="DE",
            sex=MemberSexEnum.MALE,
            club=team_at_tournament.application.team.club,
            email_confirmed_at=timezone.now(),
        )

        form = AddMemberToRosterForm(
            data={"member_id": new_foreign_member.id},
            member=new_foreign_member,
            team_at_tournament=team_at_tournament,
        )

        assert not form.is_valid()
        assert "Nationality ratio: at least 51% must be Czech citizens" in str(
            form.errors["member_id"]
        )

    @patch("tournaments.forms.FF_MIN_AGE_VERIFICATION_REQUIRED", False)
    def test_nationality_ratio_first_member_cannot_be_foreign(
        self, member_factory, team_at_tournament_factory
    ):
        """Test that first member cannot be foreign (0% Czech is not >= 51%)"""
        # Setup: empty team roster
        team_at_tournament = team_at_tournament_factory(
            tournament__rosters_deadline=timezone.now() + timezone.timedelta(days=1)
        )

        # Try to add first member as foreign
        foreign_member = member_factory(
            citizenship="US",
            sex=MemberSexEnum.MALE,
            club=team_at_tournament.application.team.club,
            email_confirmed_at=timezone.now(),
        )

        form = AddMemberToRosterForm(
            data={"member_id": foreign_member.id},
            member=foreign_member,
            team_at_tournament=team_at_tournament,
        )

        # This should fail because 0% Czech is not >= 51%
        assert not form.is_valid()
        assert "Nationality ratio: at least 51% must be Czech citizens" in str(
            form.errors["member_id"]
        )

    @patch("tournaments.forms.FF_MIN_AGE_VERIFICATION_REQUIRED", False)
    def test_nationality_ratio_first_member_can_be_czech(
        self, member_factory, team_at_tournament_factory
    ):
        """Test that first member can be Czech"""
        # Setup: empty team roster
        team_at_tournament = team_at_tournament_factory(
            tournament__rosters_deadline=timezone.now() + timezone.timedelta(days=1)
        )

        # Try to add first member as Czech
        czech_member = member_factory(
            citizenship="CZ",
            sex=MemberSexEnum.MALE,
            club=team_at_tournament.application.team.club,
            email_confirmed_at=timezone.now(),
        )

        form = AddMemberToRosterForm(
            data={"member_id": czech_member.id},
            member=czech_member,
            team_at_tournament=team_at_tournament,
        )

        assert form.is_valid()

    @patch("tournaments.forms.FF_MIN_AGE_VERIFICATION_REQUIRED", False)
    def test_nationality_ratio_50_50_split_rejected(
        self, member_factory, team_at_tournament_factory, member_at_tournament_factory
    ):
        """Test that 50/50 split is rejected (need at least 51% Czech)"""
        # Setup: team with 1 Czech member
        team_at_tournament = team_at_tournament_factory(
            tournament__rosters_deadline=timezone.now() + timezone.timedelta(days=1)
        )

        czech_member = member_factory(citizenship="CZ", email_confirmed_at=timezone.now())
        member_at_tournament_factory(
            team_at_tournament=team_at_tournament,
            tournament=team_at_tournament.tournament,
            member=czech_member,
        )

        # Try to add foreign member (would make it 50% Czech, 50% foreign)
        foreign_member = member_factory(
            citizenship="US",
            sex=MemberSexEnum.MALE,
            club=team_at_tournament.application.team.club,
            email_confirmed_at=timezone.now(),
        )

        form = AddMemberToRosterForm(
            data={"member_id": foreign_member.id},
            member=foreign_member,
            team_at_tournament=team_at_tournament,
        )

        assert not form.is_valid()
        assert "Nationality ratio: at least 51% must be Czech citizens" in str(
            form.errors["member_id"]
        )

    @patch("tournaments.forms.FF_MIN_AGE_VERIFICATION_REQUIRED", False)
    def test_nationality_ratio_exactly_51_percent_allowed(
        self, member_factory, team_at_tournament_factory, member_at_tournament_factory
    ):
        """Test that exactly 51% Czech is allowed"""
        # Setup: team with 1 Czech member and 1 foreign
        team_at_tournament = team_at_tournament_factory(
            tournament__rosters_deadline=timezone.now() + timezone.timedelta(days=1)
        )

        # Create 1 Czech member
        czech_member = member_factory(citizenship="CZ", email_confirmed_at=timezone.now())
        member_at_tournament_factory(
            team_at_tournament=team_at_tournament,
            tournament=team_at_tournament.tournament,
            member=czech_member,
        )

        # Create 1 foreign member
        foreign_member = member_factory(citizenship="US", email_confirmed_at=timezone.now())
        member_at_tournament_factory(
            team_at_tournament=team_at_tournament,
            tournament=team_at_tournament.tournament,
            member=foreign_member,
        )

        # Try to add another Czech member (2 Czech + 1 foreign = 67% Czech)
        new_czech_member = member_factory(
            citizenship="CZ",
            sex=MemberSexEnum.MALE,
            club=team_at_tournament.application.team.club,
            email_confirmed_at=timezone.now(),
        )

        form = AddMemberToRosterForm(
            data={"member_id": new_czech_member.id},
            member=new_czech_member,
            team_at_tournament=team_at_tournament,
        )

        assert form.is_valid()
