"""The build's reports (decision 0050): each writes `projects/vacated-opportunity/build/<name>.txt`.

Gains are the share of the reference forecast's squared error removed, with 90% team-bootstrap
intervals (decision 0046, call 5); scored 2017-2024; the 2025 vault stays closed.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.experts.vacated_opportunity import common as K
from pcf.experts.vacated_opportunity import ladder as Lad

c = pl.col
SC = list(K.SCORED)
RUNGS = (("f_pool", "f0", "2 pooled vs 1 no change"), ("f_pair", "f_pool", "3 + pair part vs 2"),
         ("f_team", "f_pair", "4a team rates vs 3"), ("f_coach", "f_pair", "4b coach rates vs 3"),
         ("f_trees", "f_pair", "5 trees vs 3"), ("f_trees", "f_trees_na", "5' trees vs trees without absences"),
         ("f_pair", "f0", "champion (3) vs no change"), ("f_pair_h", "f0", "hindsight ceiling vs no change"))  # fmt: skip


def scored_rows(f: pl.DataFrame, measure: str) -> pl.DataFrame:
    sc = f.filter(Lad.scored(f) & c("season").is_in(SC))
    return sc.filter(c("group") == "RB") if measure == "carry" else sc


def full(w: pl.DataFrame, trees: bool = True) -> pl.DataFrame:
    """Every rung's forecast for a walk (trees walk-forward), and the champion's ranges."""
    f = Lad.forecasts(w)
    if trees:
        keep = Lad.TREE_FEATURES
        noabs = tuple(x for x in keep if x not in ("e_same", "e_cross", "d_pool", "d_pair"))
        a = Lad.add_trees(f, SC)
        Lad.TREE_FEATURES = noabs
        try:
            b = Lad.add_trees(f, SC).select("gsis_id", "game_id", f_trees_na="f_trees")
        finally:
            Lad.TREE_FEATURES = keep
        f = f.join(a.select("gsis_id", "game_id", "f_trees"), on=["gsis_id", "game_id"], how="left")
        f = f.join(b, on=["gsis_id", "game_id"], how="left")
    return f


def _gain(sc: pl.DataFrame, ref: str, new: str) -> tuple[float, float, float]:
    y = sc["y"].to_numpy()
    return K.gain((y - sc[ref].to_numpy()) ** 2, (y - sc[new].to_numpy()) ** 2, sc["team"].to_numpy())


def ladder(W: dict[str, pl.DataFrame]) -> dict:
    out = K.Report("live_ladder")
    out("vacated-live: the ladder, Saturday-run knowledge, walk-forward 2017-2024 (decision 0050)")
    out("rows: the absent player's group-mates who played (snap share: his group; target and carry share: any")
    out("top WR, TE or RB absent; carry share scored on RBs). Gains: share of the reference's squared error.")
    res = {}
    for m, w in W.items():
        ff = pl.concat([full(w, trees=False).filter(~c("season").is_in(SC)),
                        full(w).filter(c("season").is_in(SC))], how="diagonal_relaxed")  # fmt: skip
        f = Lad.add_ranges(ff, "f_pair", SC)
        sw = Lad.add_ranges(ff, "f_pair", SC, by_swing=True, prefix="s")
        f = f.join(sw.select("gsis_id", "game_id", "sq10", "sq50", "sq90"), on=["gsis_id", "game_id"])
        res[m] = f
        sc = scored_rows(f, m)
        out(f"\n== {m} share: {sc.height:,} scored rows (alpha per season: "
            f"{f.group_by('season').agg(c('pair_alpha').first()).sort('season')['pair_alpha'].to_list()})")  # fmt: skip
        for new, ref, label in RUNGS:
            if new in sc.columns and ref in sc.columns:
                g = _gain(sc, ref, new)
                out(f"  {label:42} {K.fmt_gain(g)}")
                out.metric(f"{m}_{new}_vs_{ref}", g[0])
        out("  by group, champion vs no change:")
        for grp in sorted(sc["group"].unique().to_list()):
            s2 = sc.filter(c("group") == grp)
            out(f"    {grp}: {s2.height:6,} rows  {K.fmt_gain(_gain(s2, 'f0', 'f_pair'))}   pair vs pooled "
                f"{K.fmt_gain(_gain(s2, 'f_pool', 'f_pair'))}")  # fmt: skip
        out("  other row sets, champion vs no change:")
        for name, cond in (("flagged on Saturday (chance he plays 0.5 or less)", c("flag_pool")),
                           ("flagged and he played (false alarms)", c("flag_pool") & ~Lad.scored(f)),
                           ("absent but not flagged (surprises)", Lad.scored(f) & ~c("flag_pool")),
                           ("every row (does it hurt elsewhere?)", pl.lit(True))):  # fmt: skip
            s2 = f.filter(cond & c("played"))
            if m == "carry":
                s2 = s2.filter(c("group") == "RB")
            out(f"    {name:52} {s2.height:7,}  {K.fmt_gain(_gain(s2, 'f0', 'f_pair'))}")
        out("  by season, champion vs no change: " + ", ".join(
            f"{s} {100 * _gain(sc.filter(c('season') == s), 'f0', 'f_pair')[0]:+.0f}%" for s in SC))
        y, b, fp = sc["y"].to_numpy(), sc["f0"].to_numpy(), sc["f_pair"].to_numpy()
        out(f"  calibration slope (actual change on forecast change): {Lad.slope(y, b, fp):.2f} "
            f"(pooled alone {Lad.slope(y, b, sc['f_pool'].to_numpy()):.2f}; the brief's band 0.85-1.15)")  # fmt: skip
        for pre, lab in (("", "plain"), ("s", "widened by his swing (I14)")):
            cov = ((y >= sc[pre + "q10"].to_numpy()) & (y <= sc[pre + "q90"].to_numpy())).mean()
            above = (y > sc[pre + "q50"].to_numpy()).mean()
            rs = Lad.range_score(y, sc[pre + "q10"].to_numpy(), sc[pre + "q50"].to_numpy(), sc[pre + "q90"].to_numpy())
            out(f"  ranges, {lab:28}: q10-q90 holds {100 * cov:.1f}%, above q50 {100 * above:.1f}%, range score {rs:.3f}")
            per = sc.with_columns(inside=(c("y") >= c(pre + "q10")) & (c("y") <= c(pre + "q90"))).group_by("group").agg(
                cov=c("inside").mean()).sort("group")
            out("    by group: " + ", ".join(f"{g} {100 * v:.0f}%" for g, v in per.iter_rows()))
            band = sc.with_columns(b=Lad.swing(sc).qcut(3, labels=["steady", "mid", "swingy"]),
                                   inside=(c("y") >= c(pre + "q10")) & (c("y") <= c(pre + "q90")))
            out("    by swing third: " + ", ".join(f"{k} {100 * v:.0f}%" for k, v in
                band.group_by("b").agg(c("inside").mean()).sort("b").iter_rows()))  # fmt: skip
        out(f"  Saturday's absence source on scored rows: {sc['p_src'].value_counts().sort('count', descending=True).rows()}")
    out.save()
    for m, f in res.items():
        f.write_parquet(K.cache_dir() / f"forecast_{m}.parquet")
    return res


def forecast(measure: str) -> pl.DataFrame:
    return pl.read_parquet(K.cache_dir() / f"forecast_{measure}.parquet")


# ---------------------------------------------------------------- the shuffled null
def shuffles(W: dict[str, pl.DataFrame], copies: int = 19) -> None:
    from pcf.experts.vacated_opportunity import live as L

    out = K.Report("live_shuffles")
    out(f"vacated-live: the no-noise test, {copies} copies with absences shuffled across games within the")
    out("team-season (training absences and the walk's), every refit redone; scored on the real rows")
    inp = L.Inputs()
    real = {m: _gain(scored_rows(forecast(m), m), "f0", "f_pair")[0] for m in W}
    nulls: dict[str, list[float]] = {m: [] for m in W}
    for k in range(copies):
        smap = L.shuffle_map(inp.tg, get_config().seed + 700 + k)
        for m in W:
            w = L.walk(inp, m, list(range(2014, K.LAST + 1)), smap=smap)
            flags = W[m].select("gsis_id", "game_id", "absent_same", "absent_pool")
            w = w.drop("absent_same", "absent_pool").join(flags, on=["gsis_id", "game_id"], how="left")
            f = Lad.forecasts(w)
            nulls[m].append(_gain(scored_rows(f, m), "f0", "f_pair")[0])
        out(f"  copy {k + 1}: " + ", ".join(f"{m} {100 * nulls[m][-1]:+.1f}%" for m in W))
    for m in W:
        beaten = sum(real[m] > v for v in nulls[m])
        out(f"{m}: real {100 * real[m]:+.1f}%; copies' best {100 * max(nulls[m]):+.1f}%, mean "
            f"{100 * np.mean(nulls[m]):+.1f}%; beats {beaten} of {copies}")  # fmt: skip
    out.save()


# ---------------------------------------------------------------- the checks
def _ols_walk(df: pl.DataFrame, xcols: list[str], seasons=SC, first: int = 2016) -> np.ndarray:
    """A walk-forward linear stack: y on xcols (and 1), fit on earlier seasons' rows."""
    pred = np.full(df.height, np.nan)
    s_arr = df["season"].to_numpy()
    X = np.column_stack([np.ones(df.height)] + [df[x].to_numpy() for x in xcols])
    y = df["y"].to_numpy()
    for s in seasons:
        tr = (s_arr < s) & (s_arr >= first)
        te = s_arr == s
        if tr.sum() < 30 or te.sum() == 0:
            continue
        b, *_ = np.linalg.lstsq(X[tr], y[tr], rcond=None)
        pred[te] = X[te] @ b
    return pred.clip(0, 1)


