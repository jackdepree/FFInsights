"""H4: noise-cancelled scores. Which high-impact plays don't repeat, and does a rating built on the
margin without them forecast the next games better?

1. Candidate plays, each turned into points credited to the team that gained them:
   - `return_td`: a touchdown not scored by the offense on a pass or run (interception, fumble,
     punt, kickoff and blocked-kick returns): 7 points to the scoring team.
   - `fumble`: which side recovers. On each fumble that isn't a touchdown, the play's expected
     points minus the average fumble's. A recovered fumble credits the offense, a lost one the
     defense.
   - `kick`: field goals and extra points against the league's make rate at that distance
     (field goals, by 5-yard band) or that season (extra points), credited to the kicking team.
   - `interception`: the whole swing of an interception that isn't a touchdown (the play's
     expected points), credited to the defense.
   - `long_td`: offensive touchdowns of 40 yards or more, the play's expected points.
2. Do they repeat? Each team-season's average per game, net of the opponent's, in odd weeks
   against even weeks (regular season, 1999-2024), as a correlation across team-seasons. Next to
   the same for the margin.
3. The rating: rung 1 (margin Elo, half pull) learning from the margin with each candidate taken
   out, against rung 1 on the real margin. Step size tuned on 2002-2015, reported on 2016-2024.

Expected points come from nflverse's model, fit on seasons through 2019 (tag-tables#F4); the
fumble, interception and long-touchdown credits are measured after the game, never used before
it. The vault (2025) isn't read. Run from pcf/:
.venv/Scripts/python.exe projects/elo/explore/h4_luck.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import ladder as L  # noqa: E402

from pcf.data.tables.store import read_part  # noqa: E402

c = pl.col
CANDIDATES = ("return_td", "fumble", "kick", "interception", "long_td")
COLS = (
    "game_id",
    "season",
    "week",
    "season_type",
    "play_type",
    "posteam",
    "defteam",
    "td_team",
    "touchdown",
    "fumble",
    "interception",
    "epa",
    "yards_gained",
    "field_goal_result",
    "kick_distance",
    "extra_point_result",
)


def plays() -> pl.DataFrame:
    return (
        read_part("play", "pbp", seasons=list(range(L.FIRST, L.LAST + 1)))
        .select(COLS)
        .with_columns(epa=c("epa").fill_nan(None).fill_null(0.0))
        .collect()
    )


def credits(p: pl.DataFrame) -> pl.DataFrame:
    """One row per (game, team, candidate): the points that team gained from it."""
    td = c("touchdown") == 1
    offense_td = td & c("play_type").is_in(["pass", "run"]) & (c("td_team") == c("posteam"))
    ret = p.filter(td & c("td_team").is_not_null() & ~offense_td).select(
        "game_id", team="td_team", pts=pl.lit(7.0), kind=pl.lit("return_td")
    )

    fum = p.filter((c("fumble") == 1) & ~td & c("posteam").is_not_null())
    luck = c("epa") - fum["epa"].mean()
    fumble = pl.concat(
        [
            fum.select("game_id", team="posteam", pts=pl.max_horizontal(luck, 0.0)),
            fum.select("game_id", team="defteam", pts=pl.max_horizontal(-luck, 0.0)),
        ]
    ).with_columns(kind=pl.lit("fumble"))

    fg = p.filter(c("field_goal_result").is_not_null() & c("kick_distance").is_not_null())
    fg = fg.with_columns(band=(c("kick_distance") // 5), made=(c("field_goal_result") == "made"))
    fg = fg.with_columns(rate=c("made").cast(pl.Float64).mean().over("band"))
    xp = p.filter(c("extra_point_result").is_not_null()).with_columns(
        made=c("extra_point_result") == "good"
    )
    xp = xp.with_columns(rate=c("made").cast(pl.Float64).mean().over("season"))
    kick = pl.concat(
        [
            fg.select("game_id", team="posteam", pts=3 * (c("made").cast(pl.Float64) - c("rate"))),
            xp.select("game_id", team="posteam", pts=c("made").cast(pl.Float64) - c("rate")),
        ]
    ).with_columns(kind=pl.lit("kick"))

    ints = p.filter((c("interception") == 1) & ~td).select(
        "game_id", team="defteam", pts=-c("epa"), kind=pl.lit("interception")
    )
    long_td = p.filter(offense_td & (c("yards_gained") >= 40)).select(
        "game_id", team="posteam", pts=c("epa"), kind=pl.lit("long_td")
    )
    return pl.concat([ret, fumble, kick, ints, long_td], how="vertical_relaxed")


def by_game(g: pl.DataFrame, cr: pl.DataFrame) -> pl.DataFrame:
    """Each game with the home and away team's credit per candidate."""
    wide = (
        cr.group_by("game_id", "team", "kind")
        .agg(c("pts").sum())
        .pivot(on="kind", index=["game_id", "team"], values="pts")
        .fill_null(0.0)
    )
    for k in CANDIDATES:
        if k not in wide.columns:
            wide = wide.with_columns(pl.lit(0.0).alias(k))
    home = wide.rename({k: f"h_{k}" for k in CANDIDATES} | {"team": "home_team"})
    away = wide.rename({k: f"a_{k}" for k in CANDIDATES} | {"team": "away_team"})
    out = g.join(home, on=["game_id", "home_team"], how="left").join(
        away, on=["game_id", "away_team"], how="left"
    )
    return out.with_columns([c(f"{s}_{k}").fill_null(0.0) for s in ("h", "a") for k in CANDIDATES])


