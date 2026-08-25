from finance.forms import SeasonFeesCheckForm

from tests.factories import CompetitionFactory, SeasonFactory


class TestSeasonFeesCheckForm:
    def test_defaults_to_newest_season_with_competitions(self):
        with_competitions = SeasonFactory(name="2026")
        SeasonFactory(name="2027")
        CompetitionFactory(season=with_competitions)

        assert SeasonFeesCheckForm().initial["season"] == with_competitions

    def test_keeps_explicit_initial_season(self):
        with_competitions = SeasonFactory(name="2026")
        empty = SeasonFactory(name="2027")
        CompetitionFactory(season=with_competitions)

        assert SeasonFeesCheckForm(initial={"season": empty}).initial["season"] == empty
