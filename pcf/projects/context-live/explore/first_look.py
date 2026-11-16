# ruff: noqa: E501
"""Context (play-outcome forecaster): a first look. Discovery only, not through the harness.

What does the context of a play (the situation, the offense's call, the defense's call; no player
or team identity) explain of what happens on it? Plays 2022-2024 (FTN charting starts 2022),
scored on 2023 and 2024, each from trees fit on the earlier seasons (the after-the-season fields: fit on 2023, scored on 2024). The vault (2025) isn't read.

Run: .venv/Scripts/python.exe projects/context-live/explore/first_look.py > projects/context-live/explore/first_look.txt
"""

import sys
import time

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingRegressor as HGB

from pcf.data.gateway import Gateway

T0 = time.time()
RNG = np.random.default_rng(7)

SIT = ["down", "ydstogo", "yardline_100", "goal_to_go", "qtr", "half_seconds_remaining", "game_seconds_remaining",
       "score_differential", "posteam_timeouts_remaining", "defteam_timeouts_remaining", "home"]
OFF_LIVE = ["shotgun", "no_huddle", "qb_loc", "n_offense_backfield", "is_motion", "is_play_action", "is_screen_pass",
            "is_rpo", "is_trick_play", "is_qb_sneak", "hash"]
DEF_LIVE = ["n_defense_box", "n_blitzers", "n_pass_rushers"]
OFF_RETRO = ["formation", "n_rb", "n_te", "n_wr", "n_ol"]
DEF_RETRO = ["defenders_in_box", "number_of_pass_rushers", "n_dl", "n_lb", "n_db", "man_zone", "cov_type"]
LIVE = {"sit": SIT, "off_live": SIT + OFF_LIVE, "def_live": SIT + DEF_LIVE, "live": SIT + OFF_LIVE + DEF_LIVE}
# The participation fields changed provider and format in 2023 (boxes average 6.4 in 2022 and 5.0 after), so they are
# only comparable from 2023: those sets are fit on 2023 and scored on 2024.
RETRO = {"sit": SIT, "live": LIVE["live"], "off_all": SIT + OFF_LIVE + OFF_RETRO, "def_all": SIT + DEF_LIVE + DEF_RETRO,
         "all": SIT + OFF_LIVE + DEF_LIVE + OFF_RETRO + DEF_RETRO}
SETS = {"all": RETRO["all"]}


def log(msg):
    print(f"[{time.time() - T0:6.0f}s] {msg}", file=sys.stderr, flush=True)


def lazy(src, grain, part):
    d = src.part(grain, part)
    return d if isinstance(d, pl.LazyFrame) else d.lazy()


def code(c):
    return pl.col(c).cast(pl.Categorical).to_physical().cast(pl.Float64)


def count(col, *pos):
    """Players of these positions in a personnel string ('1 RB, 1 TE, 3 WR'); missing when the string is."""
    tot = sum(pl.col(col).str.extract(rf"(\d+) {q}(?:,|$)", 1).cast(pl.Float64).fill_null(0) for q in pos)
    return pl.when(pl.col(col).is_null()).then(None).otherwise(tot)