def repeatability(gg: pl.DataFrame) -> pl.DataFrame:
    """Odd-week against even-week team-season averages, net of the opponent, regular season."""
    reg = gg.filter(c("game_type") == "REG")
    cols = {k: (c(f"h_{k}") - c(f"a_{k}")) for k in CANDIDATES} | {"margin": c("margin")}
    home = reg.select("season", "week", team="home_team", **cols)
    away = reg.select("season", "week", team="away_team", **{k: -v for k, v in cols.items()})
    tg = pl.concat([home, away])
    names = [*cols]
    halves = tg.group_by("season", "team", odd=c("week") % 2 == 1).agg([c(n).mean() for n in names])
    odd = halves.filter(c("odd")).drop("odd")
    even = halves.filter(~c("odd")).drop("odd")
    j = odd.join(even, on=["season", "team"], suffix="_e")
    rows = []
    for n in names:
        r = float(np.corrcoef(j[n], j[f"{n}_e"])[0, 1])
        size = float(tg[n].abs().mean())
        sd = float(tg[n].std())
        rows.append(
            {
                "candidate": n,
                "split_half_r": round(r, 3),
                "mean_abs_pts": round(size, 2),
                "sd_pts": round(sd, 2),
            }
        )
    return pl.DataFrame(rows)


def main() -> None:
    g = L.games()
    priors = L.season_priors(g)
    gg = by_game(g, credits(plays()))
    print("credits per game (mean over games, home+away):")
    print(gg.select([(c(f"h_{k}").abs() + c(f"a_{k}").abs()).mean().alias(k) for k in CANDIDATES]))
    print("\nREPEATABILITY (odd vs even weeks, team-seasons 1999-2024, net of opponent)")
    print(repeatability(gg))

    variants = {f"without {k}": [k] for k in CANDIDATES}
    variants["without return_td+fumble+kick"] = ["return_td", "fumble", "kick"]
    for name, ks in variants.items():
        net = sum((c(f"h_{k}") - c(f"a_{k}")) for k in ks)
        gg = gg.with_columns((c("margin") - net).alias(name))
    grid_k = (0.05, 0.06, 0.07, 0.08)
    print("\nRATINGS (rung 1 learning from the margin without each candidate; 2016-2024)")
    for name in variants:
        grid = [{"k": k, "pull": 0.5, "signal": name} for k in grid_k]
        L.show(name, L.versus_rung1(gg, priors, "margin_pull", grid))
    # half weight on the combined set
    ks = variants["without return_td+fumble+kick"]
    net = sum((c(f"h_{k}") - c(f"a_{k}")) for k in ks)
    gg = gg.with_columns((c("margin") - 0.5 * net).alias("half"))
    grid = [{"k": k, "pull": 0.5, "signal": "half"} for k in grid_k]
    L.show("half of return_td+fumble+kick", L.versus_rung1(gg, priors, "margin_pull", grid))

    # totals: offense and defense ratings learning from points without the same set
    # (each team's credit minus the league's average credit, so points keep their level)
    avg = {k: float(pl.concat([gg[f"h_{k}"], gg[f"a_{k}"]]).mean()) for k in ks}
    gg = gg.with_columns(
        hp=c("home_pts") - sum(c(f"h_{k}") - avg[k] for k in ks),
        ap=c("away_pts") - sum(c(f"a_{k}") - avg[k] for k in ks),
    )
    grid = [{"k": k, "k_mu": 0.0, "pull": 1 / 3, "signals": ("hp", "ap")} for k in grid_k]
    L.show("off_def without the set", L.versus_rung1(gg, priors, "off_def", grid))

    # the 2020-2024 half, where expected points are out of sample
    grid = [{"k": k, "pull": 0.5, "signal": "without return_td+fumble+kick"} for k in grid_k]
    L.show("set, 2020-2024 only", L.versus_rung1(gg, priors, "margin_pull", grid, lo=2020))


if __name__ == "__main__":
    main()
