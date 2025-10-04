from django.db import models
from solo.models import SingletonModel


class AuditModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AppSettings(SingletonModel):
    email_required = models.BooleanField(
        default=False,
        help_text=(
            "Require email for members 15+ years and legal guardian email for children under 15"
        ),
    )
    email_verification_required = models.BooleanField(
        default=False,
        help_text="Block adding members to tournament rosters if email is not verified",
    )
    min_age_verification_required = models.BooleanField(
        default=False,
        help_text=(
            "Enforce minimum age validation for tournaments "
            "(when disabled, only max age is checked)"
        ),
    )
    team_management_enabled = models.BooleanField(
        default=False,
        help_text="Show/hide team management UI in club administration",
    )
    transfers_enabled = models.BooleanField(
        default=False,
        help_text="Show/hide player transfer UI between clubs",
    )

    class Meta:
        verbose_name = "Application Settings"
