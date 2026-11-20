# ruff: noqa: E501
"""skill-over-expected, the second look (2026-11-20): do the lower-noise measures pay? H77's
"pays?" question, at the CEO's direction ("the next season or maybe even the next game").

Discovery only, 2016-2024 (PFR's measures 2018-2024); the 2025 vault untouched. The calls, the
pass rule and Claude's expectations are in EXPLORATION.md ("Second look", written before the run).

For each group, a target (the downstream rate), its own past as the base, and the lower-noise
measure beside it; a weighted linear fit on every other season, scored on the left-out one; the
gain is the share of the base's weighted squared error removed, with a 90% interval from
resampling players.

Run from pcf/:  python projects/skill-over-expected/explore/second_look.py > projects/skill-over-expected/explore/second_look.txt
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.gateway import Gateway

c = pl.col
FIRST, LAST = 2016, 2024
DRAWS = 1000
rng = np.random.default_rng(get_config().seed)
spec = importlib.util.spec_from_file_location("fl", Path(__file__).with_name("first_look.py"))
fl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fl)


def fit_predict(d: pl.DataFrame, xs: list[str], y: str, w: str) -> np.ndarray:
    """Held-out predictions, leaving one target season out at a time (weighted least squares)."""
    pred = np.full(d.height, np.nan)
    seasons = d["tseason"].to_numpy()
    X = np.column_stack([np.ones(d.height)] + [d[x].to_numpy().astype(float) for x in xs])
    Y = d[y].to_numpy().astype(float)
    W = d[w].to_numpy().astype(float)
    for s in np.unique(seasons):
        tr, te = seasons != s, seasons == s
        sw = np.sqrt(W[tr])
        b = np.linalg.lstsq(X[tr] * sw[:, None], Y[tr] * sw, rcond=None)[0]
        pred[te] = X[te] @ b
    return pred


def score(d: pl.DataFrame, base: list[str], extra: list[str], y: str, w: str) -> dict:
    d = d.drop_nulls([*base, *extra, y, w]).filter(c(w) > 0)
    Y, W = d[y].to_numpy().astype(float), d[w].to_numpy().astype(float)
    p0 = fit_predict(d, [], y, w)
    p1 = fit_predict(d, base, y, w)
    p2 = fit_predict(d, base + extra, y, w)
    e0, e1, e2 = (W * (Y - p) ** 2 for p in (p0, p1, p2))
    pid = d["pid"].to_numpy()
    u, inv = np.unique(pid, return_inverse=True)
    s1, s2 = np.bincount(inv, e1), np.bincount(inv, e2)
    gains = []
    for _ in range(DRAWS):
        k = np.bincount(rng.integers(0, len(u), len(u)), minlength=len(u))
        gains.append(1 - (k @ s2) / (k @ s1))
    lo, hi = np.quantile(gains, [0.05, 0.95])
    return {
        "rows": d.height,
        "past_vs_league_avg": 1 - e1.sum() / e0.sum(),
        "gain": 1 - e2.sum() / e1.sum(),
        "lo90": lo,
        "hi90": hi,
    }


def seasons_frame(g: pl.DataFrame, sums: list[str], den: str, floor: int) -> pl.DataFrame:
    s = g.group_by("pid", "season").agg(*[c(k).sum() for k in sums]).filter(c(den) >= floor)
    nxt = s.select(
        "pid", (c("season") - 1).alias("season"), *[c(k).alias(f"{k}_next") for k in sums]
    )
    return s.join(nxt, on=["pid", "season"]).with_columns(tseason=c("season") + 1)


def to_date(g: pl.DataFrame, sums: list[str], den: str, floor: int) -> pl.DataFrame:
    """Each game with the season's sums through the previous game."""
    g = g.sort("pid", "season", "week")
    g = g.with_columns(
        *[(c(k).cum_sum().over("pid", "season") - c(k)).alias(f"{k}_td") for k in sums],
        gno=c("week").rank("ordinal").over("pid", "season"),
    )
    return g.filter((c("gno") >= 3) & (c(f"{den}_td") >= floor)).with_columns(tseason=c("season"))


