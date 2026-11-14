"""team-efficiency spot-check of R8 (the CEO's pick, 2026-11-14): the combination (DML on plays
counted by the representativeness weights) against every play counted equally (`ridge`), the
champion's choice between them.

From the build's saved histories (2016-2024, walk-forward): offense and defense pooled, per season
and horizon; how many seasons the combination wins; its gain by week band; and the same per team
(does the gain sit with a few teams?). The split luck and the frozen-model test are in
diagnose.txt (R8-R10).
Writes spotcheck_r8.txt. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/build/spotcheck_r8.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import summary as S  # noqa: E402

from pcf.data.tables.store import read_part  # noqa: E402
from pcf.experts.team_efficiency import features as F  # noqa: E402

c = pl.col
HERE = Path(__file__).parent
SEASONS = list(range(2016, 2025))


def main() -> None:
    lines = []

    def say(t: str = "") -> None:
        print(t, flush=True)
        lines.append(t)

    tg = S.load("team_game", parts=["schedule", "efficiency"])
    weeks = (
        read_part("team_game", "schedule", seasons=SEASONS)
        .select("game_id", "team", "week")
        .collect()
    )

    def pooled(rung: str, h: str) -> pl.DataFrame:
        out = []
        for s in S.SIDES:
            y = F.targets(tg, s, h).select("game_id", "team", "y")
            x = S.latest(f"{s}_{h}_{rung}").join(y, on=["game_id", "team"], how="inner")
            x = x.join(weeks, on=["game_id", "team"], how="inner").with_columns(
                season=c("game_id").str.slice(0, 4).cast(pl.Int32), team=c("team") + f"|{s}"
            )
            out.append(x.filter(c("season") <= 2024).select(*S.COLS))
        return pl.concat(out)

    say("R8 spot-check: the combination against every play counted equally (ridge), offense and")
    say("defense pooled, 2016-2024. Skill = share of ridge's squared error removed (+ is better).")
    for h in S.HORIZONS:
        a, b = pooled("combo", h), pooled("ridge", h)
        say("")
        say(f"{h}: all {S.fmt(S.skill(a, b))}")
        wins = 0
        for season in SEASONS:
            e = S.skill(a.filter(c("season") == season), b)
            wins += e[0] > 0
            say(f"  {season} {S.fmt(e)}")
        say(f"  the combination wins {wins} of {len(SEASONS)} seasons")
        for nm, w in (("weeks 1-4", c("week") <= 4), ("weeks 5-9", c("week").is_between(5, 9)),
                      ("weeks 10+", c("week") >= 10)):  # fmt: skip
            say(f"  {nm:10s} {S.fmt(S.skill(a.filter(w), b))}")
        # per team-side: the squared-error change, summed; how concentrated is the gain?
        k = ["game_id", "team"]
        j = a.select(*k, "y", "mean").join(b.select(*k, ref="mean"), on=k)
        per = (
            j.with_columns(team=c("team").str.split("|").list.first())
            .group_by("team")
            .agg(gain=((c("y") - c("ref")) ** 2 - (c("y") - c("mean")) ** 2).sum())
            .sort("gain", descending=True)
        )
        ref_se = float(j.select(((c("y") - c("ref")) ** 2).sum()).item())
        top, rest_ = per.head(5), per.slice(5)

        def pct(x: float, ref_se: float = ref_se) -> str:
            return f"{100 * x / ref_se:+.1f}%"

        say(
            f"  by team (offense and defense together, share of ridge's error): helped "
            f"{(per['gain'] > 0).sum()} of {per.height}; the top 5 ({', '.join(top['team'])}) "
            f"{pct(top['gain'].sum())}, the other 27 {pct(rest_['gain'].sum())}"
        )
    (HERE / "spotcheck_r8.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
