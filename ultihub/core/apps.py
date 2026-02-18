from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self) -> None:
        from auditlog.registry import auditlog
        from clubs.models import Club, Team
        from competitions.models import (
            AgeLimit,
            Competition,
            CompetitionApplication,
            Division,
            Season,
        )
        from finance.models import Invoice
        from international_tournaments.models import (
            InternationalTournament,
            MemberAtInternationalTournament,
            TeamAtInternationalTournament,
        )
        from members.models import CoachLicence, Member, Transfer
        from tournaments.models import MemberAtTournament, TeamAtTournament, Tournament
        from users.models import Agent, AgentAtClub

        import core.tasks  # noqa: F401
        from core.models import AppSettings

        for model in [
            Club,
            Team,
            AgeLimit,
            Competition,
            CompetitionApplication,
            Division,
            Season,
            AppSettings,
            Invoice,
            InternationalTournament,
            MemberAtInternationalTournament,
            TeamAtInternationalTournament,
            CoachLicence,
            Member,
            Transfer,
            MemberAtTournament,
            TeamAtTournament,
            Tournament,
            Agent,
            AgentAtClub,
        ]:
            auditlog.register(model, exclude_fields=["created_at", "updated_at"])
