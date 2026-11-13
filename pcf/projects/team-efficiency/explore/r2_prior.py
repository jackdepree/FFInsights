"""team-efficiency exploration, round two (2026-11-13), idea 4: better starting points for a season.

Today a team starts each season at `pull` x last season's final rating (EPA per play), the same
pull for every team. Two richer priors, each a small linear model of *this* season's final rating
from what is known at the start of week 1, fitted on 2007-2015 (pairs 2006->2007 ... 2014->2015):

- **P1, steadier measures:** last season's final EPA rating and its series success rate rating.
- **P2, plus change:** P1 plus a new starting quarterback (the week-1 depth chart's QB1 isn't last
  season's main passer) and a new head coach (the week-1 coach isn't the one who coached the last
  game of last season), each on its own and as a weaker pull on last season's EPA.

Known at kickoff of week 1: depth charts (start of that week), opening coaches (start of week 1,
decision 0025), last season's plays. Each prior replaces pull x last season in the same ridge (all
plays equal), its half-life and strength tuned on 2007-2015; scored on 2016-2024, all weeks and
weeks 1-4 (where the prior matters). Writes r2_prior.txt and caches the P-prior tables.
PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/explore/r2_prior.py
"""

# ruff: noqa: E501
from __future__ import annotations

import itertools
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import common as C  # noqa: E402

from pcf.data.clean import standard  # noqa: E402
from pcf.data.tables.store import read_part  # noqa: E402

c = pl.col
HERE = Path(__file__).parent
CACHE = C.get_config().zone("interim") / "team-efficiency"
GRID_P = [C.Params(h, l, 1.0) for h, l in itertools.product((4.0, 8.0, 16.0, 1000.0), (2.0, 5.0, 10.0, 20.0, 40.0))]


def walk_finals(s: pl.DataFrame, prm: C.Params, sched: pl.DataFrame, priors: dict[int, tuple[np.ndarray, np.ndarray]] | None = None) -> tuple[pl.DataFrame, pl.DataFrame]:
    """common.walk, with a given prior per season (centered offense, defense arrays) in place of
    pull x last season, and the end-of-season fits returned too (season, team, o_final, d_final)."""
    g = sched.join(s, on=["game_id", "team"], how="inner").with_columns(a=c("team").replace_strict(C.TIX), b=c("opponent").replace_strict(C.TIX))
    wscale = float(g["W"].mean())
    out, fin = [], []
    po, pdf = np.zeros(C.NT), np.zeros(C.NT)
    for season in C.SEASONS:
        if priors is not None and season in priors:
            po, pdf = priors[season]
        gs = g.filter(c("season") == season)
        rows = gs.select("week", "a", "b", "home", "W", "WY").to_numpy().astype(float)
        last = int(gs["week"].max())
        for w in range(1, last + 1):
            o, d = C._fit(rows[rows[:, 0] < w], w, po, pdf, prm, wscale)
            out.append(pl.DataFrame({"season": season, "week": w, "team": C.TEAMS, "o": o, "d": d}))
        o, d = C._fit(rows, last + 1, po, pdf, prm, wscale)
        fin.append(pl.DataFrame({"season": season, "team": C.TEAMS, "o_final": o - o.mean(), "d_final": d - d.mean()}))
        po, pdf = prm.pull * (o - o.mean()), prm.pull * (d - d.mean())
    return pl.concat(out), pl.concat(fin)