def checks(W: dict[str, pl.DataFrame]) -> None:
    from pcf.experts.vacated_opportunity import data as D

    out = K.Report("live_checks")
    part = D.participation()
    oq = D.opportunity()
    out("== Test 4, the obvious-input check: beside participation's next-game share if he plays (snap) and")
    out("   opportunity-quality's next-game expected points (targets, carries); walk-forward linear stacks")
    out("   fit on earlier seasons' scored rows (from 2016); skill groups only (the lines have no incumbent)")
    for m in W:
        f = forecast(m).filter(c("group").is_in(list(K.SKILL)))
        f = f.with_columns(d=c("f_pair") - c("f0"), d_tr=(c("f_trees") - c("f_trees_na")).fill_null(0.0))
        f = f.join(part.select("gsis_id", "game_id", "part_if"), on=["gsis_id", "game_id"], how="left")
        f = f.join(oq.select("gsis_id", "game_id", "oq_if"), on=["gsis_id", "game_id"], how="left")
        allrows = pl.concat([full(W[m], trees=False).filter(c("season") == 2016).with_columns(
            d=c("f_pair") - c("f0"), d_tr=pl.lit(0.0)).join(part.select("gsis_id", "game_id", "part_if"),
            on=["gsis_id", "game_id"], how="left").join(oq.select("gsis_id", "game_id", "oq_if"),
            on=["gsis_id", "game_id"], how="left"), f], how="diagonal_relaxed")  # fmt: skip
        sc = allrows.filter(Lad.scored(allrows) & c("group").is_in(list(K.SKILL)))
        if m == "carry":
            sc = sc.filter(c("group") == "RB")
        inc = ["part_if"] if m == "snap" else ["f0", "oq_if"]
        sc = sc.drop_nulls(inc)
        a = _ols_walk(sc, inc)
        b = _ols_walk(sc, inc + ["d"])
        t = _ols_walk(sc, inc + ["d", "d_tr"])
        sc = sc.with_columns(inc_=pl.Series(a), with_=pl.Series(b), trees_=pl.Series(t)).filter(
            c("season").is_in(SC) & c("inc_").is_not_nan())
        out(f"  {m}: {sc.height:,} rows; the incumbent alone vs no change {K.fmt_gain(_gain(sc, 'f0', 'inc_'))}")
        out(f"    + the expert's change: {K.fmt_gain(_gain(sc, 'inc_', 'with_'))}  (the incumbent plus it vs the "
            f"expert alone: {K.fmt_gain(_gain(sc, 'f_pair', 'with_'))})")  # fmt: skip
        out(f"    + the trees' absence part too: {K.fmt_gain(_gain(sc, 'with_', 'trees_'))}")
        for grp in K.SKILL:
            s2 = sc.filter(c("group") == grp)
            if s2.height > 100:
                out(f"      {grp}: {s2.height:,} rows, + the change {K.fmt_gain(_gain(s2, 'inc_', 'with_'))}")
    _i55(out, part)
    _i143(out, W)
    out.save()


