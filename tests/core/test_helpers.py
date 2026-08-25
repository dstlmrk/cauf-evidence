from core.helpers import get_default_season
from tests.factories import (
    CompetitionFactory,
    InternationalTournamentFactory,
    SeasonFactory,
    TournamentFactory,
)


class TestGetDefaultSeason:
    def test_returns_none_when_no_season_exists(self):
        assert get_default_season("competition") is None

    def test_returns_newest_season_when_it_has_content(self):
        SeasonFactory(name="2025")
        newest = SeasonFactory(name="2026")
        CompetitionFactory(season=newest)

        assert get_default_season("competition") == newest

    def test_skips_empty_newest_season(self):
        populated = SeasonFactory(name="2025")
        SeasonFactory(name="2026")
        CompetitionFactory(season=populated)

        assert get_default_season("competition") == populated

    def test_skips_all_trailing_empty_seasons(self):
        populated = SeasonFactory(name="2025")
        SeasonFactory(name="2026")
        SeasonFactory(name="2027")
        CompetitionFactory(season=populated)

        assert get_default_season("competition") == populated

    def test_falls_back_to_newest_season_when_none_has_content(self):
        SeasonFactory(name="2025")
        newest = SeasonFactory(name="2026")

        assert get_default_season("competition") == newest

    def test_season_with_competitions_but_no_tournaments_is_empty_for_tournaments(self):
        with_tournament = SeasonFactory(name="2025")
        without_tournament = SeasonFactory(name="2026")
        TournamentFactory(competition=CompetitionFactory(season=with_tournament))
        CompetitionFactory(season=without_tournament)

        assert get_default_season("competition__tournaments") == with_tournament

    def test_international_tournaments_relation(self):
        populated = SeasonFactory(name="2025")
        SeasonFactory(name="2026")
        InternationalTournamentFactory(season=populated)

        assert get_default_season("international_tournaments") == populated

    def test_duplicate_join_rows_do_not_break_lookup(self):
        populated = SeasonFactory(name="2025")
        SeasonFactory(name="2026")
        CompetitionFactory(season=populated)
        CompetitionFactory(season=populated)

        assert get_default_season("competition") == populated
