"""team-efficiency exploration, round two (2026-11-13), idea 2: strip luck out of EPA.

Baseball's FIP judges a pitcher on what he controls, not where balls in play happen to land.
The same idea for EPA, applied only to the *rating's input*; the target stays every play's real EPA:

- **Fumbles:** who recovers a fumble is close to a coin flip. A fumble play's EPA is replaced by the
  average EPA of fumble plays like it (down, distance, field, clock, pass or run, yards gained),
  lost or not: the team is charged for fumbling, not for the bounce.
- **Interceptions:** partly the quarterback, partly luck (tipped balls, dropped picks). An
  interception's EPA is blended with what an incompletion would have cost there:
  lambda x EPA + (1 - lambda) x EPA if incomplete. lambda is tuned on 2007-2015.
- **Huge plays:** EPA capped at +-k (k tuned on 2007-2015), so a few plays don't swing a team's average.

Both expected-EPA models are gradient-boosted, fitted on 2006-2015 only. Each variant goes through
the same pipeline (ridge, settings tuned on 2007-2015) and is scored on 2016-2024 against all plays
equal; the winner is then put through F8's combination (DML with game state + gap-aware weights).
Also each new measure's consistency. Writes r2_luck.txt and caches plays_luck.parquet.
PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/explore/r2_luck.py
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).parent))
import checks as K  # noqa: E402
import common as C  # noqa: E402
import h42_dml as D  # noqa: E402

from pcf.data.tables.store import read_part  # noqa: E402
from pcf.validation.consistency import consistency  # noqa: E402

c = pl.col
HERE = Path(__file__).parent
CACHE = C.get_config().zone("interim") / "team-efficiency"
X_FUM = ["down", "ydstogo", "yardline_100", "half_seconds_remaining", "qtr", "is_pass", "yards_gained"]
X_INC = ["down", "ydstogo", "yardline_100", "half_seconds_remaining", "qtr", "score_differential"]
LAMBDAS = (0.0, 0.25, 0.5, 0.75)
CAPS = (2.0, 3.0, 4.0, 6.0)
VERSIONS: list[str] = []  # every version tried, for the count


def gbm(tr: pl.DataFrame, xs: list[str], y: str) -> HistGradientBoostingRegressor:
    m = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=200, random_state=0)
    return m.fit(tr.select(xs).to_numpy().astype(float), tr[y].to_numpy())


def with_luck_columns(p: pl.DataFrame) -> pl.DataFrame:
    extra = (
        read_part("play", "pbp", seasons=C.SEASONS)
        .select("game_id", "play_id", "fumble", "fumble_lost", "interception", "incomplete_pass", "yards_gained")
        .collect()
    )
    p = p.join(extra, on=["game_id", "play_id"], how="left").with_columns(
        *[c(k).fill_null(0).cast(pl.Int8) for k in ("fumble", "fumble_lost", "interception", "incomplete_pass")],
        yards_gained=c("yards_gained").fill_null(0).cast(pl.Float64),
    )
    fit = p.filter(c("season").is_in(C.WEIGHT_FIT))
    mf = gbm(fit.filter(c("fumble") == 1), X_FUM, "epa")
    mi = gbm(fit.filter((c("incomplete_pass") == 1) & (c("interception") == 0)), X_INC, "epa")
    return p.with_columns(
        epa_fum=pl.Series(mf.predict(p.select(X_FUM).to_numpy().astype(float))),
        epa_inc=pl.Series(mi.predict(p.select(X_INC).to_numpy().astype(float))),
    )


def value(p: pl.DataFrame, fum: bool, lam: float | None, cap: float | None) -> pl.Series:
    v = c("epa")
    if fum:
        v = pl.when(c("fumble") == 1).then(c("epa_fum")).otherwise(v)
    if lam is not None:
        v = pl.when(c("interception") == 1).then(lam * c("epa") + (1 - lam) * c("epa_inc")).otherwise(v)
    if cap is not None:
        v = v.clip(-cap, cap)
    return p.select(v.alias("v"))["v"]


def main() -> None:
    t0 = time.time()
    lines = []

    def say(s=""):
        print(s, flush=True)
        lines.append(s)

    p = with_luck_columns(C.plays())
    sched = C.schedule()
    tg = C.team_games(p, sched)
    ufs = {h: C.unit_frame(tg, h) for h in ("next3", "rest")}
    eq = {h: pl.read_parquet(CACHE / f"equal_{h}.parquet") for h in ("next3", "rest")}
    combo_r = pl.read_parquet(CACHE / "ratings_combo.parquet")
    combo = C.score_ratings(combo_r, ufs)

    s24 = p.filter(c("season") >= 2016)
    say("How much of EPA's play-to-play spread these plays carry, 2016-2024:")
    tot = float((s24["y_rel"] ** 2).sum())
    for nm, m in (("fumbles", c("fumble") == 1), ("fumbles lost", c("fumble_lost") == 1), ("interceptions", c("interception") == 1), ("|EPA| > 3", c("epa").abs() > 3), ("|EPA| > 4", c("epa").abs() > 4)):
        x = s24.filter(m)
        say(f"  {nm:14s} {x.height / s24.height:.1%} of plays, {float((x['y_rel'] ** 2).sum()) / tot:.1%} of the squared spread")
    say("")

    def score(name: str, v: pl.Series) -> tuple[float, dict]:
        VERSIONS.append(name)
        prm, out = C.tune(C.sides(p.with_columns(v=v), "v"), sched, ufs)
        tune_mse = C.mse(out["next3"], C.TUNE)
        say(f"  {name:38s} tune next3 {tune_mse:.6f}  {prm}  ({time.time() - t0:.0f}s)")
        return tune_mse, out

    say("Variants (settings tuned on 2007-2015; the tuning error picks lambda and the cap):")
    res = {}
    res["all plays, equal (rerun)"] = score("all plays, equal (rerun)", p["epa"])
    res["fumbles: expected over the recovery"] = score("fumbles: expected over the recovery", value(p, True, None, None))
    lam_runs = {lam: score(f"interceptions: lambda {lam}", value(p, False, lam, None)) for lam in LAMBDAS}
    lam_best = min(lam_runs, key=lambda k: lam_runs[k][0])
    res[f"interceptions: lambda {lam_best} (tuned)"] = lam_runs[lam_best]
    fi_lam = {lam: score(f"fumbles + interceptions lambda {lam}", value(p, True, lam, None)) for lam in LAMBDAS}
    lam_fi = min(fi_lam, key=lambda k: fi_lam[k][0])
    res[f"fumbles + interceptions lambda {lam_fi} (tuned)"] = fi_lam[lam_fi]
    cap_runs = {k: score(f"cap +-{k}", value(p, False, None, k)) for k in CAPS}
    cap_best = min(cap_runs, key=lambda k: cap_runs[k][0])
    res[f"cap +-{cap_best} (tuned)"] = cap_runs[cap_best]
    all_runs = {k: score(f"fumbles + interceptions {lam_fi} + cap +-{k}", value(p, True, lam_fi, k)) for k in CAPS}
    all_best = min(all_runs, key=lambda k: all_runs[k][0])
    best_name = f"all three: fumbles + interceptions {lam_fi} + cap +-{all_best} (tuned)"
    res[best_name] = all_runs[all_best]

    say("")
    say("The main test, 2016-2024: skill against all plays equal (cached rung-1 run)")
    for h in ("next3", "rest"):
        for k, (_, out) in res.items():
            say(f"  {h:5s} {k:58s} {C.fmt(C.skill(out[h], eq[h]))} | off {C.fmt(C.skill(out[h], eq[h], side='off'))} def {C.fmt(C.skill(out[h], eq[h], side='def'))} | 2020-24 {C.fmt(C.skill(out[h], eq[h], seasons=list(range(2020, 2025))))}")

    # The tuned luck-free value, cached for the other round-two steps.
    v_best = value(p, True, lam_fi, all_best)
    p = p.with_columns(epa_lf=v_best)
    p.select("game_id", "play_id", "epa_lf", "fumble", "interception").write_parquet(CACHE / "plays_luck.parquet")

    # Through F8's combination: DML with game state (outcome model refitted on the luck-free value) + gap-aware weights.
    VERSIONS.append("F8 combination on the luck-free value")
    w = pl.read_parquet(CACHE / "weights_h44a.parquet").select("game_id", "play_id", "w_off", "w_def")
    q = p.join(w, on=["game_id", "play_id"]).with_columns(epa=c("epa_lf"))
    g = D.outcome_model(q, D.X_STATE)
    q = q.with_columns(yt0=pl.Series(q["epa"].to_numpy() - g))
    wpband = pl.when(c("wp") < 0.1).then(0).when(c("wp") < 0.25).then(1).when(c("wp") < 0.4).then(2).when(c("wp") < 0.6).then(3).when(c("wp") < 0.75).then(4).when(c("wp") < 0.9).then(5).otherwise(6)
    bins = (wpband * 2 + (c("qtr") > 2).cast(pl.Int32)).cast(pl.Int32)
    rats = {}
    for side, wc in (("off", "w_off"), ("def", "w_def")):
        cl = D.cells(q.with_columns(yt=c("yt0") * c(wc)), bins)
        bv, br, bp = np.inf, None, None
        for prm in C.GRID:
            r = D.walk_dml(cl, prm, 14)
            v = C.mse(C.fit_score(C.predict_frame(r, ufs["next3"]), ["own", "opp", "home"]).filter(c("side") == side), C.TUNE)
            if v < bv:
                bv, br, bp = v, r, prm
        rats[side] = br
        say(f"  combination on the luck-free value, {side}: {bp} ({time.time() - t0:.0f}s)")
    r_lf = C.combine(rats["off"], rats["def"])
    r_lf.write_parquet(CACHE / "ratings_combo_lf.parquet")
    out = C.score_ratings(r_lf, ufs)
    say("")
    say("F8's combination on the luck-free value, 2016-2024:")
    for h in ("next3", "rest"):
        say(f"  {h:5s} against F8's combination {C.fmt(C.skill(out[h], combo[h]))}; against all plays equal {C.fmt(C.skill(out[h], eq[h]))} | off {C.fmt(C.skill(out[h], eq[h], side='off'))} def {C.fmt(C.skill(out[h], eq[h], side='def'))} | 2020-24 vs combo {C.fmt(C.skill(out[h], combo[h], seasons=list(range(2020, 2025))))}")

    # Consistency of the luck-free measure.
    say("")
    say("Consistency, per team per game, 2006-2024 (week: odd against even weeks):")
    gm = p.group_by("game_id", "posteam").agg(epa_play=c("epa").mean(), epa_luckfree=c("epa_lf").mean()).rename({"posteam": "team"})
    sd = K.adjusted(gm, sched, ["epa_play", "epa_luckfree"])
    for side, rows in sd.items():
        t = consistency(rows, ["epa_play", "epa_luckfree", "epa_play_adj", "epa_luckfree_adj"])
        for r in t.iter_rows(named=True):
            say(f"  {side} {r['measure']:20s} week {r['week_r']:.2f} ({r['week_lo']:.2f}-{r['week_hi']:.2f})  season {r['season_r']:.2f} ({r['season_lo']:.2f}-{r['season_hi']:.2f})  {r['verdict']}")
    say("")
    say(f"Versions tried in this step: {len(VERSIONS)}")
    (HERE / "r2_luck.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