def _i55(out: K.Report, part: pl.DataFrame) -> None:
    """I55, the first game back: a top player who missed his team's last game and plays this one."""
    from pcf.experts.vacated_opportunity import live as L

    out("\n== I55 (a check): a top player's first game back after missing his team's last game")
    inp = L.Inputs()
    rows = []
    for s in SC:
        g = inp.grids[s].sort("gsis_id", "team", "week")
        g = g.with_columns(prev_played=c("played").shift(1).over("gsis_id", "team"),
                           prev_top=c("top").shift(1).over("gsis_id", "team"))  # fmt: skip
        back = g.filter(c("played") & c("prev_top") & (c("prev_played") == False))  # noqa: E712
        rows.append(back.select("gsis_id", "game_id", "team", "season", "group", y="y_share", td="share_td"))
    r = pl.concat(rows).join(part.select("gsis_id", "game_id", "part_if"), on=["gsis_id", "game_id"], how="inner")
    y = r["y"].to_numpy()
    out(f"  {r.height:,} skill-player games back with participation's forecast; participation's miss "
        f"(actual minus forecast) {100 * (y - r['part_if'].to_numpy()).mean():+.1f} points of share; his own "
        f"healthy mean to date misses by {100 * (y - r['td'].to_numpy()).mean():+.1f}")  # fmt: skip
    e_p = (y - r["part_if"].to_numpy()) ** 2
    e_t = (y - r["td"].to_numpy()) ** 2
    out(f"  his mean to date vs participation, squared error: {K.fmt_gain(K.gain(e_p, e_t, r['team'].to_numpy()))}")
    bl = 0.5 * (r["part_if"].to_numpy() + r["td"].to_numpy())
    out(f"  the half-and-half blend vs participation: {K.fmt_gain(K.gain(e_p, (y - bl) ** 2, r['team'].to_numpy()))}")


