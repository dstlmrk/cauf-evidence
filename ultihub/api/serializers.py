from clubs.models import Club
from competitions.models import Competition, CompetitionApplication
from members.models import Member
from rest_framework import serializers
from tournaments.models import MemberAtTournament, TeamAtTournament, Tournament


class TournamentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tournament
        fields = ["id", "name", "start_date", "end_date", "location"]


class CompetitionApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompetitionApplication
        fields = ["id", "team_name", "final_placement"]


class CompetitionSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    division = serializers.StringRelatedField()
    age_limit = serializers.StringRelatedField()
    season = serializers.StringRelatedField()
    tournaments = TournamentSerializer(many=True, read_only=True)
    accepted_applications = CompetitionApplicationSerializer(
        many=True, read_only=True, source="applications"
    )

    class Meta:
        model = Competition
        fields = [
            "id",
            "name",
            "type",
            "division",
            "age_limit",
            "season",
            "tournaments",
            "accepted_applications",
        ]

    def get_type(self, obj: Competition) -> str:
        return obj.get_type_display()

    def get_division(self, obj: Competition) -> str:
        return obj.division.name

    def get_age_limit(self, obj: Competition) -> str:
        return obj.age_limit.name if obj.age_limit else ""

    def get_season(self, obj: Competition) -> str:
        return obj.season.name


class ClubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Club
        fields = [
            "id",
            "name",
            "short_name",
            "email",
            "website",
            "city",
            "organization_name",
            "identification_number",
        ]


class MemberSerializer(serializers.ModelSerializer):
    birth_year = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = ["id", "full_name", "birth_year"]

    def get_birth_year(self, obj: Member) -> int:
        return obj.birth_date.year

    def get_full_name(self, obj: Member) -> str:
        return obj.full_name


class MemberAtTournamentSerializer(serializers.ModelSerializer):
    member = MemberSerializer()

    class Meta:
        model = MemberAtTournament
        fields = ["jersey_number", "is_captain", "is_spirit_captain", "is_coach", "member"]


class TeamAtTournamentSerializer(serializers.ModelSerializer):
    members = MemberAtTournamentSerializer(many=True, read_only=True)
    team_name = serializers.CharField(source="application.team_name", read_only=True)

    class Meta:
        model = TeamAtTournament
        fields = ["id", "team_name", "final_placement", "spirit_avg", "members"]

    def get_team_name(self, obj: TeamAtTournament) -> str:
        return obj.application.team_name


class TeamAtTournamentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamAtTournament
        fields = ["final_placement", "spirit_avg"]

    def validate_final_placement(self, value):  # type: ignore
        if value < 1:
            raise serializers.ValidationError("Final placement must be a positive integer.")
        return value

    def validate_spirit_avg(self, value):  # type: ignore
        if value < 0 or value > 20:
            raise serializers.ValidationError("Spirit average must be between 0 and 20.")
        return value


class CompetitionApplicationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompetitionApplication
        fields = ["final_placement"]

    def validate_final_placement(self, value):  # type: ignore
        if value < 1:
            raise serializers.ValidationError("Final placement must be a positive integer.")
        return value
