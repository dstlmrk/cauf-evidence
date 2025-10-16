from django.db import models


class InternationalTournamentTypeEnum(models.IntegerChoices):
    NATIONAL_TEAM = 1, "National Team"
    EUROPEAN_LEAGUE = 2, "European League"
    OTHERS = 3, "Others"
