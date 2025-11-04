import pytest
from django.conf import settings
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from django.urls import reverse

from international_tournaments.forms import (
    AddMemberToInternationalRosterForm,
    UpdateMemberToInternationalRosterForm,
)
from international_tournaments.models import MemberAtInternationalTournament
from international_tournaments.views import (
    international_roster_add_form_view,
    international_roster_update_form_view,
    remove_member_from_international_roster_view,
)


def attach_messages_storage(request) -> None:
    """Attach pluggable message storage to match middleware behaviour."""
    request._messages = FallbackStorage(request)


@pytest.mark.django_db
class TestRosterPermissions:
    """Test permission checks for international tournament roster management."""

    def test_add_member_denied_for_non_national_team_club(
        self,
        rf: RequestFactory,
        user_factory,
        club_factory,
        team_at_international_tournament_factory,
    ):
        """Users from non-national team clubs cannot add members to international rosters."""
        # Create regular club (not national team)
        regular_club = club_factory()
        user = user_factory()
        team_at_tournament = team_at_international_tournament_factory()

        # Create request with session
        request = rf.post(
            reverse(
                "international_tournaments:roster_add",
                kwargs={"team_at_tournament_id": team_at_tournament.id},
            )
        )
        request.user = user
        request.session = {"club": {"id": regular_club.id, "name": regular_club.name}}

        # Should raise PermissionDenied
        with pytest.raises(PermissionDenied) as exc_info:
            international_roster_add_form_view(request, team_at_tournament.id)

        assert "Only National Team club members" in str(exc_info.value)

    def test_add_member_allowed_for_national_team_club(
        self,
        rf: RequestFactory,
        agent_factory,
        club_factory,
        team_at_international_tournament_factory,
        member_factory,
    ):
        """Users from national team club can add members to international rosters."""
        # Create national team club with correct ID
        national_club = club_factory(id=settings.NATIONAL_TEAM_CLUB_ID)
        agent = agent_factory()
        user = agent.user
        team_at_tournament = team_at_international_tournament_factory()
        member = member_factory()

        # Create request with session
        request = rf.post(
            reverse(
                "international_tournaments:roster_add",
                kwargs={"team_at_tournament_id": team_at_tournament.id},
            ),
            data={"member_id": member.id},
        )
        request.user = user
        request.session = {"club": {"id": national_club.id, "name": national_club.name}}
        attach_messages_storage(request)

        # Should not raise PermissionDenied
        response = international_roster_add_form_view(request, team_at_tournament.id)

        # Should either render form (GET) or process form (POST)
        assert response.status_code in [200, 204]

    def test_update_member_denied_for_non_national_team_club(
        self,
        rf: RequestFactory,
        user_factory,
        club_factory,
        member_at_international_tournament_factory,
    ):
        """Users from non-national team clubs cannot update members in international rosters."""
        regular_club = club_factory()
        user = user_factory()
        member_at_tournament = member_at_international_tournament_factory()

        request = rf.post(
            reverse(
                "international_tournaments:roster_update",
                kwargs={"member_at_tournament_id": member_at_tournament.id},
            )
        )
        request.user = user
        request.session = {"club": {"id": regular_club.id, "name": regular_club.name}}

        with pytest.raises(PermissionDenied):
            international_roster_update_form_view(request, member_at_tournament.id)

    def test_update_member_allowed_for_national_team_club(
        self,
        rf: RequestFactory,
        agent_factory,
        club_factory,
        member_at_international_tournament_factory,
    ):
        """Users from national team club can update members in international rosters."""
        national_club = club_factory(id=settings.NATIONAL_TEAM_CLUB_ID)
        agent = agent_factory()
        user = agent.user
        member_at_tournament = member_at_international_tournament_factory()

        request = rf.get(
            reverse(
                "international_tournaments:roster_update",
                kwargs={"member_at_tournament_id": member_at_tournament.id},
            )
        )
        request.user = user
        request.session = {"club": {"id": national_club.id, "name": national_club.name}}

        response = international_roster_update_form_view(request, member_at_tournament.id)
        assert response.status_code == 200

    def test_remove_member_denied_for_non_national_team_club(
        self,
        rf: RequestFactory,
        user_factory,
        club_factory,
        member_at_international_tournament_factory,
    ):
        """Users from non-national team clubs cannot remove members from international rosters."""
        regular_club = club_factory()
        user = user_factory()
        member_at_tournament = member_at_international_tournament_factory()

        request = rf.post(
            reverse(
                "international_tournaments:roster_remove",
                kwargs={"member_at_tournament_id": member_at_tournament.id},
            )
        )
        request.user = user
        request.session = {"club": {"id": regular_club.id, "name": regular_club.name}}

        with pytest.raises(PermissionDenied):
            remove_member_from_international_roster_view(request, member_at_tournament.id)

    def test_remove_member_allowed_for_national_team_club(
        self,
        rf: RequestFactory,
        agent_factory,
        club_factory,
        member_at_international_tournament_factory,
    ):
        """Users from national team club can remove members from international rosters."""
        national_club = club_factory(id=settings.NATIONAL_TEAM_CLUB_ID)
        agent = agent_factory()
        user = agent.user
        member_at_tournament = member_at_international_tournament_factory()

        request = rf.post(
            reverse(
                "international_tournaments:roster_remove",
                kwargs={"member_at_tournament_id": member_at_tournament.id},
            )
        )
        request.user = user
        request.session = {"club": {"id": national_club.id, "name": national_club.name}}
        attach_messages_storage(request)

        response = remove_member_from_international_roster_view(request, member_at_tournament.id)
        assert response.status_code == 200


