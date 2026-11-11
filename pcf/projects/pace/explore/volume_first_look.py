"""pace exploration (2026-11-10): a first look at the volume forecast (the CEO's call C) and the
basketball analogy (plays = drives x plays per drive).

Per team-game, weeks 4+ of 2006-2024 regular seasons: how much of next game's plays, dropbacks
and runs can be forecast from what's known before kickoff, step by step: the season-to-date
average; the line (the team's spread and the game's total); the team's habits so far (clock-aware
pace over expected, PROE, no-huddle rate); the opponent's habits and its defense's plays allowed.
R2 with a 90% interval from resampling whole weeks; each step is also shuffled (the new columns'
rows permuted) to show what noise alone adds.

Run from pcf/projects/pace/explore: PYTHONUTF8=1 ../../../.venv/Scripts/python.exe volume_first_look.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from common import boot, plays, prior_mean, r2

from pcf.config import get_config

c = pl.col


def main() -> None:
    tg = pl.read_parquet(get_config().zone("interim") / "pace" / "team_games_pace.parquet")
    p = plays().filter(c("scrimmage") & (c("qtr") <= 4))
    dr = p.group_by("game_id", "team").agg(drives=c("fixed_drive").n_unique())
    tg = tg.join(dr, on=["game_id", "team"], how="left").with_columns(per_drive=c("plays") / c("drives"))

    print("=== the basketball analogy: plays = drives x plays per drive")
    d = tg.drop_nulls(["drives", "per_drive"])
    lp, ld, lk = np.log(d["plays"]), np.log(d["drives"]), np.log(d["per_drive"])
    print(f"team plays per game: mean {d['plays'].mean():.1f}, sd {d['plays'].std():.1f}; drives mean {d['drives'].mean():.1f}, sd {d['drives'].std():.2f}; plays per drive mean {d['per_drive'].mean():.2f}")
    print(f"share of the variance of log plays: drives {np.cov(ld, lp)[0, 1] / lp.var():.2f}, plays per drive {np.cov(lk, lp)[0, 1] / lp.var():.2f}")
    both = d.join(d.select("game_id", opp="team", opp_drives="drives", opp_plays="plays", opp_per_drive="per_drive"), on=["game_id", "opp"])
    print(f"r between the two teams in a game: drives {np.corrcoef(both['drives'], both['opp_drives'])[0, 1]:+.2f}, plays {np.corrcoef(both['plays'], both['opp_plays'])[0, 1]:+.2f}, my plays per drive and their plays {np.corrcoef(both['per_drive'], both['opp_plays'])[0, 1]:+.2f}")
    print(f"r of plays per drive with the offense's EPA per play {np.corrcoef(d.drop_nulls('epa_db')['per_drive'], d.drop_nulls('epa_db')['epa_db'])[0, 1]:+.2f} (EPA per dropback)")

    # Known before kickoff: season-to-date habits of the team and its opponent
    for m in ("plays", "dropbacks", "runs", "pace_oe_clock", "proe_game", "no_huddle_all", "per_drive"):
        tg = prior_mean(tg, m)
    allowed = tg.select("game_id", "season", "week", team=c("opp"), plays_allowed=c("plays"))
    allowed = prior_mean(allowed, "plays_allowed")
    tg = tg.join(allowed.select("game_id", opp=c("team"), opp_def_plays_allowed="plays_allowed_prior"), on=["game_id", "opp"], how="left")
    opp = tg.select("game_id", opp=c("team"), opp_pace="pace_oe_clock_prior", opp_plays="plays_prior", opp_per_drive="per_drive_prior")
    tg = tg.join(opp, on=["game_id", "opp"], how="left")
    d = tg.filter(c("week") >= 4).drop_nulls(["plays_prior", "dropbacks_prior", "runs_prior", "pace_oe_clock_prior", "proe_game_prior", "no_huddle_all_prior", "team_spread", "total_line", "opp_pace", "opp_def_plays_allowed", "per_drive_prior", "opp_per_drive"])
    d = d.with_columns(wk=c("season").cast(pl.Utf8) + "-" + c("week").cast(pl.Utf8))
    print(f"\n=== volume first look: {d.height} team-games, weeks 4+, 2006-2024")
    steps = {
        "season average": ["{y}_prior"],
        "+ the line": ["{y}_prior", "team_spread", "total_line"],
        "+ own habits": ["{y}_prior", "team_spread", "total_line", "pace_oe_clock_prior", "proe_game_prior", "no_huddle_all_prior"],
        "+ opponent": ["{y}_prior", "team_spread", "total_line", "pace_oe_clock_prior", "proe_game_prior", "no_huddle_all_prior", "opp_pace", "opp_def_plays_allowed", "opp_per_drive", "per_drive_prior"],
    }
    rng = np.random.default_rng(3)
    for y in ("plays", "dropbacks", "runs"):
        prev: list[str] = []
        print(f"{y}: sd {d[y].std():.1f}")
        for name, cols in steps.items():
            cols = [x.format(y=y) for x in cols]

            def fit(df, cols=cols, y=y):
                return r2(df[y].to_numpy(), df.select(cols).to_numpy())

            est, lo, hi = boot(d, fit, by="wk", n=100)
            new = [x for x in cols if x not in prev]
            X = d.select(cols).to_numpy().copy()
            idx = [cols.index(x) for x in new]
            X[:, idx] = X[rng.permutation(d.height)][:, idx]
            shuf = r2(d[y].to_numpy(), X)
            Xb = np.column_stack([np.ones(d.height), d.select(cols).to_numpy()])
            res = d[y].to_numpy() - Xb @ np.linalg.lstsq(Xb, d[y].to_numpy(), rcond=None)[0]
            print(f"  {name}: R2 {est:.3f} (90% {lo:.3f}-{hi:.3f}); shuffled new columns {shuf:.3f}; typical miss {np.abs(res).mean():.1f}")
            prev = cols
    g = d.group_by("game_id").agg(total=c("plays").sum(), n=pl.len()).filter(c("n") == 2)
    print(f"\ngame total plays (both teams): mean {g['total'].mean():.1f}, sd {g['total'].std():.1f}, 10th-90th percentile {g['total'].quantile(0.1):.0f}-{g['total'].quantile(0.9):.0f}")


if __name__ == "__main__":
    main()
