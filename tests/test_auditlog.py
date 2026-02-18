from auditlog.context import set_actor
from auditlog.models import LogEntry

from tests.factories import ClubFactory, MemberFactory, UserFactory


class TestAuditlogCreateAction:
    def test_create_generates_log_entry(self):
        club = ClubFactory()
        entries = LogEntry.objects.get_for_object(club)
        assert entries.count() == 1
        assert entries.first().action == LogEntry.Action.CREATE

    def test_create_log_entry_contains_changes(self):
        club = ClubFactory(name="Test Club")
        entry = LogEntry.objects.get_for_object(club).first()
        assert "name" in entry.changes


class TestAuditlogUpdateAction:
    def test_update_generates_log_entry_with_changed_field(self):
        club = ClubFactory(name="Old Name")
        club.name = "New Name"
        club.save()

        entries = LogEntry.objects.get_for_object(club)
        update_entry = entries.filter(action=LogEntry.Action.UPDATE).first()
        assert update_entry is not None
        assert "name" in update_entry.changes


class TestAuditlogDeleteAction:
    def test_delete_generates_log_entry(self):
        member = MemberFactory()
        pk = member.pk
        member.delete()

        entry = LogEntry.objects.filter(action=LogEntry.Action.DELETE, object_pk=str(pk)).first()
        assert entry is not None


class TestAuditlogExcludedFields:
    def test_created_at_and_updated_at_not_tracked(self):
        club = ClubFactory()
        entry = LogEntry.objects.get_for_object(club).first()
        assert "created_at" not in entry.changes
        assert "updated_at" not in entry.changes


class TestAuditlogActorCapture:
    def test_actor_is_captured_via_set_actor(self):
        user = UserFactory()
        with set_actor(user):
            club = ClubFactory()

        entry = LogEntry.objects.get_for_object(club).first()
        assert entry.actor == user
