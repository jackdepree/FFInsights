"""H27 (movers carry their rates?) and H30 (age by position), the CEO's hunches, 2026-11-11.

**H27, QBs, 2002-2024**, from what's known in season: the starting QB of each team-game
(`team_game.pregame.qb_id`) and the team's PROE and pace over expected in that game
(`team_game.pace`), regular season, each season's league level taken out (pace#B2). A QB-team-
season needs 4 starts. For each QB's next season with starts:
  rate at the new team ~ his rate at the old team + the new team's rate the season before
The coefficient on his own rate is what he carries; the new team's is what stays with the team.
The same for stayers (same team) and for head coaches who moved, so the three can be compared.
Intervals from resampling whole QBs (or coaches).

**H30, age, team-seasons**: within a head coach's stint at a team (so the coach's own habits are
held fixed), the team's season PROE and pace over expected against the snap-weighted age of each
position group (2013-2024, weekly snap counts and roster birth dates; age at September 1), and
the starting QB's age and rookie season (2002-2024). Defensive groups against what the opponent
did (`def_proe`, `def_pace_oe`).
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from common import TABLES, group  # noqa: E402

c = pl.col
ALL = list(range(2002, 2025))


def part(table, name, seasons, cols):
    files = [TABLES / table / name / f"season={s}" / "data.parquet" for s in seasons]
    return pl.scan_parquet([f for f in files if f.exists()], extra_columns="ignore", missing_columns="insert").select(cols).collect()


def team_games() -> pl.DataFrame:
    sch = part("team_game", "schedule", ALL, ["game_id", "team", "season", "week", "game_type"]).filter(c("game_type") == "REG")
    pre = part("team_game", "pregame", ALL, ["game_id", "team", "qb_id", "coach"])
    pace = part("team_game", "pace", ALL, ["game_id", "team", "plays", "proe", "pace_oe", "pace_snaps", "def_plays", "def_proe", "def_pace_oe", "def_pace_snaps"])
    tg = sch.join(pre, on=["game_id", "team"]).join(pace, on=["game_id", "team"])
    # league level per season taken out (pace#B2)
    for m, w in (("proe", "plays"), ("pace_oe", "pace_snaps"), ("def_proe", "def_plays"), ("def_pace_oe", "def_pace_snaps")):
        tg = tg.with_columns((c(m) - ((c(m) * c(w)).sum() / c(w).sum()).over("season")).alias(m))
    return tg


def wavg(v, w):
    return ((c(v) * c(w)).sum() / c(w).sum()).alias(v)


def ols_boot(d: pl.DataFrame, y: str, xs: list[str], block: str, n: int = 400, seed: int = 7):
    d = d.drop_nulls([y, *xs])
    Y = d[y].to_numpy()
    X = np.column_stack([np.ones(d.height), *[d[x].to_numpy() for x in xs]])
    b = np.linalg.lstsq(X, Y, rcond=None)[0]
    keys, inv = np.unique(d[block].to_numpy(), return_inverse=True)
    idx = [np.flatnonzero(inv == k) for k in range(len(keys))]
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(n):
        pick = np.concatenate([idx[k] for k in rng.integers(0, len(keys), len(keys))])
        bs.append(np.linalg.lstsq(X[pick], Y[pick], rcond=None)[0])
    lo, hi = np.percentile(bs, [5, 95], axis=0)
    return {x: (round(float(b[i + 1]), 3), round(float(lo[i + 1]), 3), round(float(hi[i + 1]), 3)) for i, x in enumerate(xs)} | {"n": d.height}


def movers(tg: pl.DataFrame, who: str, label: str) -> None:
    unit = tg.group_by(who, "team", "season").agg(wavg("proe", "plays"), wavg("pace_oe", "pace_snaps"), starts=pl.len()).filter(c("starts") >= 4)
    unit = unit.filter(c(who).is_not_null())
    # one team per who-season: the team with most starts
    unit = unit.sort("starts", descending=True).unique([who, "season"], keep="first")
    team_season = tg.group_by("team", "season").agg(wavg("proe", "plays"), wavg("pace_oe", "pace_snaps"))
    nxt = unit.select(who, "season", team_next="team", proe_next="proe", pace_next="pace_oe", season_next="season")
    # the next season he started or coached, within 3 seasons
    pairs = unit.join(nxt, on=who, suffix="_n").filter((c("season_next") > c("season")) & (c("season_next") <= c("season") + 3))
    pairs = pairs.sort("season_next").unique([who, "season"], keep="first")
    prior = team_season.select(team_next="team", season_next=c("season") + 1, proe_team_prior="proe", pace_team_prior="pace_oe")
    pairs = pairs.join(prior, on=["team_next", "season_next"], how="left")
    kinds = [("moved", pairs.filter(c("team") != c("team_next")))]
    if who == "qb_id":  # a coach who stayed has his own rate as the team's: the two inputs are one
        kinds.append(("stayed", pairs.filter(c("team") == c("team_next"))))
    for kind, d in kinds:
        print(f"  {label} {kind}: PROE  ", ols_boot(d, "proe_next", ["proe", "proe_team_prior"], who))
        print(f"  {label} {kind}: pace  ", ols_boot(d, "pace_next", ["pace_oe", "pace_team_prior"], who))
    return pairs


def ages() -> pl.DataFrame:
    seasons = list(range(2013, 2025))
    sn = part("player_game", "snaps", seasons, ["gsis_id", "game_id", "offense_snaps", "defense_snaps"])
    ro = part("player_game", "roster", seasons, ["gsis_id", "game_id", "team", "season", "position", "birth_date", "years_exp"])
    d = sn.join(ro, on=["gsis_id", "game_id"]).drop_nulls("birth_date")
    d = d.with_columns(
        group=c("position").map_elements(group, return_dtype=pl.Utf8),
        age=(pl.date(c("season"), 9, 1) - c("birth_date")).dt.total_days() / 365.25,
    )
    d = d.with_columns(snaps=pl.when(c("group").is_in(["DL", "LB", "DB"])).then(c("defense_snaps")).otherwise(c("offense_snaps"))).filter(c("snaps") > 0)
    a = d.group_by("team", "season", "group").agg(age=(c("age") * c("snaps")).sum() / c("snaps").sum())
    return a.pivot(on="group", index=["team", "season"], values="age")


def within(d: pl.DataFrame, cols: list[str], by: str) -> pl.DataFrame:
    return d.with_columns([(c(x) - c(x).mean().over(by)).alias(x) for x in cols])


def main() -> None:
    tg = team_games()
    print("team-games", tg.height, "seasons", tg["season"].min(), "-", tg["season"].max())
    print("\n=== H27: what carries to the next season (coefficients, 90% interval)")
    qb_pairs = movers(tg, "qb_id", "QB")
    coach_pairs = movers(tg, "coach", "head coach")
    m = qb_pairs.filter(c("team") != c("team_next"))
    print("  QB movers:", m.height, "; per season", round(m.height / 22, 1))

    print("\n=== H30: team-season rates against age, within the head coach's stint at the team")
    ts = tg.group_by("team", "season").agg(wavg("proe", "plays"), wavg("pace_oe", "pace_snaps"), wavg("def_proe", "def_plays"), wavg("def_pace_oe", "def_pace_snaps"), coach=c("coach").mode().first(), qb_id=c("qb_id").mode().first())
    ro = part("player_game", "roster", ALL, ["gsis_id", "season", "birth_date", "years_exp"]).unique(["gsis_id", "season"])
    ts = ts.join(ro.rename({"gsis_id": "qb_id"}), on=["qb_id", "season"], how="left").with_columns(
        qb_age=(pl.date(c("season"), 9, 1) - c("birth_date")).dt.total_days() / 365.25,
        qb_rookie=(c("years_exp") == 0).cast(pl.Float64),
    )
    ts = ts.with_columns(stint=c("coach") + "_" + c("team"))
    # years into the stint: a coach's habits drift over his tenure while the same QB ages with it
    ts = ts.with_columns(stint_year=(c("season") - c("season").min().over("stint")).cast(pl.Float64))
    q = within(ts.drop_nulls(["qb_age", "proe"]), ["proe", "pace_oe", "qb_age", "qb_rookie", "stint_year"], "stint")
    for xs in (["qb_age"], ["qb_age", "stint_year"], ["qb_rookie"], ["qb_rookie", "stint_year"]):
        print(f"  QB {xs}, 2002-2024, PROE:", ols_boot(q, "proe", xs, "stint"))
        print(f"  QB {xs}, 2002-2024, pace:", ols_boot(q, "pace_oe", xs, "stint"))
    a = ages()
    t2 = ts.join(a, on=["team", "season"]).drop_nulls(["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB"])
    off = ["QB", "RB", "WR", "TE", "OL"]
    dfn = ["DL", "LB", "DB"]
    w = within(t2, ["proe", "pace_oe", "def_proe", "def_pace_oe", "stint_year", *off, *dfn], "stint")
    print("  team-seasons with ages (2013-2024):", w.height)
    print("  offense ages, PROE:", ols_boot(w, "proe", off, "stint"))
    print("  offense ages + years into the stint, PROE:", ols_boot(w, "proe", [*off, "stint_year"], "stint"))
    print("  offense ages, pace:", ols_boot(w, "pace_oe", off, "stint"))
    print("  defense ages, opponent PROE:", ols_boot(w, "def_proe", dfn, "stint"))
    print("  defense ages, opponent pace:", ols_boot(w, "def_pace_oe", dfn, "stint"))
    print("  sd of team-season PROE within stint", round(float(w["proe"].std()), 4), " pace", round(float(w["pace_oe"].std()), 3))
    print("  sd of age within stint:", {g: round(float(w[g].std()), 2) for g in off + dfn})


if __name__ == "__main__":
    main()