def main() -> None:
    src = Gateway().source
    teams = fl.main_team(src)
    wk = src.part("game", "schedule").select("game_id", "week", "season", "game_type")
    reg = wk.filter((c("game_type") == "REG") & c("season").is_between(FIRST, LAST)).select(
        "game_id", "week", "season"
    )
    st = src.part("player_game", "stats").select(
        pid="gsis_id",
        game_id="game_id",
        ry=c("rushing_yards"),
        car=c("carries"),
        cmp=c("completions"),
        att=c("attempts"),
    )
    rows = []

    # runners: yards per carry; past ypc, then yards after contact and yards over expected (NGS)
    pfr = src.part("player_game", "pfr").select(
        pid="gsis_id",
        game_id="game_id",
        pcar=c("pfr_rush_carries"),
        yac=c("pfr_rush_rushing_yards_after_contact"),
    )
    ngs = src.part("player_game", "ngs").select(
        pid="gsis_id",
        game_id="game_id",
        ryoe=c("ngs_rush_rush_yards_over_expected"),
        natt=c("ngs_rush_rush_attempts"),
    )
    rb = st.join(reg, on="game_id").filter(c("car") > 0)
    rb = rb.join(teams.filter(c("position") == "RB").select("pid", "season"), on=["pid", "season"])
    rb = rb.join(pfr, on=["pid", "game_id"], how="left").join(
        ngs, on=["pid", "game_id"], how="left"
    )
    rb = rb.filter(c("season") >= 2018).with_columns(
        c("ryoe", "natt").fill_null(0), c("yac", "pcar").fill_null(0)
    )
    sums = ["ry", "car", "yac", "pcar", "ryoe", "natt"]
    s = (
        seasons_frame(rb, sums, "car", 80)
        .with_columns(
            ypc=c("ry") / c("car"),
            yacpc=c("yac") / c("pcar"),
            ryoepc=c("ryoe") / c("natt"),
            y=c("ry_next") / c("car_next"),
            w=c("car_next"),
        )
        .filter(c("car_next") >= 80)
    )
    for name, x in (
        ("yards after contact per carry", ["yacpc"]),
        ("yards over expected per carry (NGS)", ["ryoepc"]),
        ("both", ["yacpc", "ryoepc"]),
    ):
        rows.append(
            {
                "group": "RB",
                "horizon": "next season",
                "target": "yards per carry",
                "added": name,
                **score(s, ["ypc"], x, "y", "w"),
            }
        )
    g = (
        to_date(rb, sums, "car", 30)
        .with_columns(
            ypc=c("ry_td") / c("car_td"),
            yacpc=c("yac_td") / c("pcar_td"),
            ryoepc=c("ryoe_td") / c("natt_td"),
            y=c("ry") / c("car"),
            w=c("car"),
        )
        .filter(c("natt_td") >= 15)
    )
    for name, x in (
        ("yards after contact per carry", ["yacpc"]),
        ("yards over expected per carry (NGS)", ["ryoepc"]),
        ("both", ["yacpc", "ryoepc"]),
    ):
        rows.append(
            {
                "group": "RB",
                "horizon": "next game",
                "target": "yards per carry",
                "added": name,
                **score(g, ["ypc"], x, "y", "w"),
            }
        )

    # QBs: completion rate; past completion rate, then completion over expected
    pb = fl.plays(src)
    cp = (
        pb.filter((c("pass_attempt") == 1) & (c("sack") == 0) & c("cpoe").is_not_null())
        .group_by(pid="passer_player_id", game_id="game_id")
        .agg(cpoe=(c("cpoe") / 100).sum(), ncp=pl.len())
    )
    qb = (
        st.join(reg, on="game_id")
        .filter(c("att") > 0)
        .join(teams.filter(c("position") == "QB").select("pid", "season"), on=["pid", "season"])
    )
    qb = qb.join(cp, on=["pid", "game_id"], how="left").with_columns(c("cpoe", "ncp").fill_null(0))
    sums = ["cmp", "att", "cpoe", "ncp"]
    s = (
        seasons_frame(qb, sums, "att", 150)
        .with_columns(
            crate=c("cmp") / c("att"),
            cpoer=c("cpoe") / c("ncp"),
            y=c("cmp_next") / c("att_next"),
            w=c("att_next"),
        )
        .filter(c("att_next") >= 150)
    )
    rows.append(
        {
            "group": "QB",
            "horizon": "next season",
            "target": "completion rate",
            "added": "completion over expected",
            **score(s, ["crate"], ["cpoer"], "y", "w"),
        }
    )
    g = to_date(qb, sums, "att", 60).with_columns(
        crate=c("cmp_td") / c("att_td"),
        cpoer=c("cpoe_td") / c("ncp_td"),
        y=c("cmp") / c("att"),
        w=c("att"),
    )
    rows.append(
        {
            "group": "QB",
            "horizon": "next game",
            "target": "completion rate",
            "added": "completion over expected",
            **score(g, ["crate"], ["cpoer"], "y", "w"),
        }
    )

    # pass rushers: sacks per dropback on the field (and pressures); past sack rate, then pressure rate
    of = src.part("player_play", "on_field").filter(
        (c("side") == "defense") & c("season").is_between(2018, LAST)
    )
    drop = pb.filter(c("qb_dropback") == 1).select("game_id", "play_id")
    on = (
        of.join(drop, on=["game_id", "play_id"])
        .group_by(pid="gsis_id", game_id="game_id")
        .agg(nd=pl.len())
    )
    pr = src.part("player_game", "pfr").select(
        pid="gsis_id",
        game_id="game_id",
        press=c("pfr_def_def_pressures"),
        sacks=c("pfr_def_def_sacks"),
    )
    dr = (
        on.join(reg, on="game_id")
        .join(pr, on=["pid", "game_id"], how="left")
        .with_columns(c("press", "sacks").fill_null(0))
    )
    for label, pos in (("DE, DT, NT", ["DE", "DT", "NT"]), ("OLB", ["OLB"])):
        d = dr.join(
            teams.filter(c("position").is_in(pos)).select("pid", "season"), on=["pid", "season"]
        )
        sums = ["sacks", "press", "nd"]
        s = (
            seasons_frame(d, sums, "nd", 150)
            .with_columns(
                srate=c("sacks") / c("nd"),
                prate=c("press") / c("nd"),
                y=c("sacks_next") / c("nd_next"),
                yp=c("press_next") / c("nd_next"),
                w=c("nd_next"),
            )
            .filter(c("nd_next") >= 150)
        )
        rows.append(
            {
                "group": label,
                "horizon": "next season",
                "target": "sacks per dropback",
                "added": "pressure rate",
                **score(s, ["srate"], ["prate"], "y", "w"),
            }
        )
        rows.append(
            {
                "group": label,
                "horizon": "next season",
                "target": "pressures per dropback",
                "added": "(base: past sack rate; added: pressure rate)",
                **score(s, ["srate"], ["prate"], "yp", "w"),
            }
        )
        g = to_date(d, sums, "nd", 60).with_columns(
            srate=c("sacks_td") / c("nd_td"),
            prate=c("press_td") / c("nd_td"),
            y=c("sacks") / c("nd"),
            w=c("nd"),
        )
        rows.append(
            {
                "group": label,
                "horizon": "next game",
                "target": "sacks per dropback",
                "added": "pressure rate",
                **score(g, ["srate"], ["prate"], "y", "w"),
            }
        )

    out = pl.DataFrame(rows)
    pl.Config.set_tbl_rows(50)
    pl.Config.set_tbl_width_chars(300)
    pl.Config.set_tbl_cols(20)
    pl.Config.set_fmt_str_lengths(60)
    pl.Config.set_float_precision(4)
    print(
        "Held out by season. past_vs_league_avg = share of the league average's error the target's own past removes;"
    )
    print(
        "gain = share of the past-only model's error removed by adding the measure (90% interval, players resampled)\n"
    )
    print(out)


if __name__ == "__main__":
    main()