@pytest.mark.django_db
class TestAddMemberValidation:
    """Test validation rules for adding members to international tournament rosters."""

    def test_cannot_add_duplicate_member_to_same_team(
        self,
        team_at_international_tournament_factory,
        member_factory,
        member_at_international_tournament_factory,
    ):
        """Cannot add a member who is already in the same team roster."""
        team_at_tournament = team_at_international_tournament_factory()
        member = member_factory()

        # Add member to roster
        member_at_international_tournament_factory(
            team_at_tournament=team_at_tournament, member=member
        )

        # Try to add same member again
        form = AddMemberToInternationalRosterForm(
            data={"member_id": member.id},
            team_at_tournament=team_at_tournament,
        )

        assert not form.is_valid()
        assert "member_id" in form.errors
        assert "already in this team roster" in str(form.errors["member_id"])

    def test_cannot_add_member_already_in_another_team_at_same_tournament(
        self,
        international_tournament_factory,
        team_at_international_tournament_factory,
        member_factory,
        member_at_international_tournament_factory,
    ):
        """Cannot add a member who is already in a different team at the same tournament."""
        tournament = international_tournament_factory()
        team1 = team_at_international_tournament_factory(tournament=tournament)
        team2 = team_at_international_tournament_factory(tournament=tournament)
        member = member_factory()

        # Add member to team1
        member_at_international_tournament_factory(
            tournament=tournament, team_at_tournament=team1, member=member
        )

        # Try to add same member to team2 at same tournament
        form = AddMemberToInternationalRosterForm(
            data={"member_id": member.id},
            team_at_tournament=team2,
        )

        assert not form.is_valid()
        assert "member_id" in form.errors
        assert "already in another team at this tournament" in str(form.errors["member_id"])

    def test_can_add_member_to_different_tournament(
        self,
        team_at_international_tournament_factory,
        member_factory,
        member_at_international_tournament_factory,
    ):
        """Can add a member to different tournaments (no conflict)."""
        team1 = team_at_international_tournament_factory()
        team2 = team_at_international_tournament_factory()  # Different tournament
        member = member_factory()

        # Add member to team1's tournament
        member_at_international_tournament_factory(team_at_tournament=team1, member=member)

        # Should be able to add same member to team2's tournament
        form = AddMemberToInternationalRosterForm(
            data={"member_id": member.id},
            team_at_tournament=team2,
        )

        assert form.is_valid()

    def test_member_not_found_validation(self, team_at_international_tournament_factory):
        """Form validation fails when member doesn't exist."""
        team_at_tournament = team_at_international_tournament_factory()

        form = AddMemberToInternationalRosterForm(
            data={"member_id": 99999},  # Non-existent member
            team_at_tournament=team_at_tournament,
        )

        assert not form.is_valid()
        assert "member_id" in form.errors
        assert "Member not found" in str(form.errors["member_id"])


