# ruff: noqa: E501, B026
"""td-expert, first look (2026-11-16). Discovery only: the noise ceiling, then the CEO's hunches
H67-H68 and questions Q1-Q5.

- A chance = a target (RB, WR, TE) or a carry (QB, RB, WR, TE; scrambles included), regular
  season, 2009-2024 (2006-2008 list completed passes almost only; the 2025 vault is left out).
  A touchdown counts for the player who scored.
- Expected touchdowns (xtd) = the chance that this kind of chance scores: boosted trees on where
  it was (yard line, down, distance, throw depth, side, clock, score), fit only on earlier
  seasons, so 2012-2024 have them.
- Rest of season: after weeks 4, 8 and 12, a player's rushing + receiving touchdowns in the
  weeks left, from his games so far (2+ games, 2+ chances a game, and at least one game after).
  Lasso + trees, walk forward, fit 2012..s-1, scored 2019-2024.
- Team level: red-zone trips (drives with a play inside the 20), first half of a season (weeks
  1-9) against the second, 2006-2024.

Run from pcf/:  python projects/td-expert/explore/first_look.py > projects/td-expert/explore/first_look.txt
"""

from __future__ import annotations

import itertools
import math
import sys
import time

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import Lasso, LinearRegression
from sklearn.preprocessing import StandardScaler

from pcf.config import get_config
from pcf.data.gateway import Gateway

c = pl.col
TEST = range(2019, 2025)
DRAWS = 2000
RNG = np.random.default_rng(get_config().seed)
T0 = time.time()
POS = ("QB", "RB", "WR", "TE")
CUTS = (4, 8, 12)


def log(*a):
    print(f"[{time.time() - T0:6.0f}s]", *a, file=sys.stderr, flush=True)


def corr(a, b) -> float:
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = ~np.isnan(a) & ~np.isnan(b)
    return float(np.corrcoef(a[ok], b[ok])[0, 1])


def fisher(r: float, n: int) -> str:
    if n < 6 or abs(r) >= 1 or math.isnan(r):
        return f"{r:+.2f} (n {n})"
    z, se = math.atanh(r), 1 / math.sqrt(n - 3)
    return f"{r:+.2f} ({math.tanh(z - 1.645 * se):+.2f} to {math.tanh(z + 1.645 * se):+.2f}, n {n})"


def cf(a, b) -> str:
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = ~np.isnan(a) & ~np.isnan(b)
    return fisher(corr(a[ok], b[ok]), int(ok.sum()))


def partial(x, y, controls) -> str:
    """Correlation of x and y after a straight-line fit on the controls is taken out of both."""
    z = np.column_stack([np.ones(len(x)), *controls])
    ok = ~np.isnan(z).any(axis=1) & ~np.isnan(x) & ~np.isnan(y)
    z, x, y = z[ok], np.asarray(x, float)[ok], np.asarray(y, float)[ok]
    rx = x - z @ np.linalg.lstsq(z, x, rcond=None)[0]
    ry = y - z @ np.linalg.lstsq(z, y, rcond=None)[0]
    return fisher(corr(rx, ry), len(x))


# ---------------------------------------------------------------- plays, chances, xtd
def plays(src) -> pl.DataFrame:
    cols = ["game_id", "play_id", "season", "week", "posteam", "defteam", "yardline_100", "down",
            "ydstogo", "goal_to_go", "shotgun", "no_huddle", "qtr", "half_seconds_remaining",
            "score_differential", "play_type", "rush", "pass", "qb_scramble", "sack",
            "receiver_player_id", "rusher_player_id", "air_yards", "pass_location", "run_location",
            "run_gap", "complete_pass", "yards_gained", "touchdown", "td_player_id", "td_team", "epa",
            "success", "xpass", "third_down_converted", "third_down_failed", "fixed_drive",
            "fixed_drive_result"]  # fmt: skip
    return (
        src.part("play", "pbp").lazy()
        .filter(
            c("season").is_between(2006, 2024) & (c("season_type") == "REG")
            & (c("two_point_attempt") == 0) & c("play_type").is_in(["run", "pass"])
            & c("posteam").is_not_null()
        )
        .select(cols).collect()
    )  # fmt: skip


def chances(p: pl.DataFrame, src) -> pl.DataFrame:
    common = ["game_id", "play_id", "season", "week", "posteam", "yardline_100", "down", "ydstogo",
              "goal_to_go", "shotgun", "no_huddle", "qtr", "half_seconds_remaining",
              "score_differential"]  # fmt: skip
    tgt = p.filter(
        c("receiver_player_id").is_not_null() & (c("play_type") == "pass") & (c("sack") == 0)
    ).select(
        *common, gsis_id=c("receiver_player_id"), kind=pl.lit("target"),
        air=c("air_yards").cast(pl.Float64),
        loc=c("pass_location").replace_strict({"left": 0, "middle": 1, "right": 2}, default=None).cast(pl.Float64),
        gap=pl.lit(None, dtype=pl.Float64), scr=pl.lit(0.0),
        yards=pl.when(c("complete_pass") == 1).then(c("yards_gained")).otherwise(0).cast(pl.Float64),
        catch=c("complete_pass").cast(pl.Float64),
        td=((c("touchdown") == 1) & (c("td_player_id") == c("receiver_player_id"))).cast(pl.Float64),
    )  # fmt: skip
    run = p.filter(c("rusher_player_id").is_not_null() & (c("play_type") == "run")).select(
        *common, gsis_id=c("rusher_player_id"), kind=pl.lit("carry"),
        air=pl.lit(None, dtype=pl.Float64),
        loc=c("run_location").replace_strict({"left": 0, "middle": 1, "right": 2}, default=None).cast(pl.Float64),
        gap=c("run_gap").replace_strict({"guard": 0, "tackle": 1, "end": 2}, default=None).cast(pl.Float64),
        scr=c("qb_scramble").cast(pl.Float64),
        yards=c("yards_gained").cast(pl.Float64), catch=pl.lit(0.0),
        td=((c("touchdown") == 1) & (c("td_player_id") == c("rusher_player_id"))).cast(pl.Float64),
    )  # fmt: skip
    ch = pl.concat([tgt, run]).with_columns(
        expl=(((c("kind") == "carry") & (c("yards") >= 10)) | ((c("kind") == "target") & (c("catch") == 1) & (c("yards") >= 20))).cast(pl.Float64)
    )  # fmt: skip
    roster = src.part("player_game", "roster").lazy().select("gsis_id", "game_id", "position", "team").collect()
    # 2006-2008 list completed passes almost only (9,000-10,000 targets a season against 16,000+;
    # end-zone targets score 99%), so chances start in 2009
    ch = ch.filter(c("season") >= 2009).join(roster, on=["gsis_id", "game_id"]).filter(c("position").is_in(POS))
    return ch.filter((c("position") != "QB") | (c("kind") == "carry"))


