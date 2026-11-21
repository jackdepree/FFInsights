# ruff: noqa: E501
"""skill-over-expected, the third look (2026-11-20): the CEO's H78 to H83 and question I89.

Discovery only, 2016-2024 (PFR's measures 2018-2024); the 2025 vault untouched. Designs and pass
rules were committed before the run (EXPLORATION.md, "Third look"; commit ea062b7).

Run from pcf/:  python projects/skill-over-expected/explore/third_look.py > projects/skill-over-expected/explore/third_look.txt
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
rng = np.random.default_rng(get_config().seed)
spec = importlib.util.spec_from_file_location("fl", Path(__file__).with_name("first_look.py"))
fl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fl)
r = fl.r


def season_pairs(
    g: pl.DataFrame, sums: list[str], floor_col: str, floor: int, rates: dict, teams: pl.DataFrame
) -> pl.DataFrame:
    """Per player-season sums (floor in both seasons), named rates, next season's rates, moved."""
    s = g.group_by("pid", "season").agg(*[c(k).sum() for k in sums]).filter(c(floor_col) >= floor)
    s = s.with_columns(**{k: c(a) / c(b) for k, (a, b) in rates.items()})
    nxt = s.select("pid", (c("season") - 1).alias("season"), *[c(k).alias(f"{k}_n") for k in rates])
    p = s.join(nxt, on=["pid", "season"]).join(
        teams.select("pid", "season", "team"), on=["pid", "season"], how="left"
    )
    p = p.join(
        teams.select("pid", (c("season") - 1).alias("season"), new_team="team"),
        on=["pid", "season"],
        how="left",
    )
    return p.with_columns(moved=(c("team") != c("new_team")).fill_null(False))


def kept(p: pl.DataFrame, k: str, label: str, group: str) -> dict:
    p = p.filter(c(k).is_finite() & c(f"{k}_n").is_finite())
    raw_repeat = r(p[k], p[f"{k}_n"])
    # each season's league average out (a measure whose definition or charting shifts by season
    # would otherwise repeat for everyone, movers included)
    p = p.with_columns(
        c(k) - c(k).mean().over("season"), c(f"{k}_n") - c(f"{k}_n").mean().over("season")
    )
    st, mv = p.filter(~c("moved")), p.filter(c("moved"))
    rs, rm = r(st[k], st[f"{k}_n"]), r(mv[k], mv[f"{k}_n"])
    lo, hi = fl.boot(p, k, f"{k}_n")
    return {"hunch": group, "measure": label, "pairs": p.height, "movers": mv.height, "raw_repeat": raw_repeat, "repeat": r(p[k], p[f"{k}_n"]),
            "lo90": lo, "hi90": hi, "stayers": rs, "movers_r": rm, "share_kept": rm / rs if rs and np.isfinite(rs) else float("nan")}  # fmt: skip


def held_out(d: pl.DataFrame, xs: list[str], y: str) -> np.ndarray:
    pred = np.full(d.height, np.nan)
    s = d["tseason"].to_numpy()
    X = np.column_stack([np.ones(d.height)] + [d[x].to_numpy().astype(float) for x in xs])
    Y = d[y].to_numpy().astype(float)
    for t in np.unique(s):
        b = np.linalg.lstsq(X[s != t], Y[s != t], rcond=None)[0]
        pred[s == t] = X[s == t] @ b
    return pred