def frame():
    src = Gateway().source
    pb = (
        lazy(src, "play", "pbp")
        .filter(pl.col("season").is_between(2022, 2024), pl.col("season_type") == "REG",
                pl.col("play_type").is_in(["run", "pass", "no_play"]), pl.col("two_point_attempt").fill_null(0) == 0,
                pl.col("down").is_not_null())
        .select("game_id", pl.col("play_id").cast(pl.Int64), "season", "week", "posteam", "defteam", "home_team", "play_type",
                "down", "ydstogo", "yardline_100", "goal_to_go", "qtr", "half_seconds_remaining", "game_seconds_remaining",
                "score_differential", "posteam_timeouts_remaining", "defteam_timeouts_remaining", "shotgun", "no_huddle",
                "rush_attempt", "pass_attempt", "qb_dropback", "qb_scramble", "sack", "interception", "complete_pass", "fumble",
                "first_down", "pass_touchdown", "rush_touchdown", "penalty", "success", "epa", "yards_gained", "air_yards")
    )
    ft = lazy(src, "play", "ftn").select(
        "game_id", pl.col("play_id").cast(pl.Int64), "qb_location", "starting_hash", "n_offense_backfield", "is_motion",
        "is_play_action", "is_screen_pass", "is_rpo", "is_trick_play", "is_qb_sneak", "n_defense_box", "n_blitzers", "n_pass_rushers")
    pa = lazy(src, "play", "participation").select(
        "game_id", pl.col("play_id").cast(pl.Int64), "offense_formation", "offense_personnel", "defense_personnel",
        "defenders_in_box", "number_of_pass_rushers", "time_to_throw", "was_pressure", "defense_man_zone_type", "defense_coverage_type")
    d = pb.join(ft, on=["game_id", "play_id"], how="left").join(pa, on=["game_id", "play_id"], how="left").collect()
    blank = lambda c: pl.when(pl.col(c).str.strip_chars() == "").then(None).otherwise(pl.col(c).str.strip_chars())  # noqa: E731
    d = d.with_columns(blank("qb_location").alias("qb_location"), blank("defense_man_zone_type").alias("defense_man_zone_type"),
                       blank("defense_coverage_type").alias("defense_coverage_type"))
    d = d.with_columns(
        (pl.col("posteam") == pl.col("home_team")).cast(pl.Float64).alias("home"),
        code("qb_location").alias("qb_loc"), code("starting_hash").alias("hash"), code("offense_formation").alias("formation"),
        code("defense_man_zone_type").alias("man_zone"), code("defense_coverage_type").alias("cov_type"),
        count("offense_personnel", "RB", "FB").alias("n_rb"), count("offense_personnel", "TE").alias("n_te"),
        count("offense_personnel", "WR").alias("n_wr"), count("offense_personnel", "C", "G", "T", "OL").alias("n_ol"),
        count("defense_personnel", "DL", "DE", "DT", "NT").alias("n_dl"), count("defense_personnel", "LB", "ILB", "MLB", "OLB").alias("n_lb"),
        count("defense_personnel", "DB", "CB", "FS", "SS").alias("n_db"),
        (pl.col("pass_touchdown").fill_null(0) + pl.col("rush_touchdown").fill_null(0)).clip(0, 1).alias("td"),
        pl.col("was_pressure").cast(pl.Float64).alias("pressure"),
    )
    feats = sorted(set(RETRO["all"]))
    return d.with_columns([pl.col(c).cast(pl.Float64) for c in feats])


def fit_pred(xtr, ytr, xte):
    m = HGB(max_iter=150, learning_rate=0.06, max_leaf_nodes=15, min_samples_leaf=80, l2_regularization=1.0, early_stopping=False)
    m.fit(xtr, ytr)
    return m.predict(xte)


def walk(d, y, sets, tests=(2023, 2024), resample=False):
    """Held-out predictions for each test season from the earlier seasons in d. Returns the scored rows' base and predictions."""
    season = d["season"].to_numpy()
    preds = {k: np.full(len(y), np.nan) for k in sets}
    base = np.full(len(y), np.nan)
    for s in tests:
        tr, te = np.flatnonzero(season < s), season == s
        if resample:
            tr = RNG.choice(tr, len(tr))
        base[te] = y[tr].mean()
        for k, cols in sets.items():
            x = d.select(cols).to_numpy()
            ok = ~np.isnan(x[tr]).all(axis=0)  # the trees fail on a column that is all missing
            preds[k][te] = fit_pred(x[tr][:, ok], y[tr], x[te][:, ok])
    keep = np.isin(season, tests)
    return keep, base, preds


def boot(num, den, g, b=300):
    """90% interval of sum(num)/sum(den) over resampled games."""
    ng = g.max() + 1
    a, c = np.bincount(g, num, ng), np.bincount(g, den, ng)
    idx = RNG.integers(0, ng, (b, ng))
    r = a[idx].sum(1) / c[idx].sum(1)
    return np.percentile(r, 5), np.percentile(r, 95)


