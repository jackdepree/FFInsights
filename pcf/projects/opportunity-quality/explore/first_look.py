# ruff: noqa: E501
"""opportunity-quality, first look (2026-11-16). Discovery only: the noise ceiling, then the
CEO's hunches H56-H62.

- A chance = a target or a carry by a RB, WR or TE, regular season, 2006-2024 (air yards start
  in 2006; the 2025 vault is left out).
- Points = PPR on that chance: 1 a catch, 0.1 a yard, 6 a touchdown (no fumbles, no two-point
  tries, no passing).
- Expected points (xfp) = what the situation is worth: boosted trees on where the chance was
  (yard line, down, distance, throw depth, side, formation, clock, score), fit only on earlier
  seasons, so 2010-2024 have them. Points over expected (poe) = points - xfp.
- Player-games: every game with a snap (2012 on, when snap counts start).
- Forecast tests: lasso + trees, walk forward, fit 2012..s-1, scored 2019-2024.

Run from pcf/:  python projects/opportunity-quality/explore/first_look.py > projects/opportunity-quality/explore/first_look.txt
"""

from __future__ import annotations

import math
import sys
import time

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Lasso
from sklearn.preprocessing import StandardScaler

from pcf.config import get_config
from pcf.data.gateway import Gateway

c = pl.col
TEST = range(2019, 2025)
FIT_FROM = 2012
DRAWS = 2000
RNG = np.random.default_rng(get_config().seed)
T0 = time.time()
POS = ("RB", "WR", "TE")


def log(*a):
    print(f"[{time.time() - T0:6.0f}s]", *a, file=sys.stderr, flush=True)


def corr(a, b) -> float:
    return float(np.corrcoef(np.asarray(a, float), np.asarray(b, float))[0, 1])


def fisher(r: float, n: int) -> str:
    if n < 6 or abs(r) >= 1 or math.isnan(r):
        return f"{r:+.2f} (n {n})"
    z, se = math.atanh(r), 1 / math.sqrt(n - 3)
    return f"{r:+.2f} ({math.tanh(z - 1.645 * se):+.2f} to {math.tanh(z + 1.645 * se):+.2f}, n {n})"


# ---------------------------------------------------------------- chances and expected points
def chances(src) -> pl.DataFrame:
    p = src.part("play", "pbp").filter(
        c("season").is_between(2006, 2024) & (c("season_type") == "REG")
        & (c("two_point_attempt") == 0)
    )  # fmt: skip
    common = ["game_id", "play_id", "season", "week", "posteam", "yardline_100", "down", "ydstogo",
              "goal_to_go", "shotgun", "no_huddle", "qtr", "half_seconds_remaining",
              "score_differential"]  # fmt: skip
    tgt = p.filter(
        c("receiver_player_id").is_not_null() & (c("play_type") == "pass") & (c("sack") == 0)
    ).select(
        *common, gsis_id=c("receiver_player_id"), kind=pl.lit("target"),
        air=c("air_yards").cast(pl.Float64),
        loc=c("pass_location").replace_strict({"left": 0, "middle": 1, "right": 2}, default=None).cast(pl.Float64),
        gap=pl.lit(None, dtype=pl.Float64),
        yards=pl.when(c("complete_pass") == 1).then(c("yards_gained")).otherwise(0).cast(pl.Float64),
        catch=c("complete_pass").cast(pl.Float64),
        td=((c("touchdown") == 1) & (c("td_player_id") == c("receiver_player_id"))).cast(pl.Float64),
        yac_oe=pl.when(c("complete_pass") == 1).then(c("yards_after_catch") - c("xyac_mean_yardage")),
    )  # fmt: skip
    run = p.filter(
        c("rusher_player_id").is_not_null() & (c("play_type") == "run") & (c("rush") == 1)
    ).select(
        *common, gsis_id=c("rusher_player_id"), kind=pl.lit("carry"),
        air=pl.lit(None, dtype=pl.Float64),
        loc=c("run_location").replace_strict({"left": 0, "middle": 1, "right": 2}, default=None).cast(pl.Float64),
        gap=c("run_gap").replace_strict({"guard": 0, "tackle": 1, "end": 2}, default=None).cast(pl.Float64),
        yards=c("yards_gained").cast(pl.Float64), catch=pl.lit(0.0),
        td=((c("touchdown") == 1) & (c("td_player_id") == c("rusher_player_id"))).cast(pl.Float64),
        yac_oe=pl.lit(None, dtype=pl.Float64),
    )  # fmt: skip
    ch = pl.concat([tgt, run]).with_columns(pts=c("catch") + 0.1 * c("yards") + 6 * c("td"))
    roster = src.part("player_game", "roster").select("gsis_id", "game_id", "position", "team")
    return ch.join(roster, on=["gsis_id", "game_id"]).filter(c("position").is_in(POS))