SIT = ["yardline_100", "down", "ydstogo", "goal_to_go", "shotgun", "no_huddle", "qtr",
       "half_seconds_remaining", "score_differential", "air", "loc", "gap", "scr"]  # fmt: skip


def expected(ch: pl.DataFrame) -> pl.DataFrame:
    """xtd per chance from models fit on earlier seasons only (one for targets, one for carries)."""
    ch = ch.with_row_index("_i")
    out = np.full(ch.height, np.nan)
    for kind in ("target", "carry"):
        d = ch.filter(c("kind") == kind)
        sit = [f for f in SIT if f not in (("gap", "scr") if kind == "target" else ("air",))]
        x, y = d.select(sit).to_numpy().astype(float), d["td"].to_numpy()
        season, idx = d["season"].to_numpy(), d["_i"].to_numpy()
        for s in range(2012, 2025):
            tr, te = season < s, season == s
            m = HistGradientBoostingClassifier(
                max_iter=200, learning_rate=0.06, max_leaf_nodes=31, min_samples_leaf=100,
                random_state=0,
            ).fit(x[tr], y[tr])  # fmt: skip
            out[idx[te]] = m.predict_proba(x[te])[:, 1]
        log("xtd model", kind)
    return ch.with_columns(xtd=pl.Series(out)).filter(c("season") >= 2012).drop("_i")


KIND = (
    pl.when((c("kind") == "carry") & (c("yardline_100") <= 2)).then(pl.lit("01 carry inside the 2"))
    .when((c("kind") == "carry") & (c("yardline_100") <= 5)).then(pl.lit("02 carry from the 3 to 5"))
    .when((c("kind") == "carry") & (c("yardline_100") <= 10)).then(pl.lit("03 carry from the 6 to 10"))
    .when((c("kind") == "carry") & (c("yardline_100") <= 20)).then(pl.lit("04 carry from the 11 to 20"))
    .when(c("kind") == "carry").then(pl.lit("05 carry outside the 20"))
    .when((c("air") >= c("yardline_100")) & (c("yardline_100") <= 10)).then(pl.lit("06 target into the end zone from the 10 or closer"))
    .when((c("air") >= c("yardline_100")) & (c("yardline_100") <= 20)).then(pl.lit("07 target into the end zone from the 11 to 20"))
    .when(c("air") >= c("yardline_100")).then(pl.lit("08 target into the end zone from further"))
    .when(c("yardline_100") <= 10).then(pl.lit("09 target inside the 10, short of the goal line"))
    .when(c("yardline_100") <= 20).then(pl.lit("10 target from the 11 to 20, short of the goal line"))
    .otherwise(pl.lit("11 target outside the 20, short of the goal line"))
)  # fmt: skip


# ---------------------------------------------------------------- player-games, rest of season
PG = ["td", "xtd", "n", "tgt", "car", "yards", "air", "rz20", "in10", "gl", "ez_tgt", "expl", "snaps"]


def player_games(src, ch: pl.DataFrame) -> pl.DataFrame:
    t, k = c("kind") == "target", c("kind") == "carry"
    agg = ch.group_by("gsis_id", "game_id").agg(
        td=c("td").sum(), xtd=c("xtd").sum(), n=pl.len().cast(pl.Float64),
        tgt=t.sum().cast(pl.Float64), car=k.sum().cast(pl.Float64), yards=c("yards").sum(),
        air=c("air").fill_null(0.0).sum(),
        rz20=(c("yardline_100") <= 20).sum().cast(pl.Float64),
        in10=(c("yardline_100") <= 10).sum().cast(pl.Float64),
        gl=(k & (c("yardline_100") <= 5)).sum().cast(pl.Float64),
        ez_tgt=(t & (c("air") >= c("yardline_100"))).sum().cast(pl.Float64),
        expl=c("expl").sum(),
    )  # fmt: skip
    roster = src.part("player_game", "roster").lazy().filter(
        c("season").is_between(2012, 2024) & c("position").is_in(POS)
    ).select("gsis_id", "game_id", "season", "week", "team", "position").collect()  # fmt: skip
    snaps = src.part("player_game", "snaps").lazy().select("gsis_id", "game_id", "offense_snaps").collect()
    sched = src.part("team_game", "schedule").lazy().select("game_id", "team", "game_type").collect()
    df = (
        roster.join(sched, on=["game_id", "team"]).filter(c("game_type") == "REG")
        .join(snaps, on=["gsis_id", "game_id"]).filter(c("offense_snaps") > 0)
        .join(agg, on=["gsis_id", "game_id"], how="left")
    )  # fmt: skip
    num = [x for x in agg.columns if x not in ("gsis_id", "game_id")]
    return df.with_columns(c(num).fill_null(0), snaps=c("offense_snaps").cast(pl.Float64)).sort("gsis_id", "season", "week")


def ros(pg: pl.DataFrame) -> pl.DataFrame:
    us, out = ["gsis_id", "season"], []
    for cut in CUTS:
        a = pg.filter(c("week") <= cut).sort("week").group_by(us).agg(
            g=pl.len(), position=c("position").last(), team=c("team").last(),
            *[c(k).mean().alias(f"{k}_s") for k in PG],
        )  # fmt: skip
        b = pg.filter(c("week") > cut).group_by(us).agg(
            y=c("td").sum(), y_x=c("xtd").sum(), g_after=pl.len().cast(pl.Float64)
        )
        out.append(a.join(b, on=us).with_columns(cut=pl.lit(float(cut))))
    df = pl.concat(out).filter((c("g") >= 2) & (c("n_s") >= 2))
    last = pg.group_by(us).agg(*[c(k).mean().alias(f"{k}_ls") for k in PG]).with_columns(c("season") + 1)
    df = df.join(last, on=us, how="left")
    df = df.with_columns(
        *[(c(f"expl_{s}") / c(f"n_{s}")).alias(f"explrate_{s}") for s in ("s", "ls")],
        *[(c(f"td_{s}") - c(f"xtd_{s}")).alias(f"tdoe_{s}") for s in ("s", "ls")],
        *[(c("position") == q).cast(pl.Float64).alias(f"is_{q.lower()}") for q in POS],
        blk=c("season").cast(pl.String) + c("team"),
    )
    return df.sort("season", "cut", "gsis_id")


BASE = ["cut", "is_qb", "is_rb", "is_wr", "is_te"]


def F(*cols: str) -> list[str]:
    return [f"{k}_{sfx}" for k in cols for sfx in ("s", "ls")]