def games(d):
    return d["game_id"].cast(pl.Categorical).to_physical().to_numpy().astype(int)


def logo(d, ycol, team):
    """A team's average of the outcome over its other games that season: hindsight about who they are."""
    g = d.group_by(team, "season", "game_id").agg(pl.col(ycol).sum().alias("s"), pl.len().alias("n"))
    t = g.group_by(team, "season").agg(pl.col("s").sum().alias("S"), pl.col("n").sum().alias("N"))
    g = g.join(t, on=[team, "season"]).with_columns(((pl.col("S") - pl.col("s")) / (pl.col("N") - pl.col("n"))).alias(f"lg_{team}"))
    return d.join(g.select(team, "season", "game_id", f"lg_{team}"), on=[team, "season", "game_id"], how="left")[f"lg_{team}"].to_numpy()


KEEP, KEEP24, LATER = {}, {}, []  # held-out chances of success for the player table; the 2024-only lines, printed after each section


def score(d, y, sets, tests, pair):
    keep, base, preds = walk(d, y, sets, tests)
    g, yk = games(d)[keep], y[keep]
    se0 = (yk - base[keep]) ** 2
    se = {k: (yk - p[keep]) ** 2 for k, p in preds.items()}
    rem = {k: 100 * (1 - v.sum() / se0.sum()) for k, v in se.items()}
    top, off, dfn = pair
    lo, hi = boot(se0 - se[top], se0, g)
    syn = se[off] + se[dfn] - se["sit"] - se[top]  # what the two sides add together beyond the sum of each alone
    slo, shi = boot(syn, se0, g)
    txt = f"  ({100 * lo:5.2f} to {100 * hi:5.2f})" + f"{100 * syn.sum() / se0.sum():>8.2f} ({100 * slo:5.2f} to {100 * shi:5.2f})"
    return keep, yk, se0, preds, rem, txt


def outcome(d, name, ycol, label, extra=None, noise=False):
    d = d.filter(pl.col(ycol).is_not_null())
    d = d.with_columns(pl.Series("lg_off", logo(d, ycol, "posteam")), pl.Series("lg_def", logo(d, ycol, "defteam")))
    y = d[ycol].cast(pl.Float64).to_numpy()
    sets = dict(LIVE)
    sets["live+teams"] = LIVE["live"] + ["lg_off", "lg_def"]
    keep, yk, se0, preds, rem, txt = score(d, y, sets, (2023, 2024), ("live", "off_live", "def_live"))
    line = f"{label:<26}{len(yk):>7,}{yk.mean():>8.3f}" + "".join(f"{rem[k]:>9.2f}" for k in ["sit", "off_live", "def_live", "live"]) + txt + f"{rem['live+teams']:>9.2f}"
    if noise:
        r = []
        for _ in range(3):
            k2, _b, p2 = walk(d, y, {"live": LIVE["live"]}, resample=True)
            r.append(100 * (1 - ((y[k2] - p2["live"][k2]) ** 2).sum() / se0.sum()))
        line += f"   fitting noise (spread over 3 refits on resampled training rows): {np.std(r, ddof=1):.2f}"
    print(line, flush=True)
    if ycol == "success":
        KEEP[name] = d.filter(pl.Series(keep)).select("game_id", "play_id", "season", "week").with_columns(
            pl.Series("y", yk), pl.Series("p_sit", preds["sit"][keep]), pl.Series("p_live", preds["live"][keep]))
    d2 = d.filter(pl.col("season") >= 2023)
    y2 = d2[ycol].cast(pl.Float64).to_numpy()
    sets2 = dict(RETRO)
    if extra:
        sets2["all+pressure"] = RETRO["all"] + extra
    keep2, yk2, _se, preds2, rem2, txt2 = score(d2, y2, sets2, (2024,), ("all", "off_all", "def_all"))
    LATER.append(f"{label:<26}{len(yk2):>7,}{yk2.mean():>8.3f}" + "".join(f"{rem2[k]:>9.2f}" for k in ["sit", "live", "off_all", "def_all", "all"]) + txt2
                 + (f"{rem2['all+pressure']:>10.2f}" if extra else ""))
    if ycol == "success":
        KEEP24[name] = d2.filter(pl.Series(keep2)).select("game_id", "play_id").with_columns(pl.Series("p_all", preds2["all"][keep2]))
    log(name)
    return {"sit": rem["sit"], "live": rem["live"], "live+teams": rem["live+teams"], "all24": rem2["all"], "live24": rem2["live"]}