def changes() -> pl.DataFrame:
    """Per team-season: a new week-1 starting quarterback, and a new head coach."""
    pbp = (
        read_part("play", "pbp", seasons=list(range(2005, 2025)))
        .filter((c("season_type") == "REG") & (c("qb_dropback") == 1) & c("passer_player_id").is_not_null())
        .group_by("season", "posteam", "passer_player_id").agg(n=pl.len())
        .collect()
    )
    pbp = standard.standard_teams(pbp, "posteam")
    main_qb = pbp.sort("n", descending=True).group_by("season", "posteam").first().select(season=c("season") + 1, team="posteam", qb_last="passer_player_id")
    dep = read_part("player_game", "depth", seasons=list(range(2006, 2025))).filter((c("depth_position") == "QB") & c("game_id").str.contains("_01_")).collect()
    ros = read_part("player_game", "roster", seasons=list(range(2006, 2025))).filter(c("week") == 1).select("gsis_id", "game_id", "team").collect()
    ros = standard.standard_teams(ros, "team")
    qb1 = dep.join(ros, on=["gsis_id", "game_id"]).sort("depth", "depth_mean").group_by("season", "team").first().select("season", "team", qb_week1="gsis_id")
    pre = read_part("team_game", "pregame", seasons=list(range(2005, 2025))).select("game_id", "team", "season", "known_at", "coach").collect()
    pre = standard.standard_teams(pre, "team")
    last_coach = pre.sort("known_at").group_by("season", "team").last().select(season=c("season") + 1, team="team", coach_last="coach")
    oc = standard.standard_teams(read_part("team_game", "opening_coach", seasons=list(range(2006, 2025))).collect(), "team").select("season", "team", "opening_coach")
    x = oc.join(last_coach, on=["season", "team"], how="left").join(qb1, on=["season", "team"], how="left").join(main_qb, on=["season", "team"], how="left")
    return x.with_columns(
        coach_new=(c("opening_coach") != c("coach_last")).fill_null(False).cast(pl.Float64),
        qb_new=(c("qb_week1") != c("qb_last")).fill_null(False).cast(pl.Float64),
        qb_known=(c("qb_week1").is_not_null() & c("qb_last").is_not_null()),
    )


def prior_model(fin_epa: pl.DataFrame, fin_ssr: pl.DataFrame, ch: pl.DataFrame, use_change: bool) -> tuple[dict[int, tuple[np.ndarray, np.ndarray]], dict]:
    """This season's final EPA rating from last season's, per side; fitted on TUNE seasons."""
    last = fin_epa.select(season=c("season") + 1, team="team", lo="o_final", ld="d_final").join(
        fin_ssr.select(season=c("season") + 1, team="team", so="o_final", sd="d_final"), on=["season", "team"]
    )
    x = fin_epa.join(last, on=["season", "team"]).join(ch.select("season", "team", "qb_new", "coach_new"), on=["season", "team"], how="left").with_columns(c("qb_new", "coach_new").fill_null(0.0))
    coefs = {}
    preds = {}
    for side, y, lf, sf, extra in (("off", "o_final", "lo", "so", ["qb_new", "coach_new"]), ("def", "d_final", "ld", "sd", ["coach_new"])):
        x = x.with_columns(**{f"{e}_x_last": c(e) * c(lf) for e in extra})
        feats = [lf, sf] + ((extra + [f"{e}_x_last" for e in extra]) if use_change else [])
        tr = x.filter(c("season").is_in(C.TUNE))
        X = np.column_stack([np.ones(tr.height)] + [tr[f].to_numpy() for f in feats])
        b = np.linalg.lstsq(X, tr[y].to_numpy(), rcond=None)[0]
        coefs[side] = dict(zip(["const", *feats], np.round(b, 3)))
        Xa = np.column_stack([np.ones(x.height)] + [x[f].to_numpy() for f in feats])
        preds[side] = x.select("season", "team").with_columns(pr=pl.Series(Xa @ b))
    pri = {}
    for season in sorted(set(preds["off"]["season"].to_list())):
        po = preds["off"].filter(c("season") == season).join(pl.DataFrame({"team": C.TEAMS}), on="team", how="right")
        pd_ = preds["def"].filter(c("season") == season).join(pl.DataFrame({"team": C.TEAMS}), on="team", how="right")
        o = po.sort(pl.col("team").replace_strict(C.TIX))["pr"].fill_null(0).to_numpy()
        d = pd_.sort(pl.col("team").replace_strict(C.TIX))["pr"].fill_null(0).to_numpy()
        pri[season] = (o - o.mean(), d - d.mean())
    return pri, coefs