def walk(df, feats, y, fit_from=2012, resample=None) -> np.ndarray:
    x = df.select(feats).to_numpy().astype(float)
    yy, season = df[y].to_numpy().astype(float), df["season"].to_numpy()
    out = np.full(len(yy), np.nan)
    xl = np.nan_to_num(x, nan=0.0)
    for s in TEST:
        tr = np.flatnonzero((season < s) & (season >= fit_from))
        if resample is not None:
            tr = np.random.default_rng(resample).choice(tr, len(tr))
        te = season == s
        sc = StandardScaler().fit(xl[tr])
        lasso = Lasso(alpha=0.01 * yy[tr].std(), max_iter=5000).fit(sc.transform(xl[tr]), yy[tr])
        trees = HistGradientBoostingRegressor(
            max_iter=120, learning_rate=0.06, max_leaf_nodes=15, min_samples_leaf=40,
            l2_regularization=1.0, early_stopping=False, random_state=0,
        ).fit(x[tr], yy[tr])  # fmt: skip
        out[te] = (lasso.predict(sc.transform(xl[te])) + trees.predict(x[te])) / 2
    return out


def rate(df, y, fit_from=2012) -> np.ndarray:
    """The plain base rate: the mean of the training seasons."""
    yy, season = df[y].to_numpy().astype(float), df["season"].to_numpy()
    out = np.full(len(yy), np.nan)
    for s in TEST:
        out[season == s] = yy[(season < s) & (season >= fit_from)].mean()
    return out


def r2(df, pred, base, y, mask=None) -> float:
    yy = df[y].to_numpy().astype(float)
    ok = ~np.isnan(pred) & ~np.isnan(base)
    if mask is not None:
        ok &= mask
    return float(100 * (1 - ((pred - yy)[ok] ** 2).sum() / ((base - yy)[ok] ** 2).sum()))


def gain(df, new, base, y, mask=None) -> str:
    """Share of base's squared error removed by new, with a 90% interval over blocks (df.blk)."""
    yy = df[y].to_numpy().astype(float)
    ok = ~np.isnan(new) & ~np.isnan(base)
    if mask is not None:
        ok &= mask
    d = pl.DataFrame({"w": df["blk"].to_numpy()[ok], "a": ((new - yy) ** 2)[ok], "b": ((base - yy) ** 2)[ok]}).group_by("w").agg(c("a").sum(), c("b").sum())
    a, b = d["a"].to_numpy(), d["b"].to_numpy()
    draws = RNG.multinomial(len(a), np.full(len(a), 1 / len(a)), size=DRAWS)
    boot = 1 - (draws @ a) / (draws @ b)
    lo, hi = np.quantile(boot, [0.05, 0.95])
    return f"{100 * (1 - a.sum() / b.sum()):+6.2f}%  (90% {100 * lo:+.2f} to {100 * hi:+.2f})"


# ---------------------------------------------------------------- team tables
SUMS = ["n", "epa", "succ", "db", "xp", "sg", "nh", "n10", "pass10", "rz_n", "rz_y", "rz_y2", "rz_epa",
        "rz_epa2", "rz_succ", "t3c", "t3a", "expl", "rush_td", "pass_td", "rz_trips", "rz_tds", "rz_fgs", "g"]  # fmt: skip


def team_games(p: pl.DataFrame, by: str) -> pl.DataFrame:
    rz, db = c("yardline_100") <= 20, (c("pass") == 1)
    otd = (c("touchdown") == 1) & (c("td_team") == c("posteam"))
    y, e = c("yards_gained").cast(pl.Float64), c("epa").fill_null(0.0)
    a = p.group_by("game_id", "season", "week", by).agg(
        n=pl.len().cast(pl.Float64), epa=e.sum(), succ=c("success").fill_null(0).sum().cast(pl.Float64),
        db=db.sum().cast(pl.Float64), xp=c("xpass").fill_null(c("pass")).sum(),
        sg=c("shotgun").sum().cast(pl.Float64), nh=c("no_huddle").sum().cast(pl.Float64),
        n10=(c("yardline_100") <= 10).sum().cast(pl.Float64),
        pass10=((c("yardline_100") <= 10) & db).sum().cast(pl.Float64),
        rz_n=rz.sum().cast(pl.Float64), rz_y=y.filter(rz).sum(), rz_y2=(y**2).filter(rz).sum(),
        rz_epa=e.filter(rz).sum(), rz_epa2=(e**2).filter(rz).sum(),
        rz_succ=c("success").fill_null(0).filter(rz).sum().cast(pl.Float64),
        t3c=c("third_down_converted").fill_null(0).sum().cast(pl.Float64),
        t3a=(c("third_down_converted").fill_null(0) + c("third_down_failed").fill_null(0)).sum().cast(pl.Float64),
        expl=(((c("play_type") == "run") & (y >= 10)) | ((c("play_type") == "pass") & (y >= 20))).sum().cast(pl.Float64),
        rush_td=(otd & (c("play_type") == "run")).sum().cast(pl.Float64),
        pass_td=(otd & (c("play_type") == "pass")).sum().cast(pl.Float64),
    )  # fmt: skip
    d = p.group_by("game_id", by, "fixed_drive").agg(rz=rz.any(), res=c("fixed_drive_result").first()).filter(c("rz"))
    d = d.group_by("game_id", by).agg(
        rz_trips=pl.len().cast(pl.Float64), rz_tds=(c("res") == "Touchdown").sum().cast(pl.Float64),
        rz_fgs=c("res").is_in(["Field goal", "Missed field goal"]).sum().cast(pl.Float64),
    )
    return a.join(d, on=["game_id", by], how="left").with_columns(c("rz_trips", "rz_tds", "rz_fgs").fill_null(0.0), g=pl.lit(1.0)).rename({by: "team"})


def rates(df: pl.DataFrame, pre: str = "") -> pl.DataFrame:
    s = lambda k: c(pre + k)  # noqa: E731
    return df.with_columns(
        epa_p=s("epa") / s("n"), succ_p=s("succ") / s("n"), pass_rate=s("db") / s("n"),
        proe=(s("db") - s("xp")) / s("n"), sg_rate=s("sg") / s("n"), nh_rate=s("nh") / s("n"),
        pass10_rate=s("pass10") / s("n10"), rz_td_rate=s("rz_tds") / s("rz_trips"),
        rz_ypp=s("rz_y") / s("rz_n"), rz_epa_p=s("rz_epa") / s("rz_n"), rz_succ_p=s("rz_succ") / s("rz_n"),
        rz_y_sd=(s("rz_y2") / s("rz_n") - (s("rz_y") / s("rz_n")) ** 2).sqrt(),
        rz_epa_sd=(s("rz_epa2") / s("rz_n") - (s("rz_epa") / s("rz_n")) ** 2).sqrt(),
        t3=s("t3c") / s("t3a"), expl_rate=s("expl") / s("n"),
        rush_td_share=s("rush_td") / (s("rush_td") + s("pass_td")),
        rz_trips_g=s("rz_trips") / s("g"), td_g=(s("rush_td") + s("pass_td")) / s("g"),
    )