def later(title):
    print(f"\n-- {title}: fit on 2023, scored on 2024, with the after-the-season fields --")
    print(f"{'outcome':<26}{'n':>7}{'mean':>8}" + "".join(f"{k:>9}" for k in ["sit", "live", "off_all", "def_all", "all"]) + "  (90% for all)   together-beyond-each (90%)  +pressure")
    print("\n".join(LATER))
    LATER.clear()


def h63(runs, drops):
    print("\n== H63: a run, a blitz and a light box ==")
    print(f"Blitzers are charted on dropbacks only: of {len(runs):,} designed runs, {int((runs['n_blitzers'] > 0).sum())} have one. The run half is tested with the box count alone.")
    box = pl.when(pl.col("n_defense_box") <= 6).then(pl.lit("6 or fewer")).when(pl.col("n_defense_box") == 7).then(pl.lit("7")).otherwise(pl.lit("8 or more")).alias("box")
    r = runs.filter(pl.col("n_defense_box").is_not_null()).with_columns(box)
    agg = [pl.len().alias("n"), pl.col("yards_gained").mean().round(2).alias("yards"), (pl.col("yards_gained") <= 0).mean().round(3).alias("stuffed"),
           (pl.col("yards_gained") >= 10).mean().round(3).alias("10+"), pl.col("success").mean().round(3).alias("success"), pl.col("epa").mean().round(3).alias("epa")]
    print(r.group_by("box").agg(agg).sort("box"))
    print("by how the offense lined up (shotgun = 'showing pass'):")
    print(r.group_by("shotgun", "box").agg(agg).sort("shotgun", "box"))
    print("first and second down with 5 to 10 to go only (so short-yardage plays don't drive it):")
    print(r.filter(pl.col("down") <= 2, pl.col("ydstogo").is_between(5, 10)).group_by("shotgun", "box").agg(agg).sort("shotgun", "box"))
    for ycol, lab in [("yards_gained", "rushing yards"), ("stuffed", "stuffed"), ("success", "success")]:
        y = r[ycol].cast(pl.Float64).to_numpy()
        keep, base, p = walk(r, y, {"box": ["n_defense_box"], "box+gun": ["n_defense_box", "shotgun"], "sit": SIT, "sit+box": SIT + ["n_defense_box", "shotgun"]})
        se0 = ((y[keep] - base[keep]) ** 2).sum()
        f = lambda k: 100 * (1 - ((y[keep] - p[k][keep]) ** 2).sum() / se0)  # noqa: E731, B023
        print(f"  {lab}: the box count alone removes {f('box'):.2f}%; box count and shotgun {f('box+gun'):.2f}%; the situation {f('sit'):.2f}%; all three {f('sit+box'):.2f}%")
    print("the pass half: dropbacks by blitz and box")
    dd = drops.filter(pl.col("n_defense_box").is_not_null(), pl.col("n_blitzers").is_not_null()).with_columns(box, (pl.col("n_blitzers") > 0).alias("blitz"))
    agg2 = [pl.len().alias("n"), pl.col("pressure").mean().round(3).alias("pressure"), pl.col("sack").mean().round(3).alias("sack"), pl.col("yards_gained").mean().round(2).alias("yards"),
            (pl.col("yards_gained") >= 20).mean().round(3).alias("20+"), pl.col("success").mean().round(3).alias("success"), pl.col("epa").mean().round(3).alias("epa")]
    print(dd.group_by("blitz").agg(agg2).sort("blitz"))
    print(dd.group_by("blitz", "box").agg(agg2).sort("box", "blitz"))
    for ycol, lab in [("pressure", "pressure"), ("sack", "sack"), ("yards_gained", "yards"), ("success", "success")]:
        d3 = dd.filter(pl.col(ycol).is_not_null())
        y = d3[ycol].cast(pl.Float64).to_numpy()
        keep, base, p = walk(d3, y, {"two": ["n_blitzers", "n_defense_box"], "sit": SIT, "sit+two": SIT + ["n_blitzers", "n_defense_box"]})
        se0 = ((y[keep] - base[keep]) ** 2).sum()
        f = lambda k: 100 * (1 - ((y[keep] - p[k][keep]) ** 2).sum() / se0)  # noqa: E731, B023
        print(f"  {lab}: blitzers and box count alone remove {f('two'):.2f}%; the situation {f('sit'):.2f}%; all {f('sit+two'):.2f}%")


