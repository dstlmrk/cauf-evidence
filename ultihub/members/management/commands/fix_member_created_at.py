from argparse import ArgumentParser
from datetime import datetime
from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone

from members.management.commands.import_members import Client as OldEvidenceClient
from members.models import Member

ORIGINAL_EVIDENCE_URL = "https://api.evidence.czechultimate.cz/"


class Command(BaseCommand):
    help = "Fix created_at for all members imported from old evidence"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show changes without executing them",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write("=== DRY RUN MODE ===")

        client = OldEvidenceClient()
        self.stdout.write("Connected to old evidence")

        # Find all members with original_id (imported from old evidence)
        members_with_original_id = Member.objects.exclude(original_id="")
        total_members = members_with_original_id.count()

        self.stdout.write(f"Found {total_members} members with original_id to fix")

        success_count = 0
        error_count = 0

        for i, member in enumerate(members_with_original_id, 1):
            self.stdout.write(
                f"[{i}/{total_members}] Processing member: "
                f"{member.first_name} {member.last_name} (ID: {member.id}, "
                f"original_id: {member.original_id})"
            )

            try:
                # Get data from old evidence
                old_player_data = client.get(f"player/{member.original_id}")

                if not old_player_data:
                    self.stdout.write(
                        f"  ❌ Member with original_id {member.original_id} not found "
                        "in old evidence"
                    )
                    error_count += 1
                    continue

                # Parse created_at from old evidence
                old_created_at_str = old_player_data["created_at"]
                old_created_at = timezone.make_aware(
                    datetime.strptime(old_created_at_str, "%Y-%m-%d %H:%M:%S"),
                    timezone.get_current_timezone(),
                )

                # Compare with current created_at
                current_created_at = member.created_at

                if old_created_at == current_created_at:
                    self.stdout.write(f"  ✅ Created_at is already correct: {current_created_at}")
                else:
                    self.stdout.write("  🔄 Change needed:")
                    self.stdout.write(f"     Current:  {current_created_at}")
                    self.stdout.write(f"     Correct:  {old_created_at}")

                    if not dry_run:
                        member.created_at = old_created_at
                        member.save(update_fields=["created_at"])
                        self.stdout.write("  ✅ Updated!")

                success_count += 1

            except Exception as e:
                self.stdout.write(f"  ❌ Error processing member {member.original_id}: {e}")
                error_count += 1
                continue

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("SUMMARY:")
        self.stdout.write(f"  Successfully processed: {success_count}")
        self.stdout.write(f"  Errors: {error_count}")
        self.stdout.write(f"  Total: {total_members}")

        if dry_run:
            self.stdout.write("\n⚠️  Run without --dry-run to execute changes")
