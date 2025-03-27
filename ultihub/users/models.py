from core.models import AuditModel
from django.contrib.auth.models import User
from django.db import models


class NewAgentRequest(AuditModel):
    email = models.EmailField(unique=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_primary = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.DO_NOTHING,
        # Club is optional because the user might not be associated
        # with a club but is still needed for staff/superuser
        null=True,
        blank=True,
        help_text="The club the agent has permission to manage",
    )
    invited_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
    )


class Agent(AuditModel):
    picture_url = models.URLField(blank=True)
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name="agent")
    has_email_notifications_enabled = models.BooleanField(
        default=True, verbose_name="Email notifications enabled"
    )

    def __str__(self) -> str:
        return f"<Agent({self.user.email})>"


class AgentAtClub(AuditModel):
    agent = models.ForeignKey(
        Agent,
        on_delete=models.PROTECT,
    )
    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.PROTECT,
    )
    is_primary = models.BooleanField(
        default=False,
    )
    is_active = models.BooleanField(
        default=True,
    )
    invited_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
    )

    class Meta:
        unique_together = ("agent", "club")

    def __str__(self) -> str:
        return f"<AgentAtClub({self.pk}, agent={self.agent.user.email}, club={self.club.name})>"