SIT = ["yardline_100", "down", "ydstogo", "goal_to_go", "shotgun", "no_huddle", "qtr",
       "half_seconds_remaining", "score_differential", "air", "loc", "gap"]  # fmt: skip


def expected(ch: pl.DataFrame) -> pl.DataFrame:
    """xfp per chance from models fit on earlier seasons only (one for targets, one for carries)."""
    ch = ch.with_row_index("_i")
    out = np.full(ch.height, np.nan)
    for kind in ("target", "carry"):
        d = ch.filter(c("kind") == kind)
        sit = [f for f in SIT if f != ("gap" if kind == "target" else "air")]  # all missing for that kind
        x, y = d.select(sit).to_numpy().astype(float), d["pts"].to_numpy()
        season, idx = d["season"].to_numpy(), d["_i"].to_numpy()
        for s in range(2010, 2025):
            tr, te = season < s, season == s
            m = HistGradientBoostingRegressor(
                max_iter=200, learning_rate=0.06, max_leaf_nodes=31, min_samples_leaf=100,
                random_state=0,
            ).fit(x[tr], y[tr])  # fmt: skip
            out[idx[te]] = m.predict(x[te])
        log("xfp model", kind)
    return ch.with_columns(xfp=pl.Series(out)).filter(c("season") >= 2010).drop("_i")


# ---------------------------------------------------------------- player-games and lags
def player_games(src, ch: pl.DataFrame) -> pl.DataFrame:
    gl = c("yardline_100") <= 5
    agg = ch.group_by("gsis_id", "game_id").agg(
        fp=c("pts").sum(), xfp=c("xfp").sum(), n=pl.len(),
        tgt=(c("kind") == "target").sum().cast(pl.Float64),
        car=(c("kind") == "carry").sum().cast(pl.Float64),
        gl_car=((c("kind") == "carry") & gl).sum().cast(pl.Float64),
        rz_tgt=((c("kind") == "target") & (c("yardline_100") <= 10)).sum().cast(pl.Float64),
        ez_tgt=((c("kind") == "target") & (c("air") >= c("yardline_100"))).sum().cast(pl.Float64),
        deep_tgt=((c("kind") == "target") & (c("air") >= 20)).sum().cast(pl.Float64),
        air=c("air").fill_null(0.0).sum(),
        td=c("td").sum(),
        xfp_sg=c("xfp").filter(c("shotgun") == 1).sum(), xfp_uc=c("xfp").filter(c("shotgun") == 0).sum(),
    )  # fmt: skip
    roster = src.part("player_game", "roster").filter(
        c("season").is_between(2012, 2024) & c("position").is_in(POS)
    ).select("gsis_id", "game_id", "season", "week", "team", "position", "years_exp")  # fmt: skip
    snaps = src.part("player_game", "snaps").select("gsis_id", "game_id", "offense_snaps")
    sched = src.part("team_game", "schedule").select("game_id", "team", "game_type")
    df = (
        roster.join(sched, on=["game_id", "team"]).filter(c("game_type") == "REG")
        .join(snaps, on=["gsis_id", "game_id"]).filter(c("offense_snaps") > 0)
        .join(agg, on=["gsis_id", "game_id"], how="left")
    )  # fmt: skip
    num = [x for x in agg.columns if x not in ("gsis_id", "game_id")]
    df = df.with_columns(c(num).fill_null(0)).with_columns(
        poe=c("fp") - c("xfp"), n=c("n").cast(pl.Float64), snaps=c("offense_snaps").cast(pl.Float64)
    )
    return df.sort("gsis_id", "season", "week")