def main() -> None:
    t0 = time.time()
    lines = []

    def say(s=""):
        print(s, flush=True)
        lines.append(s)

    p = C.plays()
    sched = C.schedule()
    tg = C.team_games(p, sched)
    ufs = {h: C.unit_frame(tg, h) for h in ("next3", "rest")}
    eq = {h: pl.read_parquet(CACHE / f"equal_{h}.parquet") for h in ("next3", "rest")}
    s_epa = C.sides(p, "epa")
    ser = p.group_by("game_id", "posteam", "series_key").agg(succ=c("series_success").first().cast(pl.Float64))
    s_ssr = C.sides(ser, "succ")
    # The prior model's inputs and target: each season's own final rating, with no prior at all
    # (pull 0), so this season's final doesn't already contain last season's (first run, fixed).
    base = C.Params(16.0, 5.0, 0.0)
    _, fin_epa = walk_finals(s_epa, base, sched)
    _, fin_ssr = walk_finals(s_ssr, base, sched)
    ch = changes()
    k = ch.filter(c("season") >= 2007)
    say(f"Change flags, 2007-2024: new week-1 QB {k['qb_new'].mean():.0%} of team-seasons (known for {k['qb_known'].mean():.0%}); new head coach {k['coach_new'].mean():.0%}")
    say("")

    versions = 0
    results = {}
    tune_err = {"usual prior": {side: C.mse(eq["next3"].filter(c("side") == side), C.TUNE) for side in ("off", "def")}}
    for nm, use in (("P1: last season's EPA + series success", False), ("P2: P1 + new QB + new coach", True)):
        pri, coefs = prior_model(fin_epa, fin_ssr, ch, use)
        say(f"{nm}: coefficients (fitted on 2007-2015) offense {coefs['off']}; defense {coefs['def']}")
        bv, bo, bp = np.inf, None, None
        for prm in GRID_P:
            versions += 1
            r, _ = walk_finals(s_epa, prm, sched, pri)
            pf = C.fit_score(C.predict_frame(r, ufs["next3"]), ["own", "opp", "home"])
            v = C.mse(pf, C.TUNE)
            if v < bv:
                bv, bo, bp = v, r, prm
        results[nm] = C.score_ratings(bo, ufs) | {"_ratings": bo}
        tune_err[nm] = {side: C.mse(results[nm]["next3"].filter(c("side") == side), C.TUNE) for side in ("off", "def")}
        bo.write_parquet(CACHE / f"ratings_prior_{'p2' if use else 'p1'}.parquet")
        say(f"  settings {bp} ({time.time() - t0:.0f}s)")

    # Each side picks its prior by its 2007-2015 error (no look at 2016-2024).
    pick = {side: min(tune_err, key=lambda k: tune_err[k][side]) for side in ("off", "def")}
    say(f"Picked on 2007-2015, per side: offense {pick['off']}, defense {pick['def']} (tuning errors {tune_err})")
    rr = {k: v["_ratings"] for k, v in results.items()} | {"usual prior": pl.read_parquet(CACHE / "equal_ratings.parquet")}
    r_pick = C.combine(rr[pick["off"]], rr[pick["def"]])
    r_pick.write_parquet(CACHE / "ratings_prior_pick.parquet")
    results["picked per side on 2007-2015"] = C.score_ratings(r_pick, ufs)
    say("")
    say("The main test, 2016-2024: skill against all plays equal (the usual prior, pull x last season's EPA)")
    for h in ("next3", "rest"):
        for nm, out in results.items():
            say(f"  {h:5s} {nm:40s} all weeks {C.fmt(C.skill(out[h], eq[h]))} | weeks 1-4 {C.fmt(C.skill(out[h].filter(c('w') <= 4), eq[h]))} | weeks 5-9 {C.fmt(C.skill(out[h].filter(c('w').is_between(5, 9)), eq[h]))}")
        for nm, out in results.items():
            say(f"  {h:5s} {nm:40s} off {C.fmt(C.skill(out[h], eq[h], side='off'))} def {C.fmt(C.skill(out[h], eq[h], side='def'))} | 2020-24 {C.fmt(C.skill(out[h], eq[h], seasons=list(range(2020, 2025))))}")
    # How good is each prior on its own, at week 1 (the prior is the whole rating then)?
    say("")
    say("Week 1 alone (the rating is the prior), next 3 games, 2016-2024, skill against the usual prior:")
    for nm, out in results.items():
        say(f"  {nm:40s} {C.fmt(C.skill(out['next3'].filter(c('w') == 1), eq['next3']))}")
    say("")
    say(f"Versions tried in this step: 2 priors x {len(GRID_P)} settings (tuned on 2007-2015); 2 scored")
    (HERE / "r2_prior.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
