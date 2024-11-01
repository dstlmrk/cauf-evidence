from competitions.models import Competition
from rest_framework import serializers


class CompetitionSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    division = serializers.StringRelatedField()
    age_restriction = serializers.StringRelatedField()
    season = serializers.StringRelatedField()

    class Meta:
        model = Competition
        fields = "__all__"

    def get_type(self, obj: Competition) -> str:
        return obj.get_type_display()

    def get_division(self, obj: Competition) -> str:
        return obj.division.name

    def get_age_restriction(self, obj: Competition) -> str:
        return obj.age_restriction.name if obj.age_restriction else ""

    def get_season(self, obj: Competition) -> str:
        return obj.season.name