def spread_line(name, lab, p, y):
    q = np.quantile(p, [0.05, 0.1, 0.5, 0.9, 0.95])
    dec = np.digitize(p, np.quantile(p, np.linspace(0.1, 0.9, 9)))
    act = [y[dec == i].mean() for i in range(10)]
    print(f"  {name:<10}{lab:<26} spread {p.std():.3f}; 5th {q[0]:.2f}, 10th {q[1]:.2f}, median {q[2]:.2f}, 90th {q[3]:.2f}, 95th {q[4]:.2f}; "
          f"actual by tenth: " + " ".join(f"{a:.2f}" for a in act))


def doomed():
    print("\n== How far apart are good and bad contexts? (held-out chance of a successful play) ==")
    for name, k in KEEP.items():
        for col, lab in [("p_sit", "situation only"), ("p_live", "live fields")]:
            spread_line(name, lab, k[col].to_numpy(), k["y"].to_numpy())
        j = k.join(KEEP24[name], on=["game_id", "play_id"], how="inner")
        spread_line(name, "everything (2024 only)", j["p_all"].to_numpy(), j["y"].to_numpy())
        res = (j["p_all"] - j["p_sit"]).to_numpy()
        print(f"  {name:<10}what the calls move beyond the situation (2024): spread {res.std():.3f}; 5th {np.quantile(res, 0.05):+.3f}, 95th {np.quantile(res, 0.95):+.3f}; "
              f"plays moved 10 points or more: {100 * (np.abs(res) >= 0.10).mean():.1f}%")


