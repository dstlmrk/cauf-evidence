import pytest
from django.utils import timezone
from members.models import MemberSexEnum
from tournaments.forms import AddMemberToRosterForm


class TestAddMemberToRosterForm:
    """Test nationality ratio validation in AddMemberToRosterForm"""

    def test_nationality_ratio_allowed_with_enough_czech_members(
        self, member_factory, team_at_tournament, member_at_tournament_factory
    ):
        """Test that foreign member can be added when Czech ratio remains >= 51%"""
        # Setup: team with 3 Czech members (will be 75% Czech after adding foreign member)

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
            team_at_tournament=team_at_tournament,
        )

        assert form.is_valid()

    def test_nationality_ratio_rejected_when_too_many_foreigners(
        self, member_factory, team_at_tournament, member_at_tournament_factory
    ):
        """Test that foreign member is rejected when Czech ratio would drop below 51%"""
        # Setup: team with 1 Czech member (would be 33% Czech after adding foreign member)

        # Create 1 Czech member already on roster
        czech_member = member_factory(
            citizenship="CZ",
            email_confirmed_at=timezone.now(),
        )
        member_at_tournament_factory(
            team_at_tournament=team_at_tournament,
            tournament=team_at_tournament.tournament,
            member=czech_member,
        )

        # Create 1 foreign member already on roster
        existing_foreign = member_factory(
            citizenship="US",
            email_confirmed_at=timezone.now(),
        )
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
            team_at_tournament=team_at_tournament,
        )

        assert not form.is_valid()
        assert "Nationality ratio: at least 51% must be Czech citizens" in str(
            form.errors["member_id"]
        )

    def test_nationality_ratio_first_member_cannot_be_foreign(
        self, member_factory, team_at_tournament
    ):
        """Test that first member cannot be foreign (0% Czech is not >= 51%)"""
        # Setup: empty team roster

        # Try to add first member as foreign
        foreign_member = member_factory(
            citizenship="US",
            sex=MemberSexEnum.MALE,
            club=team_at_tournament.application.team.club,
            email_confirmed_at=timezone.now(),
        )

        form = AddMemberToRosterForm(
            data={"member_id": foreign_member.id},
            team_at_tournament=team_at_tournament,
        )

        # This should fail because 0% Czech is not >= 51%
        assert not form.is_valid()
        assert "Nationality ratio: at least 51% must be Czech citizens" in str(
            form.errors["member_id"]
        )

    def test_nationality_ratio_first_member_can_be_czech(self, member_factory, team_at_tournament):
        """Test that first member can be Czech"""
        # Setup: empty team roster

        # Try to add first member as Czech
        czech_member = member_factory(
            citizenship="CZ",
            sex=MemberSexEnum.MALE,
            club=team_at_tournament.application.team.club,
            email_confirmed_at=timezone.now(),
        )

        form = AddMemberToRosterForm(
            data={"member_id": czech_member.id},
            team_at_tournament=team_at_tournament,
        )

        assert form.is_valid()

    def test_nationality_ratio_50_50_split_rejected(
        self, member_factory, team_at_tournament, member_at_tournament_factory
    ):
        """Test that 50/50 split is rejected (need at least 51% Czech)"""
        # Setup: team with 1 Czech member

        czech_member = member_factory(
            citizenship="CZ",
            email_confirmed_at=timezone.now(),
        )
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
            team_at_tournament=team_at_tournament,
        )

        assert not form.is_valid()
        assert "Nationality ratio: at least 51% must be Czech citizens" in str(
            form.errors["member_id"]
        )

    def test_nationality_ratio_exactly_51_percent_allowed(
        self, member_factory, team_at_tournament, member_at_tournament_factory
    ):
        """Test that exactly 51% Czech is allowed"""
        # Setup: team with 1 Czech member and 1 foreign

        # Create 1 Czech member
        czech_member = member_factory(
            citizenship="CZ",
            email_confirmed_at=timezone.now(),
        )
        member_at_tournament_factory(
            team_at_tournament=team_at_tournament,
            tournament=team_at_tournament.tournament,
            member=czech_member,
        )

        # Create 1 foreign member
        foreign_member = member_factory(
            citizenship="US",
            email_confirmed_at=timezone.now(),
        )
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
            team_at_tournament=team_at_tournament,
        )

        assert form.is_valid()

    def test_member_cannot_play_for_different_team_in_same_competition(
        self,
        member_factory,
        team_at_tournament_factory,
        member_at_tournament_factory,
        competition_application_factory,
    ):
        """Member already on team A's roster in competition cannot be added to team B's roster"""
        # Create two tournaments in the same competition, each with a different team
        tat_a = team_at_tournament_factory()
        competition = tat_a.tournament.competition

        application_b = competition_application_factory(competition=competition)
        tat_b = team_at_tournament_factory(
            tournament__competition=competition,
            application=application_b,
        )

        member = member_factory(
            citizenship="CZ",
            sex=MemberSexEnum.MALE,
            club=tat_b.application.team.club,
            email_confirmed_at=timezone.now(),
        )

        # Add member to team A's roster on the first tournament
        member_at_tournament_factory(
            team_at_tournament=tat_a,
            tournament=tat_a.tournament,
            member=member,
        )

        # Try to add the same member to team B's roster on the second tournament
        form = AddMemberToRosterForm(
            data={"member_id": member.id},
            team_at_tournament=tat_b,
        )

        assert not form.is_valid()
        assert "Member is already registered for another team in this competition" in str(
            form.errors["member_id"]
        )

    def test_member_can_play_for_same_team_in_same_competition(
        self,
        member_factory,
        team_at_tournament_factory,
        member_at_tournament_factory,
    ):
        """Member on team A's roster can be added to team A's roster on another tournament"""
        tat_a = team_at_tournament_factory()
        competition = tat_a.tournament.competition

        # Second tournament in same competition, same team (same application)
        tat_a2 = team_at_tournament_factory(
            tournament__competition=competition,
            application=tat_a.application,
        )

        member = member_factory(
            citizenship="CZ",
            sex=MemberSexEnum.MALE,
            club=tat_a.application.team.club,
            email_confirmed_at=timezone.now(),
        )

        member_at_tournament_factory(
            team_at_tournament=tat_a,
            tournament=tat_a.tournament,
            member=member,
        )

        form = AddMemberToRosterForm(
            data={"member_id": member.id},
            team_at_tournament=tat_a2,
        )

        assert form.is_valid()

    def test_member_can_play_for_different_team_in_different_competition(
        self,
        member_factory,
        team_at_tournament_factory,
        member_at_tournament_factory,
    ):
        """Member on team A in competition X can play for team B in competition Y"""
        tat_a = team_at_tournament_factory()
        tat_b = team_at_tournament_factory()  # different competition by default

        member = member_factory(
            citizenship="CZ",
            sex=MemberSexEnum.MALE,
            club=tat_b.application.team.club,
            email_confirmed_at=timezone.now(),
        )

        member_at_tournament_factory(
            team_at_tournament=tat_a,
            tournament=tat_a.tournament,
            member=member,
        )

        form = AddMemberToRosterForm(
            data={"member_id": member.id},
            team_at_tournament=tat_b,
        )

        assert form.is_valid()

    @pytest.mark.parametrize(
        "min_age_verification_enabled,expected_valid",
        [
            (True, False),  # With verification enabled, too young member should be rejected
            (False, True),  # With verification disabled, too young member should be allowed
        ],
    )
    def test_min_age_verification(
        self,
        member_factory,
        team_at_tournament_factory,
        min_age_verification_enabled,
        expected_valid,
    ):
        """Test that min_age_verification_required controls minimum age validation"""
        from tests.conftest import override_app_settings

        with override_app_settings(min_age_verification_required=min_age_verification_enabled):
            # Setup: tournament with age limit (U20: min 12, max 19 for males)
            team_at_tournament = team_at_tournament_factory(
                tournament__competition__age_limit__m_min=12,
                tournament__competition__age_limit__m_max=19,
            )

            # Create member who is 11 years old (below minimum but under max)
            young_member = member_factory(
                citizenship="CZ",
                sex=MemberSexEnum.MALE,
                birth_date=timezone.now().date()
                - timezone.timedelta(days=365 * 11 + 100),  # 11 years old
                club=team_at_tournament.application.team.club,
                email_confirmed_at=timezone.now(),
            )

            form = AddMemberToRosterForm(
                data={"member_id": young_member.id},
                team_at_tournament=team_at_tournament,
            )

            assert form.is_valid() == expected_valid
            if not expected_valid:
                assert "Member does not meet age requirements" in str(form.errors["member_id"])
