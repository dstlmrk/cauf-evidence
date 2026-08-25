from django.db.models.signals import post_delete
from django.dispatch import receiver

from clubs.models import Club, ClubLogo


@receiver(post_delete, sender=ClubLogo)
def clear_logo_stamp_on_delete(
    sender: type[ClubLogo], instance: ClubLogo, **kwargs: object
) -> None:
    """
    Keep Club.logo_updated_at honest however the logo goes away - a service call, the admin
    delete action or a cascade - so nothing is left pointing at a logo that no longer exists.
    """
    if instance.is_approved:
        Club.objects.filter(pk=instance.club_id).update(logo_updated_at=None)