def h66():
    print("\n== H66: do players differ in the context they play in? ==")
    k = pl.concat(list(KEEP.values()))
    mu = k["y"].mean()
    k = k.with_columns((pl.col("p_live") - mu).alias("ctx"), (pl.col("p_sit") - mu).alias("ctx_sit"), (pl.col("y") - mu).alias("act"))
    src = Gateway().source
    of = (lazy(src, "player_play", "on_field").filter(pl.col("season").is_between(2023, 2024))
          .select("game_id", pl.col("play_id").cast(pl.Int64), "side", "gsis_id", "position").collect())
    j = of.join(k, on=["game_id", "play_id"], how="inner")
    print(f"  plays {len(k):,} (average success {mu:.3f}); player-plays {len(j):,}. Context = the held-out chance of success from the situation and the live call fields, minus the league average; runs and dropbacks together, so whether it was a run or a pass is part of it.")
    ps = j.group_by("gsis_id", "side", "season").agg(
        pl.len().alias("n"), pl.col("position").mode().first().alias("pos"), pl.col("ctx").mean(), pl.col("ctx_sit").mean(), pl.col("act").mean(),
        pl.col("ctx").filter(pl.col("week") % 2 == 1).mean().alias("odd"), pl.col("ctx").filter(pl.col("week") % 2 == 0).mean().alias("even"),
        (pl.col("week") % 2 == 1).sum().alias("n_odd"), (pl.col("week") % 2 == 0).sum().alias("n_even")).filter(pl.col("n") >= 200)
    for side in ps["side"].unique().sort().to_list():
        s = ps.filter(pl.col("side") == side)
        c, a = s["ctx"].to_numpy(), s["act"].to_numpy()
        h = s.filter(pl.col("n_odd") >= 75, pl.col("n_even") >= 75)
        w = s.filter(pl.col("season") == 2023).join(s.filter(pl.col("season") == 2024), on="gsis_id", suffix="_next")
        print(f"  {side}: {len(s):,} player-seasons with 200+ plays. Average context (points of success rate): spread {100 * c.std():.2f}, "
              f"5th {100 * np.quantile(c, 0.05):+.1f}, 95th {100 * np.quantile(c, 0.95):+.1f}, furthest {100 * c.min():+.1f} and {100 * c.max():+.1f}; "
              f"beyond 2 points either way: {100 * (np.abs(c) >= 0.02).mean():.1f}% of players; beyond 5: {100 * (np.abs(c) >= 0.05).mean():.1f}%; beyond 10: {100 * (np.abs(c) >= 0.10).mean():.1f}%")
        print(f"    repeats odd against even weeks r {np.corrcoef(h['odd'], h['even'])[0, 1]:.2f} (n {len(h)}); 2023 to 2024 r {np.corrcoef(w['ctx'], w['ctx_next'])[0, 1]:.2f} (n {len(w)})")
        print(f"    spread of players' actual success over average {100 * a.std():.2f} points; context's variance is {100 * c.var() / a.var():.0f}% of that; "
              f"r(actual, context) {np.corrcoef(a, c)[0, 1]:.2f}; situation-only context spread {100 * s['ctx_sit'].std():.2f}; r(situation-only, live) {np.corrcoef(s['ctx_sit'], c)[0, 1]:.2f}")
        print(s.group_by("pos").agg(pl.len().alias("players"), (100 * pl.col("ctx").mean()).round(2).alias("avg context"), (100 * pl.col("ctx").std()).round(2).alias("spread"),
                                    (100 * pl.col("ctx").min()).round(1).alias("lowest"), (100 * pl.col("ctx").max()).round(1).alias("highest")).filter(pl.col("players") >= 15).sort("avg context"))