@pytest.mark.django_db
class TestUpdateMemberValidation:
    """Test validation rules for updating members in international tournament rosters."""

    def test_cannot_set_multiple_captains(
        self,
        team_at_international_tournament_factory,
        member_at_international_tournament_factory,
    ):
        """Cannot set multiple captains for the same team."""
        team_at_tournament = team_at_international_tournament_factory()
        member_at_international_tournament_factory(  # captain
            team_at_tournament=team_at_tournament, is_captain=True
        )
        other_member = member_at_international_tournament_factory(
            team_at_tournament=team_at_tournament, is_captain=False
        )

        # Try to set another member as captain
        form = UpdateMemberToInternationalRosterForm(
            data={"is_captain": True, "is_spirit_captain": False, "is_coach": False},
            instance=other_member,
        )

        assert not form.is_valid()
        assert "is_captain" in form.errors
        assert "already has a captain" in str(form.errors["is_captain"])

    def test_cannot_set_multiple_spirit_captains(
        self,
        team_at_international_tournament_factory,
        member_at_international_tournament_factory,
    ):
        """Cannot set multiple spirit captains for the same team."""
        team_at_tournament = team_at_international_tournament_factory()
        member_at_international_tournament_factory(  # spirit captain
            team_at_tournament=team_at_tournament, is_spirit_captain=True
        )
        other_member = member_at_international_tournament_factory(
            team_at_tournament=team_at_tournament, is_spirit_captain=False
        )

        # Try to set another member as spirit captain
        form = UpdateMemberToInternationalRosterForm(
            data={"is_captain": False, "is_spirit_captain": True, "is_coach": False},
            instance=other_member,
        )

        assert not form.is_valid()
        assert "is_spirit_captain" in form.errors
        assert "already has a spirit captain" in str(form.errors["is_spirit_captain"])

    def test_can_update_same_member_captain_status(
        self, member_at_international_tournament_factory
    ):
        """Can update the same member's captain status without conflict."""
        member_at_tournament = member_at_international_tournament_factory(is_captain=True)

        # Update same member (should not conflict with itself)
        form = UpdateMemberToInternationalRosterForm(
            data={
                "is_captain": True,
                "is_spirit_captain": False,
                "is_coach": False,
                "jersey_number": 10,
            },
            instance=member_at_tournament,
        )

        assert form.is_valid()

    def test_cannot_set_duplicate_jersey_number(
        self,
        team_at_international_tournament_factory,
        member_at_international_tournament_factory,
    ):
        """Cannot set duplicate jersey numbers for the same team."""
        team_at_tournament = team_at_international_tournament_factory()
        member_at_international_tournament_factory(  # member1
            team_at_tournament=team_at_tournament, jersey_number=10
        )
        member2 = member_at_international_tournament_factory(
            team_at_tournament=team_at_tournament, jersey_number=20
        )

        # Try to set member2's jersey number to 10 (already used by member1)
        form = UpdateMemberToInternationalRosterForm(
            data={
                "is_captain": False,
                "is_spirit_captain": False,
                "is_coach": False,
                "jersey_number": 10,
            },
            instance=member2,
        )

        assert not form.is_valid()
        assert "jersey_number" in form.errors
        assert "Another player already has jersey number 10" in str(form.errors["jersey_number"])

    def test_can_update_same_member_jersey_number(self, member_at_international_tournament_factory):
        """Can update the same member's data without jersey number conflict."""
        member_at_tournament = member_at_international_tournament_factory(jersey_number=10)

        # Update same member with same jersey number (should not conflict with itself)
        form = UpdateMemberToInternationalRosterForm(
            data={
                "is_captain": False,
                "is_spirit_captain": False,
                "is_coach": True,
                "jersey_number": 10,
            },
            instance=member_at_tournament,
        )

        assert form.is_valid()

    def test_jersey_number_unique_per_team_not_tournament(
        self,
        international_tournament_factory,
        team_at_international_tournament_factory,
        member_at_international_tournament_factory,
    ):
        """Jersey numbers must be unique per team, but can be reused across different teams."""
        tournament = international_tournament_factory()
        team1 = team_at_international_tournament_factory(tournament=tournament)
        team2 = team_at_international_tournament_factory(tournament=tournament)

        member_at_international_tournament_factory(  # member1
            team_at_tournament=team1, jersey_number=10
        )
        member2 = member_at_international_tournament_factory(
            team_at_tournament=team2, jersey_number=20
        )

        # Should be able to set jersey 10 for member2 in team2 (different team)
        form = UpdateMemberToInternationalRosterForm(
            data={
                "is_captain": False,
                "is_spirit_captain": False,
                "is_coach": False,
                "jersey_number": 10,
            },
            instance=member2,
        )

        assert form.is_valid()


