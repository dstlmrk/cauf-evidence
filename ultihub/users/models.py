from core.models import AuditModel
from django.contrib.auth.models import User
from django.db import models


class NewAgentRequest(AuditModel):
    email = models.EmailField(unique=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)


class Agent(models.Model):
    picture_url = models.URLField()
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="agent")

    def __str__(self) -> str:
        return f"<Agent({self.pk})>"
