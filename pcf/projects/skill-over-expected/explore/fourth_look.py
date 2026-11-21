# ruff: noqa: E501
"""skill-over-expected, the fourth look (2026-11-20): the CEO's H84, the third look's measures over
context-live's expectation (its back-history, decision 0038) against the plain rates.

Discovery only, 2017-2024; the 2025 vault untouched. Designs and pass rules were committed before
the run (EXPLORATION.md, "Fourth look"; commit 3b57c2a).

Run from pcf/:  python projects/skill-over-expected/explore/fourth_look.py > projects/skill-over-expected/explore/fourth_look.txt
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import polars as pl

from pcf.data.gateway import Gateway
from pcf.experts.context_live import back

c = pl.col
FIRST, LAST = 2017, 2024
spec = importlib.util.spec_from_file_location("tl", Path(__file__).with_name("third_look.py"))
tl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tl)
fl = tl.fl
EDITIONS = ("situation", "calls16")
SHORT = {"pressure_prob": "pr", "sack_prob": "sk", "completion_prob": "cp",
         "time_to_throw_exp": "tt", "air_yards_exp": "ay", "rush_yards_exp": "ry"}  # fmt: skip
FORMS = ("plain", "over situation", "over calls16")


def expectations() -> tuple[pl.DataFrame, dict]:
    """One row per play: `<short>_<edition>` for each outcome and edition."""
    out, shares = None, {}
    for ed in EDITIONS:
        rep = json.loads((back.cache_dir() / f"back_{ed}.json").read_text())
        shares[ed] = rep["share_removed"]
        h = pl.read_parquet(rep["path"]).select("game_id", "play_id", "quantity", "mean")
        w = h.pivot(on="quantity", index=["game_id", "play_id"], values="mean")
        w = w.rename({q: f"{SHORT[q]}_{ed}" for q in SHORT if q in w.columns})
        out = (
            w if out is None else out.join(w, on=["game_id", "play_id"], how="full", coalesce=True)
        )
    return out, shares


def sums(d: pl.DataFrame, by: list[str], actual: str, exp: str) -> pl.DataFrame:
    """Per group: the actual's sum `a`, the plays `n`, and each edition's expected sum."""
    d = d.filter(
        c(actual).is_not_null()
        & pl.all_horizontal([c(f"{exp}_{ed}").is_not_null() for ed in EDITIONS])
    )
    return d.group_by(by).agg(
        a=c(actual).sum(), n=pl.len(), **{f"e_{ed}": c(f"{exp}_{ed}").sum() for ed in EDITIONS}
    )


def three(
    g: pl.DataFrame, floor: int, teams: pl.DataFrame, scale: pl.DataFrame | None = None
) -> pl.DataFrame:
    """Season pairs with the three forms. `scale` (pid, season, lam): a pass rusher's own pressures
    against his team's expected pressures, scaled by his position's ratio that season."""
    p = tl.season_pairs(g, ["a", "n", "e_situation", "e_calls16"], "n", floor,
                        {"plain": ("a", "n"), "ea_s": ("e_situation", "n"), "ea_c": ("e_calls16", "n")}, teams)  # fmt: skip
    lam = {"situation": pl.lit(1.0), "calls16": pl.lit(1.0)}
    lam_n = dict(lam)
    if scale is not None:
        p = p.join(
            scale.select("pid", "season", "lam_situation", "lam_calls16"),
            on=["pid", "season"],
            how="left",
        )
        p = p.join(scale.select("pid", (c("season") - 1).alias("season"), ln_situation="lam_situation", ln_calls16="lam_calls16"),
                   on=["pid", "season"], how="left")  # fmt: skip
        lam = {ed: c(f"lam_{ed}") for ed in EDITIONS}
        lam_n = {ed: c(f"ln_{ed}") for ed in EDITIONS}
    return p.with_columns(
        **{"over situation": c("plain") - lam["situation"] * c("ea_s"),
           "over situation_n": c("plain_n") - lam_n["situation"] * c("ea_s_n"),
           "over calls16": c("plain") - lam["calls16"] * c("ea_c"),
           "over calls16_n": c("plain_n") - lam_n["calls16"] * c("ea_c_n")}
    )  # fmt: skip


def assess(p: pl.DataFrame, label: str) -> list[dict]:
    out = []
    for f in FORMS:
        k = tl.kept(p, f, label, f)
        k["passes"] = bool(k["repeat"] >= 0.2 and k["share_kept"] >= 0.5)
        k["form"] = f
        out.append(k)
    return out


def main() -> None:
    src = Gateway().source
    teams = fl.main_team(src)
    sch = src.part("game", "schedule").select("game_id", "season", "week", "game_type")
    reg = sch.filter((c("game_type") == "REG") & c("season").is_between(FIRST, LAST)).drop(
        "game_type"
    )
    cols = ["game_id", "play_id", "qb_dropback", "pass_attempt", "sack", "complete_pass", "air_yards",
            "rush_attempt", "qb_scramble", "yards_gained", "passer_player_id", "receiver_player_id", "rusher_player_id"]  # fmt: skip
    pb = src.part("play", "pbp").select(cols).join(reg, on="game_id")
    pa = src.part("play", "participation").select(
        "game_id",
        c("play_id").cast(pl.Int64),
        pres=c("was_pressure").cast(pl.Float64),
        ttt=c("time_to_throw"),
    )
    ex, shares = expectations()
    pb = (
        pb.with_columns(c("play_id").cast(pl.Int64))
        .join(pa, on=["game_id", "play_id"], how="left")
        .join(ex, on=["game_id", "play_id"], how="left")
    )
    drop = pb.filter(c("qb_dropback") == 1)
    att = drop.filter((c("pass_attempt") == 1) & (c("sack") == 0) & (c("qb_scramble") == 0))
    runs = pb.filter((c("rush_attempt") == 1) & (c("qb_dropback") == 0))
    rows: list[dict] = []
    pos = lambda ps: teams.filter(c("position").is_in(ps)).select("pid", "season")  # noqa: E731

    # pass rushers: PFR pressures per game against the team's expected pressures on his dropbacks
    of = src.part("player_play", "on_field").filter(
        (c("side") == "defense") & c("season").is_between(2018, LAST)
    )
    of = of.select("game_id", c("play_id").cast(pl.Int64), pid="gsis_id").join(
        drop.select("game_id", "play_id", "pres", "pr_situation", "pr_calls16"),
        on=["game_id", "play_id"],
    )
    of = of.filter(
        c("pres").is_not_null() & c("pr_situation").is_not_null() & c("pr_calls16").is_not_null()
    )
    on = of.group_by(pid="pid", game_id="game_id").agg(
        n=pl.len(), e_situation=c("pr_situation").sum(), e_calls16=c("pr_calls16").sum()
    )
    pfr = src.part("player_game", "pfr").select(
        pid="gsis_id",
        game_id="game_id",
        a=c("pfr_def_def_pressures").fill_null(0),
        tgt=c("pfr_def_def_targets").fill_null(0),
    )
    dg = (
        on.join(reg, on="game_id")
        .join(pfr, on=["pid", "game_id"], how="left")
        .with_columns(c("a", "tgt").fill_null(0))
    )
    for label, ps in (("DE, DT, NT", ["DE", "DT", "NT"]), ("OLB", ["OLB"])):
        d = dg.join(pos(ps), on=["pid", "season"])
        # the position's own pressures over its expected team pressures, by season
        lam = d.group_by("season").agg(
            **{f"lam_{ed}": c("a").sum() / c(f"e_{ed}").sum() for ed in EDITIONS}
        )
        scale = d.select("pid", "season").unique().join(lam, on="season")
        p = three(d.with_columns(pt=c("a") + c("tgt")), 150, teams, scale)
        rows += assess(p, f"{label} pressures per dropback (PFR)")
        if label == "OLB":
            s = (
                d.group_by("pid", "season")
                .agg(c("a", "tgt").sum())
                .with_columns(rush=c("a") / (c("a") + c("tgt")))
            )
            rushers = s.filter(c("rush") > 2 / 3).select("pid", "season")
            rows += assess(
                p.join(rushers, on=["pid", "season"]), "OLB pressures per dropback, rushers only"
            )

    # receivers and QBs: catch rate and completion
    wr = sums(
        att.drop_nulls("receiver_player_id"),
        ["receiver_player_id", "season", "week"],
        "complete_pass",
        "cp",
    ).rename({"receiver_player_id": "pid"})
    rows += assess(three(wr.join(pos(["WR"]), on=["pid", "season"]), 40, teams), "WR catch rate")
    qb_ids = pos(["QB"])
    qa = sums(
        att.drop_nulls("passer_player_id"),
        ["passer_player_id", "season", "week"],
        "complete_pass",
        "cp",
    ).rename({"passer_player_id": "pid"})
    rows += assess(three(qa.join(qb_ids, on=["pid", "season"]), 150, teams), "QB completion rate")

    # QBs and linemen: sacks, pressures, time to throw, depth
    olp = (
        src.part("player_play", "on_field")
        .filter(
            (c("side") == "offense")
            & c("position").is_in(["C", "LT", "RT", "LG", "RG", "G", "T"])
            & c("season").is_between(FIRST, LAST)
        )
        .select("game_id", c("play_id").cast(pl.Int64), pid="gsis_id")
    )
    for label, frame, actual, short in (
        ("sacks per dropback", drop, "sack", "sk"),
        ("pressures per dropback", drop, "pres", "pr"),
        ("time to throw", drop, "ttt", "tt"),
        ("throw depth", att, "air_yards", "ay"),
    ):
        q = sums(
            frame.drop_nulls("passer_player_id"),
            ["passer_player_id", "season", "week"],
            actual,
            short,
        ).rename({"passer_player_id": "pid"})
        rows += assess(three(q.join(qb_ids, on=["pid", "season"]), 150, teams), f"QB {label}")
        o = sums(
            olp.join(frame, on=["game_id", "play_id"]), ["pid", "season", "week"], actual, short
        )
        rows += assess(three(o, 300, teams), f"OL (team's on his dropbacks) {label}")

    # runners: yards per carry
    rb = sums(
        runs.drop_nulls("rusher_player_id"),
        ["rusher_player_id", "season", "week"],
        "yards_gained",
        "ry",
    ).rename({"rusher_player_id": "pid"})
    rows += assess(
        three(rb.join(pos(["RB"]), on=["pid", "season"]), 80, teams), "RB yards per carry"
    )

    t = pl.DataFrame(rows, infer_schema_length=None).select(
        "measure",
        "form",
        "pairs",
        "movers",
        "repeat",
        "lo90",
        "hi90",
        "stayers",
        "movers_r",
        "share_kept",
        "passes",
    )
    pl.Config.set_tbl_rows(100)
    pl.Config.set_tbl_width_chars(250)
    pl.Config.set_fmt_str_lengths(70)
    print(
        "Seasons 2017-2024 (PFR 2018-2024). Every form with each season's league average taken out; over = actual minus context-live's back-history expectation (decision 0038). passes = repeat 0.2+ and movers keep half.\n"
    )
    print(
        "== How much of each outcome's spread (season level out) the expectation removes, % by test season"
    )
    for ed in EDITIONS:
        print(ed, {q: {s: round(v, 2) for s, v in d.items()} for q, d in shares[ed].items()})
    print("\n== Every measure, three forms")
    print(t.with_columns(c("repeat", "lo90", "hi90", "stayers", "movers_r", "share_kept").round(3)))
    wide = t.pivot(on="form", index="measure", values=["repeat", "share_kept", "passes"])
    print("\n== H84: measures passing both bars, by form")
    for f in FORMS:
        print(
            f"{f}: {int(t.filter(c('form') == f)['passes'].sum())} of {t.filter(c('form') == f).height}"
        )
    for f in FORMS[1:]:
        dr = wide[f"repeat_{f}"] - wide["repeat_plain"]
        dk = wide[f"share_kept_{f}"] - wide["share_kept_plain"]
        print(
            f"{f} against plain: repeat up on {int((dr > 0).sum())} of {wide.height}, mean change {np.nanmean(dr.to_numpy()):+.3f}; "
            f"|change| under 0.03 on {int((dr.abs() < 0.03).sum())}; share kept up on {int((dk > 0).sum())}, median change {np.nanmedian(dk.to_numpy()):+.3f}"
        )
    print(
        wide.select(
            "measure", *[x for x in wide.columns if x.startswith("repeat") or x.startswith("share")]
        ).with_columns(pl.selectors.numeric().round(3))
    )


if __name__ == "__main__":
    main()
