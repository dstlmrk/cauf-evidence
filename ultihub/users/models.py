from core.models import AuditModel
from django.contrib.auth.models import User
from django.db import models


class NewAgentRequest(AuditModel):
    email = models.EmailField(unique=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
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


class Agent(models.Model):
    picture_url = models.URLField()
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="agent")

    def __str__(self) -> str:
        return f"<Agent({self.pk})>"
