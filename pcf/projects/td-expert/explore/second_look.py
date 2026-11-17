# ruff: noqa: E501, B026
"""td-expert, second look (2026-11-17). The scope the CEO added on 2026-11-17 (next game, teams,
passing touchdowns), the CEO's two ideas (the noisiness of a touchdown, ahead and looking back; how
close a field-goal drive came to a touchdown) and whether method C can work.

Same chances and expected touchdowns (xtd) as first_look.py: chances from 2009, xtd fit on earlier
seasons only, so 2012-2024 have them; forecasts walk forward, fit 2012..s-1, scored 2019-2024.

- Next game: each game a player (team) played, from his season so far (2+ earlier games) and last
  season. Whether he plays is taken as known (availability is another expert's job).
- Team touchdowns: rushing + receiving touchdowns scored by its QBs, RBs, WRs and TEs (nearly all
  offensive touchdowns). Opponent: the touchdowns it allowed so far.
- Passing touchdowns: a QB's thrown touchdowns = touchdowns on targets he threw (the target's xtd
  is the throw's xtd).
- Near miss: for a drive that ended in a field-goal try, the chance that at least one of its
  chances scores, 1 - product(1 - xtd).

Run from pcf/:  python projects/td-expert/explore/second_look.py > projects/td-expert/explore/second_look.txt
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).parent))
import first_look as fl  # noqa: E402

c, cf, gain, log, r2, rate, walk, F = fl.c, fl.cf, fl.gain, fl.log, fl.r2, fl.rate, fl.walk, fl.F
POS, CUTS = fl.POS, fl.CUTS


# ---------------------------------------------------------------- generic rows
def next_rows(gt: pl.DataFrame, key: str, cols: list[str]) -> pl.DataFrame:
    """Each game with the season-so-far average of every column (earlier games only) and last season's."""
    gt = gt.sort(key, "season", "week")
    k = pl.int_range(pl.len()).over(key, "season").cast(pl.Float64)
    s = gt.with_columns(
        g_s=k, *[((c(x).cum_sum().over(key, "season") - c(x)) / k).alias(f"{x}_s") for x in cols]
    ).filter(c("g_s") >= 2)
    last = (
        gt.group_by(key, "season")
        .agg(*[c(x).mean().alias(f"{x}_ls") for x in cols])
        .with_columns(c("season") + 1)
    )
    return s.join(last, on=[key, "season"], how="left")


def rest_rows(gt: pl.DataFrame, key: str, cols: list[str], ys: list[str], keep=()) -> pl.DataFrame:
    """After weeks 4, 8, 12: season-so-far averages, then the sums of ys over the games left."""
    out = []
    for cut in CUTS:
        a = gt.filter(c("week") <= cut).sort("week").group_by(key, "season").agg(
            g_s=pl.len().cast(pl.Float64), *[c(x).last() for x in keep], *[c(x).mean().alias(f"{x}_s") for x in cols]
        )  # fmt: skip
        b = (
            gt.filter(c("week") > cut)
            .group_by(key, "season")
            .agg(*[c(y).sum().alias(f"{y}_after") for y in ys], g_after=pl.len().cast(pl.Float64))
        )
        out.append(a.join(b, on=[key, "season"]).with_columns(cut=pl.lit(float(cut))))
    df = pl.concat(out).filter(c("g_s") >= 2)
    last = (
        gt.group_by(key, "season")
        .agg(*[c(x).mean().alias(f"{x}_ls") for x in cols])
        .with_columns(c("season") + 1)
    )
    return df.join(last, on=[key, "season"], how="left").sort("season", "cut", key)


