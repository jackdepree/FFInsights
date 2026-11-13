"""team-efficiency build: the no-noise test and the side targets (brief: "Elo: a test of whether
better-measured efficiency finally adds to the margin"; the team's fantasy points beside the main
test).

Inputs are walk-forward outputs only (rule e): Elo's margin history and the ratings that
`off_next3_combo` published with its history, each made before the game.

1. **No noise (VALIDATION.md §5): Elo's margin, with and without efficiency.** The baseline is
   Elo's own margin forecast. The challenger refits margin = a x Elo + b x (home offense - away
   offense) + c x (away defense - home defense) on earlier test seasons only (2016 on; first
   scored season 2017). Absolute miss, 90% interval of the change from resampling weeks.
2. **Next game's points scored**, per team: points = a + b x offense + c x the opponent's defense
   + d x home, refit on earlier seasons, against the league's mean points (same walk).
3. **The team's fantasy points (PPR) over its next game and next 3 games**, the same way.

Writes downstream.txt. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/build/downstream.py
"""

from __future__ import annotations

import glob
import os
from pathlib import Path

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.tables.store import read_part

c = pl.col
HERE = Path(__file__).parent
SEASONS = list(range(2016, 2025))


def latest(project: str, variant: str) -> pl.DataFrame:
    root = get_config().zone("outputs") / project / variant
    runs = sorted(glob.glob(str(root / "*" / "history.parquet")), key=os.path.getmtime)
    if not runs:
        raise FileNotFoundError(f"no history for {project}/{variant}")
    return pl.read_parquet(runs[-1])


def walk(df: pl.DataFrame, y: str, xs: list[str]) -> np.ndarray:
    """Predictions for seasons 2017 on, each from a least-squares fit on earlier seasons."""
    pred = np.full(df.height, np.nan)
    seasons = df["season"].to_numpy()
    x = np.column_stack([np.ones(df.height)] + [df[v].to_numpy().astype(float) for v in xs])
    yy = df[y].to_numpy().astype(float)
    for s in SEASONS[1:]:
        tr, te = seasons < s, seasons == s
        beta = np.linalg.lstsq(x[tr], yy[tr], rcond=None)[0]
        pred[te] = x[te] @ beta
    return pred


def change(df: pl.DataFrame, a: str, b: str, y: str, loss: str = "abs", n: int = 1000) -> str:
    """Mean loss of a against b (negative is better), with a 90% interval from weeks."""
    d = df.with_columns(c(a, b).fill_nan(None)).filter(c(a).is_not_null() & c(b).is_not_null())
    f = (lambda e: e.abs()) if loss == "abs" else (lambda e: e**2)
    d = d.with_columns(la=f(c(y) - c(a)), lb=f(c(y) - c(b)))
    per = d.group_by("season", "week").agg(diff=(c("la") - c("lb")).sum(), k=pl.len())
    s, k = per["diff"].to_numpy(), per["k"].to_numpy()
    rng = np.random.default_rng(0)
    idx = rng.integers(0, len(s), size=(n, len(s)))
    boots = s[idx].sum(1) / k[idx].sum(1)
    lo, hi = np.percentile(boots, [5, 95])
    base = float(d["lb"].mean())
    est = s.sum() / k.sum()
    verdict = "adds value" if hi < 0 else ("adds noise" if lo > 0 else "neutral")
    return (f"{est:+.3f} (90% {lo:+.3f} to {hi:+.3f}) on a baseline of {base:.3f}; "
            f"{100 * est / base:+.2f}%; {verdict}; {d.height:,} rows")  # fmt: skip


