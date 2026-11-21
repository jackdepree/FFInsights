# ruff: noqa: E501
"""skill-over-expected, the first look (2026-11-20): which skills over expected repeat, follow a
player who moves, and beat EPA, by position. Discovery only, 2016-2024 (the 2025 vault untouched).

The technical calls and pass rules are in BRIEF.md ("The first look's technical calls", "Pass
rules, written before the run"). Per player-season, a rate with a volume floor; then:
  - reliability: odd against even weeks within a season, stepped up to a full season (the noise
    ceiling for the season-to-season repeat);
  - repeat: season s against s+1, stayers and movers apart, and share kept = movers / stayers;
  - against EPA (or sacks for pass rushers): the same players' repeat, the difference with a 90%
    interval from resampling players.
A last section checks QBs' completion and runners' yards against context-live's own expectations
(2023-2024, one season pair).

Run from pcf/:  python projects/skill-over-expected/explore/first_look.py > projects/skill-over-expected/explore/first_look.txt
"""

from __future__ import annotations

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.gateway import Gateway

c = pl.col
FIRST, LAST = 2016, 2024
DRAWS = 2000
rng = np.random.default_rng(get_config().seed)


def r(x, y) -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    return float(np.corrcoef(x[ok], y[ok])[0, 1]) if ok.sum() > 10 else float("nan")


def boot(pairs: pl.DataFrame, a: str, b: str, a2: str | None = None, b2: str | None = None):
    """90% interval of r(a, b), or of r(a, b) - r(a2, b2), resampling players."""
    pid = pairs["pid"].to_numpy()
    u, inv = np.unique(pid, return_inverse=True)
    cols = [pairs[k].to_numpy().astype(float) for k in (a, b, a2, b2) if k]
    out = []
    for _ in range(DRAWS):
        pick = rng.integers(0, len(u), len(u))
        w = np.bincount(pick, minlength=len(u))[inv]
        idx = np.repeat(np.arange(len(pid)), w)
        v = r(cols[0][idx], cols[1][idx])
        if a2:
            v -= r(cols[2][idx], cols[3][idx])
        out.append(v)
    return tuple(np.nanquantile(out, [0.05, 0.95]))


def main_team(src) -> pl.DataFrame:
    """Main team (most games, roster) and main position (most snaps on the on-field map, whose
    depth-chart labels are finer than the roster's DL/OL/LB/DB; the roster's where he has none)."""
    ro = src.part("player_game", "roster").filter(c("season").is_between(FIRST, LAST + 1))
    team = (
        ro.group_by("gsis_id", "season", "team", "position")
        .agg(n=pl.len())
        .sort("n", descending=True)
        .group_by("gsis_id", "season", maintain_order=True)
        .first()
        .select(pid="gsis_id", season="season", team="team", roster_pos="position")
    )
    of = src.part("player_play", "on_field").filter(c("season").is_between(FIRST, LAST + 1))
    pos = (
        of.group_by("gsis_id", "season", "position")
        .agg(n=pl.len())
        .sort("n", descending=True)
        .group_by("gsis_id", "season", maintain_order=True)
        .first()
        .select(pid="gsis_id", season="season", field_pos="position")
    )
    return team.join(pos, on=["pid", "season"], how="left").select(
        "pid", "season", "team", position=pl.coalesce("field_pos", "roster_pos")
    )


def season_rates(g: pl.DataFrame, num: list[str], den: str, floor: int) -> pl.DataFrame:
    """Per player-season and per odd/even half: sum(num) / sum(den)."""
    g = g.with_columns(half=(c("week") % 2))
    full = g.group_by("pid", "season").agg(*[c(k).sum() for k in num], c(den).sum())
    full = full.filter(c(den) >= floor)
    halves = g.group_by("pid", "season", "half").agg(*[c(k).sum() for k in num], c(den).sum())
    return full, halves