def _i143(out: K.Report, W: dict[str, pl.DataFrame]) -> None:
    """I143: the pooled same-group rates on COVID-list absences against the others (2020-2021)."""
    from pcf.data.gateway import END_OF_TIME, Gateway, TableSource
    from pcf.experts.vacated_opportunity import data as D
    from pcf.experts.vacated_opportunity import rates as R

    out("\n== I143: COVID-list absences (2020-2021) against the others, same-group snap rates")
    v = Gateway(TableSource(seasons=[2020, 2021])).view(END_OF_TIME, "retrospective", {"roster_week": ("status",)})
    rw = v.table("roster_week", seasons=[2020, 2021])
    covid = rw.filter(c("status_code").is_in(["R59", "R61"])).select(j="gsis_id", team="team", season="season",
                                                                     week="week").unique()  # fmt: skip
    pg, tg = D.player_games(), D.team_games()
    ab = R.absences(pg, tg).join(covid.with_columns(cv=pl.lit(True)), on=["j", "team", "season", "week"], how="left")
    ab = ab.with_columns(group_j=pl.when(c("cv").fill_null(False) & c("season").is_in([2020, 2021]))
                         .then(c("group_j") + "_covid").otherwise(c("group_j")))  # fmt: skip
    n_cv = ab.filter(c("group_j").str.ends_with("_covid")).height
    out(f"  {n_cv} top-player absences on the COVID list (codes R59/R61), of {ab.filter(c('season').is_in([2020, 2021])).height} in 2020-2021")
    rows = pg.filter(c("group").is_in(list(K.GROUPS)))
    seasons = list(range(2016, 2025))
    blocks = {s: R.design(rows.filter(c("season") == s).select("gsis_id", "team", "season", "game_id", "group", "share"),
                          ab.filter(c("season") == s), "share", "w_share", K.GROUPS) for s in seasons}  # fmt: skip
    X, y, keys = R.stack([blocks[s] for s in seasons])
    teams = sorted(set(pl.concat([blocks[s].rows.select("team") for s in seasons])["team"].to_list()))
    tix = {t: i for i, t in enumerate(teams)}
    rt = np.array([tix[t] for t in pl.concat([blocks[s].rows.select("team") for s in seasons])["team"].to_list()])
    wts = K.team_weights(teams, draws=100, seed=get_config().seed + 143)
    ix = {k: i for i, k in enumerate(keys)}
    pairs = [g for g in K.GROUPS if f"{g}>{g}_covid" in ix]
    base = R.ridge(X, y, 0.3)
    draws = []
    for b in range(wts.shape[0]):
        sw = np.sqrt(wts[b, rt])
        bb = R.ridge(sp_diag(sw) @ X, sw * y, 0.3)
        draws.append([bb[ix[f"{g}>{g}_covid"]] - bb[ix[f"{g}>{g}"]] for g in pairs])
    draws = np.array(draws)
    for i, g in enumerate(pairs):
        lo, hi = np.percentile(draws[:, i], [5, 95])
        out(f"  {g}: injury and other {base[ix[f'{g}>{g}']]:+.3f}, COVID list {base[ix[f'{g}>{g}_covid']]:+.3f}; "
            f"difference 90% {lo:+.3f} to {hi:+.3f}")  # fmt: skip