def main() -> None:
    lines = []

    def say(t: str = "") -> None:
        print(t, flush=True)
        lines.append(t)

    rat = latest("team-efficiency", "off_next3_combo").select(
        "game_id", "team", "off_combo", "def_combo"
    )
    sched = (
        read_part("team_game", "schedule", seasons=SEASONS)
        .filter(c("game_type") == "REG")
        .select("game_id", "team", "opponent", "home", "season", "week")
        .collect()
    )
    games = read_part("game", "schedule", seasons=SEASONS).select("game_id", "home_team").collect()
    res = read_part("game", "result", seasons=SEASONS).select(
        "game_id", "home_score", "away_score"
    ).collect()

    # 1. Elo's margin, with and without efficiency
    elo = latest("elo", "margin").select("game_id", elo="mean")
    home = rat.join(games, left_on=["game_id", "team"], right_on=["game_id", "home_team"])
    home = home.select("game_id", h_off="off_combo", h_def="def_combo")
    away = rat.join(games, on="game_id").filter(c("team") != c("home_team"))
    away = away.select("game_id", a_off="off_combo", a_def="def_combo")
    g = (
        elo.join(home, on="game_id")
        .join(away, on="game_id")
        .join(res, on="game_id")
        .join(sched.filter(c("home") == 1).select("game_id", "season", "week"), on="game_id")
        .with_columns(
            margin=(c("home_score") - c("away_score")).cast(pl.Float64),
            off_gap=c("h_off") - c("a_off"),
            def_gap=c("a_def") - c("h_def"),
        )
        .drop_nulls(["margin", "elo", "off_gap", "def_gap"])
        .sort("season", "week", "game_id")
    )
    g = g.with_columns(
        with_eff=pl.Series(walk(g, "margin", ["elo", "off_gap", "def_gap"])),
        elo_refit=pl.Series(walk(g, "margin", ["elo"])),
    )
    say("1. No noise: Elo's home margin (points), 2017-2024, absolute miss")
    say(f"  Elo + efficiency against Elo refit alike: {change(g, 'with_eff', 'elo_refit', 'margin')}")
    say(f"  Elo + efficiency against Elo as published: {change(g, 'with_eff', 'elo', 'margin')}")

    # 2. next game's points scored, and 3. team fantasy points
    pts = read_part("team_game", "result", seasons=SEASONS).select(
        "game_id", "team", "points_for"
    ).collect()
    roster = read_part("player_game", "roster", seasons=SEASONS).select(
        "gsis_id", "game_id", "team"
    ).collect()
    fp = (
        read_part("player_game", "stats", seasons=SEASONS)
        .select("gsis_id", "game_id", "fantasy_points_ppr")
        .collect()
        .join(roster, on=["gsis_id", "game_id"])
        .group_by("game_id", "team")
        .agg(fp=c("fantasy_points_ppr").sum())
    )
    t = (
        sched.join(rat, on=["game_id", "team"])
        .join(
            rat.select("game_id", opponent="team", opp_def="def_combo"),
            on=["game_id", "opponent"],
        )
        .join(pts, on=["game_id", "team"], how="left")
        .join(fp, on=["game_id", "team"], how="left")
        .sort("season", "team", "week")
        .with_columns(c("home").cast(pl.Float64))
    )
    # the next 3 games' fantasy points per game (the game and the two after it)
    t = t.with_columns(
        fp3=pl.concat_list(
            c("fp"),
            c("fp").shift(-1).over("season", "team"),
            c("fp").shift(-2).over("season", "team"),
        ).list.mean()
    )
    for y, nm in (("points_for", "next game's points"), ("fp", "next game's fantasy points"),
                  ("fp3", "fantasy points per game, next 3 games")):  # fmt: skip
        d = t.drop_nulls([y, "off_combo", "opp_def"])
        d = d.with_columns(
            eff=pl.Series(walk(d, y, ["off_combo", "opp_def", "home"])),
            league=pl.Series(walk(d, y, [])),
        )
        say("")
        say(f"{'2' if y == 'points_for' else '3'}. {nm}, 2017-2024, squared miss:")
        say(f"  efficiency against the league's mean: {change(d, 'eff', 'league', y, 'sq')}")
        r = d.filter(c("eff").is_not_nan()).select(pl.corr("eff", y)).item()
        say(f"  r of the forecast with the result: {r:.3f}")
    (HERE / "downstream.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