def assess(
    name: str,
    g: pl.DataFrame,
    measure: str,
    compare: str | None,
    den: str,
    floor: int,
    teams: pl.DataFrame,
) -> dict:
    """g: one row per player-game with week, the numerators (measure, compare) and the chances."""
    num = [measure] + ([compare] if compare else [])
    full, halves = season_rates(g, num, den, floor)
    for k in num:
        full = full.with_columns((c(k) / c(den)).alias(f"{k}_r"))
        halves = halves.with_columns((c(k) / c(den)).alias(f"{k}_r"))
    # reliability: odd vs even weeks, halves with at least a third of the floor each
    h = halves.filter(c(den) >= floor / 3)
    hp = h.filter(c("half") == 1).join(h.filter(c("half") == 0), on=["pid", "season"], suffix="_e")
    hp = hp.join(full.select("pid", "season"), on=["pid", "season"])
    rel = {}
    for k in num:
        rh = r(hp[f"{k}_r"], hp[f"{k}_r_e"])
        rel[k] = 2 * rh / (1 + rh) if np.isfinite(rh) else float("nan")
    # season to season
    nxt = full.select(
        "pid", (c("season") - 1).alias("season"), *[c(f"{k}_r").alias(f"{k}_n") for k in num]
    )
    p = full.join(nxt, on=["pid", "season"]).join(teams, on=["pid", "season"], how="left")
    p = p.join(
        teams.select("pid", (c("season") - 1).alias("season"), new_team="team"),
        on=["pid", "season"],
        how="left",
    )
    p = p.with_columns(moved=(c("team") != c("new_team")).fill_null(False))
    st, mv = p.filter(~c("moved")), p.filter(c("moved"))
    m = f"{measure}_r"
    row = {
        "measure": name,
        "pairs": p.height,
        "movers": mv.height,
        "reliability": rel[measure],
        "repeat": r(p[m], p[f"{measure}_n"]),
        "repeat_lo": None,
        "repeat_hi": None,
        "stayers": r(st[m], st[f"{measure}_n"]),
        "movers_r": r(mv[m], mv[f"{measure}_n"]),
    }
    row["repeat_lo"], row["repeat_hi"] = boot(p, m, f"{measure}_n")
    row["share_kept"] = row["movers_r"] / row["stayers"] if row["stayers"] else float("nan")
    if compare:
        cm = f"{compare}_r"
        row["compare_repeat"] = r(p[cm], p[f"{compare}_n"])
        row["diff"] = row["repeat"] - row["compare_repeat"]
        row["diff_lo"], row["diff_hi"] = boot(p, m, f"{measure}_n", cm, f"{compare}_n")
        row["compare_reliability"] = rel[compare]
    return row


def plays(src) -> pl.DataFrame:
    p = (
        src.part("play", "pbp")
        .filter(c("season_type") == "REG")
        .select(
            "game_id",
            "play_id",
            "week",
            "posteam",
            "defteam",
            "down",
            "ydstogo",
            "epa",
            "cp",
            "cpoe",
            "complete_pass",
            "pass_attempt",
            "sack",
            "qb_dropback",
            "rush_attempt",
            "qb_scramble",
            "passer_player_id",
            "receiver_player_id",
            "rusher_player_id",
        )
    )
    s = src.part("game", "schedule").select("game_id", "season")
    return p.join(s, on="game_id").filter(c("season").is_between(FIRST, LAST))