def sp_diag(v: np.ndarray):
    import scipy.sparse as sp

    return sp.diags(v)


# ---------------------------------------------------------------- I160 and I164
def ideas(W: dict[str, pl.DataFrame]) -> None:
    from pcf.experts.vacated_opportunity import data as D
    from pcf.experts.vacated_opportunity import rates as R

    out = K.Report("live_ideas")
    out("== I160: the forecast change recalibrated by a slope fit on earlier seasons' scored rows")
    for m in W:
        f = forecast(m)
        warm = full(W[m], trees=False).filter(c("season").is_in([2015, 2016]))
        allr = pl.concat([warm, f], how="diagonal_relaxed")
        sc = allr.filter(Lad.scored(allr))
        if m == "carry":
            sc = sc.filter(c("group") == "RB")
        y, b, fp, s_ = (sc[x].to_numpy() for x in ("y", "f0", "f_pair", "season"))
        cal = fp.copy()
        ks = []
        for s in SC:
            tr = s_ < s
            k = Lad.slope(y[tr], b[tr], fp[tr])
            ks.append(round(k, 2))
            te = s_ == s
            cal[te] = np.clip(b[te] + k * (fp[te] - b[te]), 0, 1)
        sc = sc.with_columns(f_cal=pl.Series(cal)).filter(c("season").is_in(SC))
        out(f"  {m}: slopes by season {ks}; recalibrated vs the champion {K.fmt_gain(_gain(sc, 'f_pair', 'f_cal'))}")
    out("\n== I164: the same-group snap rate in the first game of an absence spell against its later games")
    pg, tg = D.player_games(), D.team_games()
    ab = R.absences(pg, tg).sort("j", "team", "season", "week")
    order = tg.select("team", "season", "week").unique().sort("team", "season", "week").with_columns(
        gi=c("week").rank("ordinal").over("team", "season"))
    ab = ab.join(order, on=["team", "season", "week"]).with_columns(
        first=(c("gi") - c("gi").shift(1).over("j", "team", "season")).fill_null(99) != 1)
    ab = ab.with_columns(group_j=pl.when(c("first")).then(c("group_j") + "_first").otherwise(c("group_j")))
    out(f"  {ab.filter(c('first')).height} first games of a spell, {ab.filter(~c('first')).height} later games (2013-2024)")
    rows = pg.filter(c("group").is_in(list(K.GROUPS)))
    seasons = list(range(K.FIRST, K.LAST + 1))
    blocks = [R.design(rows.filter(c("season") == s).select("gsis_id", "team", "season", "game_id", "group", "share"),
                       ab.filter(c("season") == s), "share", "w_share", K.GROUPS) for s in seasons]  # fmt: skip
    X, y, keys = R.stack(blocks)
    teams_r = pl.concat([b.rows.select("team") for b in blocks])["team"].to_list()
    teams = sorted(set(teams_r))
    tix = {t: i for i, t in enumerate(teams)}
    rt = np.array([tix[t] for t in teams_r])
    ix = {k: i for i, k in enumerate(keys)}
    base = R.ridge(X, y, 0.3)
    wts = K.team_weights(teams, draws=100, seed=get_config().seed + 164)
    gs = [g for g in K.GROUPS if f"{g}>{g}_first" in ix]
    draws = []
    for bi in range(wts.shape[0]):
        sw = np.sqrt(wts[bi, rt])
        bb = R.ridge(sp_diag(sw) @ X, sw * y, 0.3)
        draws.append([bb[ix[f"{g}>{g}_first"]] - bb[ix[f"{g}>{g}"]] for g in gs])
    draws = np.array(draws)
    for i, g in enumerate(gs):
        lo, hi = np.percentile(draws[:, i], [5, 95])
        out(f"  {g}: later games {base[ix[f'{g}>{g}']]:+.3f}, first game {base[ix[f'{g}>{g}_first']]:+.3f}; "
            f"difference 90% {lo:+.3f} to {hi:+.3f}")  # fmt: skip
    pooled = draws[:, [gs.index(g) for g in ("WR", "RB", "OL")]].mean(1)
    lo, hi = np.percentile(pooled, [5, 95])
    out(f"  WR, RB and OL together: difference {np.mean(pooled):+.3f} (90% {lo:+.3f} to {hi:+.3f})")
    out.save()


