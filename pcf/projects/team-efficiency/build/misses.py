"""team-efficiency: where the champion misses (a team-level stand-in for `pcf.validation.misses`,
whose lens list is built for player-games; pace did without one).

The champion's next-3-games forecasts, 2016-2024 (offense `change`, defense `ridge`), by group:
bias (mean result minus mean forecast, EPA per play; + means the forecast was too low) with a 90%
interval from resampling weeks, and skill against the league's level (share of its squared error
removed). Groups, all known before the game except the playoff lens (a hindsight lens, as in
schemes-v2): week of the season, the team's rated fifth, playoff teams, a new QB or coach.
Writes misses.txt. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/build/misses.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import summary as S  # noqa: E402

from pcf.data.tables.store import load, read_part  # noqa: E402
from pcf.experts.team_efficiency import changes as X  # noqa: E402
from pcf.experts.team_efficiency import features as F  # noqa: E402

c = pl.col
HERE = Path(__file__).parent
SEASONS = list(range(2016, 2025))
CHAMPION = {"off": "off_next3_change", "def": "def_next3_ridge"}


def bias(x: pl.DataFrame, n: int = 1000) -> str:
    m = x.group_by("season", "week").agg(e=(c("y") - c("mean")).sum(), k=pl.len())
    e, k = m["e"].to_numpy(), m["k"].to_numpy()
    rng = np.random.default_rng(0)
    idx = rng.integers(0, len(e), size=(n, len(e)))
    lo, hi = np.percentile(e[idx].sum(1) / k[idx].sum(1), [5, 95])
    return f"{e.sum() / k.sum():+.4f} ({lo:+.4f} to {hi:+.4f})"


def main() -> None:
    lines = []

    def say(t: str = "") -> None:
        print(t, flush=True)
        lines.append(t)

    tg = S.load("team_game", parts=["schedule", "efficiency"])
    sched = read_part("team_game", "schedule", seasons=SEASONS).collect()
    weeks = sched.select("game_id", "team", "week")
    playoff = sched.filter(c("game_type") != "REG").select("season", "team").unique()
    playoff = playoff.with_columns(playoff=pl.lit(True))
    flags = X.season_changes(
        load("team_game", parts=["schedule", "pregame", "opening_coach"]),
        load("player_game", parts=["roster", "depth"]),
    ).select("season", "team", "new_qb", "new_coach")
    say("Where the champion misses: next 3 games, 2016-2024. Bias = result - forecast (EPA per")
    say("play; + = forecast too low); skill = share of the league level's squared error removed.")
    for side, v in CHAMPION.items():
        y = F.targets(tg, side, "next3").select("game_id", "team", "y")
        a = S.latest(v).join(y, on=["game_id", "team"]).join(weeks, on=["game_id", "team"])
        a = a.with_columns(season=c("game_id").str.slice(0, 4).cast(pl.Int32))
        a = a.filter(c("season") <= 2024)
        lg = S.latest(f"{side}_next3_league").join(y, on=["game_id", "team"])
        a = (
            a.join(playoff, on=["season", "team"], how="left")
            .join(flags, on=["season", "team"], how="left")
            .with_columns(
                c("playoff").fill_null(False),
                c("new_qb", "new_coach").fill_null(0.0),
                fifth=(
                    c("mean").rank("ordinal").over("season", "week")
                    * 5
                    / (pl.len().over("season", "week") + 1)
                )
                .floor()
                .cast(pl.Int8)
                + 1,
            )  # fmt: skip
        )
        say("")
        say(f"{side} ({v}): group | bias | skill vs league | rows")
        groups = [
            ("all", pl.lit(True)),
            ("weeks 1-4", c("week") <= 4),
            ("weeks 5-9", c("week").is_between(5, 9)),
            ("weeks 10+", c("week") >= 10),
            *[(f"rated fifth {q} ({'best' if q == 5 else 'worst' if q == 1 else ''})"
               .replace(" ()", ""), c("fifth") == q) for q in range(1, 6)],
            ("playoff team (hindsight)", c("playoff")),
            ("not a playoff team", ~c("playoff")),
            ("new QB", c("new_qb") > 0),
            ("new coach", c("new_coach") > 0),
        ]  # fmt: skip
        if side == "def":
            groups = [(nm.replace("best", "most allowed").replace("worst", "least allowed"), g)
                      for nm, g in groups]  # fmt: skip
        for nm, g in groups:
            x = a.filter(g)
            say(f"  {nm:26s} {bias(x)} | {S.fmt(S.skill(x, lg))} | {x.height:,}")
    (HERE / "misses.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