def main() -> None:
    src = Gateway().source
    teams = fl.main_team(src)
    sch = src.part("game", "schedule").select("game_id", "season", "week", "game_type")
    reg = sch.filter((c("game_type") == "REG") & c("season").is_between(FIRST, LAST)).drop(
        "game_type"
    )
    cols = ["game_id", "play_id", "posteam", "qb_dropback", "pass_attempt", "sack", "complete_pass", "cp", "air_yards",
            "rush_attempt", "qb_scramble", "yards_gained", "touchdown", "passer_player_id", "receiver_player_id", "rusher_player_id",
            "pass_defense_1_player_id", "pass_defense_2_player_id", "solo_tackle_1_player_id", "solo_tackle_2_player_id",
            "assist_tackle_1_player_id", "assist_tackle_2_player_id", "assist_tackle_3_player_id", "assist_tackle_4_player_id",
            "tackle_with_assist_1_player_id", "tackle_with_assist_2_player_id"]  # fmt: skip
    pb = src.part("play", "pbp").select(cols).join(reg, on="game_id")
    rows, notes = [], []

    # ---------------- H79: plain catch rate against catches over expected (WR)
    t = pb.filter((c("pass_attempt") == 1) & (c("sack") == 0) & c("cp").is_not_null()).drop_nulls(
        "receiver_player_id"
    )
    t = t.group_by(pid="receiver_player_id", season="season", week="week").agg(
        catch=c("complete_pass").sum(), coe=(c("complete_pass") - c("cp")).sum(), n=pl.len()
    )
    wr = t.join(teams.filter(c("position") == "WR").select("pid", "season"), on=["pid", "season"])
    p = season_pairs(
        wr,
        ["catch", "coe", "n"],
        "n",
        40,
        {"catch_rate": ("catch", "n"), "coe_rate": ("coe", "n")},
        teams,
    )
    rows.append(kept(p, "catch_rate", "plain catch rate (catches / targets)", "H79"))
    rows.append(kept(p, "coe_rate", "catches over expected per target (for comparison)", "H79"))
    d_lo, d_hi = fl.boot(p, "catch_rate", "catch_rate_n", "coe_rate", "coe_rate_n")
    notes.append(
        f"H79: plain catch rate's repeat minus catches over expected's: {rows[-2]['repeat'] - rows[-1]['repeat']:+.3f} (90% {d_lo:+.3f} to {d_hi:+.3f})"
    )

    # ---------------- H80: outside linebackers' roles
    of = src.part("player_play", "on_field").filter(
        (c("side") == "defense") & c("season").is_between(2018, LAST)
    )
    drop = pb.filter(c("qb_dropback") == 1).select("game_id", "play_id")
    on = (
        of.join(drop, on=["game_id", "play_id"])
        .group_by(pid="gsis_id", game_id="game_id")
        .agg(nd=pl.len())
    )
    pfr = src.part("player_game", "pfr").select(
        pid="gsis_id", game_id="game_id", press=c("pfr_def_def_pressures").fill_null(0), tgt=c("pfr_def_def_targets").fill_null(0),
        cmp=c("pfr_def_def_completions_allowed").fill_null(0), yds=c("pfr_def_def_yards_allowed").fill_null(0),
        ints=c("pfr_def_def_ints").fill_null(0), adot=c("pfr_def_def_adot"),
    )  # fmt: skip
    dg = (
        on.join(reg, on="game_id")
        .join(pfr, on=["pid", "game_id"], how="left")
        .with_columns(c("press", "tgt", "cmp", "yds", "ints").fill_null(0))
    )
    dg = dg.with_columns(
        air=(c("adot").fill_null(0) * c("tgt")),
        nadot=pl.when(c("adot").is_not_null()).then(c("tgt")).otherwise(0),
    )
    for label, pos in (("OLB", ["OLB"]), ("ILB", ["ILB", "MLB"])):
        d = dg.join(
            teams.filter(c("position").is_in(pos)).select("pid", "season"), on=["pid", "season"]
        )
        s = (
            d.group_by("pid", "season")
            .agg(c("press", "tgt", "nd").sum())
            .filter((c("nd") >= 150) & ((c("press") + c("tgt")) >= 10))
        )
        s = s.with_columns(rush=c("press") / (c("press") + c("tgt")))
        outer = s.filter((c("rush") < 1 / 3) | (c("rush") > 2 / 3)).height / s.height
        hist = np.histogram(s["rush"].to_numpy(), bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0001])[0]
        notes.append(
            f"H80 (a) {label}: {s.height} seasons; outside the middle third {outer:.0%}; rush share by fifths {hist.tolist()}"
        )
        d2 = d.with_columns(pt=c("press") + c("tgt"))
        p = season_pairs(
            d2,
            ["press", "tgt", "pt", "nd"],
            "nd",
            150,
            {"rush_share": ("press", "pt"), "press_rate": ("press", "nd")},
            teams,
        )
        rows.append(
            kept(
                p,
                "rush_share",
                f"{label} role: rush share = pressures / (pressures + coverage targets)",
                "H80 (c)",
            )
        )
        if label == "OLB":
            rows.append(
                kept(p, "press_rate", "OLB pressure rate, all (the first look's 97%)", "H80 (b)")
            )
            rows.append(
                kept(
                    p.filter(c("rush_share") > 2 / 3),
                    "press_rate",
                    "OLB pressure rate, rushers only (rush share over 2/3 in the first season)",
                    "H80 (b)",
                )
            )

    # ---------------- H81: defensive backs' coverage
    pd_ = pl.concat([
        pb.select(pid="pass_defense_1_player_id", game_id="game_id"),
        pb.select(pid="pass_defense_2_player_id", game_id="game_id"),
    ]).drop_nulls("pid").group_by("pid", "game_id").agg(pd=pl.len())  # fmt: skip
    db = dg.join(pd_, on=["pid", "game_id"], how="left").with_columns(c("pd").fill_null(0))
    db = db.join(
        teams.filter(c("position").is_in(["CB", "FS", "SS"])).select("pid", "season"),
        on=["pid", "season"],
    )
    rates = {
        "catch_allowed": ("cmp", "tgt"),
        "yds_per_tgt": ("yds", "tgt"),
        "pd_per_tgt": ("pd", "tgt"),
        "int_per_tgt": ("ints", "tgt"),
        "depth_against": ("air", "nadot"),
    }
    p = season_pairs(
        db, ["cmp", "tgt", "yds", "pd", "ints", "air", "nadot"], "tgt", 30, rates, teams
    )
    for k, lab in zip(
        rates,
        [
            "catch rate allowed",
            "yards per target",
            "passes defensed per target",
            "interceptions per target",
            "throw depth against",
        ],
        strict=True,
    ):
        rows.append(kept(p, k, f"DB {lab}", "H81"))

    # ---------------- H82: sacks per pressure, QBs against linemen; I89 time to throw
    pa = (
        src.part("play", "participation")
        .filter(c("was_pressure").is_not_null())
        .select(
            "game_id", "play_id", pres=c("was_pressure").cast(pl.Float64), ttt=c("time_to_throw")
        )
    )
    dp = pb.filter(c("qb_dropback") == 1).join(pa, on=["game_id", "play_id"])
    dp = dp.with_columns(
        sp=c("sack") * c("pres"),
        air_att=pl.when((c("pass_attempt") == 1) & (c("sack") == 0)).then(c("air_yards")),
    )
    dp = dp.with_columns(
        n_air=c("air_att").is_not_null().cast(pl.Int32),
        n_ttt=c("ttt").is_not_null().cast(pl.Int32),
        air_att=c("air_att").fill_null(0),
        ttt=c("ttt").fill_null(0),
    )
    sums = ["n", "pres", "sack", "sp", "ttt", "n_ttt", "air_att", "n_air"]
    qg = (
        dp.drop_nulls("passer_player_id")
        .group_by(pid="passer_player_id", season="season", week="week")
        .agg(
            c("pres").sum(),
            c("sack").sum(),
            c("sp").sum(),
            c("ttt").sum(),
            c("n_ttt").sum(),
            c("air_att").sum(),
            c("n_air").sum(),
            n=pl.len(),
        )
    )
    qg = qg.join(teams.filter(c("position") == "QB").select("pid", "season"), on=["pid", "season"])
    rq = {
        "sack_per_pressure": ("sack", "pres"),
        "pressure_rate": ("pres", "n"),
        "sack_rate": ("sack", "n"),
        "ttt": ("ttt", "n_ttt"),
        "depth": ("air_att", "n_air"),
    }
    pq = season_pairs(qg, sums, "n", 150, rq, teams)
    olp = src.part("player_play", "on_field").filter(
        (c("side") == "offense")
        & c("position").is_in(["C", "LT", "RT", "LG", "RG", "G", "T"])
        & c("season").is_between(FIRST, LAST)
    )
    og = olp.select("game_id", "play_id", pid="gsis_id").join(
        dp.select(
            "game_id",
            "play_id",
            "season",
            "week",
            "pres",
            "sack",
            "sp",
            "ttt",
            "n_ttt",
            "air_att",
            "n_air",
        ),
        on=["game_id", "play_id"],
    )
    og = og.group_by("pid", "season", "week").agg(
        c("pres").sum(),
        c("sack").sum(),
        c("sp").sum(),
        c("ttt").sum(),
        c("n_ttt").sum(),
        c("air_att").sum(),
        c("n_air").sum(),
        n=pl.len(),
    )
    po = season_pairs(og, sums, "n", 300, rq, teams)
    for k, lab in (
        ("sack_per_pressure", "sacks per pressure"),
        ("sack_rate", "sacks per dropback"),
        ("pressure_rate", "pressures per dropback"),
    ):
        rows.append(kept(pq, k, f"QB {lab}", "H82"))
        rows.append(kept(po, k, f"OL (team's on his dropbacks) {lab}", "H82"))
    for k, lab in (("ttt", "time to throw"), ("depth", "throw depth (air yards per attempt)")):
        rows.append(kept(pq, k, f"QB {lab}", "I89"))
        rows.append(kept(po, k, f"OL (team's on his dropbacks) {lab}", "I89"))

    # ---------------- H83: broken tackles and tacklers needed (RB)
    tk = ["solo_tackle_1_player_id", "solo_tackle_2_player_id", "assist_tackle_1_player_id", "assist_tackle_2_player_id",
          "assist_tackle_3_player_id", "assist_tackle_4_player_id", "tackle_with_assist_1_player_id", "tackle_with_assist_2_player_id"]  # fmt: skip
    ru = pb.filter((c("rush_attempt") == 1) & (c("qb_scramble") == 0)).drop_nulls(
        "rusher_player_id"
    )
    ru = ru.with_columns(
        tacklers=pl.sum_horizontal([c(k).is_not_null().cast(pl.Int32) for k in tk])
    )
    ru = ru.with_columns(
        after=((c("yards_gained") > 0) & (c("tacklers") > 0)).cast(pl.Int32),
        before=((c("yards_gained") <= 0) & (c("tacklers") > 0)).cast(pl.Int32),
    ).with_columns(
        multi_after=(c("after") * (c("tacklers") >= 2)).cast(pl.Int32),
        multi_before=(c("before") * (c("tacklers") >= 2)).cast(pl.Int32),
    )
    rg = ru.group_by(pid="rusher_player_id", game_id="game_id", season="season", week="week").agg(
        c("after").sum(),
        c("before").sum(),
        c("multi_after").sum(),
        c("multi_before").sum(),
        car=pl.len(),
    )
    bt = src.part("player_game", "pfr").select(
        pid="gsis_id",
        game_id="game_id",
        bt=c("pfr_rush_rushing_broken_tackles"),
        pcar=c("pfr_rush_carries"),
    )
    rg = rg.join(bt, on=["pid", "game_id"], how="left").with_columns(c("bt", "pcar").fill_null(0))
    rg = rg.join(teams.filter(c("position") == "RB").select("pid", "season"), on=["pid", "season"])
    pr_ = season_pairs(rg, ["car", "after", "before", "multi_after", "multi_before"], "car", 80,
                       {"multi_after_share": ("multi_after", "after"), "multi_before_share": ("multi_before", "before")}, teams)  # fmt: skip
    pb_ = season_pairs(
        rg.filter(c("season") >= 2018),
        ["car", "bt", "pcar"],
        "car",
        80,
        {"bt_per_carry": ("bt", "pcar")},
        teams,
    )
    rows.append(kept(pb_, "bt_per_carry", "RB broken tackles per carry (PFR)", "H83"))
    rows.append(
        kept(
            pr_, "multi_after_share", "RB tackled after the line: share needing 2+ tacklers", "H83"
        )
    )
    rows.append(
        kept(
            pr_,
            "multi_before_share",
            "RB tackled at or behind the line: share needing 2+ tacklers",
            "H83",
        )
    )

    # ---------------- H78: a moving back's new share
    car = ru.join(
        teams.select(pid="pid", season="season", position="position"),
        left_on=["rusher_player_id", "season"],
        right_on=["pid", "season"],
    )
    car = (
        car.filter(c("position") == "RB")
        .group_by(pid="rusher_player_id", season="season", team="posteam")
        .agg(car=pl.len())
    )
    tot = car.group_by("team", "season").agg(tcar=c("car").sum())
    car = car.join(tot, on=["team", "season"]).with_columns(share=c("car") / c("tcar"))
    pfr_rb = (
        src.part("player_game", "pfr")
        .select(
            pid="gsis_id",
            season="season",
            yac=c("pfr_rush_rushing_yards_after_contact"),
            pcar=c("pfr_rush_carries"),
        )
        .drop_nulls(["yac", "pcar"])
        .group_by("pid", "season")
        .agg(c("yac").sum(), c("pcar").sum())
    )
    pfr_rb = pfr_rb.with_columns(yacpc=pl.when(c("pcar") >= 20).then(c("yac") / c("pcar")))
    league = float(pfr_rb.filter(c("pcar") >= 20).select(c("yac").sum() / c("pcar").sum()).item())
    top = car.group_by("team", "season").agg(habit=c("share").max())
    mt = teams.select("pid", "season", main="team")
    old = car.join(mt, on=["pid", "season"]).filter(
        (c("team") == c("main")) & (c("car") >= 20) & (c("season") >= 2018) & (c("season") < LAST)
    )
    nxt = mt.select("pid", (c("season") - 1).alias("season"), new_team="main")
    mv = old.join(nxt, on=["pid", "season"]).filter(c("new_team") != c("team"))
    mv = mv.join(
        car.select("pid", (c("season") - 1).alias("season"), new_team="team", y="share"),
        on=["pid", "season", "new_team"],
        how="left",
    ).with_columns(c("y").fill_null(0))
    mv = mv.join(top.rename({"team": "new_team"}), on=["new_team", "season"], how="left")
    # the backs who stay: on the new team last season and still its players next season
    stay = car.join(
        mt.select("pid", (c("season") - 1).alias("season"), nxt_main="main"),
        on=["pid", "season"],
        how="left",
    ).filter(c("team") == c("nxt_main"))
    stay = stay.join(
        pfr_rb.select("pid", "season", "yacpc"), on=["pid", "season"], how="left"
    ).with_columns(c("yacpc").fill_null(league))
    sg = stay.group_by(new_team="team", season="season").agg(
        stay_share=c("share").sum(), stay_yac=(c("yacpc") * c("car")).sum() / c("car").sum()
    )
    mv = mv.join(sg, on=["new_team", "season"], how="left").with_columns(
        c("stay_share").fill_null(0), c("stay_yac").fill_null(league), c("habit").fill_null(0)
    )
    mv = mv.join(
        pfr_rb.select("pid", "season", own_yac="yacpc"), on=["pid", "season"], how="left"
    ).with_columns(c("own_yac").fill_null(league))
    mv = mv.with_columns(tseason=c("season") + 1)
    Y = mv["y"].to_numpy()
    preds = {
        "habit (his old share + the backfield's top share)": held_out(mv, ["share", "habit"], "y"),
        "who (his old share + the staying backs' share)": held_out(
            mv, ["share", "stay_share"], "y"
        ),
        "who and how good (+ yards after contact, his and theirs)": held_out(
            mv, ["share", "stay_share", "own_yac", "stay_yac"], "y"
        ),
    }
    err = {k: (Y - v) ** 2 for k, v in preds.items()}
    pid = mv["pid"].to_numpy()
    u, inv = np.unique(pid, return_inverse=True)
    names = list(err)

    def gain(a, b):
        sa, sb = np.bincount(inv, err[a]), np.bincount(inv, err[b])
        g = []
        for _ in range(1000):
            k = np.bincount(rng.integers(0, len(u), len(u)), minlength=len(u))
            g.append(1 - (k @ sb) / (k @ sa))
        return 1 - err[b].sum() / err[a].sum(), *np.quantile(g, [0.05, 0.95])

    h78 = [
        {
            "comparison": "who against habit",
            **dict(zip(["gain", "lo90", "hi90"], gain(names[0], names[1]), strict=True)),
        },
        {
            "comparison": "who and how good against habit",
            **dict(zip(["gain", "lo90", "hi90"], gain(names[0], names[2]), strict=True)),
        },
        {
            "comparison": "who and how good against who (how good adds?)",
            **dict(zip(["gain", "lo90", "hi90"], gain(names[1], names[2]), strict=True)),
        },
    ]
    notes.append(f"H78: {mv.height} moving backs (20+ carries the season before, 2018-2023 to 2019-2024); mean new share {Y.mean():.3f}; "
                 f"squared error, habit {err[names[0]].mean():.4f}, who {err[names[1]].mean():.4f}, who and how good {err[names[2]].mean():.4f}")  # fmt: skip

    pl.Config.set_tbl_rows(80)
    pl.Config.set_tbl_cols(20)
    pl.Config.set_tbl_width_chars(300)
    pl.Config.set_fmt_str_lengths(80)
    pl.Config.set_float_precision(3)
    print(
        "Seasons 2016-2024 (PFR 2018-2024). raw_repeat = season-to-season r; repeat and the rest with each season's league average taken out (90%, players resampled); share_kept = movers_r / stayers\n"
    )
    print(pl.DataFrame(rows, infer_schema_length=None))
    print()
    for n in notes:
        print(n)
    print(
        "\n== H78: a moving back's new share of his team's running-back carries, held out by season (gain = share of error removed)"
    )
    print(pl.DataFrame(h78))


if __name__ == "__main__":
    main()
