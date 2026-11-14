"""team-efficiency spot-check of R6 (the CEO's pick, 2026-11-14): efficiency adds nothing to Elo's
margin. Is that because Elo already holds it, or because the test is too weak?

Same rows and walk as downstream.py (2017-2024 regular-season games, each fit on earlier seasons
only): the ratings `off_next3_ridge` published (made before each game) and Elo's margin history.
1. How much of efficiency Elo already holds: the correlation of their margins.
2. Each alone, and together, against the result.
3. The games where they disagree most (efficiency's margin minus Elo's, in fifths): who's closer?
4. By the week of the season.
5. A stronger yardstick: the closing spread (known at kickoff, so a research check, not a
   Saturday forecast). Does efficiency, or Elo, add to the line?
Writes spotcheck_r6.txt. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/build/spotcheck_r6.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import downstream as D  # noqa: E402

from pcf.data.tables.store import read_part  # noqa: E402

c = pl.col
HERE = Path(__file__).parent
S = D.SEASONS


def main() -> None:
    lines = []

    def say(t: str = "") -> None:
        print(t, flush=True)
        lines.append(t)

    rat = D.latest("team-efficiency", "off_next3_ridge").select(
        "game_id", "team", "off_ridge", "def_ridge"
    )
    games = read_part("game", "schedule", seasons=S).select("game_id", "home_team").collect()
    res = read_part("game", "result", seasons=S).select(
        "game_id", "home_score", "away_score"
    ).collect()  # fmt: skip
    sched = (
        read_part("team_game", "schedule", seasons=S)
        .filter((c("game_type") == "REG") & c("home"))
        .select("game_id", "season", "week")
        .collect()
    )
    line = (
        read_part("team_game", "pregame", seasons=S).select("game_id", "team", "spread").collect()
    )
    elo = D.latest("elo", "margin").select("game_id", elo="mean")
    home = rat.join(games, left_on=["game_id", "team"], right_on=["game_id", "home_team"])
    away = rat.join(games, on="game_id").filter(c("team") != c("home_team"))
    g = (
        elo.join(home.select("game_id", "team", h_off="off_ridge", h_def="def_ridge"), on="game_id")
        .join(away.select("game_id", a_off="off_ridge", a_def="def_ridge"), on="game_id")
        .join(res, on="game_id")
        .join(sched, on="game_id")
        .join(line, on=["game_id", "team"], how="left")
        .with_columns(
            margin=(c("home_score") - c("away_score")).cast(pl.Float64),
            off_gap=c("h_off") - c("a_off"),
            def_gap=c("a_def") - c("h_def"),
            vegas=-c("spread"),  # the home team's spread: negative when favoured
        )
        .drop_nulls(["margin", "elo", "off_gap", "def_gap"])
        .sort("season", "week", "game_id")
    )
    g = g.with_columns(
        eff=pl.Series(D.walk(g, "margin", ["off_gap", "def_gap"])),  # efficiency + home alone
        elo_refit=pl.Series(D.walk(g, "margin", ["elo"])),
        both=pl.Series(D.walk(g, "margin", ["elo", "off_gap", "def_gap"])),
    )
    every = g
    g = g.filter(c("season") >= S[1])

    def miss(x: pl.DataFrame, col: str) -> float:
        return float((x["margin"] - x[col]).abs().mean())

    say("R6 spot-check: efficiency and Elo's margin, 2017-2024 regular season, walk-forward.")
    say(f"Games: {g.height:,}. Mean absolute miss in points (lower is better).")
    say("")
    r = g.select(pl.corr("eff", "elo_refit")).item()
    say(f"1. Efficiency's margin and Elo's correlate at r = {r:.2f}: Elo holds {r * r:.0%} of")
    say("   efficiency's spread between games.")
    say("")
    say("2. Each alone and together:")
    for nm, col in (("Elo refit", "elo_refit"), ("efficiency alone", "eff"), ("both", "both")):
        say(f"   {nm:17s} {miss(g, col):.3f}")
    say(f"   both against Elo: {D.change(g, 'both', 'elo_refit', 'margin')}")
    say(f"   efficiency against Elo: {D.change(g, 'eff', 'elo_refit', 'margin')}")
    say("")
    say("3. Where they disagree (efficiency's margin minus Elo's, fifths of games):")
    say("   fifth | mean gap | games | Elo miss | efficiency miss | both miss | both vs Elo")
    g = g.with_columns(gap=c("eff") - c("elo_refit"))
    g = g.with_columns(fifth=(c("gap").rank("ordinal") * 5 / (g.height + 1)).floor().cast(pl.Int8))
    for q in range(5):
        x = g.filter(c("fifth") == q)
        say(f"   {q + 1}     | {x['gap'].mean():+6.2f}   | {x.height:4d}  | "
            f"{miss(x, 'elo_refit'):.3f}   | {miss(x, 'eff'):.3f}          | {miss(x, 'both'):.3f}"
            f"     | {D.change(x, 'both', 'elo_refit', 'margin').split(';')[0]}")  # fmt: skip
    big = g.filter(c("gap").abs() >= 3.0)
    side = big.select(
        (((c("margin") - c("elo_refit")) * c("gap")) > 0).mean().alias("eff_side")
    ).item()  # fmt: skip
    say(f"   Games where they differ by 3+ points: {big.height}; the result moved toward")
    say(f"   efficiency's side in {side:.1%} of them (50% = no information).")
    say("")
    say("4. By the week of the season (both against Elo):")
    for nm, w in (("weeks 1-4", c("week") <= 4), ("weeks 5-9", c("week").is_between(5, 9)),
                  ("weeks 10+", c("week") >= 10)):  # fmt: skip
        say(f"   {nm:10s} {D.change(g.filter(w), 'both', 'elo_refit', 'margin')}")
    say("")
    v = every.drop_nulls("vegas")
    v = v.with_columns(
        line_refit=pl.Series(D.walk(v, "margin", ["vegas"])),
        line_eff=pl.Series(D.walk(v, "margin", ["vegas", "off_gap", "def_gap"])),
        line_elo=pl.Series(D.walk(v, "margin", ["vegas", "elo"])),
    ).filter(c("season") >= S[1])
    say("5. A stronger yardstick, the closing spread (known at kickoff):")
    lo, el = miss(v, "line_refit"), miss(v, "elo_refit")
    say(f"   the line alone misses by {lo:.3f}; Elo alone {el:.3f}")
    say(f"   line + efficiency against the line: {D.change(v, 'line_eff', 'line_refit', 'margin')}")
    say(f"   line + Elo against the line: {D.change(v, 'line_elo', 'line_refit', 'margin')}")
    rr = v.select(pl.corr("eff", "vegas")).item()
    beta = np.linalg.lstsq(
        np.column_stack([np.ones(v.height), v["vegas"].to_numpy(), v["eff"].to_numpy()]),
        v["margin"].to_numpy(), rcond=None,
    )[0]  # fmt: skip
    say(f"   efficiency's margin and the line correlate at r = {rr:.2f}; fit on every season,")
    say(f"   margin = {beta[0]:+.2f} + {beta[1]:.2f} x line + {beta[2]:+.2f} x efficiency's margin")
    # 6. Totals: Elo has no offense/defense split, so this is where efficiency could differ
    tot = read_part("team_game", "pregame", seasons=S).select("game_id", "team", "total_line")
    t = every.join(tot.collect(), on=["game_id", "team"], how="left").drop_nulls("total_line")
    t = t.with_columns(
        total=(c("home_score") + c("away_score")).cast(pl.Float64),
        off_sum=c("h_off") + c("a_off"),
        def_sum=c("h_def") + c("a_def"),
    )
    t = t.with_columns(
        tl=pl.Series(D.walk(t, "total", ["total_line"])),
        tl_eff=pl.Series(D.walk(t, "total", ["total_line", "off_sum", "def_sum"])),
        t_eff=pl.Series(D.walk(t, "total", ["off_sum", "def_sum"])),
        t_mean=pl.Series(D.walk(t, "total", [])),
    ).filter(c("season") >= S[1])
    say("")
    say("6. Game totals (where offense and defense apart could matter; Elo has no split):")
    say(f"   efficiency against the league's mean: {D.change(t, 't_eff', 't_mean', 'total')}")
    say(f"   line + efficiency against the total line: {D.change(t, 'tl_eff', 'tl', 'total')}")
    (HERE / "spotcheck_r6.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
