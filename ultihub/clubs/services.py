import io
import logging

from core.tasks import send_email
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils.timezone import now
from PIL import Image, ImageOps
from users.models import Agent, AgentAtClub

from clubs.models import Club, ClubLogo, ClubNotification

logger = logging.getLogger(__name__)

LOGO_LARGE_SIZE = 512
LOGO_SMALL_SIZE = 96
LOGO_MIN_SIZE = 256
# Small tolerance so an image that is a pixel or two off square is still accepted
LOGO_MAX_ASPECT_RATIO = 1.02
LOGO_MAX_BYTES = 5 * 1024 * 1024
LOGO_ALLOWED_FORMATS = ("PNG", "JPEG", "WEBP")


def notify_club(club: Club, subject: str, message: str) -> None:
    logger.info("Notifying club %s about %s", club.name, subject)

    club_agents = AgentAtClub.objects.filter(club=club, is_active=True)
    ClubNotification.objects.bulk_create(
        [
            ClubNotification(agent_at_club=agent_at_club, subject=subject, message=message)
            for agent_at_club in club_agents
        ]
    )

    agents_with_email = club_agents.filter(
        agent__has_email_notifications_enabled=True
    ).select_related("agent__user")
    for agent_at_club in agents_with_email:
        send_email(subject, message, to=[agent_at_club.agent.user.email])


def build_logo_variants(uploaded_file: UploadedFile) -> tuple[bytes, bytes]:
    """
    Render an uploaded image into the two square WebP variants that are served. Input is
    validated as square, so the padding here only absorbs the tolerated pixel or two and
    never crops anything away.
    """
    with Image.open(uploaded_file) as opened:
        image = (ImageOps.exif_transpose(opened) or opened).convert("RGBA")

    # Never upscale; blowing a small logo up to the full size only costs bytes and looks blurry
    large_size = min(LOGO_LARGE_SIZE, max(image.size))
    return _render_square_webp(image, large_size), _render_square_webp(image, LOGO_SMALL_SIZE)


def _render_square_webp(image: Image.Image, size: int) -> bytes:
    padded = ImageOps.pad(image, (size, size), method=Image.Resampling.LANCZOS, color=(0, 0, 0, 0))
    buffer = io.BytesIO()
    padded.save(buffer, format="WEBP", quality=90, method=6)
    return buffer.getvalue()


@transaction.atomic
def save_club_logo(club: Club, uploaded_file: UploadedFile) -> ClubLogo:
    """
    Store an uploaded image as the club's logo waiting for approval, replacing whatever else
    was waiting. Any already approved logo stays in use until this one is approved.
    """
    logger.info("Saving logo of club %s for approval", club.pk)

    large, small = build_logo_variants(uploaded_file)
    ClubLogo.objects.filter(club=club, is_approved=False).delete()
    return ClubLogo.objects.create(club=club, large=large, small=small)


@transaction.atomic
def approve_club_logo(logo: ClubLogo, approved_by: Agent | None = None) -> None:
    logger.info("Approving logo %s of club %s", logo.pk, logo.club_id)

    # The logo currently in use has to go first; a club can only hold one approved logo
    ClubLogo.objects.filter(club_id=logo.club_id, is_approved=True).exclude(pk=logo.pk).delete()

    logo.is_approved = True
    logo.approved_at = now()
    logo.approved_by = approved_by
    logo.save(update_fields=["is_approved", "approved_at", "approved_by", "updated_at"])

    club = logo.club
    club.logo_updated_at = logo.approved_at
    club.save(update_fields=["logo_updated_at", "updated_at"])


@transaction.atomic
def reject_club_logo(logo: ClubLogo) -> None:
    logger.info("Rejecting logo %s of club %s", logo.pk, logo.club_id)
    logo.delete()


@transaction.atomic
def remove_club_logo(club: Club, *, pending_only: bool = False) -> None:
    logger.info("Removing logo of club %s (pending_only=%s)", club.pk, pending_only)

    logos = ClubLogo.objects.filter(club=club)
    if pending_only:
        logos = logos.filter(is_approved=False)
    logos.delete()