# ---------------------------------------------------------------- the yardstick
def yardstick(W: dict[str, pl.DataFrame], copies: int = 19) -> None:
    from pcf.baselines.crude import yardstick as Y

    out = K.Report("live_yardstick")
    out("vacated-live on the yardstick (crude forecaster, next game), beside participation; the input is the")
    out(f"plus-minus's change (forecast minus no change) for snap, target and carry share, 0 where none;")
    out(f"{copies} copies shuffled within each week. A gain counts if its interval clears 0 and it beats every copy.")
    cols = {}
    for m in W:
        f = forecast(m).select("gsis_id", "game_id", (c("f_pair") - c("f0")).alias(f"vac_{m}"))
        cols[m] = f
    frame = cols["snap"].join(cols["target"], on=["gsis_id", "game_id"], how="full", coalesce=True).join(
        cols["carry"], on=["gsis_id", "game_id"], how="full", coalesce=True)
    for target in ("receiving", "rushing"):
        board = Y.load_board(target, "next")
        fr = board.features.select(board.keys).join(frame, on=board.keys, how="left").fill_null(0.0)
        r = Y.score_input(board, fr, "vacated-live", fill=0.0, beside=("participation",), copies=copies)
        active = fr.filter(pl.any_horizontal(c(f"vac_{m}").abs() > 0.005 for m in W)).select(board.keys)
        ra = Y.score_input(board, fr, "vacated-live (rows it moves)", fill=0.0, rows=active, beside=("participation",))
        out(f"  {target}: {100 * r['alone']:+.2f}% of the squared error (90% {100 * r['alone_lo']:+.2f} to "
            f"{100 * r['alone_hi']:+.2f}); range score {100 * r['range_alone']:+.2f}%; copies' best "
            f"{100 * r.get('copies_max', float('nan')):+.2f}%; counts: {r.get('counts')} ({r['rows']} rows)")  # fmt: skip
        out(f"    on the {active.height:,} rows it moves: {100 * ra['alone']:+.2f}% (90% {100 * ra['alone_lo']:+.2f} "
            f"to {100 * ra['alone_hi']:+.2f})")  # fmt: skip
        out.metric(f"yardstick_{target}", r["alone"])
    out.save()


# ---------------------------------------------------------------- the saved history
LIVE = "vacated-live"


def unclaimed(f: pl.DataFrame, tops: pl.DataFrame) -> pl.DataFrame:
    """Per team-game and group: the top players' expected absent share (snap), what the stayers'
    forecasts absorb, and the rest, unclaimed (newcomers, call-ups, the team's lost volume)."""
    vac = tops.with_columns(e=(1 - c("p_play")) * c("share_td")).group_by("game_id", "team", "group").agg(
        vacated=c("e").sum())
    absorbed = f.group_by("game_id", "team", "group").agg(absorbed=(c("f_pair") - c("f0")).sum())
    return vac.join(absorbed, on=["game_id", "team", "group"], how="left").with_columns(
        c("absorbed").fill_null(0.0)).with_columns(unclaimed=c("vacated") - c("absorbed")).filter(c("vacated") > 0.01)