def lags(df: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    """Season so far, last 4 games, last season: per player, from earlier games he played."""
    us = ["gsis_id", "season"]
    out = []
    for k in cols:
        x = c(k)
        n_s = x.cum_count().over(us) - 1
        prev = [x.shift(i).over("gsis_id") for i in range(1, 5)]
        n4 = sum(p.is_not_null().cast(pl.Float64) for p in prev)
        out += [
            pl.when(n_s > 0).then((x.cum_sum().over(us) - x) / n_s).alias(f"{k}_s"),
            pl.when(n4 > 0).then(sum(p.fill_null(0.0) for p in prev) / n4).alias(f"{k}_l4"),
        ]
    df = df.with_columns(out, n_games=(c("fp").cum_count().over(us) - 1).cast(pl.Float64))
    last = df.group_by(us).agg(*[c(k).mean().alias(f"{k}_ls") for k in cols]).with_columns(c("season") + 1)
    df = df.join(last, on=us, how="left")
    return df.with_columns(*[c(f"{k}_s").fill_null(c(f"{k}_ls")) for k in cols])


def L(*cols: str) -> list[str]:
    return [f"{k}_{sfx}" for k in cols for sfx in ("s", "l4", "ls")]


# ---------------------------------------------------------------- the forecast tests
def walk(df: pl.DataFrame, feats: list[str], y: str) -> np.ndarray:
    x = df.select(feats).to_numpy().astype(float)
    yy, season = df[y].to_numpy().astype(float), df["season"].to_numpy()
    out = np.full(len(yy), np.nan)
    xl = np.nan_to_num(x, nan=0.0)
    for s in TEST:
        tr, te = (season < s) & (season >= FIT_FROM), season == s
        sc = StandardScaler().fit(xl[tr])
        lasso = Lasso(alpha=0.01 * yy[tr].std(), max_iter=5000).fit(sc.transform(xl[tr]), yy[tr])
        trees = HistGradientBoostingRegressor(
            max_iter=150, learning_rate=0.06, max_leaf_nodes=15, min_samples_leaf=40,
            l2_regularization=1.0, early_stopping=False, random_state=0,
        ).fit(x[tr], yy[tr])  # fmt: skip
        out[te] = (lasso.predict(sc.transform(xl[te])) + trees.predict(x[te])) / 2
    return out


def r2(df, pred, y) -> float:
    yy = df[y].to_numpy().astype(float)
    ok = ~np.isnan(pred)
    return float(1 - ((pred - yy)[ok] ** 2).sum() / ((yy[ok].mean() - yy[ok]) ** 2).sum())


def gain(df, new, base, y, mask=None) -> str:
    yy = df[y].to_numpy().astype(float)
    ok = ~np.isnan(new) & ~np.isnan(base)
    if mask is not None:
        ok &= mask
    d = pl.DataFrame({
        "w": (df["season"].to_numpy() * 100 + df["week"].to_numpy())[ok],
        "a": ((new - yy) ** 2)[ok], "b": ((base - yy) ** 2)[ok],
    }).group_by("w").agg(c("a").sum(), c("b").sum())  # fmt: skip
    a, b = d["a"].to_numpy(), d["b"].to_numpy()
    draws = RNG.multinomial(len(a), np.full(len(a), 1 / len(a)), size=DRAWS)
    boot = 1 - (draws @ a) / (draws @ b)
    lo, hi = np.quantile(boot, [0.05, 0.95])
    return f"{100 * (1 - a.sum() / b.sum()):+6.2f}%  (90% {100 * lo:+.2f} to {100 * hi:+.2f})"


def seasons(pg: pl.DataFrame, min_n: int = 50) -> pl.DataFrame:
    """Player-seasons with enough chances, and the same player's next season beside them."""
    s = pg.group_by("gsis_id", "season").agg(
        position=c("position").last(), team=c("team").last(), teams=c("team").n_unique(),
        g=pl.len(), n=c("n").sum(), fp=c("fp").sum(), xfp=c("xfp").sum(), snaps=c("snaps").sum(),
        xfp_sg=c("xfp_sg").sum(), xfp_uc=c("xfp_uc").sum(),
    ).with_columns(
        xfp_g=c("xfp") / c("g"), xfp_snap=c("xfp") / c("snaps"), xfp_ch=c("xfp") / c("n"),
        poe_ch=(c("fp") - c("xfp")) / c("n"), fp_g=c("fp") / c("g"),
    ).filter(c("n") >= min_n)  # fmt: skip
    nxt = s.with_columns(c("season") - 1)
    return s.join(nxt, on=["gsis_id", "season"], suffix="_n").with_columns(
        moved=(c("team") != c("team_n")) & (c("teams") == 1) & (c("teams_n") == 1),
        stayed=(c("team") == c("team_n")) & (c("teams") == 1) & (c("teams_n") == 1),
    )


def main() -> None:
    src = Gateway().source
    ch = expected(chances(src))
    pg = player_games(src, ch)
    log("chances", ch.height, "player-games", pg.height)
    print("opportunity-quality, first look. RB, WR and TE targets and carries, regular seasons.")
    print(f"Chances with expected points: {ch.height} (2010-2024). Player-games with a snap: {pg.height} (2012-2024).")
    print("PPR points on targets and carries only. Discovery only.\n")

    # ---- sanity: the expected-points model, and nflverse's own
    te = ch.filter(c("season") >= 2019)
    for kind in ("target", "carry"):
        e = te.filter(c("kind") == kind)
        yv, pv = e["pts"].to_numpy(), e["xfp"].to_numpy()
        print(f"  one {kind}: average {yv.mean():.2f} points; the situation removes {100 * (1 - ((pv - yv) ** 2).sum() / ((yv - yv.mean()) ** 2).sum()):.1f}% of the squared error (2019-2024, {e.height} chances)")
    ffo = src.part("player_game", "ff_opportunity").select(
        "gsis_id", "game_id", ffo=c("ffo_rec_fantasy_points_exp").fill_null(0) + c("ffo_rush_fantasy_points_exp").fill_null(0)
    )
    j = pg.join(ffo, on=["gsis_id", "game_id"]).filter(c("ffo").is_not_null())
    print(f"  against nflverse's expected points (their scoring, {j.height} player-games): r {corr(j['xfp'], j['ffo']):.3f}\n")

    # ---- 1. the noise ceiling
    print("== 1. The noise ceiling: next game's points (players with a snap)")
    pg = lags(pg, ["fp", "xfp", "poe", "tgt", "car", "gl_car", "rz_tgt", "ez_tgt", "deep_tgt", "air", "td", "snaps"])
    pg = pg.with_columns(*[(c("position") == p).cast(pl.Float64).alias(f"pos_{p}") for p in POS]).sort("season", "week", "game_id", "gsis_id")
    posf = [f"pos_{p}" for p in POS] + ["n_games"]
    base_f = L("fp") + posf
    base = walk(pg, base_f, "fp")
    t = pg.filter(c("season") >= 2019)
    orc = pg.with_columns(o=(c("fp").sum().over("gsis_id", "season") - c("fp")) / (pl.len().over("gsis_id", "season") - 1))["o"].fill_null(0.0).to_numpy()
    orc = np.where(np.isnan(base), np.nan, orc)
    same = np.where(np.isnan(base), np.nan, pg["xfp"].to_numpy())
    print(f"  rows scored {t.height}; average {t['fp'].mean():.2f} points, spread {t['fp'].std():.2f}")
    print(f"  past points only (season, last 4, last season) removes {100 * r2(pg, base, 'fp'):.1f}%")
    print(f"  hindsight average (his other games that season) removes {100 * r2(pg, orc, 'fp'):.1f}%")
    print(f"  knowing the game's own expected points (the chances he actually got) removes {100 * r2(pg, same, 'fp'):.1f}%")
    xb = walk(pg, L("xfp") + posf, "xfp")
    print(f"  next game's expected points from past expected points: removes {100 * r2(pg, xb, 'xfp'):.1f}% of their error")
    pb = walk(pg, L("poe") + posf, "poe")
    print(f"  next game's points over expected from past points over expected: removes {100 * r2(pg, pb, 'poe'):.1f}%")
    print("  (fitting noise not measured: these trees have no randomness as configured.)")
    log("ceiling")

    # ---- 2. H59: consistency
    print("\n== 2. H59: which repeats, expected points or points over expected?")
    try:
        from pcf.validation.consistency import consistency

        with pl.Config(tbl_cols=20, tbl_width_chars=220, tbl_rows=20):
            print(consistency(pg.with_columns(xfp_ch=c("xfp") / c("n"), poe_ch=c("poe") / c("n")).filter(c("n") > 0), ["fp", "xfp", "poe", "xfp_ch", "poe_ch"], unit="gsis_id"))
    except Exception as e:  # noqa: BLE001
        print("  (pcf.validation.consistency failed:", str(e)[:120], ")")
    h = pg.with_columns(odd=c("week") % 2 == 1).group_by("gsis_id", "season", "odd").agg(
        g=pl.len(), n=c("n").sum(), fp=c("fp").mean(), xfp=c("xfp").mean(), poe=c("poe").mean(),
        xfp_ch=c("xfp").sum() / c("n").sum(), poe_ch=c("poe").sum() / c("n").sum(),
    ).filter((c("g") >= 5) & (c("n") >= 20))  # fmt: skip
    a = h.filter(c("odd")).join(h.filter(~c("odd")), on=["gsis_id", "season"], suffix="_e")
    for m, label in (("fp", "points per game"), ("xfp", "expected points per game"), ("poe", "points over expected per game"),
                     ("xfp_ch", "expected points per chance (quality)"), ("poe_ch", "points over expected per chance")):  # fmt: skip
        print(f"  odd against even weeks, {label:<40} r {fisher(corr(a[m], a[m + '_e']), a.height)}")

    # ---- 3. H56: what is each kind of chance worth?
    print("\n== 3. H56: points per chance by kind (2019-2024; actual, and the model's expected)")
    k = te.with_columns(
        kind2=pl.when(c("kind") == "carry").then(
            pl.when(c("yardline_100") <= 2).then(pl.lit("carry, inside the 2"))
            .when(c("yardline_100") <= 5).then(pl.lit("carry, 3 to 5 out"))
            .when(c("yardline_100") <= 10).then(pl.lit("carry, 6 to 10 out"))
            .when(c("yardline_100") <= 20).then(pl.lit("carry, 11 to 20 out"))
            .otherwise(pl.lit("carry, outside the 20"))
        ).otherwise(
            pl.when(c("air") >= c("yardline_100")).then(
                pl.when(c("yardline_100") <= 10).then(pl.lit("target into the end zone, from 10 or closer"))
                .otherwise(pl.lit("target into the end zone, from further out")))
            .when(c("yardline_100") <= 10).then(pl.lit("target short of the goal line, inside the 10"))
            .when(c("air") >= 20).then(pl.lit("target 20+ yards downfield"))
            .when(c("air") >= 10).then(pl.lit("target 10 to 19 downfield"))
            .when(c("air") > 0).then(pl.lit("target 1 to 9 downfield"))
            .otherwise(pl.lit("target at or behind the line"))
        )
    ).group_by("kind2").agg(n=pl.len(), pts=c("pts").mean(), xfp=c("xfp").mean(), td=c("td").mean()).sort("pts", descending=True)  # fmt: skip
    tot = k["n"].sum()
    for r in k.iter_rows(named=True):
        print(f"  {r['kind2']:<46} {r['pts']:5.2f} points ({r['xfp']:5.2f} expected)  touchdown {100 * r['td']:4.1f}%  {100 * r['n'] / tot:4.1f}% of chances")
    allc = te.group_by("kind").agg(pts=c("pts").mean())
    print("  average:", ", ".join(f"{r['kind']} {r['pts']:.2f}" for r in allc.iter_rows(named=True)))

    print("\n  Does it pay? Next game's points, added to past points (share of squared error removed):")
    counts = walk(pg, base_f + L("tgt", "car", "snaps"), "fp")
    print(f"    + past targets, carries and snaps        {gain(pg, counts, base, 'fp')}")
    wx = walk(pg, base_f + L("tgt", "car", "snaps", "xfp"), "fp")
    print(f"    + expected points, beyond those counts   {gain(pg, wx, counts, 'fp')}")
    detail = ["gl_car", "rz_tgt", "ez_tgt", "deep_tgt", "air"]
    wd = walk(pg, base_f + L("tgt", "car", "snaps", *detail), "fp")
    print(f"    + counts by kind (inside the 5, end zone, deep, air yards), beyond plain counts {gain(pg, wd, counts, 'fp')}")
    wg = walk(pg, base_f + L("tgt", "car", "snaps", "gl_car", "rz_tgt", "ez_tgt"), "fp")
    print(f"    + only the goal-line kinds (carries inside the 5, targets inside the 10 and into the end zone) {gain(pg, wg, counts, 'fp')}")
    xonly = walk(pg, L("xfp") + posf, "fp")
    print(f"    past expected points alone against past points alone  {gain(pg, xonly, base, 'fp')}")
    both = walk(pg, base_f + L("xfp"), "fp")
    print(f"    past expected points beside past points               {gain(pg, both, base, 'fp')}")
    for p in POS:
        print(f"      {p}: expected points beside past points {gain(pg, both, base, 'fp', (pg['position'] == p).to_numpy())}")
    td_b = walk(pg, L("td", "fp") + posf, "td")
    td_x = walk(pg, L("td", "fp", "gl_car", "rz_tgt", "ez_tgt") + posf, "td")
    print(f"    next game's touchdowns: the goal-line kinds beside past touchdowns and points {gain(pg, td_x, td_b, 'td')}")
    log("H56")

    # ---- 4. H61: does efficiency create opportunity?
    print("\n== 4. H61: do past points over expected predict next game's expected points?")
    x0 = walk(pg, L("xfp", "tgt", "car", "snaps") + posf, "xfp")
    x1 = walk(pg, L("xfp", "tgt", "car", "snaps", "poe") + posf, "xfp")
    print(f"  everyone                   {gain(pg, x1, x0, 'xfp')}")
    ye = pg["years_exp"].fill_null(5).to_numpy()
    print(f"  first two seasons          {gain(pg, x1, x0, 'xfp', ye <= 1)}")
    print(f"  third season on            {gain(pg, x1, x0, 'xfp', ye >= 2)}")
    for p in POS:
        print(f"  {p}                         {gain(pg, x1, x0, 'xfp', (pg['position'] == p).to_numpy())}")
    d = pg.filter(c("poe_l4").is_not_null() & c("xfp_l4").is_not_null() & (c("n_games") >= 4)).with_columns(
        chg=c("xfp") - c("xfp_l4"), q=c("poe_l4").qcut(5, labels=["lowest", "low", "middle", "high", "highest"])
    )
    print("  change in expected points (this game minus the last-4 average), by the last 4 games' points over expected:")
    for r in d.group_by("q").agg(n=pl.len(), poe=c("poe_l4").mean(), chg=c("chg").mean(), lvl=c("xfp_l4").mean()).sort("poe").iter_rows(named=True):
        print(f"    {r['q']:<8} (over expected {r['poe']:+.2f} a game, level {r['lvl']:.1f}): {r['chg']:+.2f} points  (n {r['n']})")
    log("H61")

    # ---- 5. H57: movers
    print("\n== 5. H57: season to next season, movers against stayers (50+ chances both seasons, one team each)")
    ss = seasons(pg)
    for label, col in (("expected points per game", "xfp_g"), ("expected points per snap", "xfp_snap"),
                       ("expected points per chance (quality)", "xfp_ch"), ("points per game", "fp_g"),
                       ("points over expected per chance", "poe_ch")):  # fmt: skip
        st, mv = ss.filter(c("stayed")), ss.filter(c("moved"))
        print(f"  {label:<40} stayers r {fisher(corr(st[col], st[col + '_n']), st.height)}   movers r {fisher(corr(mv[col], mv[col + '_n']), mv.height)}")
    for p in POS:
        st, mv = ss.filter(c("stayed") & (c("position") == p)), ss.filter(c("moved") & (c("position") == p))
        print(f"    {p}: expected points per game, stayers {fisher(corr(st['xfp_g'], st['xfp_g_n']), st.height)}; movers {fisher(corr(mv['xfp_g'], mv['xfp_g_n']), mv.height)};"
              f" change for movers {(mv['xfp_g_n'] - mv['xfp_g']).mean():+.2f} a game, stayers {(st['xfp_g_n'] - st['xfp_g']).mean():+.2f}")  # fmt: skip
    # the seat: what the new team gave that position's same-ranked player the season before
    rank = pg.group_by("gsis_id", "season", "team", "position").agg(xfp=c("xfp").sum(), g=pl.len()).with_columns(
        rk=c("xfp").rank("ordinal", descending=True).over("season", "team", "position")
    )
    mv = ss.filter(c("moved")).join(
        rank.select("gsis_id", season=c("season") - 1, rk_n="rk"), on=["gsis_id", "season"], how="left"
    ).join(
        rank.select(team_n="team", position="position", season="season", rk_n="rk", seat=c("xfp") / c("g")),
        on=["team_n", "position", "season", "rk_n"], how="left",
    ).filter(c("seat").is_not_null())  # fmt: skip
    if mv.height > 30:
        X = np.column_stack([np.ones(mv.height), mv["xfp_g"].to_numpy(), mv["seat"].to_numpy()])
        yv = mv["xfp_g_n"].to_numpy()
        beta = np.linalg.lstsq(X, yv, rcond=None)[0]
        r_own, r_seat = corr(mv["xfp_g"], yv), corr(mv["seat"], yv)
        print(f"  movers ({mv.height}): next season's expected points per game against his own last season (r {r_own:+.2f}) and against what the")
        print(f"    new team gave the player who held his depth-rank the season before, 'the seat' (r {r_seat:+.2f}, hindsight: the rank is the one he ended up with);")
        print(f"    together: {beta[1]:.2f} x his own + {beta[2]:.2f} x the seat")
    log("H57")

    # ---- 6. H60: by scheme, for movers
    print("\n== 6. H60: for movers, last season's expected points split by formation, re-weighted to the new team's mix")
    tm = ch.group_by("season", "posteam").agg(sg=(c("shotgun") == 1).mean()).rename({"posteam": "team"})
    m = ss.filter(c("moved")).join(tm.rename({"sg": "sg_old"}), on=["season", "team"]).join(
        tm.select(team_n="team", season="season", sg_new="sg"), on=["team_n", "season"]
    )  # the new team's mix in the season before he arrived: known ahead
    m = m.with_columns(
        rew=(c("xfp_sg") / c("sg_old").clip(0.05) * c("sg_new") + c("xfp_uc") / (1 - c("sg_old")).clip(0.05) * (1 - c("sg_new"))) / c("g"),
        share_sg=c("xfp_sg") / c("xfp"),
    )
    yv = m["xfp_g_n"].to_numpy()
    print(f"  movers {m.height}: overall rate r {corr(m['xfp_g'], yv):+.3f}; re-weighted by formation r {corr(m['rew'], yv):+.3f}")
    big = m.filter((c("sg_new") - c("sg_old")).abs() >= 0.10)
    print(f"  movers to a team at least 10 points of shotgun rate different ({big.height}): overall r {corr(big['xfp_g'], big['xfp_g_n']):+.3f}; re-weighted r {corr(big['rew'], big['xfp_g_n']):+.3f}")
    X = np.column_stack([np.ones(m.height), m["xfp_g"].to_numpy(), ((m["share_sg"] - m["share_sg"].mean()) * (m["sg_new"] - m["sg_old"])).to_numpy()])
    beta, res = np.linalg.lstsq(X, yv, rcond=None)[:2]
    se = math.sqrt(res[0] / (m.height - 3) * np.linalg.inv(X.T @ X)[2, 2])
    print(f"  fit term (his shotgun share x the change in shotgun rate): {beta[2]:+.2f}, standard error {se:.2f}")
    st = ss.filter(c("stayed")).with_columns(share_sg=c("xfp_sg") / c("xfp"), share_sg_n=c("xfp_sg_n") / c("xfp_n"))
    mvs = ss.filter(c("moved")).with_columns(share_sg=c("xfp_sg") / c("xfp"), share_sg_n=c("xfp_sg_n") / c("xfp_n"))
    print(f"  a player's shotgun share of his expected points, season to season: stayers {fisher(corr(st['share_sg'], st['share_sg_n']), st.height)}; movers {fisher(corr(mvs['share_sg'], mvs['share_sg_n']), mvs.height)}")

    # ---- 7. H58: yards after the catch
    print("\n== 7. H58: yards after the catch over expected (per catch), receivers and tight ends, 30+ catches a season")
    y = ch.filter(c("yac_oe").is_not_null() & (c("season") >= 2012)).group_by("gsis_id", "season").agg(
        position=c("position").last(), rec=pl.len(), yac_oe=c("yac_oe").mean()
    ).filter(c("rec") >= 30)  # fmt: skip
    sa = pg.group_by("gsis_id", "season").agg(n=c("n").sum(), poe_ch=c("poe").sum() / c("n").sum(), xfp_ch=c("xfp").sum() / c("n").sum())
    y = y.join(sa, on=["gsis_id", "season"])
    yn = y.join(y.with_columns(c("season") - 1), on=["gsis_id", "season"], suffix="_n")
    for p in ("WR", "TE", "RB"):
        e = yn.filter(c("position") == p)
        if e.height < 30:
            continue
        print(f"  {p}: repeats season to season r {fisher(corr(e['yac_oe'], e['yac_oe_n']), e.height)};"
              f" same season with points over expected per chance r {corr(e['yac_oe'], e['poe_ch']):+.2f};"
              f" predicts next season's points over expected r {fisher(corr(e['yac_oe'], e['poe_ch_n']), e.height)}"
              f" (last season's points over expected itself: r {corr(e['poe_ch'], e['poe_ch_n']):+.2f})")  # fmt: skip
        X = np.column_stack([np.ones(e.height), e["poe_ch"].to_numpy(), e["yac_oe"].to_numpy()])
        beta, res = np.linalg.lstsq(X, e["poe_ch_n"].to_numpy(), rcond=None)[:2]
        se = math.sqrt(res[0] / (e.height - 3) * np.linalg.inv(X.T @ X)[2, 2])
        top = e.filter(c("yac_oe") >= e["yac_oe"].quantile(0.75))
        print(f"      beside last season's points over expected, a yard of it adds {beta[2]:+.3f} points per chance (se {se:.3f});"
              f" the top quarter's next season: {top['poe_ch_n'].mean():+.3f} points per chance over expected, {100 * (top['poe_ch_n'] > 0).mean():.0f}% above zero")  # fmt: skip

    # ---- 8. H62 and the regression measure
    print("\n== 8. H62: how much of a season's points over expected per chance is kept the next season?")

    def kept(e: pl.DataFrame) -> str:
        if e.height < 25:
            return f"too few (n {e.height})"
        x, yv = e["poe_ch"].to_numpy(), e["poe_ch_n"].to_numpy()
        slope = np.polyfit(x, yv, 1)[0]
        idx = RNG.integers(0, len(x), size=(1000, len(x)))
        bs = [np.polyfit(x[i], yv[i], 1)[0] for i in idx]
        return f"keeps {100 * slope:3.0f}% (90% {100 * np.quantile(bs, 0.05):.0f} to {100 * np.quantile(bs, 0.95):.0f}); same sign next season {100 * (np.sign(x) == np.sign(yv)).mean():.0f}%; n {e.height}"

    print(f"  everyone                              {kept(ss)}")
    for p in POS:
        print(f"  {p}                                    {kept(ss.filter(c('position') == p))}")
    print(f"  stayers                               {kept(ss.filter(c('stayed')))}")
    print(f"  movers                                {kept(ss.filter(c('moved')))}")
    prev = ss.select("gsis_id", season=c("season") + 1, poe_prev="poe_ch", moved_prev="moved")
    s3 = ss.join(prev, on=["gsis_id", "season"])
    same = s3.filter(c("poe_prev").sign() == c("poe_ch").sign())
    print(f"  same side of zero two seasons running {kept(same)}")
    print(f"     of those, above zero both seasons   {kept(same.filter(c('poe_ch') > 0))}; their next season averages {same.filter(c('poe_ch') > 0)['poe_ch_n'].mean():+.3f} a chance")
    print(f"  opposite sides the two seasons        {kept(s3.filter(c('poe_prev').sign() != c('poe_ch').sign()))}")
    car = s3.filter(c("moved_prev") & (c("poe_prev").sign() == c("poe_ch").sign()))
    print(f"  moved, and kept the same side on the new team (the CEO's 'carried it') {kept(car)}")
    hi = ss.filter(c("n") >= 150)
    print(f"  150+ chances a season                 {kept(hi)}")
    sd_true = ss.select(((c("poe_ch") * c("poe_ch_n")).mean()).alias("cov"))["cov"][0]
    print(f"  spread of points over expected per chance across player-seasons: {ss['poe_ch'].std():.3f}; the part that lasts (square root of the season-to-season covariance): {math.sqrt(max(sd_true, 0)):.3f}")
    print("  the chance the gap closes by half or more next season (|next| <= half of |this|, same side or crossed):")
    for label, e in (("everyone", ss), ("gap of 0.10+ a chance", ss.filter(c("poe_ch").abs() >= 0.10)), ("two seasons same side, 0.10+", same.filter(c("poe_ch").abs() >= 0.10))):
        x, yv = e["poe_ch"].to_numpy(), e["poe_ch_n"].to_numpy()
        closes = (np.sign(x) != np.sign(yv)) | (np.abs(yv) <= 0.5 * np.abs(x))
        print(f"    {label:<32} {100 * closes.mean():.0f}%  (n {e.height})")
    log("done")


if __name__ == "__main__":
    main()