@pytest.mark.django_db
class TestRosterCRUDOperations:
    """Test CRUD operations for international tournament rosters."""

    def test_add_member_to_roster(
        self,
        rf: RequestFactory,
        agent_factory,
        club_factory,
        team_at_international_tournament_factory,
        member_factory,
    ):
        """Successfully add a member to international tournament roster."""
        national_club = club_factory(id=settings.NATIONAL_TEAM_CLUB_ID)
        agent = agent_factory()
        user = agent.user
        team_at_tournament = team_at_international_tournament_factory()
        member = member_factory(default_jersey_number=15)

        initial_count = MemberAtInternationalTournament.objects.count()

        request = rf.post(
            reverse(
                "international_tournaments:roster_add",
                kwargs={"team_at_tournament_id": team_at_tournament.id},
            ),
            data={"member_id": member.id},
        )
        request.user = user
        request.session = {"club": {"id": national_club.id, "name": national_club.name}}
        attach_messages_storage(request)

        response = international_roster_add_form_view(request, team_at_tournament.id)

        # Should return 204 No Content on success
        assert response.status_code == 204
        assert MemberAtInternationalTournament.objects.count() == initial_count + 1

        # Verify member was added with correct data
        member_at_tournament = MemberAtInternationalTournament.objects.get(
            team_at_tournament=team_at_tournament, member=member
        )
        assert member_at_tournament.jersey_number == 15
        assert member_at_tournament.is_captain is False

    def test_update_member_in_roster(
        self,
        rf: RequestFactory,
        agent_factory,
        club_factory,
        member_at_international_tournament_factory,
    ):
        """Successfully update a member in international tournament roster."""
        national_club = club_factory(id=settings.NATIONAL_TEAM_CLUB_ID)
        agent = agent_factory()
        user = agent.user
        member_at_tournament = member_at_international_tournament_factory(
            is_captain=False, jersey_number=10
        )

        request = rf.post(
            reverse(
                "international_tournaments:roster_update",
                kwargs={"member_at_tournament_id": member_at_tournament.id},
            ),
            data={
                "is_captain": True,
                "is_spirit_captain": False,
                "is_coach": False,
                "jersey_number": 99,
            },
        )
        request.user = user
        request.session = {"club": {"id": national_club.id, "name": national_club.name}}
        attach_messages_storage(request)

        response = international_roster_update_form_view(request, member_at_tournament.id)

        assert response.status_code == 204

        # Verify updates
        member_at_tournament.refresh_from_db()
        assert member_at_tournament.is_captain is True
        assert member_at_tournament.jersey_number == 99

    def test_remove_member_from_roster(
        self,
        rf: RequestFactory,
        agent_factory,
        club_factory,
        member_at_international_tournament_factory,
    ):
        """Successfully remove a member from international tournament roster."""
        national_club = club_factory(id=settings.NATIONAL_TEAM_CLUB_ID)
        agent = agent_factory()
        user = agent.user
        member_at_tournament = member_at_international_tournament_factory()

        initial_count = MemberAtInternationalTournament.objects.count()

        request = rf.post(
            reverse(
                "international_tournaments:roster_remove",
                kwargs={"member_at_tournament_id": member_at_tournament.id},
            )
        )
        request.user = user
        request.session = {"club": {"id": national_club.id, "name": national_club.name}}
        attach_messages_storage(request)

        response = remove_member_from_international_roster_view(request, member_at_tournament.id)

        assert response.status_code == 200
        assert MemberAtInternationalTournament.objects.count() == initial_count - 1
        assert not MemberAtInternationalTournament.objects.filter(
            pk=member_at_tournament.id
        ).exists()
