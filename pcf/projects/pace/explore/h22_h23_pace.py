"""pace exploration (2026-11-10): H22 (expected pace on every play) and H23 (are our features
consistent game to game?).

The gap: game seconds from the previous snap of the same drive and quarter to this one (0-60 s;
nflverse has no play clock). Quarters 1-4 of regular-season games, 2006-2024.

Expected pace, fit with gradient-boosted trees, out of fold (each season predicted by a model fit
on the other seasons' folds, five folds of seasons):
- `ceo`: the CEO's H22 inputs, win chance and expected points (plus the season, so pace is
  measured against that season's league).
- `clock`: Claude's addition, labelled as such: the same, plus what stops or slows the clock
  (the previous snap an incompletion, out of bounds, a penalty or no-play, a spike, a sack;
  timeouts since the previous snap; the quarter and seconds left in the half).
Pace over expected per team-game is the mean of (gap - expected) over the offense's snaps.
Negative is fast.

The usual way, neutral only (win chance 20-80%, downs 1-3, outside the last 2 minutes):
- `neutral_secs`: mean gap over neutral snaps (seconds per snap, as pace sites measure it);
- `tempo`: schemes-v2's tempo, neutral snaps after an in-bounds run (5-60 s).

Tests: (1) consistency (`pcf.validation.consistency`, unit team-season, regular season);
(2) does each measure's season-to-date mean forecast the next game's plays, beyond the line?
(3) how much each measure is really pass rate (r with the game's pass rate).

Run from pcf/projects/pace/explore: PYTHONUTF8=1 ../../../.venv/Scripts/python.exe h22_h23_pace.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from common import plays, prior_mean, r2
from sklearn.ensemble import HistGradientBoostingRegressor

from pcf.config import get_config
from pcf.validation.consistency import consistency

c = pl.col
CEO = ["wp", "ep", "season"]
CLOCK = [*CEO, "prev_incomplete", "prev_oob", "prev_penalty", "prev_noplay", "prev_spike", "prev_sack", "timeouts_before", "qtr", "half_seconds_remaining"]


def expected(s: pl.DataFrame, cols: list[str], name: str) -> pl.DataFrame:
    seasons = np.array(sorted(s["season"].unique()))
    fold = {int(x): i % 5 for i, x in enumerate(seasons)}
    s = s.with_columns(fold=c("season").replace_strict(fold))
    pred = np.full(s.height, np.nan)
    X = s.select(cols).to_numpy().astype(float)
    y = s["gap"].to_numpy().astype(float)
    f = s["fold"].to_numpy()
    for k in range(5):
        m = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.1, max_leaf_nodes=63, random_state=0)
        m.fit(X[f != k], y[f != k])
        pred[f == k] = m.predict(X[f == k])
    res = y - pred
    print(f"expected pace `{name}`: R2 of the gap {1 - res.var() / y.var():.3f}")
    return s.with_columns(pl.Series(f"exp_{name}", pred)).drop("fold")


def main() -> None:
    p = plays()
    s = p.filter(c("gap").is_not_null() & (c("qtr") <= 4) & c("wp").is_not_null() & c("ep").is_not_null())
    print(f"{s.height} snaps with a gap; mean {s['gap'].mean():.1f} s")
    s = expected(s, CEO, "ceo")
    s = expected(s, CLOCK, "clock")
    s = s.with_columns(
        oe_ceo=c("gap") - c("exp_ceo"),
        oe_clock=c("gap") - c("exp_clock"),
        after_run=(c("prev_rush") == 1) & (c("prev_oob") == 0) & (c("prev_penalty") == 0) & (c("prev_noplay") == 0),
    )
    tg = s.group_by("game_id", "season", "week", "team").agg(
        pace_oe_ceo=c("oe_ceo").mean(),
        pace_oe_clock=c("oe_clock").mean(),
        neutral_secs=c("gap").filter(c("neutral")).mean(),
        tempo=c("gap").filter(c("neutral") & c("after_run") & (c("gap") >= 5)).mean(),
        snaps_full=pl.len(),
        snaps_neutral=c("neutral").sum(),
        no_huddle_all=c("no_huddle").mean(),
        no_huddle_neutral=c("no_huddle").filter(c("neutral")).mean(),
    )
    g = pl.read_parquet(get_config().zone("interim") / "pace" / "team_games.parquet")
    tg = g.join(tg, on=["game_id", "season", "week", "team"], how="left")
    sched = pl.read_parquet(get_config().zone("raw") / "nflverse" / "schedules" / "games.parquet").select("game_id", "spread_line", "total_line")
    tg = tg.join(sched, on="game_id", how="left").with_columns(team_spread=pl.when(c("home")).then(c("spread_line")).otherwise(-c("spread_line")))
    tg.write_parquet(get_config().zone("interim") / "pace" / "team_games_pace.parquet")
    print("snaps per team-game used: full sample", round(tg["snaps_full"].mean(), 1), "| neutral", round(tg["snaps_neutral"].mean(), 1))

    measures = ["pace_oe_ceo", "pace_oe_clock", "neutral_secs", "tempo", "no_huddle_all", "no_huddle_neutral"]
    print("\n=== how much each pace measure is pass rate: r with the same game's pass rate and PROE")
    for m in measures:
        d = tg.drop_nulls([m, "pass_rate"])
        print(f"{m}: r with pass rate {np.corrcoef(d[m], d['pass_rate'])[0, 1]:+.2f}, with PROE {np.corrcoef(d[m], d['proe_game'])[0, 1]:+.2f}")

    print("\n=== H22 / H23: consistency, 2006-2024 regular season (unit: team-season)")
    allm = [*measures, "proe_game", "proe_neutral_game", "epa_db_adj", "sr_db_adj", "plays", "dropbacks", "runs", "pass_rate"]
    with pl.Config(tbl_rows=30, tbl_width_chars=220, float_precision=2):
        print(consistency(tg, allm))
        print("2020-2024")
        print(consistency(tg.filter(c("season") >= 2020), allm))

    print("\n=== H22: season-to-date mean (games before this one) against the next game's plays")
    for m in measures:
        tg = prior_mean(tg, m)
    tg = prior_mean(tg, "plays")
    d = tg.filter(c("week") >= 4).drop_nulls([f"{m}_prior" for m in measures] + ["team_spread", "total_line", "plays_prior"])
    y = d["plays"].to_numpy()
    line = d.select("team_spread", "total_line").to_numpy()
    base = r2(y, line)
    print(f"{d.height} team-games, weeks 4+. Line alone (team's spread, total): R2 {base:.4f}; + plays so far: {r2(y, np.column_stack([line, d['plays_prior']])):.4f}")
    for m in measures:
        x = d[f"{m}_prior"].to_numpy()
        print(f"{m}: r with next plays {np.corrcoef(x, y)[0, 1]:+.3f}; R2 with the line {r2(y, np.column_stack([line, x])):.4f}; with the line and plays so far {r2(y, np.column_stack([line, d['plays_prior'], x])):.4f}")
    both = r2(y, np.column_stack([line, d["plays_prior"], d["pace_oe_clock_prior"], d["neutral_secs_prior"], d["tempo_prior"]]))
    print(f"line + plays so far + clock-aware pace + neutral secs + tempo: {both:.4f}")


if __name__ == "__main__":
    main()
