"""Standings, seeds and seed locks (`pcf.data.standings`): tiebreakers on small hand-made cases,
and (with the local tables) every real playoff field 2016-2024."""

from datetime import UTC, datetime

import polars as pl
import pytest

from pcf.data import standings as S

c = pl.col


def g(home, away, r):
    return S.Game(home, away, r)


def test_a_division_tie_goes_to_the_head_to_head_winner():
    # BUF won at MIA and lost at home to NE; MIA beat NE: both 1-1
    rec = S.Record([g("MIA", "BUF", 0.0), g("BUF", "NE", 0.0), g("MIA", "NE", 1.0)])
    assert rec.pct("BUF") == rec.pct("MIA") == 0.5
    assert S.best(["MIA", "BUF"], rec, "division") == "BUF"


def test_then_division_record_when_they_split():
    rec = S.Record([
        g("BUF", "MIA", 1.0), g("MIA", "BUF", 1.0),  # split
        g("BUF", "NYJ", 1.0), g("MIA", "NYJ", 0.0),  # BUF better in the division
        g("MIA", "KC", 1.0), g("BUF", "KC", 0.0),  # same overall record
    ])  # fmt: skip
    assert rec.pct("BUF") == rec.pct("MIA")
    assert S.best(["MIA", "BUF"], rec, "division") == "BUF"


def test_a_three_team_conference_tie_goes_to_a_sweep():
    rec = S.Record([g("BUF", "KC", 1.0), g("BUF", "HOU", 1.0), g("KC", "HOU", 1.0),
                    g("BUF", "BAL", 0.0), g("KC", "BAL", 1.0), g("HOU", "BAL", 1.0)])  # fmt: skip
    # BUF 2-1, KC 2-1, HOU 1-2: BUF beat each of the others
    assert S.best(["KC", "BUF"], rec, "conference") == "BUF"


def test_a_tie_nothing_breaks_is_unresolved():
    rec = S.Record([g("BUF", "NE", 1.0), g("KC", "LV", 1.0)])
    with pytest.raises(S.Unresolved):
        S.best(["BUF", "KC"], rec, "conference")


def _season(last_known: bool = False, playoff_row: bool = False) -> pl.DataFrame:
    """A tiny NFL season: week 1 played (BUF beat MIA), week 2 the final week (MIA@NE, BUF@NYJ),
    optionally a playoff row listed later."""
    t = pl.Datetime("us", "UTC")
    d = lambda day: datetime(2023, 9, day, 17, tzinfo=UTC)  # noqa: E731
    rows = {
        "season": [2023, 2023, 2023], "game_type": ["REG"] * 3, "week": [1, 2, 2],
        "home_team": ["BUF", "NE", "NYJ"], "away_team": ["MIA", "MIA", "BUF"],
        "kickoff": [d(10), d(17), d(17)], "known_at": [d(1)] * 3,
        "home_score": [20, 10 if last_known else None, None],
        "away_score": [10, 3 if last_known else None, None],
        "result_known_at": [d(11), d(18) if last_known else None, None],
    }  # fmt: skip
    if playoff_row:
        for k, v in {"season": 2023, "game_type": "REG", "week": 9, "home_team": "BUF",
                     "away_team": "NE", "kickoff": d(25), "known_at": d(24), "home_score": None,
                     "away_score": None, "result_known_at": None}.items():  # fmt: skip
            rows[k].append(v)
    types = {"kickoff": t, "known_at": t, "result_known_at": t, "season": pl.Int32}
    return pl.DataFrame(rows, schema_overrides=types)


def test_no_locks_outside_the_nfl():
    t = pl.Datetime("us", "UTC")
    game = pl.DataFrame(
        {"season": [2023], "game_type": ["REG"], "week": [1], "home_team": ["AAA"],
         "away_team": ["BBB"], "kickoff": [datetime(2023, 9, 10, tzinfo=UTC)],
         "known_at": [datetime(2023, 9, 1, tzinfo=UTC)], "home_score": [None],
         "away_score": [None], "result_known_at": [None]},
        schema_overrides={"kickoff": t, "known_at": t, "result_known_at": t, "season": pl.Int32},
    )  # fmt: skip
    assert S.final_week_locks(game, 2023, datetime(2023, 9, 9, tzinfo=UTC)).is_empty()


def test_no_locks_before_the_final_week_or_after_its_results():
    early = datetime(2023, 9, 9, tzinfo=UTC)  # week 1 not played yet
    assert S.final_week_locks(_season(), 2023, early).is_empty()
    late = datetime(2023, 9, 19, tzinfo=UTC)  # a final-week result is known
    assert S.final_week_locks(_season(last_known=True), 2023, late).is_empty()
    run = datetime(2023, 9, 16, 16, tzinfo=UTC)
    assert S.final_week_locks(_season(), 2023, run).height == 32


def test_rows_listed_after_the_moment_are_ignored():
    run = datetime(2023, 9, 16, 16, tzinfo=UTC)
    assert S.final_week_locks(_season(playoff_row=True), 2023, run).equals(
        S.final_week_locks(_season(), 2023, run)
    )


def test_an_outcome_left_unresolved_never_makes_a_lock():
    # two teams, nothing to separate them: every outcome is unresolved
    lk = S.locks([g("BUF", "KC", 0.5)], [], 2023)
    assert not any(v["locked"] for v in lk.values())


@pytest.mark.local_data
def test_seeds_match_every_real_playoff_field():
    from pcf.data.gateway import Gateway

    src = Gateway().source
    game = src.part("game", "schedule").join(
        src.part("game", "result").select("game_id", "home_score", "away_score",
                                          result_known_at="known_at"),
        on="game_id", how="left",
    )  # fmt: skip
    for season in range(2016, 2025):
        reg = game.filter((c("season") == season) & (c("game_type") == "REG")
                          & c("home_score").is_not_null())  # fmt: skip
        sd = S.seeds(S._games(reg), season)
        wc = game.filter((c("season") == season) & (c("game_type") == "WC"))
        for h, a in wc.select("home_team", "away_team").iter_rows():
            assert sd[h] < sd[a] and sd[h] + sd[a] == 9, (season, h, a)
    last = game.filter((c("season") == 2020) & (c("week") == 17))["kickoff"].min()
    lk = S.final_week_locks(game, 2020, last)
    assert lk.filter(c("seed_locked") == 1)["team"].to_list() == ["KC"]