def main():
    pl.Config.set_tbl_rows(40)
    pl.Config.set_tbl_cols(20)
    pl.Config.set_tbl_width_chars(200)
    d = frame()
    log(f"frame {d.shape}")
    scr = d.filter(pl.col("play_type") != "no_play")
    runs = scr.filter(pl.col("rush_attempt") == 1, pl.col("qb_dropback") == 0).with_columns(
        (pl.col("yards_gained") <= 0).cast(pl.Float64).alias("stuffed"), (pl.col("yards_gained") >= 10).cast(pl.Float64).alias("explosive"))
    drops = scr.filter(pl.col("qb_dropback") == 1).with_columns((pl.col("yards_gained") >= 20).cast(pl.Float64).alias("explosive"))
    atts = drops.filter(pl.col("pass_attempt") == 1, pl.col("sack") == 0, pl.col("qb_scramble") == 0)
    print(f"Plays 2022-2024, regular season: designed runs {len(runs):,}; dropbacks {len(drops):,}; pass attempts {len(atts):,}; all snaps with a down {len(d):,}")
    print("Field coverage (share of rows with a value), runs / dropbacks:")
    r24, d24 = runs.filter(pl.col("season") >= 2023), drops.filter(pl.col("season") >= 2023)
    for c in OFF_LIVE + DEF_LIVE:
        print(f"  {c:<24}{runs[c].is_not_null().mean():6.2f}{drops[c].is_not_null().mean():6.2f}")
    print("after-the-season fields, 2023-2024 only:")
    for c in OFF_RETRO + DEF_RETRO + ["pressure", "time_to_throw"]:
        print(f"  {c:<24}{r24[c].is_not_null().mean():6.2f}{d24[c].is_not_null().mean():6.2f}")
    head = f"{'outcome':<26}{'n':>7}{'mean':>8}" + "".join(f"{k:>9}" for k in ["sit", "off_live", "def_live", "live"]) + "  (90% for live)  together-beyond-each (90%)  +teams in hindsight"
    print("\nShare of squared error removed (%), held out, against the base rate. sit = the situation; off_live, def_live = + each side's call fields that arrive in-season (play-by-play, FTN); live = both.")
    print("First table of each pair: fit on earlier seasons from 2022, scored on 2023 and 2024.")
    print("\n== Designed runs ==\n" + head)
    res = {}
    for name, ycol, lab, nz in [("run_yards", "yards_gained", "rushing yards", True), ("run_stuffed", "stuffed", "stuffed (0 or fewer)", False), ("run_explosive", "explosive", "explosive (10+)", False),
                                ("runs", "success", "successful play", True), ("run_fd", "first_down", "first down", False), ("run_td", "td", "touchdown", False),
                                ("run_fumble", "fumble", "fumble", False), ("run_epa", "epa", "EPA", False)]:
        res[lab + " (run)"] = outcome(runs, name, ycol, lab, noise=nz)
    later("Designed runs")
    print("\n== Dropbacks ==\n" + head)
    for name, ycol, lab, ex, nz in [("db_pressure", "pressure", "pressure", None, True), ("db_sack", "sack", "sack", ["pressure"], True), ("db_scramble", "qb_scramble", "scramble", None, False),
                                    ("db_ttt", "time_to_throw", "time to throw (s)", None, False), ("db_yards", "yards_gained", "yards", ["pressure"], False),
                                    ("db_explosive", "explosive", "explosive (20+)", None, False), ("dropbacks", "success", "successful play", ["pressure"], True),
                                    ("db_fd", "first_down", "first down", None, False), ("db_td", "td", "touchdown", None, False), ("db_fumble", "fumble", "fumble", None, False),
                                    ("db_epa", "epa", "EPA", None, False)]:
        res[lab + " (dropback)"] = outcome(drops, name, ycol, lab, extra=ex, noise=nz)
    later("Dropbacks")
    print("\n== Pass attempts ==\n" + head)
    for name, ycol, lab, ex, nz in [("att_air", "air_yards", "depth of target (yards)", None, False), ("att_comp", "complete_pass", "completion", ["pressure"], True),
                                    ("att_int", "interception", "interception", ["pressure"], False)]:
        res[lab + " (attempt)"] = outcome(atts, name, ycol, lab, extra=ex, noise=nz)
    later("Pass attempts")
    print("\n== Penalties: all snaps with a down ==")
    print("The call fields are charted differently on plays wiped out by a penalty (the first run 'removed' 28% from that alone), so only the situation is used.")
    dp = d.filter(pl.col("penalty").is_not_null())
    y = dp["penalty"].cast(pl.Float64).to_numpy()
    keep, base, p = walk(dp, y, {"sit": SIT})
    print(f"penalty: n {int(keep.sum()):,}, rate {y[keep].mean():.3f}, the situation removes {100 * (1 - ((y[keep] - p['sit'][keep]) ** 2).sum() / ((y[keep] - base[keep]) ** 2).sum()):.2f}%")
    print("\n== H64: outcomes ranked by the share removed with the live fields ==")
    for lab, r in sorted(res.items(), key=lambda kv: -kv[1]["live"]):
        print(f"  {lab:<36} live {r['live']:6.2f}   situation {r['sit']:6.2f}   beyond the situation {r['live'] - r['sit']:+6.2f}   with teams in hindsight {r['live+teams']:6.2f}   |  2024 only: live {r['live24']:6.2f}, everything {r['all24']:6.2f}")
    h63(runs, drops)
    doomed()
    h66()
    log("done")


if __name__ == "__main__":
    main()
