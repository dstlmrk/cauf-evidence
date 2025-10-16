from django.db import models


class EnvironmentEnum(models.IntegerChoices):
    OUTDOOR = 1, "Outdoor"
    INDOOR = 2, "Indoor"
    BEACH = 3, "Beach"


class ApplicationStateEnum(models.IntegerChoices):
    AWAITING_PAYMENT = 1, "Awaiting Payment"
    PAID = 2, "Paid"
    ACCEPTED = 3, "Accepted"
    DECLINED = 4, "Declined"


class CompetitionFeeTypeEnum(models.IntegerChoices):
    FREE = 1, "Free"
    DISCOUNTED = 2, "Discounted"
    REGULAR = 3, "Regular"
