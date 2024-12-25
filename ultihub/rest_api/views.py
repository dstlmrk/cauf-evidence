from competitions.models import Competition
from rest_framework.generics import ListAPIView

from .serializers import CompetitionSerializer


class CompetitionView(ListAPIView):
    queryset = (
        Competition.objects.select_related("age_limit", "season", "division").order_by("-pk").all()
    )
    serializer_class = CompetitionSerializer