RATES = ["epa_p", "succ_p", "pass_rate", "proe", "sg_rate", "nh_rate", "pass10_rate", "rz_td_rate", "rz_ypp",
         "rz_epa_p", "rz_succ_p", "rz_y_sd", "rz_epa_sd", "t3", "expl_rate", "rush_td_share", "rz_trips_g", "td_g"]  # fmt: skip


def halves(tg: pl.DataFrame, split) -> pl.DataFrame:
    a = rates(tg.filter(split).group_by("team", "season").agg(c(SUMS).sum())).select("team", "season", *RATES)
    b = rates(tg.filter(~split).group_by("team", "season").agg(c(SUMS).sum())).select("team", "season", *RATES)
    return a.join(b, on=["team", "season"], suffix="_2")


def before(tg: pl.DataFrame, pre: str) -> pl.DataFrame:
    """Each team-game's season-so-far rates from its earlier games (3+ games)."""
    t = tg.sort("team", "season", "week").with_columns(
        [(c(k).cum_sum().over("team", "season") - c(k)).alias("c_" + k) for k in SUMS]
    )
    t = rates(t, "c_").filter(c("c_g") >= 3)
    return t.select("game_id", "team", *[c(k).alias(pre + k) for k in RATES])


def loso(d: pl.DataFrame, feats: list[str], y: str) -> float:
    """Leave one season out, straight-line fit: share of squared error removed against the other seasons' mean."""
    d = d.drop_nulls([*feats, y]) if feats else d.drop_nulls([y])
    yy, season = d[y].to_numpy(), d["season"].to_numpy()
    x = d.select(feats).to_numpy() if feats else None
    se = sb = 0.0
    for s in np.unique(season):
        tr, te = season != s, season == s
        base = yy[tr].mean()
        pred = LinearRegression().fit(x[tr], yy[tr]).predict(x[te]) if feats else base
        se += ((pred - yy[te]) ** 2).sum()
        sb += ((base - yy[te]) ** 2).sum()
    return 100 * (1 - se / sb)