def ceiling(df, feats, y, yx, label, masks=None, dv=None, yx2=None) -> np.ndarray:
    """Games so far against the plain mean, fitting noise, hindsight and the dice share."""
    base, yy, test = rate(df, y), df[y].to_numpy().astype(float), df["season"].to_numpy() >= 2019
    full = walk(df, feats, y)
    hx = df[yx].to_numpy().astype(float)
    refit = [r2(df, walk(df, feats, y, resample=i), base, y) for i in (1, 2)]
    mse = ((base - yy)[test] ** 2).mean()
    print(
        f"{label}: n {int(test.sum()):,} scored, mean {yy[test].mean():.3f}, sd {yy[test].std():.3f}"
    )
    print(
        f"  so far removes {gain(df, full, base, y)}; refits {', '.join(f'{v:.2f}' for v in refit)}"
    )
    print(
        f"  hindsight, knowing every chance (its xtd): {gain(df, hx, base, y)}; luck left {100 * ((hx - yy)[test] ** 2).mean() / mse:.1f}% (pure dice on those chances {100 * df[dv].to_numpy()[test].mean() / mse:.1f}%)"
    )
    if yx2 is not None:
        print(
            f"  hindsight, knowing only where each drive started (drive model): {gain(df, df[yx2].to_numpy().astype(float), base, y)}"
        )
    for nm, m in (masks or {}).items():
        print(
            f"    {nm}: so far {r2(df, full, base, y, m):.1f}%, hindsight {r2(df, hx, base, y, m):.1f}%"
        )
    return full


DRIVE = [
    "yardline_100",
    "down",
    "ydstogo",
    "goal_to_go",
    "qtr",
    "half_seconds_remaining",
    "score_differential",
]


def drive_prob(p: pl.DataFrame) -> pl.DataFrame:
    """Each play's chance that its drive ends in a touchdown, from the state before the snap; fit on earlier seasons."""
    d = (
        p.filter(c("fixed_drive").is_not_null() & c("fixed_drive_result").is_not_null())
        .sort("game_id", "play_id")
        .with_columns(dtd=(c("fixed_drive_result") == "Touchdown").cast(pl.Int8))
    )
    x, y, season = (
        d.select(DRIVE).to_numpy().astype(float),
        d["dtd"].to_numpy(),
        d["season"].to_numpy(),
    )
    out = np.full(d.height, np.nan)
    for s in range(2012, 2025):
        tr, te = season < s, season == s
        m = HistGradientBoostingClassifier(
            max_iter=200,
            learning_rate=0.06,
            max_leaf_nodes=31,
            min_samples_leaf=200,
            random_state=0,
        ).fit(x[tr], y[tr])
        out[te] = m.predict_proba(x[te])[:, 1]
    log("drive model")
    return d.with_columns(dp=pl.Series(out)).filter(c("season") >= 2012)


