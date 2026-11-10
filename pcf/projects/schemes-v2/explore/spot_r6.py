"""The CEO's spot-check of R6, the pass anti-trait (2026-11-09), in depth.

R6: on held-out seasons, a team's pass use over expected (known before kickoff) predicts its gain
from passing in the next game: +0.015 EPA a play per sd, beating 196 of 200 shuffles.

The worry: `pass_gain` is plain EPA on dropbacks less EPA on runs in neutral situations, with no
adjustment for where the plays happen. A run-heavy team throws more on third and long and runs more
on first and ten, so its passes may look worse than its runs for that reason alone, while the use
side (pass rate over nflfastR's expected) is already situation-adjusted. So:
1. **Situation-adjusted gain:** each play's EPA less the league's mean EPA for the same choice
   (pass or run) in the same cell (down × distance 1-3/4-6/7-10/11+ × field zone 1-20/21-50/51-80/
   81-99 × season), all neutral plays; the gain is the mean of that residual on passes less on runs.
   Same features, same sign test (exactly R6's script), and the shotgun for comparison.
2. **Unweighted** (R6 weights each game by its effective plays).
3. **The rows:** the biggest pass-avoiding and pass-heavy team-seasons (mean use over their test
   games), with their mean raw and adjusted gains, against the league.
The vault (2025) isn't read.

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/spot_r6.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from anti_sign import rows, slope, test

from pcf.data.gateway import Gateway
from pcf.data.tables.store import read_part
from pcf.data.tables.tendencies import PBP_COLUMNS, scrimmage

c = pl.col


def adjusted_gains() -> pl.DataFrame:
    frames = []
    for s in range(2006, 2025):
        p = (
            read_part("play", "pbp", [s])
            .select(*PBP_COLUMNS, "ydstogo", "yardline_100", "season_type")
            .collect()
        )
        p = scrimmage(p.filter(c("season_type") == "REG")).filter(
            c("neutral") & c("epa").is_not_null()
        )
        frames.append(
            p.select(
                "game_id",
                "season",
                "posteam",
                "pass",
                "shotgun",
                "down",
                "ydstogo",
                "yardline_100",
                "epa",
            )
        )
    p = pl.concat(frames).with_columns(
        dist=pl.sum_horizontal(c("ydstogo") > 3, c("ydstogo") > 6, c("ydstogo") > 10),
        zone=pl.sum_horizontal(
            c("yardline_100") > 20, c("yardline_100") > 50, c("yardline_100") > 80
        ),
    )
    p = p.with_columns(
        res=c("epa") - c("epa").mean().over("season", "down", "dist", "zone", "pass")
    )
    pass_ = p.group_by("game_id", team="posteam").agg(
        pass_adj=c("res").filter(c("pass") == 1).mean() - c("res").filter(c("pass") == 0).mean(),
        pass_raw_check=c("epa").filter(c("pass") == 1).mean()
        - c("epa").filter(c("pass") == 0).mean(),
    )
    cells = (
        p.with_columns(
            sres=c("epa")
            - c("epa").mean().over("season", "down", "dist", "zone", "pass", "shotgun")
        )
        .group_by("game_id", "posteam", "pass")
        .agg(
            g=c("res").filter(c("shotgun") == 1).mean() - c("res").filter(c("shotgun") == 0).mean(),
            w=((c("shotgun") == 1).sum() * (c("shotgun") == 0).sum() / pl.len()).cast(pl.Float64),
        )
    )
    sg = (
        cells.filter(c("w") > 0)
        .group_by("game_id", team="posteam")
        .agg(shotgun_adj=(c("g") * c("w")).sum() / c("w").sum())
    )
    return pass_.join(sg, on=["game_id", "team"], how="full", coalesce=True)


def show(label: str, r: dict) -> None:
    print(
        f"   {label:<34} slope {r['slope']:+.4f} per sd [{r['lo']:+.4f}, {r['hi']:+.4f}]; beaten {r['beats']}/200 shuffles; positive in {r['positive']}/{r['seasons']} seasons"
    )


def main() -> None:
    gw = Gateway()
    adj = adjusted_gains()
    for option in ("pass", "shotgun"):
        df = rows(option, gw).join(adj, on=["game_id", "team"], how="left")
        print(f"\n== {option}: {df.height:,} team-games (R6's rows)")
        if option == "pass":
            chk = df.drop_nulls("pass_raw_check")
            print(
                f"   (check: the rebuilt raw gain matches the table's: r {np.corrcoef(chk['y'].to_numpy(), chk['pass_raw_check'].to_numpy())[0, 1]:.3f})"
            )
        show("R6 as published (raw gain)", test(df, f"{option}_use"))
        dfa = df.filter(c(f"{option}_adj").is_not_null()).with_columns(y=c(f"{option}_adj"))
        show("situation-adjusted gain", test(dfa, f"{option}_use"))
        dfu = df.with_columns(n=pl.lit(1.0))
        show("raw gain, unweighted", test(dfu, f"{option}_use"))
        show(
            "situation-adjusted, unweighted", test(dfa.with_columns(n=pl.lit(1.0)), f"{option}_use")
        )
        if option == "pass":
            x = (df["pass_use"] - df["pass_use"].mean()) / df["pass_use"].std()
            print(
                f"   raw gain mean {df['y'].mean():+.3f}; adjusted mean {dfa['y'].mean():+.3f} (league gain removed)"
            )
            print(
                f"   check: slope of the adjusted gain on use with R6's weights: {slope(((dfa['pass_use'] - dfa['pass_use'].mean()) / dfa['pass_use'].std()).to_numpy(), dfa['y'].to_numpy(), dfa['n'].to_numpy()):+.4f}"
            )
            ts = (
                df.join(
                    adj.select("game_id", "team", "pass_adj"),
                    on=["game_id", "team"],
                    how="left",
                    suffix="_2",
                )
                .group_by("team", "season")
                .agg(
                    use=c("pass_use").mean(),
                    raw=c("y").mean(),
                    adj=c("pass_adj").mean(),
                    games=pl.len(),
                )
                .filter(c("games") >= 8)
                .sort("use")
            )
            sd = df["pass_use"].std()
            print(
                "\n== The rows: team-seasons by mean pass use (sd units), mean raw gain and adjusted gain per game (EPA a play)"
            )
            print("   most pass-avoiding:")
            for r_ in ts.head(8).iter_rows(named=True):
                print(
                    f"      {r_['season']} {r_['team']:<4} use {r_['use'] / sd:+.1f} sd   raw gain {r_['raw']:+.3f}   adjusted {r_['adj']:+.3f}   ({r_['games']} games)"
                )
            print("   most pass-heavy:")
            for r_ in ts.tail(8).reverse().iter_rows(named=True):
                print(
                    f"      {r_['season']} {r_['team']:<4} use {r_['use'] / sd:+.1f} sd   raw gain {r_['raw']:+.3f}   adjusted {r_['adj']:+.3f}   ({r_['games']} games)"
                )
            q = (
                ts.with_columns(fifth=(c("use").rank() / pl.len() * 5).ceil().clip(1, 5))
                .group_by("fifth")
                .agg(raw=c("raw").mean(), adj=c("adj").mean(), n=pl.len())
                .sort("fifth")
            )
            print(
                "   by fifth of use (team-seasons): "
                + "; ".join(
                    f"{int(r_['fifth'])}: raw {r_['raw']:+.3f}, adj {r_['adj']:+.3f}"
                    for r_ in q.iter_rows(named=True)
                )
            )


if __name__ == "__main__":
    main()