# ---------------------------------------------------------------- main
def main() -> None:
    src = Gateway().source
    p = plays(src)
    log("plays", p.height)
    ch = expected(chances(p, src))
    pg = player_games(src, ch)
    df = ros(pg)
    log("chances", ch.height, "player-games", pg.height, "rest-of-season rows", df.height)
    print(f"Chances 2012-2024: {ch.height:,} ({int(ch['td'].sum()):,} touchdowns). Player-games 2012-2024: {pg.height:,}. Rest-of-season rows: {df.height:,} ({df.filter(c('season') >= 2019).height:,} scored).")
    for k in ("target", "carry"):
        d = ch.filter(c("kind") == k)
        print(f"  xtd check, {k}: touchdowns {d['td'].sum():.0f}, expected {d['xtd'].sum():.0f}")
    tens = ch.with_columns(b=(c("xtd") * 10).floor().clip(0, 9)).group_by("b").agg(pl.len(), c("xtd").mean(), c("td").mean()).sort("b")
    print("  calibration by tenth of xtd (n, expected, actual):", "; ".join(f"{r['len']:,} {r['xtd']:.3f} {r['td']:.3f}" for r in tens.iter_rows(named=True)))

    y = "y"
    base = rate(df, y)
    yy = df[y].to_numpy()
    test = df["season"].to_numpy() >= 2019
    ALL = ["td", "xtd", "n", "tgt", "car", "yards", "air", "rz20", "in10", "gl", "ez_tgt", "expl", "explrate", "snaps"]
    pos_m = {q: (df["position"].to_numpy() == q) for q in POS}

    # ------------------------------------------------------------ noise ceiling
    print("\n== THE NOISE CEILING ==")
    full = walk(df, BASE + F(*ALL), y)
    print(f"Rest-of-season touchdowns: mean {yy[test].mean():.2f}, sd {yy[test].std():.2f} a player (scored rows)")
    print(f"Everything from his games so far removes {gain(df, full, base, y)} of the error (against the plain mean)")
    refits = [r2(df, walk(df, BASE + F(*ALL), y, resample=i), base, y) for i in (1, 2, 3)]
    print(f"Fitting noise: the same model refit on resampled training rows: {', '.join(f'{v:.2f}' for v in refits)} (sd {np.std(refits):.2f} points)")
    yx = df["y_x"].to_numpy()
    print(f"Hindsight: knowing every chance he then got (its expected touchdowns) removes {gain(df, yx, base, y)}")
    print(f"  so the luck of scoring on a chance is {100 * ((yx - yy)[test] ** 2).sum() / ((base - yy)[test] ** 2).sum():.1f}% of the error even then; if touchdowns were pure dice on those chances it would be {100 * yx[test].mean() / ((base - yy)[test] ** 2).mean():.1f}%")
    ga = df["g_after"].to_numpy()
    hind = walk(df.with_columns(ga=c("g_after")), BASE + F(*ALL) + ["ga"], y)
    print(f"Hindsight: knowing only how many games he then played: {r2(df, hind, base, y):.2f}% (from {r2(df, full, base, y):.2f}%)")
    for q in POS:
        print(f"  {q}: n {int((test & pos_m[q]).sum()):,}, mean {yy[test & pos_m[q]].mean():.2f}; so far {r2(df, full, base, y, pos_m[q]):.1f}%, hindsight chances {r2(df, yx, base, y, pos_m[q]):.1f}%")
    # split halves within a season
    odd = pg.with_columns(h=c("week") % 2).group_by("gsis_id", "season", "position").agg(
        n=c("n").sum(), g=pl.len(),
        *[c(k).filter(c("h") == i).sum().alias(f"{k}{i}") for k in ("td", "xtd", "n") for i in (0, 1)],
    ).filter((c("n") >= 50) & (c("g") >= 8))  # fmt: skip
    print(f"Split halves (odd against even weeks, player-seasons with 50+ chances): touchdowns {cf(odd['td0'], odd['td1'])}; expected touchdowns {cf(odd['xtd0'], odd['xtd1'])}; touchdowns over expected {cf(odd['td0'] - odd['xtd0'], odd['td1'] - odd['xtd1'])}")
    for q in POS:
        o = odd.filter(c("position") == q)
        print(f"  {q}: touchdowns {cf(o['td0'], o['td1'])}; expected {cf(o['xtd0'], o['xtd1'])}; over expected {cf(o['td0'] - o['xtd0'], o['td1'] - o['xtd1'])}")
    del ga

    # ------------------------------------------------------------ H68
    print("\n== H68: THE STRONGEST PREDICTORS OF REST-OF-SEASON TOUCHDOWNS ==")
    b0 = walk(df, BASE, y)
    print(f"Position and week alone: {r2(df, b0, base, y):.2f}%")
    NAME = {"td": "touchdowns", "xtd": "expected touchdowns", "n": "chances", "tgt": "targets", "car": "carries",
            "yards": "yards", "air": "air yards", "rz20": "chances inside the 20", "in10": "chances inside the 10",
            "gl": "carries inside the 5", "ez_tgt": "end-zone targets", "expl": "explosive plays (count)",
            "explrate": "explosive-play rate", "snaps": "snaps"}  # fmt: skip
    single = {k: walk(df, BASE + F(k), y) for k in ALL}
    log("singles")
    print("Single predictors (each a game so far and a game last season, beside position and week):")
    for i, k in enumerate(sorted(ALL, key=lambda k: -r2(df, single[k], base, y)), 1):
        print(f"  {i:2d}. {NAME[k]:28s} {r2(df, single[k], base, y):6.2f}%   RB {r2(df, single[k], base, y, pos_m['RB']):6.2f}  WR {r2(df, single[k], base, y, pos_m['WR']):6.2f}  TE {r2(df, single[k], base, y, pos_m['TE']):6.2f}  QB {r2(df, single[k], base, y, pos_m['QB']):6.2f}")
    pairs = {(a, b): walk(df, BASE + F(a, b), y) for a, b in itertools.combinations(ALL, 2)}
    log("pairs")
    rank = sorted(pairs, key=lambda k: -r2(df, pairs[k], base, y))
    print(f"Pairs ({len(pairs)}), the top 12:")
    for i, k in enumerate(rank[:12], 1):
        print(f"  {i:2d}. {NAME[k[0]]} + {NAME[k[1]]}: {r2(df, pairs[k], base, y):.2f}%")
    for k in (("rz20", "explrate"), ("in10", "explrate"), ("rz20", "expl"), ("in10", "expl")):
        print(f"  The CEO's pair, {NAME[k[0]]} + {NAME[k[1]]}: rank {rank.index(k) + 1} of {len(pairs)}, {r2(df, pairs[k], base, y):.2f}%; against the best pair {gain(df, pairs[k], pairs[rank[0]], y)}")
    print(f"All 14 together: {r2(df, full, base, y):.2f}%; best pair {r2(df, pairs[rank[0]], base, y):.2f}%; best single {max(r2(df, v, base, y) for v in single.values()):.2f}%")
    vol = walk(df, BASE + F("n", "yards", "snaps", "tgt", "car"), y)
    volrz = walk(df, BASE + F("n", "yards", "snaps", "tgt", "car", "rz20", "in10", "gl", "ez_tgt"), y)
    volex = walk(df, BASE + F("n", "yards", "snaps", "tgt", "car", "expl", "explrate"), y)
    volboth = walk(df, BASE + F("n", "yards", "snaps", "tgt", "car", "rz20", "in10", "gl", "ez_tgt", "expl", "explrate"), y)
    print(f"Volume (chances, targets, carries, yards, snaps): {r2(df, vol, base, y):.2f}%")
    print(f"  + red-zone chances (inside 20, inside 10, carries inside 5, end-zone targets): {gain(df, volrz, vol, y)}")
    print(f"  + explosive plays (count and rate): {gain(df, volex, vol, y)}")
    print(f"  + explosive plays, beyond volume and red-zone chances: {gain(df, volboth, volrz, y)}")
    for q in POS:
        print(f"    {q}: red zone beyond volume {gain(df, volrz, vol, y, pos_m[q])}; explosive beyond volume {gain(df, volex, vol, y, pos_m[q])}")
    for cut in CUTS:
        m = df["cut"].to_numpy() == cut
        print(f"    after week {cut}: all 14 {r2(df, full, base, y, m):.2f}%; red zone beyond volume {gain(df, volrz, vol, y, m)}; explosive beyond volume {gain(df, volex, vol, y, m)}")

    # ------------------------------------------------------------ Q3 regression
    print("\n== Q3: TOUCHDOWN REGRESSION ==")
    only_td, only_x = single["td"], single["xtd"]
    both = pairs[("td", "xtd")]
    print(f"Rest-of-season touchdowns from past touchdowns alone {r2(df, only_td, base, y):.2f}%; from expected touchdowns alone {r2(df, only_x, base, y):.2f}%; expected against actual {gain(df, only_x, only_td, y)}")
    print(f"  both {r2(df, both, base, y):.2f}%: past touchdowns beyond expected {gain(df, both, only_x, y)}; expected beyond past touchdowns {gain(df, both, only_td, y)}")
    print(f"  past touchdowns beyond everything else (13 measures): {gain(df, full, walk(df, BASE + F(*[k for k in ALL if k != 'td']), y), y)}")
    d8 = df.filter((c("cut") == 8) & (c("season") >= 2012)).with_columns(
        after=c("y") / c("g_after"), after_x=c("y_x") / c("g_after"), oe=c("td_s") - c("xtd_s")
    )
    x = np.column_stack([np.ones(d8.height), d8["td_s"].to_numpy(), d8["xtd_s"].to_numpy()])
    co = np.linalg.lstsq(x, d8["after"].to_numpy(), rcond=None)[0]
    print(f"After week 8 (n {d8.height:,}), touchdowns a game afterwards = {co[0]:.3f} + {co[1]:.3f} x past touchdowns a game + {co[2]:.3f} x past expected touchdowns a game")
    for q in POS:
        dq = d8.filter(c("position") == q)
        xq = np.column_stack([np.ones(dq.height), dq["td_s"].to_numpy(), dq["xtd_s"].to_numpy()])
        cq = np.linalg.lstsq(xq, dq["after"].to_numpy(), rcond=None)[0]
        print(f"    {q} (n {dq.height:,}): {cq[1]:.3f} x past touchdowns + {cq[2]:.3f} x past expected; over expected so far against over expected afterwards {cf(dq['oe'], dq['after'] - dq['after_x'])}")
    print("  Players through week 8 by touchdowns over expected a game (tenths): before: touchdowns, expected; after: touchdowns, expected")
    d8t = d8.with_columns(t=(c("oe").rank("ordinal") * 10 / (d8.height + 1)).floor())
    for r in d8t.group_by("t").agg(pl.len(), c("td_s").mean(), c("xtd_s").mean(), c("after").mean(), c("after_x").mean(), c("oe").mean()).sort("t").iter_rows(named=True):
        kept = (r["after"] - r["after_x"]) / r["oe"] if abs(r["oe"]) > 0.02 else float("nan")
        print(f"    tenth {int(r['t']) + 1:2d} (n {r['len']}): before {r['td_s']:.3f}, {r['xtd_s']:.3f} ({r['oe']:+.3f}); after {r['after']:.3f}, {r['after_x']:.3f} ({r['after'] - r['after_x']:+.3f}); kept {100 * kept:.0f}%")
    # season to season
    ss = pg.group_by("gsis_id", "season").agg(position=c("position").last(), g=pl.len(), n=c("n").sum(), td=c("td").sum(), xtd=c("xtd").sum()).filter(c("n") >= 50)
    ss = ss.with_columns(oe=(c("td") - c("xtd")) / c("n"), td_g=c("td") / c("g"), xtd_g=c("xtd") / c("g"), rate=c("td") / c("n"))
    s2 = ss.join(ss.with_columns(c("season") - 1), on=["gsis_id", "season"], suffix="_n")
    print(f"Season to season (50+ chances both seasons): touchdowns a game {cf(s2['td_g'], s2['td_g_n'])}; expected a game {cf(s2['xtd_g'], s2['xtd_g_n'])}; over expected per chance {cf(s2['oe'], s2['oe_n'])}")
    print(f"  next season's touchdowns a game from: this season's touchdowns a game {cf(s2['td_g'], s2['td_g_n'])}; this season's expected a game {cf(s2['xtd_g'], s2['td_g_n'])}")
    for q in POS:
        o = s2.filter(c("position") == q)
        slope = np.polyfit(o["oe"].to_numpy(), o["oe_n"].to_numpy(), 1)[0]
        print(f"    {q}: over expected per chance repeats {cf(o['oe'], o['oe_n'])}, keeps {100 * slope:.0f}%; touchdowns a game {cf(o['td_g'], o['td_g_n'])}; expected {cf(o['xtd_g'], o['xtd_g_n'])}")

    # ------------------------------------------------------------ Q4 noisiness
    print("\n== Q4: HOW NOISY IS ONE TOUCHDOWN ==")
    tds = ch.filter(c("td") == 1)
    q = tds["xtd"].quantile
    print(f"The scored touchdowns ({tds.height:,}): the chance was worth {tds['xtd'].mean():.3f} on average before the snap (quartiles {q(0.25):.3f}, {q(0.5):.3f}, {q(0.75):.3f}); {100 * (tds['xtd'] < 0.1).mean():.0f}% came on chances worth under 10%, {100 * (tds['xtd'] >= 0.5).mean():.0f}% on chances worth 50% or more")
    for k in ("target", "carry"):
        t = tds.filter(c("kind") == k)
        print(f"  {k}s: {t.height:,} touchdowns, the chance worth {t['xtd'].mean():.3f} on average, median {t['xtd'].median():.3f}; under 10%: {100 * (t['xtd'] < 0.1).mean():.0f}%")
    for q_ in POS:
        t = tds.filter(c("position") == q_)
        print(f"  {q_}: {t.height:,} touchdowns, the chance worth {t['xtd'].mean():.3f} on average")
    a = pg.filter(c("n") > 0)
    print(f"One player-game ({a.height:,} with a chance): expected touchdowns explain {100 * corr(a['xtd'], a['td']) ** 2:.1f}% of the spread in touchdowns; the rest is the luck of the chance")
    for lo, hi in ((0, 0.1), (0.1, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 1.0), (1.0, 9)):
        b = a.filter((c("xtd") >= lo) & (c("xtd") < hi))
        print(f"    expected {lo} to {hi}: n {b.height:,}, mean expected {b['xtd'].mean():.2f}, touchdowns {b['td'].mean():.2f}, scored at least one {100 * (b['td'] >= 1).mean():.0f}%, variance over mean {b['td'].var() / b['td'].mean():.2f}")
    print(f"Evidence: after week 8, one past touchdown a game is worth {co[1]:.2f} later touchdowns a game and one past expected touchdown {co[2]:.2f}: a touchdown is worth {co[1] / co[2]:.2f} of an expected one")

    # ------------------------------------------------------------ Q5 how many chances
    print("\n== Q5: HOW MANY CHANCES FOR HALF A TOUCHDOWN ==")
    kk = ch.with_columns(k=KIND).group_by("k").agg(pl.len(), c("td").mean(), c("xtd").mean()).sort("k")
    for r in kk.iter_rows(named=True):
        print(f"  {r['k'][3:]:52s} n {r['len']:7,}  scores {100 * r['td']:5.1f}%   chances for half a touchdown: {0.5 / r['td']:5.1f}")
    for q_ in POS:
        t = ch.filter(c("position") == q_)
        for k in ("target", "carry"):
            u = t.filter(c("kind") == k)
            if u.height > 1000:
                print(f"  {q_} {k}: scores {100 * u['td'].mean():.2f}%, {0.5 / u['td'].mean():.0f} for half a touchdown")
    for q_ in POS:
        a = pg.filter(c("position") == q_)
        print(f"  {q_}: {100 * (a['xtd'] > 0.5).mean():.1f}% of games played have more than 0.5 expected touchdowns ({100 * (a.filter(c('snaps') >= 30)['xtd'] > 0.5).mean():.1f}% of games with 30+ snaps); 1.0 or more: {100 * (a['xtd'] >= 1).mean():.2f}%")
    sx = pg.group_by("gsis_id", "season", "position").agg(g=pl.len(), xtd=c("xtd").mean(), td=c("td").mean()).filter(c("g") >= 8)
    print(f"  Player-seasons (8+ games) averaging more than 0.5 expected touchdowns a game: {sx.filter(c('xtd') > 0.5).height} of {sx.height} ({sx.filter(c('xtd') > 0.5).group_by('position').len().sort('position').rows()}); more than 0.5 actual: {sx.filter(c('td') > 0.5).height}")
    print("  How many chances before a player's own rate is worth as much as the league's (half own record, half league):")
    for q_, k in (("RB", "carry"), ("WR", "target"), ("TE", "target"), ("QB", "carry"), ("RB", "target")):
        t = ch.filter((c("position") == q_) & (c("kind") == k) & (c("season") >= 2012)).group_by("gsis_id").agg(
            n=pl.len().cast(pl.Float64), td=c("td").sum(), xtd=c("xtd").sum(), v=(c("xtd") * (1 - c("xtd"))).sum()
        ).filter(c("n") >= 100)  # fmt: skip
        n, pbar = t["n"].to_numpy(), t["td"].sum() / t["n"].sum()
        rate_ = t["td"].to_numpy() / n
        var_true = max(np.average((rate_ - pbar) ** 2, weights=n) - np.average(pbar * (1 - pbar) / n, weights=n), 1e-9)
        oe = (t["td"].to_numpy() - t["xtd"].to_numpy()) / n
        samp = t["v"].to_numpy() / n**2
        var_oe = np.average(oe**2, weights=n) - np.average(samp, weights=n)
        k_oe = (t["v"].sum() / t["n"].sum()) / var_oe if var_oe > 0 else float("inf")
        print(f"    {q_} {k}s ({t.height} players with 100+ since 2012): raw touchdown rate {pbar * (1 - pbar) / var_true:,.0f} {k}s (true spread between players {100 * math.sqrt(var_true):.2f} points around {100 * pbar:.2f}%); rate over expected {k_oe:,.0f} {k}s (true spread {100 * math.sqrt(max(var_oe, 0)):.2f} points)")

    # ------------------------------------------------------------ team level
    tg, dg = team_games(p, "posteam"), team_games(p, "defteam")
    h = halves(tg, c("week") <= 9)
    oe_ = halves(tg, c("week") % 2 == 1)
    log("team tables", tg.height)

    print("\n== Q1: RED-ZONE EFFICIENCY FROM THE SPREAD OF PAST RED-ZONE PLAYS ==")
    print(f"Team half-seasons 2006-2024: {h.height}. Red-zone trips a half {tg.filter(c('week') <= 9).group_by('team', 'season').agg(c('rz_trips').sum())['rz_trips'].mean():.1f}; touchdown rate per trip {tg['rz_tds'].sum() / tg['rz_trips'].sum():.3f}")
    NM = {"rz_td_rate": "red-zone touchdown rate", "rz_ypp": "red-zone yards a play", "rz_y_sd": "spread of red-zone yards a play",
          "rz_epa_p": "red-zone EPA a play", "rz_epa_sd": "spread of red-zone EPA a play", "rz_succ_p": "red-zone success rate",
          "epa_p": "EPA a play, whole field", "succ_p": "success rate, whole field", "expl_rate": "explosive-play rate, whole field",
          "t3": "third-down conversion rate", "rz_trips_g": "red-zone trips a game", "pass10_rate": "pass share inside the 10",
          "pass_rate": "pass share", "proe": "pass rate over expected", "sg_rate": "shotgun rate", "nh_rate": "no-huddle rate",
          "rush_td_share": "rushing share of touchdowns", "td_g": "touchdowns a game"}  # fmt: skip
    print("  first half against the second half's red-zone touchdown rate | repeats with itself (first to second half; odd to even weeks)")
    for k in ("rz_td_rate", "rz_ypp", "rz_y_sd", "rz_epa_p", "rz_epa_sd", "rz_succ_p", "epa_p", "succ_p", "expl_rate", "t3", "rz_trips_g"):
        print(f"    {NM[k]:36s} {cf(h[k], h['rz_td_rate_2'])} | {cf(h[k], h[k + '_2'])}; {cf(oe_[k], oe_[k + '_2'])}")
    ctl = [h["rz_td_rate"].to_numpy(), h["rz_ypp"].to_numpy()]
    print(f"  The spread, beyond the half's own touchdown rate and yards a play: yards {partial(h['rz_y_sd'].to_numpy(), h['rz_td_rate_2'].to_numpy(), ctl)}; EPA {partial(h['rz_epa_sd'].to_numpy(), h['rz_td_rate_2'].to_numpy(), ctl)}")
    print(f"  ... and beyond whole-field EPA a play too: yards {partial(h['rz_y_sd'].to_numpy(), h['rz_td_rate_2'].to_numpy(), [*ctl, h['epa_p'].to_numpy()])}; EPA {partial(h['rz_epa_sd'].to_numpy(), h['rz_td_rate_2'].to_numpy(), [*ctl, h['epa_p'].to_numpy()])}")
    for nm, fs in (("past red-zone touchdown rate", ["rz_td_rate"]), ("+ the spread (yards and EPA)", ["rz_td_rate", "rz_y_sd", "rz_epa_sd"]),
                   ("whole-field EPA a play", ["epa_p"]), ("whole-field EPA + red-zone rate", ["epa_p", "rz_td_rate"]),
                   ("whole-field EPA + red-zone rate + the spread", ["epa_p", "rz_td_rate", "rz_y_sd", "rz_epa_sd"])):  # fmt: skip
        print(f"    second-half red-zone touchdown rate, leave one season out, from {nm}: {loso(h, fs, 'rz_td_rate_2'):.2f}%")
    # season to season
    full_s = rates(tg.group_by("team", "season").agg(c(SUMS).sum())).select("team", "season", *RATES)
    s2t = full_s.join(full_s.with_columns(c("season") - 1), on=["team", "season"], suffix="_n")
    print(f"  season to season: red-zone touchdown rate {cf(s2t['rz_td_rate'], s2t['rz_td_rate_n'])}; whole-field EPA {cf(s2t['epa_p'], s2t['epa_p_n'])}; spread of red-zone yards {cf(s2t['rz_y_sd'], s2t['rz_y_sd_n'])}")

    print("\n== Q2: TOUCHDOWN OR FIELD GOAL ==")
    rz = c("yardline_100") <= 20
    dr = p.group_by("game_id", "season", "week", "posteam", "defteam", "fixed_drive").agg(rz=rz.any(), res=c("fixed_drive_result").first(), first=c("yardline_100").filter(rz).first()).filter(c("rz"))
    dr = dr.join(before(tg, "o_"), left_on=["game_id", "posteam"], right_on=["game_id", "team"]).join(before(dg, "d_"), left_on=["game_id", "defteam"], right_on=["game_id", "team"])
    dr = dr.with_columns(td=(c("res") == "Touchdown").cast(pl.Float64), blk=c("season").cast(pl.String) + "_" + c("week").cast(pl.String)).sort("season", "week", "game_id")
    print(f"Red-zone trips from each team's 4th game on, 2006-2024: {dr.height:,}; touchdown {100 * dr['td'].mean():.1f}%, field goal tried {100 * dr['res'].is_in(['Field goal', 'Missed field goal']).mean():.1f}%, neither {100 * (~dr['res'].is_in(['Touchdown', 'Field goal', 'Missed field goal'])).mean():.1f}%")
    sets = {
        "the offense's red-zone history (touchdown rate, EPA, success, yards)": ["o_rz_td_rate", "o_rz_epa_p", "o_rz_succ_p", "o_rz_ypp"],
        "the offense everywhere (EPA, success, explosive rate, third downs)": ["o_epa_p", "o_succ_p", "o_expl_rate", "o_t3"],
        "both": ["o_rz_td_rate", "o_rz_epa_p", "o_rz_succ_p", "o_rz_ypp", "o_epa_p", "o_succ_p", "o_expl_rate", "o_t3"],
        "the defense (EPA allowed, red-zone touchdown rate allowed, success allowed)": ["d_epa_p", "d_rz_td_rate", "d_succ_p", "d_rz_epa_p"],
        "the offense's tendencies (pass share, inside the 10, over expected, shotgun)": ["o_pass_rate", "o_pass10_rate", "o_proe", "o_sg_rate"],
        "the spread of the offense's red-zone plays": ["o_rz_y_sd", "o_rz_epa_sd"],
    }
    sets["everything"] = sorted({f for v in sets.values() for f in v})
    for nm, d_ in (("every red-zone trip", dr), ("trips that ended in a touchdown or a field-goal try", dr.filter(c("res").is_in(["Touchdown", "Field goal", "Missed field goal"])))):
        bs = rate(d_, "td", 2006)
        print(f"  {nm} (scored 2019-2024: {d_.filter(c('season') >= 2019).height:,}, touchdown {100 * d_.filter(c('season') >= 2019)['td'].mean():.1f}%):")
        pr = {k: walk(d_, v, "td", 2006) for k, v in sets.items()}
        for k in sets:
            print(f"    {k}: {gain(d_, pr[k], bs, 'td')}")
        print(f"    red-zone history beyond the offense everywhere: {gain(d_, pr['both'], pr['the offense everywhere (EPA, success, explosive rate, third downs)'], 'td')}")
        for f in ("o_epa_p", "o_rz_td_rate", "o_succ_p", "o_t3", "o_expl_rate", "d_epa_p", "d_rz_td_rate", "o_pass10_rate", "o_rz_y_sd"):
            print(f"      {f}: correlation with a touchdown {cf(d_[f], d_['td'])}")
    log("drives")

    # ------------------------------------------------------------ H67
    print("\n== H67: IS ALLOCATION TIED TO SCHEME AND PLAY CALLING ==")
    TEND = ["pass10_rate", "pass_rate", "proe", "sg_rate", "nh_rate"]
    print("(a) Team half-seasons: first-half tendencies against the second half's rushing share of touchdowns | each repeats (first to second half)")
    for k in [*TEND, "rush_td_share", "epa_p"]:
        print(f"    {NM[k]:30s} {cf(h[k], h['rush_td_share_2'])} | {cf(h[k], h[k + '_2'])}")
    for nm, fs in (("the tendencies", TEND), ("the past rushing share of touchdowns", ["rush_td_share"]), ("both", [*TEND, "rush_td_share"]), ("both + EPA a play", [*TEND, "rush_td_share", "epa_p"])):
        print(f"    second-half rushing share of touchdowns, leave one season out, from {nm}: {loso(h, fs, 'rush_td_share_2'):.2f}%")
    print(f"    (a half-season has {(tg.filter(c('week') > 9).group_by('team', 'season').agg((c('rush_td') + c('pass_td')).sum())['rush_td'].mean()):.1f} touchdowns, so the share is noisy: its dice-only spread is about {100 * math.sqrt(0.36 * 0.64 / 18):.0f} points against an actual {100 * h['rush_td_share_2'].std():.0f})")
    # shares by position
    pt = ch.with_columns(half=(c("week") > 9).cast(pl.Int8)).group_by("posteam", "season", "half").agg(
        *[c("td").filter(c("position") == q_).sum().alias(q_) for q_ in POS], tot=c("td").sum()
    ).with_columns(*[(c(q_) / c("tot")).alias(f"sh_{q_}") for q_ in POS]).rename({"posteam": "team"})  # fmt: skip
    hp = h.join(pt.filter(c("half") == 0).select("team", "season", *[f"sh_{q_}" for q_ in POS]), on=["team", "season"]).join(
        pt.filter(c("half") == 1).select("team", "season", *[c(f"sh_{q_}").alias(f"sh2_{q_}") for q_ in POS]), on=["team", "season"])  # fmt: skip
    print("    Each position's share of the team's rushing + receiving touchdowns, second half (2012-2024), leave one season out:")
    for q_ in POS:
        print(f"      {q_} (mean {100 * hp[f'sh2_{q_}'].mean():.0f}%): from the tendencies {loso(hp, TEND, f'sh2_{q_}'):.2f}%; from the position's past share {loso(hp, [f'sh_{q_}'], f'sh2_{q_}'):.2f}%; both {loso(hp, [*TEND, f'sh_{q_}'], f'sh2_{q_}'):.2f}%; the share repeats {cf(hp[f'sh_{q_}'], hp[f'sh2_{q_}'])}; pass share inside the 10 against it {cf(hp['pass10_rate'], hp[f'sh2_{q_}'])}")
    # (b) player level
    tc = pl.concat([
        rates(tg.filter(c("week") <= cut).group_by("team", "season").agg(c(SUMS).sum())).select("team", "season", *[c(k).alias("t_" + k) for k in RATES]).with_columns(cut=pl.lit(float(cut)))
        for cut in CUTS
    ])  # fmt: skip
    df2 = df.join(tc, on=["team", "season", "cut"], how="left").sort("season", "cut", "gsis_id")
    assert (df2["gsis_id"] == df["gsis_id"]).all()
    T_TEND = ["t_" + k for k in TEND]
    T_QUAL = ["t_epa_p", "t_rz_trips_g", "t_td_g", "t_rz_td_rate"]
    own = BASE + F(*ALL)
    p_own = walk(df2, own, y)
    p_t = walk(df2, own + T_TEND, y)
    p_q = walk(df2, own + T_QUAL, y)
    p_tq = walk(df2, own + T_QUAL + T_TEND, y)
    print("(b) A player's rest-of-season touchdowns:")
    print(f"    his own 14 measures {r2(df2, p_own, base, y):.2f}%")
    print(f"    + his team's tendencies so far (pass share, inside the 10, over expected, shotgun, no huddle): {gain(df2, p_t, p_own, y)}")
    print(f"    + his team's offense so far (EPA a play, red-zone trips, touchdowns a game, red-zone touchdown rate): {gain(df2, p_q, p_own, y)}")
    print(f"    + tendencies beyond both: {gain(df2, p_tq, p_q, y)}")
    for q_ in POS:
        print(f"      {q_}: tendencies {gain(df2, p_t, p_own, y, pos_m[q_])}; offense quality {gain(df2, p_q, p_own, y, pos_m[q_])}")
    p_pos = walk(df2, BASE + F("n", "snaps"), y)
    p_pos_t = walk(df2, BASE + F("n", "snaps") + T_TEND, y)
    print(f"    Knowing only his position, chances and snaps: {r2(df2, p_pos, base, y):.2f}%; + tendencies {gain(df2, p_pos_t, p_pos, y)}")
    # share of own xtd from targets vs the team's pass share inside the 10: is the player's red-zone role tied to scheme?
    rb = df2.filter((c("position") == "RB") & (c("cut") == 8))
    wr = df2.filter(c("position").is_in(["WR", "TE"]) & (c("cut") == 8))
    print(f"    After week 8: an RB's carries inside the 5 a game against his team's pass share inside the 10 {cf(rb['gl_s'], rb['t_pass10_rate'])}; a WR or TE's end-zone targets a game against it {cf(wr['ez_tgt_s'], wr['t_pass10_rate'])}; their later touchdowns against it: RB {cf(rb['t_pass10_rate'], rb['y'])}, WR and TE {cf(wr['t_pass10_rate'], wr['y'])}")
    log("done")


if __name__ == "__main__":
    main()