def main() -> None:
    src = Gateway().source
    teams = main_team(src)
    pb = plays(src)
    rows = []

    # QBs: completion over expected per pass; EPA per dropback
    qa = pb.filter((c("pass_attempt") == 1) & (c("sack") == 0) & c("cpoe").is_not_null())
    qa = qa.group_by(pid="passer_player_id", season="season", week="week").agg(
        cpoe=(c("cpoe") / 100).sum(), n=pl.len()
    )
    qd = (
        pb.filter(c("qb_dropback") == 1)
        .drop_nulls("epa")
        .group_by(pid="passer_player_id", season="season", week="week")
        .agg(epa=c("epa").sum(), nd=pl.len())
    )
    q = qa.join(qd, on=["pid", "season", "week"], how="left").with_columns(
        epa=c("epa") * c("n") / c("nd")
    )
    rows.append(
        {
            "group": "QB",
            **assess(
                "completion over expected per pass (EPA per dropback beside)",
                q,
                "cpoe",
                "epa",
                "n",
                150,
                teams,
            ),
        }
    )

    # receivers: catches over expected per target; EPA per target
    ta = pb.filter((c("pass_attempt") == 1) & (c("sack") == 0) & c("cp").is_not_null()).drop_nulls(
        "receiver_player_id"
    )
    ta = ta.group_by(pid="receiver_player_id", season="season", week="week").agg(
        coe=(c("complete_pass") - c("cp")).sum(), epa=c("epa").fill_null(0).sum(), n=pl.len()
    )
    for pos in (["WR"], ["TE"], ["RB"]):
        ids = teams.filter(c("position").is_in(pos)).select("pid", "season")
        rows.append(
            {
                "group": pos[0],
                **assess(
                    "catches over expected per target (EPA per target beside)",
                    ta.join(ids, on=["pid", "season"]),
                    "coe",
                    "epa",
                    "n",
                    40,
                    teams,
                ),
            }
        )

    # runners: NGS rushing yards over expected per carry; EPA per carry; PFR before and after contact
    ngs = src.part("player_game", "ngs").filter(
        c("season").is_between(FIRST, LAST) & c("ngs_rush_rush_attempts").is_not_null()
    )
    wk = src.part("game", "schedule").select("game_id", "week")
    ngs = ngs.join(wk, on="game_id").select(
        pid="gsis_id",
        season="season",
        week="week",
        ryoe=c("ngs_rush_rush_yards_over_expected"),
        n=c("ngs_rush_rush_attempts"),
    )
    ra = pb.filter((c("rush_attempt") == 1) & (c("qb_scramble") == 0)).drop_nulls(
        ["rusher_player_id", "epa"]
    )
    ra = ra.group_by(pid="rusher_player_id", season="season", week="week").agg(
        epa=c("epa").sum(), nr=pl.len()
    )
    rb_ids = teams.filter(c("position") == "RB").select("pid", "season")
    rr = (
        ngs.join(ra, on=["pid", "season", "week"], how="left")
        .with_columns(epa=c("epa") * c("n") / c("nr"))
        .join(rb_ids, on=["pid", "season"])
    )
    rows.append(
        {
            "group": "RB",
            **assess(
                "rushing yards over expected per carry (EPA per carry beside)",
                rr.drop_nulls("epa"),
                "ryoe",
                "epa",
                "n",
                80,
                teams,
            ),
        }
    )
    # the line's part removed: his rate minus his teammates' (other backs, same team-season)
    full = (
        rr.group_by("pid", "season")
        .agg(c("ryoe").sum(), c("n").sum())
        .join(teams, on=["pid", "season"])
    )
    team_tot = full.group_by("team", "season").agg(t_ryoe=c("ryoe").sum(), t_n=c("n").sum())
    rel_line = rr.join(teams.select("pid", "season", "team"), on=["pid", "season"]).join(
        team_tot, on=["team", "season"]
    )
    # per game: his yards over expected minus what his teammates' season rate predicts for his carries
    pidtot = full.select("pid", "season", s_ryoe="ryoe", s_n="n")
    rel_line = (
        rel_line.join(pidtot, on=["pid", "season"])
        .with_columns(
            mates=pl.when(c("t_n") - c("s_n") >= 40).then(
                (c("t_ryoe") - c("s_ryoe")) / (c("t_n") - c("s_n"))
            )
        )
        .drop_nulls("mates")
        .with_columns(rel=c("ryoe") - c("n") * c("mates"))
    )
    rows.append(
        {
            "group": "RB",
            **assess(
                "rushing yards over expected minus his teammates' rate (the line removed)",
                rel_line,
                "rel",
                None,
                "n",
                80,
                teams,
            ),
        }
    )
    pfr = src.part("player_game", "pfr").filter(
        c("season").is_between(2018, LAST) & c("pfr_rush_carries").is_not_null()
    )
    pfr = (
        pfr.join(wk, on="game_id")
        .select(
            pid="gsis_id",
            season="season",
            week="week",
            n=c("pfr_rush_carries"),
            ybc=c("pfr_rush_rushing_yards_before_contact"),
            yac=c("pfr_rush_rushing_yards_after_contact"),
        )
        .join(rb_ids, on=["pid", "season"])
        .drop_nulls(["ybc", "yac"])
    )
    rows.append(
        {
            "group": "RB",
            **assess(
                "yards after contact per carry (yards before contact beside)",
                pfr,
                "yac",
                "ybc",
                "n",
                80,
                teams,
            ),
        }
    )
    rows.append(
        {
            "group": "RB",
            **assess(
                "yards before contact per carry (the line's, by the CEO's reading)",
                pfr,
                "ybc",
                None,
                "n",
                80,
                teams,
            ),
        }
    )

    # pass rushers: PFR pressures per dropback on the field; sacks per dropback beside
    of = src.part("player_play", "on_field").filter(
        (c("side") == "defense") & c("season").is_between(2018, LAST)
    )
    drop = pb.filter(c("qb_dropback") == 1).select("game_id", "play_id", "week")
    on = (
        of.join(drop, on=["game_id", "play_id"])
        .group_by(pid="gsis_id", game_id="game_id", week="week")
        .agg(nd=pl.len())
    )
    pr = (
        src.part("player_game", "pfr")
        .filter(c("season").is_between(2018, LAST))
        .select(
            pid="gsis_id",
            game_id="game_id",
            press=c("pfr_def_def_pressures").fill_null(0),
            sacks=c("pfr_def_def_sacks").fill_null(0),
        )
    )
    pr = on.join(pr, on=["pid", "game_id"], how="left").with_columns(
        c("press").fill_null(0), c("sacks").fill_null(0)
    )
    pr = pr.join(src.part("game", "schedule").select("game_id", "season"), on="game_id")
    for label, pos in (
        ("defensive linemen (DE, DT, NT)", ["DE", "DT", "NT"]),
        ("outside linebackers (OLB)", ["OLB"]),
        ("inside linebackers", ["ILB", "MLB", "LB"]),
    ):
        ids = teams.filter(c("position").is_in(pos)).select("pid", "season")
        d = pr.join(ids, on=["pid", "season"])
        rows.append(
            {
                "group": label,
                **assess(
                    "pressures per dropback on the field (sacks beside)",
                    d,
                    "press",
                    "sacks",
                    "nd",
                    150,
                    teams,
                ),
            }
        )

    # offensive linemen: the team's pressure over expected on his dropbacks
    pa = src.part("play", "participation").filter(
        c("season").is_between(FIRST, LAST) & c("was_pressure").is_not_null()
    )
    pa = pa.select(
        "game_id", "play_id", "number_of_pass_rushers", pres=c("was_pressure").cast(pl.Float64)
    )
    d = (
        pb.filter(c("qb_dropback") == 1)
        .select("game_id", "play_id", "season", "week", "posteam", "defteam", "down", "ydstogo")
        .join(pa, on=["game_id", "play_id"])
    )
    d = d.with_columns(
        dist=pl.when(c("ydstogo") <= 3).then(0).when(c("ydstogo") <= 7).then(1).otherwise(2),
        rush=c("number_of_pass_rushers").fill_null(-1).clip(-1, 7),
    )
    d = d.with_columns(exp=c("pres").mean().over("season", "down", "dist", "rush"))
    d = d.with_columns(res=c("pres") - c("exp"))
    d = d.with_columns(
        def_habit=(c("res").sum().over("defteam", "season") - c("res"))
        / (pl.len().over("defteam", "season") - 1)
    )
    d = d.with_columns(poe=c("res") - c("def_habit"))
    ol = src.part("player_play", "on_field").filter(
        (c("side") == "offense")
        & c("position").is_in(["C", "LT", "RT", "LG", "RG", "G", "T"])
        & c("season").is_between(FIRST, LAST)
    )
    ol = ol.select("game_id", "play_id", pid="gsis_id").join(
        d.select("game_id", "play_id", "week", "poe", "pres"), on=["game_id", "play_id"]
    )
    olg = ol.group_by("pid", "game_id", "week").agg(
        poe=c("poe").sum(), pres=c("pres").sum(), n=pl.len()
    )
    olg = olg.join(src.part("game", "schedule").select("game_id", "season"), on="game_id")
    rows.append(
        {
            "group": "OL",
            **assess(
                "team pressure over expected on his dropbacks (raw pressure rate beside)",
                olg,
                "poe",
                "pres",
                "n",
                300,
                teams,
            ),
        }
    )

    out = pl.DataFrame(rows, infer_schema_length=None)
    pl.Config.set_tbl_rows(50)
    pl.Config.set_tbl_cols(30)
    pl.Config.set_tbl_width_chars(400)
    pl.Config.set_fmt_str_lengths(80)
    pl.Config.set_float_precision(3)
    print(
        f"Seasons {FIRST}-{LAST} (PFR measures 2018-{LAST}), regular season. repeat = season-to-season r (90% interval, players resampled);"
    )
    print(
        "reliability = odd vs even weeks, stepped up to a season; share_kept = movers_r / stayers; diff = repeat minus the measure beside it\n"
    )
    print(
        out.select(
            "group",
            "measure",
            "pairs",
            "movers",
            "reliability",
            "repeat",
            "repeat_lo",
            "repeat_hi",
            "stayers",
            "movers_r",
            "share_kept",
        )
    )
    print("\n== against the measure beside it (EPA, sacks, before contact, raw pressure)")
    print(
        out.filter(c("diff").is_not_null()).select(
            "group",
            "measure",
            "repeat",
            "compare_repeat",
            "diff",
            "diff_lo",
            "diff_hi",
            "compare_reliability",
        )
    )

    # context-live's own expectations, 2023 -> 2024
    import glob
    import os

    runs = [
        f
        for f in glob.glob(
            str(get_config().zone("outputs") / "context-live" / "*" / "history.parquet")
        )
    ]
    best = None
    for f in sorted(runs, key=os.path.getmtime, reverse=True):
        s = pl.scan_parquet(f).select(n=c("quantity").n_unique(), hi=c("game_id").max()).collect()
        if s["n"][0] >= 17 and s["hi"][0] < "2025":
            best = f
            break
    h = (
        pl.scan_parquet(best)
        .filter(c("quantity").is_in(["completion_prob", "rush_yards_exp"]))
        .select("game_id", "play_id", "quantity", "mean")
        .collect()
    )
    pc = pb.filter(c("season").is_between(2023, 2024)).select(
        "game_id",
        "play_id",
        "season",
        "week",
        "complete_pass",
        "passer_player_id",
        "rusher_player_id",
        "pass_attempt",
        "sack",
        "rush_attempt",
        "qb_scramble",
    )
    yds = src.part("play", "pbp").select("game_id", "play_id", "rushing_yards")
    comp = pc.filter((c("pass_attempt") == 1) & (c("sack") == 0)).join(
        h.filter(c("quantity") == "completion_prob"), on=["game_id", "play_id"]
    )
    comp = comp.group_by(pid="passer_player_id", season="season", week="week").agg(
        coe=(c("complete_pass") - c("mean")).sum(), n=pl.len()
    )
    run = (
        pc.filter((c("rush_attempt") == 1) & (c("qb_scramble") == 0))
        .join(h.filter(c("quantity") == "rush_yards_exp"), on=["game_id", "play_id"])
        .join(yds, on=["game_id", "play_id"])
    )
    run = (
        run.drop_nulls("rusher_player_id")
        .group_by(pid="rusher_player_id", season="season", week="week")
        .agg(ryoe=(c("rushing_yards").fill_null(0) - c("mean")).sum(), n=pl.len())
    )
    run = run.join(rb_ids, on=["pid", "season"])
    cl = [
        {
            "group": "QB",
            **assess(
                "completion over context-live's expected (2023 -> 2024)",
                comp,
                "coe",
                None,
                "n",
                150,
                teams,
            ),
        },
        {
            "group": "RB",
            **assess(
                "rushing yards over context-live's expected (2023 -> 2024)",
                run,
                "ryoe",
                None,
                "n",
                80,
                teams,
            ),
        },
    ]
    print("\n== context-live's own expectations, one season pair (2023 -> 2024)")
    print(
        pl.DataFrame(cl, infer_schema_length=None).select(
            "group",
            "measure",
            "pairs",
            "movers",
            "reliability",
            "repeat",
            "repeat_lo",
            "repeat_hi",
            "share_kept",
        )
    )


if __name__ == "__main__":
    main()