def main() -> None:
    src = fl.Gateway().source
    p = fl.plays(src)
    ch = fl.expected(fl.chances(p, src))
    passer = (
        src.part("play", "pbp")
        .lazy()
        .filter(c("season").is_between(2012, 2024))
        .select("game_id", "play_id", "passer_player_id")
        .collect()
    )
    drv = p.select("game_id", "play_id", "fixed_drive", "fixed_drive_result", "defteam")
    ch = ch.join(passer, on=["game_id", "play_id"], how="left").join(
        drv, on=["game_id", "play_id"], how="left"
    )
    ch = ch.with_columns(
        v=c("xtd") * (1 - c("xtd")), hi=pl.when(c("xtd") >= 0.3).then(c("xtd")).otherwise(0.0)
    )
    pg = (
        fl.player_games(src, ch)
        .join(
            ch.group_by("gsis_id", "game_id").agg(c("v").sum(), c("hi").sum()),
            on=["gsis_id", "game_id"],
            how="left",
        )
        .with_columns(c("v", "hi").fill_null(0.0))
    )
    log("loaded", ch.height, pg.height)
    pos_cols = [(c("position") == q).cast(pl.Float64).alias(f"is_{q.lower()}") for q in POS]
    B = ["week", "is_qb", "is_rb", "is_wr", "is_te"]

    # ============================================================ S-1 next game, players
    print("== S-1: NEXT GAME, A PLAYER'S RUSHING + RECEIVING TOUCHDOWNS ==")
    COLS = [*fl.PG, "v", "hi"]
    ng = (
        next_rows(pg, "gsis_id", COLS)
        .filter(c("n_s") >= 2)
        .with_columns(*pos_cols, blk=c("season").cast(pl.String) + c("team"))
        .sort("season", "week", "gsis_id")
    )
    ALL = [
        "td",
        "xtd",
        "n",
        "tgt",
        "car",
        "yards",
        "air",
        "rz20",
        "in10",
        "gl",
        "ez_tgt",
        "expl",
        "snaps",
    ]
    pm = {q: ng["position"].to_numpy() == q for q in POS}
    full = ceiling(ng, B + F(*ALL), "td", "xtd", "Next game", pm, dv="v")
    base = rate(ng, "td")
    sing = {
        k: r2(ng, walk(ng, B + F(k), "td"), base, "td")
        for k in ("td", "xtd", "n", "yards", "snaps", "rz20", "in10")
    }
    print(
        "  single predictors: "
        + "; ".join(f"{k} {v:.2f}%" for k, v in sorted(sing.items(), key=lambda kv: -kv[1]))
    )
    log("S-1")

    # ============================================================ I-a noisiness ahead
    print("\n== I-a (ahead): THE CHANCE OF 0, 1, 2+ TOUCHDOWNS NEXT GAME ==")
    yy, season = ng["td"].to_numpy(), ng["season"].to_numpy()
    mu = np.clip(full, 0.005, None)
    t = season >= 2019
    p0, p1 = np.exp(-mu), mu * np.exp(-mu)
    pois = np.column_stack([p0, p1, 1 - p0 - p1])
    cls = np.minimum(yy, 2).astype(int)
    print(
        f"  Poisson around the forecast: chance of 1+ says {100 * (1 - p0[t]).mean():.1f}%, actual {100 * (yy[t] >= 1).mean():.1f}%; 2+ says {100 * pois[t, 2].mean():.2f}%, actual {100 * (yy[t] >= 2).mean():.2f}%"
    )
    q = np.quantile(1 - p0[t], np.linspace(0, 1, 11))
    b = np.clip(np.searchsorted(q, 1 - p0, side="right") - 1, 0, 9)
    print(
        "  by tenth of the chance of 1+ (says, actual): "
        + "; ".join(
            f"{100 * (1 - p0[t & (b == i)]).mean():.0f} {100 * (yy[t & (b == i)] >= 1).mean():.0f}"
            for i in range(10)
        )
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        conc = np.nan_to_num(ng["hi_s"].to_numpy() / ng["xtd_s"].to_numpy())
        disp = np.nan_to_num(ng["v_s"].to_numpy() / ng["xtd_s"].to_numpy())
        perch = np.nan_to_num(ng["xtd_s"].to_numpy() / ng["n_s"].to_numpy())

    def ll(pr, m):
        return -np.log(np.clip(pr[m, cls[m]], 1e-9, None)).mean()

    out = {"mu": np.full((len(yy), 3), np.nan), "mu+conc": np.full((len(yy), 3), np.nan)}
    lmu = np.log(mu)
    for nm, x in (
        ("mu", lmu[:, None]),
        (
            "mu+conc",
            np.column_stack(
                [lmu, conc, disp, perch, ng["is_rb"].to_numpy(), ng["is_qb"].to_numpy()]
            ),
        ),
    ):
        for s in range(2020, 2025):
            tr, te = (season >= 2019) & (season < s), season == s
            m = LogisticRegression(C=1.0, max_iter=2000).fit(x[tr], cls[tr])
            out[nm][te] = m.predict_proba(x[te])
    t2 = season >= 2020
    lp, lm, lc = ll(pois, t2), ll(out["mu"], t2), ll(out["mu+conc"], t2)
    print(
        f"  log loss of 0/1/2+, 2020-2024: Poisson around the forecast {lp:.4f}; fitted on the forecast alone {lm:.4f}; + how concentrated his chances are {lc:.4f} ({100 * (1 - lc / lm):+.2f}% against the forecast alone)"
    )
    for q_ in POS:
        m = t2 & pm[q_]
        print(
            f"    {q_}: Poisson {ll(pois, m):.4f}, forecast alone {ll(out['mu'], m):.4f}, + concentration {ll(out['mu+conc'], m):.4f}; chance of 1+ says {100 * (1 - p0[m]).mean():.1f}%, actual {100 * (yy[m] >= 1).mean():.1f}%"
        )
    log("I-a ahead")

    # ============================================================ I-a noisiness looking back
    print("\n== I-a (looking back): HOW MUCH OF A STRETCH'S TOUCHDOWNS WAS LUCK ==")
    ps = (
        pg.group_by("gsis_id", "season")
        .agg(
            position=c("position").last(),
            g=pl.len(),
            td=c("td").sum(),
            xtd=c("xtd").sum(),
            v=c("v").sum(),
        )
        .filter(c("xtd") >= 2)
    )
    z = ((ps["td"] - ps["xtd"]) / ps["v"].sqrt()).to_numpy()
    print(
        f"  Player-seasons with 2+ expected touchdowns: {ps.height:,}. Touchdowns minus expected, in units of the dice's spread: beyond 2 either way {100 * (np.abs(z) > 1.96).mean():.1f}% (pure dice and a right xtd: 5%); spread {z.std():.2f} (dice: 1.00)"
    )
    for q_ in POS:
        zq = z[ps["position"].to_numpy() == q_]
        print(
            f"    {q_}: n {len(zq)}, beyond 2: {100 * (np.abs(zq) > 1.96).mean():.1f}%, spread {zq.std():.2f}"
        )
    vt, vx, mv = ps["td"].var(), ps["xtd"].var(), ps["v"].mean()
    print(
        f"  Across player-seasons, touchdowns vary {vt:.2f} (squared); the dice add {mv:.2f} of it: {100 * mv / vt:.0f}% of the spread in a season's touchdowns is luck; expected touchdowns vary {vx:.2f}"
    )
    for lo, hi in ((2, 4), (4, 7), (7, 99)):
        m = ((ps["xtd"] >= lo) & (ps["xtd"] < hi)).to_numpy()
        print(
            f"    expected {lo} to {hi}: n {m.sum()}, luck share of the spread {100 * ps['v'].to_numpy()[m].mean() / ps['td'].to_numpy()[m].var():.0f}%, a 90% range around the expected: +/- {1.645 * np.sqrt(ps['v'].to_numpy()[m].mean()):.1f} touchdowns"
        )
    g1 = pg.filter(c("n") > 0)
    tail = 1 - np.array(
        [
            sum(np.exp(-x) * x**k / math.factorial(k) for k in range(int(t_)))
            for x, t_ in zip(g1["xtd"].to_numpy(), g1["td"].to_numpy(), strict=True)
        ]
    )
    sc = g1["td"].to_numpy() >= 1
    print(
        f"  Single games with a touchdown ({sc.sum():,}): the chance of scoring at least that many, from that game's chances (Poisson): median {np.median(tail[sc]):.2f}; under 10% for {100 * (tail[sc] < 0.1).mean():.0f}% of them"
    )
    log("I-a back")

    # ============================================================ I-b near misses
    print("\n== I-b: HOW CLOSE A FIELD-GOAL DRIVE CAME TO A TOUCHDOWN ==")
    d = ch.group_by("game_id", "season", "week", "posteam", "fixed_drive").agg(
        res=c("fixed_drive_result").first(), p_any=1 - (1 - c("xtd")).product(), sx=c("xtd").sum(),
        best=c("xtd").max(), td=c("td").max(), rz=(c("yardline_100") <= 20).any(), n=pl.len(),
    )  # fmt: skip
    d = d.with_columns(fg=c("res").is_in(["Field goal", "Missed field goal"]))
    print(
        f"  Drives with a chance 2012-2024: {d.height:,}. Is 'chance of a touchdown' right? by tenth (says, a chance on it scored):"
    )
    print(
        "    "
        + "; ".join(
            f"{100 * r['p_any']:.0f} {100 * r['td']:.0f}"
            for r in d.with_columns(b=(c("p_any") * 10).floor().clip(0, 9))
            .group_by("b")
            .agg(c("p_any").mean(), c("td").mean())
            .sort("b")
            .iter_rows(named=True)
        )
    )
    for nm, m in (
        ("field-goal drives", c("fg")),
        ("field-goal drives that reached the 20", c("fg") & c("rz")),
        ("touchdown drives", c("res") == "Touchdown"),
        ("other drives (punts, turnovers, downs, clock)", ~c("fg") & (c("res") != "Touchdown")),
    ):
        x = d.filter(m)
        qq = x["p_any"].quantile
        print(
            f"  {nm}: {x.height:,}; chance of a touchdown {100 * x['p_any'].mean():.1f}% (quartiles {100 * qq(0.25):.0f}, {100 * qq(0.5):.0f}, {100 * qq(0.75):.0f}); 50%+ for {100 * (x['p_any'] >= 0.5).mean():.0f}%; best single chance {100 * x['best'].mean():.1f}%"
        )
    print(
        "  (the chance-based number is too high near the goal line: a drive that fails at the 1 gets four chances there, so the drive model below measures it instead)"
    )
    dp = drive_prob(p)
    dd = dp.group_by("game_id", "season", "week", "posteam", "fixed_drive").agg(
        res=c("fixed_drive_result").first(), start=c("dp").first(), peak=c("dp").max(), rz=(c("yardline_100") <= 20).any(), dtd=c("dtd").first()
    ).with_columns(fg=c("res").is_in(["Field goal", "Missed field goal"]))  # fmt: skip
    print(
        f"  Drive model, 2012-2024 ({dd.height:,} drives): chance of a touchdown at the drive's start by tenth (says, actual): "
        + "; ".join(
            f"{100 * r['start']:.0f} {100 * r['dtd']:.0f}"
            for r in dd.with_columns(b=(c("start") * 10).floor().clip(0, 9))
            .group_by("b")
            .agg(c("start").mean(), c("dtd").mean())
            .sort("b")
            .iter_rows(named=True)
        )
    )
    for nm, m in (
        ("field-goal drives", c("fg")),
        ("field-goal drives that reached the 20", c("fg") & c("rz")),
        ("touchdown drives", c("res") == "Touchdown"),
        ("other drives", ~c("fg") & (c("res") != "Touchdown")),
    ):
        x = dd.filter(m)
        qq = x["peak"].quantile
        print(
            f"  {nm}: {x.height:,}; the closest it came (the drive's highest chance of a touchdown before a snap) {100 * x['peak'].mean():.1f}% (quartiles {100 * qq(0.25):.0f}, {100 * qq(0.5):.0f}, {100 * qq(0.75):.0f}); 50%+ for {100 * (x['peak'] >= 0.5).mean():.0f}%, 70%+ for {100 * (x['peak'] >= 0.7).mean():.0f}%; at its start {100 * x['start'].mean():.1f}%"
        )
    fgd = (
        dd.filter(c("fg"))
        .group_by("game_id", "posteam")
        .agg(nm=c("peak").sum(), n_fg=pl.len().cast(pl.Float64))
    )
    dst = dd.group_by("game_id", "posteam").agg(
        dstart=c("start").sum(), dvar=(c("start") * (1 - c("start"))).sum()
    )
    gm = p.select("game_id", "season", "week", "posteam", "defteam").unique(["game_id", "posteam"])
    tt = (
        ch.group_by("game_id", "posteam").agg(ttd=c("td").sum(), txtd=c("xtd").sum(), tv=c("v").sum())
        .join(gm, on=["game_id", "posteam"]).join(fgd, on=["game_id", "posteam"], how="left").with_columns(c("nm", "n_fg").fill_null(0.0)).join(dst, on=["game_id", "posteam"], how="left")
    )  # fmt: skip
    tg = fl.team_games(p.filter(c("season") >= 2012), "posteam").select(
        "game_id", "team", "epa", "n", "rz_trips", "rz_tds", "db"
    )
    tt = tt.join(tg, left_on=["game_id", "posteam"], right_on=["game_id", "team"]).rename(
        {"posteam": "team"}
    )
    tt = tt.with_columns(nm_fg=pl.when(c("n_fg") > 0).then(c("nm") / c("n_fg")))
    # consistency: halves and seasons
    hh = [
        tt.filter(m)
        .group_by("team", "season")
        .agg(
            nm=c("nm").mean(),
            fgsum=c("nm").sum(),
            nfg=c("n_fg").sum(),
            ttd=c("ttd").mean(),
            txtd=c("txtd").mean(),
        )
        for m in (c("week") <= 9, c("week") > 9)
    ]
    hj = (
        hh[0]
        .join(hh[1], on=["team", "season"], suffix="_2")
        .with_columns(per=c("fgsum") / c("nfg"), per_2=c("fgsum_2") / c("nfg_2"))
    )
    ss = tt.group_by("team", "season").agg(nm=c("nm").mean(), per=c("nm").sum() / c("n_fg").sum())
    s2 = ss.join(ss.with_columns(c("season") - 1), on=["team", "season"], suffix="_n")
    print(
        f"  Consistency (team half-seasons, n {hj.height}): near misses a game repeat {cf(hj['nm'], hj['nm_2'])}; near-miss chance per field-goal drive {cf(hj['per'], hj['per_2'])}; season to season {cf(s2['nm'], s2['nm_n'])} and {cf(s2['per'], s2['per_n'])}"
    )
    print(
        f"    first-half near misses a game against the second half's touchdowns a game {cf(hj['nm'], hj['ttd_2'])}; beyond first-half touchdowns and expected touchdowns {fl.partial(hj['nm'].to_numpy(), hj['ttd_2'].to_numpy(), [hj['ttd'].to_numpy(), hj['txtd'].to_numpy()])}"
    )
    log("I-b")

    # ============================================================ S-2 teams
    print("\n== S-2: A TEAM'S TOUCHDOWNS ==")
    TC = ["ttd", "txtd", "tv", "nm", "n_fg", "epa", "n", "rz_trips", "rz_tds", "db"]
    allowed = next_rows(
        tt.rename({"team": "off", "defteam": "team"}), "team", ["ttd", "txtd"]
    ).select("game_id", c("team").alias("defteam"), a_ttd=c("ttd_s"), a_txtd=c("txtd_s"))
    tn = (
        next_rows(tt, "team", TC)
        .join(allowed, on=["game_id", "defteam"], how="left")
        .with_columns(blk=c("season").cast(pl.String) + c("team"))
        .sort("season", "week", "team")
    )
    TB = ["week", "a_ttd", "a_txtd"]
    TF = ["ttd", "txtd", "epa", "n", "rz_trips", "rz_tds", "db", "n_fg"]
    tfull = ceiling(tn, TB + F(*TF), "ttd", "txtd", "Next game, team", dv="tv", yx2="dstart")
    tnm = walk(tn, TB + F(*TF, "nm"), "ttd")
    print(f"  + near misses so far: {gain(tn, tnm, tfull, 'ttd')}")
    tno = walk(tn, ["week"] + F(*TF), "ttd")
    print(f"  the opponent's touchdowns allowed so far add {gain(tn, tfull, tno, 'ttd')}")
    tr_ = rest_rows(tt, "team", TC, ["ttd", "txtd", "tv", "dstart"]).with_columns(
        y=c("ttd_after") / c("g_after"),
        yx=c("txtd_after") / c("g_after"),
        yv=c("tv_after") / c("g_after") ** 2,
        yd=c("dstart_after") / c("g_after"),
        blk=c("season").cast(pl.String) + c("team"),
    )
    rfull = ceiling(
        tr_,
        ["cut"] + F(*TF),
        "y",
        "yx",
        "Rest of season, team (touchdowns a game)",
        dv="yv",
        yx2="yd",
    )
    rnm = walk(tr_, ["cut"] + F(*TF, "nm"), "y")
    rtx = walk(tr_, ["cut"] + F("ttd", "txtd"), "y")
    rtxn = walk(tr_, ["cut"] + F("ttd", "txtd", "nm"), "y")
    rb = rate(tr_, "y")
    print(
        f"  + near misses so far: {gain(tr_, rnm, rfull, 'y')}; from touchdowns and expected only {r2(tr_, rtx, rb, 'y'):.2f}%, + near misses {gain(tr_, rtxn, rtx, 'y')}"
    )
    print(
        f"  touchdowns alone {r2(tr_, walk(tr_, ['cut'] + F('ttd'), 'y'), rb, 'y'):.2f}%; expected alone {r2(tr_, walk(tr_, ['cut'] + F('txtd'), 'y'), rb, 'y'):.2f}%; EPA alone {r2(tr_, walk(tr_, ['cut'] + F('epa', 'n'), 'y'), rb, 'y'):.2f}%"
    )
    log("S-2")

    # ============================================================ S-3 passing touchdowns
    print("\n== S-3: A QUARTERBACK'S THROWN TOUCHDOWNS ==")
    th = ch.filter((c("kind") == "target") & c("passer_player_id").is_not_null()).group_by("passer_player_id", "game_id").agg(
        ptd=c("td").sum(), pxtd=c("xtd").sum(), att=pl.len().cast(pl.Float64), pyds=c("yards").sum(), pair=c("air").fill_null(0.0).sum(), pv=c("v").sum()
    )  # fmt: skip
    qg = (
        pg.filter(c("position") == "QB")
        .join(
            th, left_on=["gsis_id", "game_id"], right_on=["passer_player_id", "game_id"], how="left"
        )
        .with_columns(c("ptd", "pxtd", "att", "pyds", "pair", "pv").fill_null(0.0))
    )
    QC = ["ptd", "pxtd", "att", "pyds", "pair", "snaps", "td", "car"]
    qn = (
        next_rows(qg, "gsis_id", QC)
        .filter(c("att_s") >= 10)
        .with_columns(blk=c("season").cast(pl.String) + c("team"))
        .sort("season", "week", "gsis_id")
    )
    ceiling(qn, ["week"] + F(*QC), "ptd", "pxtd", "Next game, thrown touchdowns", dv="pv")
    qb_ = rate(qn, "ptd")
    print(
        "  single predictors: "
        + "; ".join(
            f"{k} {r2(qn, walk(qn, ['week'] + F(k), 'ptd'), qb_, 'ptd'):.2f}%"
            for k in ("ptd", "pxtd", "att", "pyds", "pair")
        )
    )
    qr = (
        rest_rows(qg, "gsis_id", QC, ["ptd", "pxtd", "pv"])
        .filter(c("att_s") >= 10)
        .with_columns(
            y=c("ptd_after"), yx=c("pxtd_after"), blk=c("season").cast(pl.String) + c("gsis_id")
        )
    )
    ceiling(qr, ["cut"] + F(*QC), "y", "yx", "Rest of season, thrown touchdowns", dv="pv_after")
    qrb = rate(qr, "y")
    sg = {k: walk(qr, ["cut"] + F(k), "y") for k in ("ptd", "pxtd", "att", "pyds")}
    print(
        "  single predictors: "
        + "; ".join(f"{k} {r2(qr, v, qrb, 'y'):.2f}%" for k, v in sg.items())
    )
    both = walk(qr, ["cut"] + F("ptd", "pxtd"), "y")
    print(
        f"  expected against actual {gain(qr, sg['pxtd'], sg['ptd'], 'y')}; past thrown touchdowns beyond expected {gain(qr, both, sg['pxtd'], 'y')}"
    )
    qs = qg.with_columns(h=c("week") % 2).group_by("gsis_id", "season").agg(
        att=c("att").sum(), *[c(k).filter(c("h") == i).sum().alias(f"{k}{i}") for k in ("ptd", "pxtd", "att", "pv") for i in (0, 1)]
    ).filter((c("att0") >= 100) & (c("att1") >= 100))  # fmt: skip
    oe = [((qs[f"ptd{i}"] - qs[f"pxtd{i}"]) / qs[f"att{i}"]).to_numpy() for i in (0, 1)]
    print(
        f"  Split halves (QB-seasons, 100+ throws each half, n {qs.height}): thrown touchdowns {cf(qs['ptd0'], qs['ptd1'])}; expected {cf(qs['pxtd0'], qs['pxtd1'])}; over expected per throw {cf(oe[0], oe[1])}"
    )
    qy = (
        qg.group_by("gsis_id", "season")
        .agg(att=c("att").sum(), ptd=c("ptd").sum(), pxtd=c("pxtd").sum(), pv=c("pv").sum())
        .filter(c("att") >= 200)
        .with_columns(oe=(c("ptd") - c("pxtd")) / c("att"))
    )
    q2 = qy.join(qy.with_columns(c("season") - 1), on=["gsis_id", "season"], suffix="_n")
    slope = np.polyfit(q2["oe"].to_numpy(), q2["oe_n"].to_numpy(), 1)[0]
    zq = ((qy["ptd"] - qy["pxtd"]) / qy["pv"].sqrt()).to_numpy()
    var_oe = np.average(qy["oe"].to_numpy() ** 2) - np.average(
        (qy["pv"] / qy["att"] ** 2).to_numpy()
    )
    print(
        f"  Season to season (200+ throws, n {q2.height}): over expected per throw repeats {cf(q2['oe'], q2['oe_n'])}, keeps {100 * slope:.0f}%. QB-seasons beyond 2 dice spreads: {100 * (np.abs(zq) > 1.96).mean():.1f}% (spread {zq.std():.2f}); throws to trust his own rate over expected {(qy['pv'].sum() / qy['att'].sum()) / var_oe:,.0f}"
        if var_oe > 0
        else "  no true spread over expected"
    )
    log("S-3")

    # ============================================================ S-4 can method C work
    print(
        "\n== S-4: METHOD C, DOES A PLAYER'S SHARE OF HIS TEAM'S CHANCES NEAR THE GOAL LINE REPEAT =="
    )
    team10 = ch.with_columns(h=(c("week") > 9).cast(pl.Int8)).group_by("posteam", "season", "h").agg(
        t10=(c("yardline_100") <= 10).sum().cast(pl.Float64), t20=(c("yardline_100") <= 20).sum().cast(pl.Float64), tn=pl.len().cast(pl.Float64), tx=c("xtd").sum()
    ).rename({"posteam": "team"})  # fmt: skip
    ph = (
        pg.with_columns(h=(c("week") > 9).cast(pl.Int8))
        .group_by("gsis_id", "team", "season", "h")
        .agg(
            position=c("position").last(),
            g=pl.len(),
            in10=c("in10").sum(),
            rz20=c("rz20").sum(),
            n=c("n").sum(),
            xtd=c("xtd").sum(),
            td=c("td").sum(),
        )
        .filter(c("g") >= 3)
    )
    ph = ph.join(team10, on=["team", "season", "h"]).with_columns(
        s10=c("in10") / c("t10"),
        s20=c("rz20") / c("t20"),
        sn=c("n") / c("tn"),
        sx=c("xtd") / c("tx"),
    )
    pj = ph.filter(c("h") == 0).join(
        ph.filter(c("h") == 1), on=["gsis_id", "team", "season"], suffix="_2"
    )
    for q_ in POS:
        x = pj.filter(c("position") == q_)
        print(
            f"  {q_} (n {x.height}): share of the team's chances inside the 10 repeats {cf(x['s10'], x['s10_2'])}; inside the 20 {cf(x['s20'], x['s20_2'])}; all chances {cf(x['sn'], x['sn_2'])}; expected touchdowns {cf(x['sx'], x['sx_2'])}"
        )
        print(
            f"      second-half share inside the 10 from: first-half share inside the 10 {cf(x['s10'], x['s10_2'])}; first-half share of all chances {cf(x['sn'], x['s10_2'])}; beyond all chances {fl.partial(x['s10'].to_numpy(), x['s10_2'].to_numpy(), [x['sn'].to_numpy()])}"
        )
    log("done")


if __name__ == "__main__":
    main()
