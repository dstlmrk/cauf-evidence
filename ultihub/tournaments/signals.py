from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from tournaments.models import TeamAtTournament


@receiver(post_save, sender=TeamAtTournament)
def update_tournament_winners_on_save(
    sender: type[TeamAtTournament], instance: TeamAtTournament, **kwargs: object
) -> None:
    """Update tournament winners when a team's results are modified."""
    # Only update if final_placement or spirit_avg might have changed
    # We update on every save to keep it simple and consistent
    instance.tournament.update_winners()


@receiver(post_delete, sender=TeamAtTournament)
def update_tournament_winners_on_delete(
    sender: type[TeamAtTournament], instance: TeamAtTournament, **kwargs: object
) -> None:
    """Update tournament winners when a team is deleted."""
    instance.tournament.update_winners()