def history(W: dict[str, pl.DataFrame]) -> str:
    from pcf.core import tracking
    from pcf.core.contract import UTC_TIME, check_output
    from pcf.data.gateway import Gateway
    from pcf.data.timeline.moments import game_moments
    from pcf.experts.vacated_opportunity import data as D
    from pcf.experts.vacated_opportunity import live as L
    from pcf.experts.vacated_opportunity import rates as R

    out = K.Report("live_history")
    mom = game_moments(Gateway().calendar, "saturday").select("game_id", as_of=c("moment").cast(UTC_TIME))
    tg = D.team_games()
    ends = tg.group_by("season", "week").agg(last=c("kickoff").max()).sort("season", "week")
    ends = ends.with_columns(train_end=(c("last").shift(1).over("season") + pl.duration(hours=4)).cast(UTC_TIME))
    parts = []
    for m in W:
        f = forecast(m)
        h = f.select(
            "gsis_id", "game_id", "season", "week", "team", "group",
            quantity=pl.lit(K.QUANTITY[m]), mean=c("f_pair"), q10="sq10", q50="sq50", q90="sq90",
            no_change="f0", change=c("f_pair") - c("f0"), pooled_change=c("f_pool") - c("f0"),
            expected_absent=c("e_pool"), drivers="drivers", played="played",
        )  # fmt: skip
        h = h.with_columns(q10=pl.min_horizontal("q10", "mean"), q90=pl.max_horizontal("q90", "mean"))
        h = h.with_columns(q50=c("q50").clip(c("q10"), c("q90")))
        parts.append(h)
    h = pl.concat(parts).join(mom, on="game_id", how="left").join(ends.select("season", "week", "train_end"),
                                                                   on=["season", "week"], how="left")  # fmt: skip
    h = h.with_columns(train_end=pl.coalesce(c("train_end"), c("as_of") - pl.duration(days=150)))
    inp = L.Inputs()
    unc = unclaimed(forecast("snap"), pl.concat([inp.tops[s] for s in SC]))
    fits = L.pooled_fits(inp, "snap", list(range(2014, K.LAST + 2)))
    rates = pl.concat([R.rate_table(fits, K.GROUPS, "snap")] + [
        R.rate_table(L.pooled_fits(inp, m, list(range(2014, K.LAST + 2))), K.SKILL, m) for m in ("target", "carry")])
    train_end = h["train_end"].max()
    with tracking.attempt(LIVE, train_end=train_end, name="vacated-live v1 (pooled + pair)") as run:
        rid = run.info.run_id
        h = h.with_columns(model=pl.lit(LIVE), model_version=pl.lit("backtest"), run_id=pl.lit(rid),
                           cadence=pl.lit("in_season"))  # fmt: skip
        check_output(h, ["gsis_id", "game_id"])
        folder = get_config().zone("outputs") / LIVE / rid
        folder.mkdir(parents=True, exist_ok=True)
        h.write_parquet(folder / "history.parquet")
        unc.write_parquet(folder / "unclaimed.parquet")
        rates.write_parquet(folder / "rates.parquet")
        import mlflow

        for name in ("live_ladder", "live_shuffles", "live_checks", "live_ideas", "live_yardstick"):
            path = K.report_dir() / f"{name}.txt"
            if path.exists():
                mlflow.log_artifact(str(path))
        lad = K.report_dir() / "live_ladder.txt"
        tracking.log_metrics({"rows": float(h.height)})
    out(f"history: {folder / 'history.parquet'} ({h.height:,} rows; {h.filter(c('played')).height:,} played)")
    out(f"run {rid}")
    out(f"unclaimed: {unc.height:,} team-game-groups; mean vacated {unc['vacated'].mean():.3f}, absorbed "
        f"{unc['absorbed'].mean():.3f}, unclaimed {unc['unclaimed'].mean():.3f}")  # fmt: skip
    out("the transfer rates through 2024 (same group): " + ", ".join(
        f"{r['measure']} {r['group']} {r['rate']:+.3f}" for r in rates.filter(
            (c("through") == K.LAST) & (c("group") == c("absent_group"))).iter_rows(named=True)))
    _ = lad
    out.save()
    return rid
