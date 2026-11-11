"""The scorecard's interval: n whole weeks drawn from the backtest's same week numbers."""

import polars as pl

from pcf.validation.ledger_score import against_close, interval


def weeks(losses: dict[int, float], rows: int = 100) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "season": [2020] * len(losses),
            "week": list(losses),
            "rows": [rows] * len(losses),
            "loss": [v * rows for v in losses.values()],
        }
    )


def test_identical_weeks_give_a_point_interval():
    lo, hi = interval(weeks({1: 0.04, 2: 0.04, 3: 0.04}), [1, 2], seed=1)
    assert abs(lo - 0.04) < 1e-12 and abs(hi - 0.04) < 1e-12


def test_only_the_live_week_numbers_are_drawn():
    lo, hi = interval(weeks({1: 0.02, 2: 0.03, 17: 0.10}), [1, 2], seed=1)
    assert 0.02 <= lo <= hi <= 0.03


def test_more_weeks_give_a_narrower_interval():
    pool = pl.concat(
        weeks({w: 0.02 + 0.002 * ((w + s) % 5) for w in range(1, 19)}).with_columns(
            season=pl.lit(s)
        )
        for s in range(2016, 2025)
    )
    lo1, hi1 = interval(pool, [5], seed=1)
    lo8, hi8 = interval(pool, list(range(1, 9)), seed=1)
    assert hi8 - lo8 < hi1 - lo1


LINES = pl.DataFrame(
    {
        "game_id": ["g1", "g2", "g3"],
        "spread_line": [6.0, -2.0, None],  # g3 has no line: left out of both sides
        "total_line": [44.0, 41.0, 47.0],
        "home_moneyline": [-250, 110, -400],
        "away_moneyline": [210, -130, 320],
    }
)


def test_elo_is_set_against_the_close_on_the_same_games():
    scored = pl.DataFrame(
        {"game_id": ["g1", "g2", "g3"], "y": [7.0, -3.0, 10.0], "q50": [3.0, 0.0, 4.0]}
    )
    row = against_close(scored, "elo/margin", LINES)
    assert row["games"] == 2
    assert row["elo"] == (4 + 3) / 2
    assert row["close"] == (1 + 1) / 2
    assert row["behind_close"] == row["elo"] - row["close"] > 0


def test_a_win_chance_is_set_against_the_no_vig_moneyline():
    scored = pl.DataFrame({"game_id": ["g1", "g2"], "y": [1.0, 0.0], "mean": [0.6, 0.4]})
    row = against_close(scored, "elo/win", LINES)
    assert row["measure"] == "log loss"
    assert row["games"] == 2
    assert row["close"] < row["elo"]  # the close leaned the right way harder in both games
