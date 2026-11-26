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
    return K.gain(
        (y - sc[ref].to_numpy()) ** 2, (y - sc[new].to_numpy()) ** 2, sc["team"].to_numpy()
    )


def ladder(W: dict[str, pl.DataFrame]) -> dict:
    out = K.Report("live_ladder")
    out("vacated-live: the ladder, Saturday-run knowledge, walk-forward 2017-2024 (decision 0050)")
    out(
        "rows: the absent player's group-mates who played (snap share: his group; target and carry share: any"
    )
    out(
        "top WR, TE or RB absent; carry share scored on RBs). Gains: share of the reference's squared error."
    )
    res = {}
    for m, w in W.items():
        ff = pl.concat([full(w, trees=False).filter(~c("season").is_in(SC)),
                        full(w).filter(c("season").is_in(SC))], how="diagonal_relaxed")  # fmt: skip
        f = Lad.add_ranges(ff, "f_pair", SC)
        sw = Lad.add_ranges(ff, "f_pair", SC, by_swing=True, prefix="s")
        f = f.join(
            sw.select("gsis_id", "game_id", "sq10", "sq50", "sq90"), on=["gsis_id", "game_id"]
        )
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
        out(
            "  by season, champion vs no change: "
            + ", ".join(
                f"{s} {100 * _gain(sc.filter(c('season') == s), 'f0', 'f_pair')[0]:+.0f}%"
                for s in SC
            )
        )
        y, b, fp = sc["y"].to_numpy(), sc["f0"].to_numpy(), sc["f_pair"].to_numpy()
        out(f"  calibration slope (actual change on forecast change): {Lad.slope(y, b, fp):.2f} "
            f"(pooled alone {Lad.slope(y, b, sc['f_pool'].to_numpy()):.2f}; the brief's band 0.85-1.15)")  # fmt: skip
        for pre, lab in (("", "plain"), ("s", "widened by his swing (I14)")):
            cov = ((y >= sc[pre + "q10"].to_numpy()) & (y <= sc[pre + "q90"].to_numpy())).mean()
            above = (y > sc[pre + "q50"].to_numpy()).mean()
            rs = Lad.range_score(
                y,
                sc[pre + "q10"].to_numpy(),
                sc[pre + "q50"].to_numpy(),
                sc[pre + "q90"].to_numpy(),
            )
            out(
                f"  ranges, {lab:28}: q10-q90 holds {100 * cov:.1f}%, above q50 {100 * above:.1f}%, range score {rs:.3f}"
            )
            per = (
                sc.with_columns(inside=(c("y") >= c(pre + "q10")) & (c("y") <= c(pre + "q90")))
                .group_by("group")
                .agg(cov=c("inside").mean())
                .sort("group")
            )
            out("    by group: " + ", ".join(f"{g} {100 * v:.0f}%" for g, v in per.iter_rows()))
            band = sc.with_columns(
                b=Lad.swing(sc).qcut(3, labels=["steady", "mid", "swingy"]),
                inside=(c("y") >= c(pre + "q10")) & (c("y") <= c(pre + "q90")),
            )
            out("    by swing third: " + ", ".join(f"{k} {100 * v:.0f}%" for k, v in
                band.group_by("b").agg(c("inside").mean()).sort("b").iter_rows()))  # fmt: skip
        out(
            f"  Saturday's absence source on scored rows: {sc['p_src'].value_counts().sort('count', descending=True).rows()}"
        )
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
    out(
        f"vacated-live: the no-noise test, {copies} copies with absences shuffled across games within the"
    )
    out(
        "team-season (training absences and the walk's), every refit redone; scored on the real rows"
    )
    inp = L.Inputs()
    real = {m: _gain(scored_rows(forecast(m), m), "f0", "f_pair")[0] for m in W}
    nulls: dict[str, list[float]] = {m: [] for m in W}
    for k in range(copies):
        smap = L.shuffle_map(inp.tg, get_config().seed + 700 + k)
        for m in W:
            w = L.walk(inp, m, list(range(2014, K.LAST + 1)), smap=smap)
            flags = W[m].select("gsis_id", "game_id", "absent_same", "absent_pool")
            w = w.drop("absent_same", "absent_pool").join(
                flags, on=["gsis_id", "game_id"], how="left"
            )
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
    out(
        "== Test 4, the obvious-input check: beside participation's next-game share if he plays (snap) and"
    )
    out(
        "   opportunity-quality's next-game expected points (targets, carries); walk-forward linear stacks"
    )
    out(
        "   fit on earlier seasons' scored rows (from 2016); skill groups only (the lines have no incumbent)"
    )
    for m in W:
        f = forecast(m).filter(c("group").is_in(list(K.SKILL)))
        f = f.with_columns(
            d=c("f_pair") - c("f0"), d_tr=(c("f_trees") - c("f_trees_na")).fill_null(0.0)
        )
        f = f.join(
            part.select("gsis_id", "game_id", "part_if"), on=["gsis_id", "game_id"], how="left"
        )
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
            c("season").is_in(SC) & c("inc_").is_not_nan()
        )
        out(
            f"  {m}: {sc.height:,} rows; the incumbent alone vs no change {K.fmt_gain(_gain(sc, 'f0', 'inc_'))}"
        )
        out(f"    + the expert's change: {K.fmt_gain(_gain(sc, 'inc_', 'with_'))}  (the incumbent plus it vs the "
            f"expert alone: {K.fmt_gain(_gain(sc, 'f_pair', 'with_'))})")  # fmt: skip
        out(f"    + the trees' absence part too: {K.fmt_gain(_gain(sc, 'with_', 'trees_'))}")
        for grp in K.SKILL:
            s2 = sc.filter(c("group") == grp)
            if s2.height > 100:
                out(
                    f"      {grp}: {s2.height:,} rows, + the change {K.fmt_gain(_gain(s2, 'inc_', 'with_'))}"
                )
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
        rows.append(
            back.select("gsis_id", "game_id", "team", "season", "group", y="y_share", td="share_td")
        )
    r = pl.concat(rows).join(
        part.select("gsis_id", "game_id", "part_if"), on=["gsis_id", "game_id"], how="inner"
    )
    y = r["y"].to_numpy()
    out(f"  {r.height:,} skill-player games back with participation's forecast; participation's miss "
        f"(actual minus forecast) {100 * (y - r['part_if'].to_numpy()).mean():+.1f} points of share; his own "
        f"healthy mean to date misses by {100 * (y - r['td'].to_numpy()).mean():+.1f}")  # fmt: skip
    e_p = (y - r["part_if"].to_numpy()) ** 2
    e_t = (y - r["td"].to_numpy()) ** 2
    out(
        f"  his mean to date vs participation, squared error: {K.fmt_gain(K.gain(e_p, e_t, r['team'].to_numpy()))}"
    )
    bl = 0.5 * (r["part_if"].to_numpy() + r["td"].to_numpy())
    out(
        f"  the half-and-half blend vs participation: {K.fmt_gain(K.gain(e_p, (y - bl) ** 2, r['team'].to_numpy()))}"
    )


def _i143(out: K.Report, W: dict[str, pl.DataFrame]) -> None:
    """I143: the pooled same-group rates on COVID-list absences against the others (2020-2021)."""
    from pcf.data.gateway import END_OF_TIME, Gateway, TableSource
    from pcf.experts.vacated_opportunity import data as D
    from pcf.experts.vacated_opportunity import rates as R

    out("\n== I143: COVID-list absences (2020-2021) against the others, same-group snap rates")
    v = Gateway(TableSource(seasons=[2020, 2021])).view(
        END_OF_TIME, "retrospective", {"roster_week": ("status",)}
    )
    rw = v.table("roster_week", seasons=[2020, 2021])
    covid = rw.filter(c("status_code").is_in(["R59", "R61"])).select(j="gsis_id", team="team", season="season",
                                                                     week="week").unique()  # fmt: skip
    pg, tg = D.player_games(), D.team_games()
    ab = R.absences(pg, tg).join(
        covid.with_columns(cv=pl.lit(True)), on=["j", "team", "season", "week"], how="left"
    )
    ab = ab.with_columns(group_j=pl.when(c("cv").fill_null(False) & c("season").is_in([2020, 2021]))
                         .then(c("group_j") + "_covid").otherwise(c("group_j")))  # fmt: skip
    n_cv = ab.filter(c("group_j").str.ends_with("_covid")).height
    out(
        f"  {n_cv} top-player absences on the COVID list (codes R59/R61), of {ab.filter(c('season').is_in([2020, 2021])).height} in 2020-2021"
    )
    rows = pg.filter(c("group").is_in(list(K.GROUPS)))
    seasons = list(range(2016, 2025))
    blocks = {s: R.design(rows.filter(c("season") == s).select("gsis_id", "team", "season", "game_id", "group", "share"),
                          ab.filter(c("season") == s), "share", "w_share", K.GROUPS) for s in seasons}  # fmt: skip
    X, y, keys = R.stack([blocks[s] for s in seasons])
    teams = sorted(
        set(pl.concat([blocks[s].rows.select("team") for s in seasons])["team"].to_list())
    )
    tix = {t: i for i, t in enumerate(teams)}
    rt = np.array(
        [
            tix[t]
            for t in pl.concat([blocks[s].rows.select("team") for s in seasons])["team"].to_list()
        ]
    )
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
        out(
            f"  {m}: slopes by season {ks}; recalibrated vs the champion {K.fmt_gain(_gain(sc, 'f_pair', 'f_cal'))}"
        )
    out(
        "\n== I164: the same-group snap rate in the first game of an absence spell against its later games"
    )
    pg, tg = D.player_games(), D.team_games()
    ab = R.absences(pg, tg).sort("j", "team", "season", "week")
    order = (
        tg.select("team", "season", "week")
        .unique()
        .sort("team", "season", "week")
        .with_columns(gi=c("week").rank("ordinal").over("team", "season"))
    )
    ab = ab.join(order, on=["team", "season", "week"]).with_columns(
        first=(c("gi") - c("gi").shift(1).over("j", "team", "season")).fill_null(99) != 1
    )
    ab = ab.with_columns(
        group_j=pl.when(c("first")).then(c("group_j") + "_first").otherwise(c("group_j"))
    )
    out(
        f"  {ab.filter(c('first')).height} first games of a spell, {ab.filter(~c('first')).height} later games (2013-2024)"
    )
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
    out(
        "vacated-live on the yardstick (crude forecaster, next game), beside participation; the input is the"
    )
    out(
        f"plus-minus's change (forecast minus no change) for snap, target and carry share, 0 where none;"
    )
    out(
        f"{copies} copies shuffled within each week. A gain counts if its interval clears 0 and it beats every copy."
    )
    cols = {}
    for m in W:
        f = forecast(m).select("gsis_id", "game_id", (c("f_pair") - c("f0")).alias(f"vac_{m}"))
        cols[m] = f
    frame = (
        cols["snap"]
        .join(cols["target"], on=["gsis_id", "game_id"], how="full", coalesce=True)
        .join(cols["carry"], on=["gsis_id", "game_id"], how="full", coalesce=True)
    )
    for target in ("receiving", "rushing"):
        board = Y.load_board(target, "next")
        fr = board.features.select(board.keys).join(frame, on=board.keys, how="left").fill_null(0.0)
        r = Y.score_input(
            board, fr, "vacated-live", fill=0.0, beside=("participation",), copies=copies
        )
        active = fr.filter(pl.any_horizontal(c(f"vac_{m}").abs() > 0.005 for m in W)).select(
            board.keys
        )
        ra = Y.score_input(
            board,
            fr,
            "vacated-live (rows it moves)",
            fill=0.0,
            rows=active,
            beside=("participation",),
        )
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
    vac = (
        tops.with_columns(e=(1 - c("p_play")) * c("share_td"))
        .group_by("game_id", "team", "group")
        .agg(vacated=c("e").sum())
    )
    absorbed = f.group_by("game_id", "team", "group").agg(absorbed=(c("f_pair") - c("f0")).sum())
    return (
        vac.join(absorbed, on=["game_id", "team", "group"], how="left")
        .with_columns(c("absorbed").fill_null(0.0))
        .with_columns(unclaimed=c("vacated") - c("absorbed"))
        .filter(c("vacated") > 0.01)
    )


def history(W: dict[str, pl.DataFrame]) -> str:
    from pcf.core import tracking
    from pcf.core.contract import UTC_TIME, check_output
    from pcf.data.gateway import Gateway
    from pcf.data.timeline.moments import game_moments
    from pcf.experts.vacated_opportunity import data as D
    from pcf.experts.vacated_opportunity import live as L
    from pcf.experts.vacated_opportunity import rates as R

    out = K.Report("live_history")
    mom = game_moments(Gateway().calendar, "saturday").select(
        "game_id", as_of=c("moment").cast(UTC_TIME)
    )
    tg = D.team_games()
    ends = tg.group_by("season", "week").agg(last=c("kickoff").max()).sort("season", "week")
    ends = ends.with_columns(
        train_end=(c("last").shift(1).over("season") + pl.duration(hours=4)).cast(UTC_TIME)
    )
    parts = []
    for m in W:
        f = forecast(m)
        h = f.select(
            "gsis_id", "game_id", "season", "week", "team", "group",
            quantity=pl.lit(K.QUANTITY[m]), mean=c("f_pair"), q10="sq10", q50="sq50", q90="sq90",
            no_change="f0", change=c("f_pair") - c("f0"), pooled_change=c("f_pool") - c("f0"),
            expected_absent=c("e_pool"), drivers="drivers", played="played",
        )  # fmt: skip
        h = h.with_columns(
            q10=pl.min_horizontal("q10", "mean"), q90=pl.max_horizontal("q90", "mean")
        )
        h = h.with_columns(q50=c("q50").clip(c("q10"), c("q90")))
        parts.append(h)
    h = pl.concat(parts).join(mom, on="game_id", how="left").join(ends.select("season", "week", "train_end"),
                                                                   on=["season", "week"], how="left")  # fmt: skip
    h = h.with_columns(train_end=pl.coalesce(c("train_end"), c("as_of") - pl.duration(days=150)))
    inp = L.Inputs()
    unc = unclaimed(forecast("snap"), pl.concat([inp.tops[s] for s in SC]))
    fits = L.pooled_fits(inp, "snap", list(range(2014, K.LAST + 2)))
    rates = pl.concat(
        [R.rate_table(fits, K.GROUPS, "snap")]
        + [
            R.rate_table(L.pooled_fits(inp, m, list(range(2014, K.LAST + 2))), K.SKILL, m)
            for m in ("target", "carry")
        ]
    )
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
    out(
        f"history: {folder / 'history.parquet'} ({h.height:,} rows; {h.filter(c('played')).height:,} played)"
    )
    out(f"run {rid}")
    out(f"unclaimed: {unc.height:,} team-game-groups; mean vacated {unc['vacated'].mean():.3f}, absorbed "
        f"{unc['absorbed'].mean():.3f}, unclaimed {unc['unclaimed'].mean():.3f}")  # fmt: skip
    out(
        "the transfer rates through 2024 (same group): "
        + ", ".join(
            f"{r['measure']} {r['group']} {r['rate']:+.3f}"
            for r in rates.filter(
                (c("through") == K.LAST) & (c("group") == c("absent_group"))
            ).iter_rows(named=True)
        )
    )
    _ = lad
    out.save()
    return rid


# ---------------------------------------------------------------- method 3, the choice model
def choice_fits(refresh: bool = False) -> pl.DataFrame:
    """The nested logit's nest parameters per completed season, 2016-2024, targets and carries."""
    from pcf.experts.vacated_opportunity import choice as C
    from pcf.experts.vacated_opportunity import data as D
    from pcf.experts.vacated_opportunity import rates as R

    path = K.cache_dir() / "choice_lams.parquet"
    if path.exists() and not refresh:
        return pl.read_parquet(path)
    grp = R.season_tops(D.player_games()).select("gsis_id", "team", "season", "group")
    rows = []
    for kind in ("target", "carry"):
        for s in range(2016, K.LAST + 1):
            a, _ = C.arrays(C.plays(s, kind, grp))
            lam, _, ll = C.fit(a)
            lam1, ll1 = C.fit_given(a, np.ones(C.OUT))[1], None
            rows.append({"kind": kind, "season": s, **{f"lam_{g}": float(lam[i]) for i, g in enumerate(C.NESTS)},
                         "loglik": ll, "loglik_mnl": lam1, "plays": a.n_plays})  # fmt: skip
            print(rows[-1], flush=True)
    t = pl.DataFrame(rows)
    t.write_parquet(path)
    return t


def choice_forecast(measure: str, lams: dict[int, np.ndarray], mnl: bool = False) -> pl.DataFrame:
    """The choice model's in-season forecast for target or carry share on every team-game where
    the Saturday run expects an absence in the pool (no change elsewhere)."""
    from pcf.experts.vacated_opportunity import choice as C
    from pcf.experts.vacated_opportunity import live as L

    inp = L.Inputs()
    q = pl.concat([inp.tops[s].select("gsis_id", "game_id", q=1 - c("p_play")) for s in SC])
    f = forecast(measure).select("gsis_id", "game_id", "team", "season", "group", "f0", "e_pool")
    sn = forecast("snap").select("gsis_id", "game_id", snap0="f0", snap_if="f_pair")
    f = f.join(sn, on=["gsis_id", "game_id"], how="left").join(
        q, on=["gsis_id", "game_id"], how="left"
    )
    f = f.with_columns(
        snap0=c("snap0").fill_null(0.0),
        snap1=(c("snap_if").fill_null(0.0) * (1 - c("q").fill_null(0.0))),
    )
    hot = f.group_by("game_id", "team").agg(hot=(c("e_pool") > 0.01).any())
    f = f.join(hot, on=["game_id", "team"])
    nest_ix = {g: i for i, g in enumerate(C.NESTS)}
    parts = [f.filter(~c("hot")).with_columns(f_choice=c("f0"))]
    for (_g, _t), d in f.filter(c("hot")).group_by("game_id", "team"):
        s = int(d["season"][0])
        lam = np.ones(C.OUT) if mnl else lams[s]
        nest = np.array([nest_ix[g] for g in d["group"].to_list()])
        new = C.divert(d["f0"].to_numpy(), d["snap0"].to_numpy(), d["snap1"].to_numpy(), nest, lam)
        parts.append(d.with_columns(f_choice=pl.Series(new)))
    return pl.concat(parts).select("gsis_id", "game_id", "f_choice")


def choice(W: dict[str, pl.DataFrame]) -> None:
    from pcf.experts.vacated_opportunity import choice as C

    out = K.Report("choice")
    out(
        "Method 3: a nested logit over the WR, TE and RB on the field for each target and carry (plus an"
    )
    out(
        "outside option), nests = groups, fit on each completed season's plays (participation's on-field data)."
    )
    t = choice_fits()
    out(
        "\n== The nest parameters by season (1 = no closer substitution within the group than across)"
    )
    for kind in ("target", "carry"):
        d = t.filter(c("kind") == kind).sort("season")
        out(f"  {kind}: " + "; ".join(f"{r['season']} WR {r['lam_WR']:.2f} TE {r['lam_TE']:.2f} RB {r['lam_RB']:.2f}"
                                      for r in d.iter_rows(named=True)))  # fmt: skip
        for g in C.NESTS:
            v = d[f"lam_{g}"].to_numpy()
            se = v.std(ddof=1) / np.sqrt(len(v))
            out(f"    {g}: mean {v.mean():.2f}, 90% across seasons {v.mean() - 1.86 * se:.2f} to {v.mean() + 1.86 * se:.2f}; "
                f"below 1 in {int((v < 1).sum())} of {len(v)} seasons")  # fmt: skip
        gain_ll = (d["loglik"] - d["loglik_mnl"]).to_numpy()
        out(f"    log likelihood over the plain logit (all nests 1): {gain_ll.mean():+.1f} a season "
            f"({d['plays'].mean():,.0f} plays)")  # fmt: skip
    out(
        "\n== In season, scored like vacated-live (2017-2024, the same rows): the choice model's shares"
    )
    for m in ("target", "carry"):
        d = t.filter(c("kind") == m)
        fits = {
            r["season"]: np.array([r["lam_WR"], r["lam_TE"], r["lam_RB"]])
            for r in d.iter_rows(named=True)
        }
        lams = C.walk_lams(fits, SC)
        fc = choice_forecast(m, lams)
        fm = choice_forecast(m, lams, mnl=True).rename({"f_choice": "f_mnl"})
        f = (
            forecast(m)
            .join(fc, on=["gsis_id", "game_id"], how="left")
            .join(fm, on=["gsis_id", "game_id"], how="left")
        )
        f.write_parquet(K.cache_dir() / f"forecast_{m}_choice.parquet")
        sc = scored_rows(f, m)
        out(f"  {m}: {sc.height:,} rows")
        out(f"    choice model vs no change      {K.fmt_gain(_gain(sc, 'f0', 'f_choice'))}")
        out(f"    choice model vs the plus-minus {K.fmt_gain(_gain(sc, 'f_pair', 'f_choice'))}")
        out(f"    nests vs a plain logit (I163)  {K.fmt_gain(_gain(sc, 'f_mnl', 'f_choice'))}")
        sc2 = sc.with_columns(f_avg=(c("f_pair") + c("f_choice")) / 2)
        out(
            f"    the average of the two vs the plus-minus {K.fmt_gain(_gain(sc2, 'f_pair', 'f_avg'))}"
        )
        for grp in K.SKILL:
            s2 = sc.filter(c("group") == grp)
            if s2.height > 100:
                out(f"      {grp}: {s2.height:,} rows; vs no change {K.fmt_gain(_gain(s2, 'f0', 'f_choice'))}; "
                    f"vs the plus-minus {K.fmt_gain(_gain(s2, 'f_pair', 'f_choice'))}")  # fmt: skip
    out.save()


# ---------------------------------------------------------------- vacated-offseason
OFF = "vacated-offseason"
OSC = list(
    range(2016, K.LAST)
)  # pairs s -> s + 1 scored (s + 1 = 2017-2024); 2015 -> 2016 warms up
TABLE_COLS = ("gsis_id", "team", "season", "group", "pkey", "rank", "top", "games", "with_", "y", "games_next",
              "intake", "s_share")  # fmt: skip
ROLE_COLS = (
    "t0_snap_share",
    "t1_tgt_per_pass",
    "t2_car_per_run",
    "t3_adot",
    "t4_adj_run",
    "t5_adj_p11",
)


def offseason_fits(measure: str) -> dict:
    """vacated-live's refits through each completed season s (pooled + season s's pair part)."""
    from pcf.experts.vacated_opportunity import data as D
    from pcf.experts.vacated_opportunity import offseason as O
    from pcf.experts.vacated_opportunity import rates as R

    pg, tg = D.player_games(), D.team_games()
    ab = R.absences(pg, tg)
    blocks = R.blocks_for(pg, ab, measure, range(K.FIRST, K.LAST))
    return {s: R.fit_through(blocks, s) for s in O.PAIRS}


def _off_rows(st: pl.DataFrame, measure: str, which: str) -> pl.DataFrame:
    d = st.filter(c("y").is_not_null() & c("season").is_in(OSC))
    skill = (c("group") == "RB") if measure == "carry" else c("group").is_in(list(K.SKILL))
    lines = c("group").is_in(["OL", "DL"])
    pick = {
        "empty": skill & ~c("intake"),
        "brought": skill & c("intake"),
        "lines": lines,
        "all": skill | lines,
    }
    return d.filter(pick[which])


def _g(sc: pl.DataFrame, ref: str, new: str) -> str:
    return K.fmt_gain(_gain(sc, ref, new)) if sc.height > 20 else "n/a"


def _first_games() -> pl.DataFrame:
    from pcf.experts.vacated_opportunity import data as D

    return D.team_games().sort("week").group_by("team", "season").agg(game_id=c("game_id").first())


def _reforecast(
    st: pl.DataFrame, deps: dict, fits: dict, measure: str, pair: bool = True
) -> pl.DataFrame:
    from pcf.experts.vacated_opportunity import offseason as O

    base = st.select(TABLE_COLS)
    parts = [
        O.forecast(base.filter(c("season") == s), deps[s], fits[s], O.TOPS[measure], pair)
        for s in deps
    ]
    return pl.concat(parts, how="diagonal_relaxed")


def offseason() -> None:
    from pcf.experts.vacated_opportunity import data as D
    from pcf.experts.vacated_opportunity import offseason as O

    out = K.Report("offseason")
    out(
        "vacated-offseason: each stayer's next-season share after a top player left (the event: the week-1"
    )
    out(
        "roster); pairs 2016->2017 to 2023->2024 scored; vacated-live's rates fit through season s; 90% team"
    )
    out(
        "bootstrap. No change = his season-s share in games where every departed group-mate played."
    )
    res = {}
    for m in ("snap", "target", "carry"):
        fits = offseason_fits(m)
        st, deps = O.build(m, fits)
        pooled = _reforecast(st, deps, fits, m, pair=False).select(
            "gsis_id", "team", "season", f_pool_only="f_pm"
        )
        st = st.join(pooled, on=["gsis_id", "team", "season"], how="left")
        res[m] = (st, deps, fits)
        n_dep = sum(d.height for s, d in deps.items() if s in OSC)
        so = st.filter(c("season").is_in(OSC))
        out(f"\n== {m} share")
        out(f"  {n_dep} departures; {so.height:,} stayers, {so.filter(c('y').is_not_null()).height:,} who played in "
            f"s + 1; a top player came in at the group for {100 * so['intake'].mean():.0f}% of stayer rows")  # fmt: skip
        for which, lab in (("empty", "skill groups left empty"), ("brought", "skill groups, a top player came in"),
                           ("lines", "the lines"), ("all", "every stayer")):  # fmt: skip
            if m != "snap" and which == "lines":
                continue
            sc = _off_rows(st, m, which)
            if sc.height == 0:
                continue
            out(f"  {lab}: {sc.height:,} rows")
            out(f"    plus-minus vs no change {_g(sc, 'f0', 'f_pm')} (pooled alone {_g(sc, 'f0', 'f_pool_only')}; "
                f"the pair part over pooled {_g(sc, 'f_pool_only', 'f_pm')})")  # fmt: skip
            out(f"    gated vs no change {_g(sc, 'f0', 'f_gate')}; the proportional split vs no change "
                f"{_g(sc, 'f0', 'f_prop')}; gated vs the proportional split {_g(sc, 'f_prop', 'f_gate')}")  # fmt: skip
        for which in ("empty", "lines") if m == "snap" else ("empty",):
            sc = _off_rows(st, m, which)
            for grp in sorted(sc["group"].unique().to_list()):
                s2 = sc.filter(c("group") == grp)
                out(
                    f"      {which}, {grp}: {s2.height} rows, plus-minus vs no change {_g(s2, 'f0', 'f_pm')}"
                )
            out(f"    calibration slope ({which}): "
                f"{Lad.slope(sc['y'].to_numpy(), sc['f0'].to_numpy(), sc['f_pm'].to_numpy()):.2f}")  # fmt: skip
    _offseason_shuffles(out, res)
    _offseason_shrink(out, res)
    _offseason_ranges(out, res)
    _offseason_obvious(out, res, D.season_incumbents())
    _offseason_roles(out, res)
    _offseason_choice(out, res)
    _offseason_yardstick(out, res)
    out.save()
    _offseason_history(res)


def _offseason_shuffles(out: K.Report, res: dict, copies: int = 19) -> None:
    from pcf.experts.vacated_opportunity import offseason as O

    out(
        f"\n== No noise: {copies} copies with each season's departure lists moved to another team (no change kept)"
    )
    for m, (st, deps, fits) in res.items():
        whiches = ("empty", "lines") if m == "snap" else ("empty",)
        real = {w: _gain(_off_rows(st, m, w), "f0", "f_pm")[0] for w in whiches}
        nulls = {w: [] for w in whiches}
        for k in range(copies):
            s2 = _reforecast(st, O.shuffled_departures(deps, get_config().seed + 900 + k), fits, m)
            for w in whiches:
                nulls[w].append(_gain(_off_rows(s2, m, w), "f0", "f_pm")[0])
        for w in whiches:
            out(f"  {m}, {w}: real {100 * real[w]:+.1f}%; copies' best {100 * max(nulls[w]):+.1f}%, mean "
                f"{100 * np.mean(nulls[w]):+.1f}%; beats {sum(real[w] > v for v in nulls[w])} of {copies}")  # fmt: skip


def _offseason_shrink(out: K.Report, res: dict) -> None:
    """I165: the change scaled by a slope fit on earlier pairs (skill groups left empty and the
    lines apart; where a top player came in the gate already keeps no change). Then the
    champion per measure (rule k): of no change, the gated plus-minus and the shrunk one, the
    most complex that beats every simpler one over all stayers with an interval above 0."""
    out(
        "\n== I165: the change shrunk by a slope fit on earlier pairs; then the champion per measure (rule k)"
    )
    for m, (st, deps, fits) in list(res.items()):
        st, slopes = shrink(st, m)
        for which, b in slopes.items():
            sc = _off_rows(st, m, which)
            out(f"  {m}, {which}: slopes by season " + ", ".join(f"{s + 1} {b[s]:.2f}" for s in OSC))
            out(f"    shrunk vs the plus-minus {_g(sc, 'f_pm', 'f_shr')}; shrunk vs no change {_g(sc, 'f0', 'f_shr')}")
        sc = _off_rows(st, m, "all")
        ladder = ("f0", "f_gate", "f_shr")
        champ = "f0"
        for i, cand in enumerate(ladder[1:], start=1):
            if all(_gain(sc, simpler, cand)[1] > 0 for simpler in ladder[:i]):
                champ = cand
        out(f"  {m}, every stayer: gated vs no change {_g(sc, 'f0', 'f_gate')}; shrunk vs no change {_g(sc, 'f0', 'f_shr')}; "
            f"shrunk vs gated {_g(sc, 'f_gate', 'f_shr')} -> the champion: {CHAMP_NAMES[champ]}")  # fmt: skip
        res[m] = (st.with_columns(f_champ=c(champ), champ=pl.lit(CHAMP_NAMES[champ])), deps, fits)


def shrink(st: pl.DataFrame, m: str, hindsight: bool = False) -> tuple[pl.DataFrame, dict]:
    """I165's shrunk forecast (`f_shr`): no change plus the plus-minus's change times a slope
    through the origin of (actual - no change) on the change, fit on earlier pairs only (or, with
    `hindsight`, on every pair: the room, never shipped). Skill groups left empty and the lines
    get their own slopes; elsewhere `f_shr` is the gated forecast. Returns the slopes per cell
    and season (the pair's first season s)."""
    st = st.with_columns(f_shr=c("f_gate"), slope_=pl.lit(None, pl.Float64))
    lines = c("group").is_in(["OL", "DL"])
    skill = (c("group") == "RB") if m == "carry" else c("group").is_in(list(K.SKILL))
    cells = {"empty": skill & ~c("intake")} | ({"lines": lines} if m == "snap" else {})
    slopes = {}
    for which, cond in cells.items():
        d = st.filter(cond & c("season").is_in(PAIRS_ALL)).with_columns(dlt=c("f_pm") - c("f0"))
        fit_rows = d.filter(c("y").is_not_null())
        s_arr = fit_rows["season"].to_numpy()
        x = fit_rows["dlt"].to_numpy()
        y = (fit_rows["y"] - fit_rows["f0"]).to_numpy()
        b = {}
        for s in OSC:
            tr = np.ones_like(s_arr, dtype=bool) if hindsight else s_arr < s
            b[s] = float((x[tr] * y[tr]).sum() / max((x[tr] ** 2).sum(), 1e-12)) if tr.sum() >= 30 else 1.0
        d = d.with_columns(slope_=c("season").replace_strict(b, default=None, return_dtype=pl.Float64))
        d = d.with_columns(f_shr=(c("f0") + c("slope_") * c("dlt")).clip(0, 1))
        st = st.update(d.select("gsis_id", "team", "season", "f_shr", "slope_"), on=["gsis_id", "team", "season"])
        slopes[which] = b
    return st, slopes


PAIRS_ALL = list(range(2015, K.LAST))
CHAMP_NAMES = {
    "f0": "no change",
    "f_gate": "the gated plus-minus",
    "f_shr": "the gated plus-minus, shrunk",
}


def _offseason_ranges(out: K.Report, res: dict) -> None:
    out(
        "\n== Ranges around the champion: q10-q90 from earlier pairs' residuals per cell (group | intake | the"
    )
    out("   plus-minus moves it > 0.02)")
    for m, (st, _, _) in res.items():
        st = st.with_columns(
            cell=c("group") + "|" + c("intake").cast(pl.Utf8) + "|" + ((c("f_gate") - c("f0")).abs() > 0.02).cast(pl.Utf8),
            r=c("y") - c("f_champ"))  # fmt: skip
        parts = []
        for s in OSC:
            pri = st.filter((c("season") < s) & c("y").is_not_null())
            q = pri.group_by("cell").agg([c("r").quantile(p).alias(f"r{z}") for z, p in ((10, 0.1), (50, 0.5), (90, 0.9))]
                                         + [pl.len().alias("n")])  # fmt: skip
            a = {f"r{z}": pri["r"].quantile(p) for z, p in ((10, 0.1), (50, 0.5), (90, 0.9))}
            te = (
                st.filter(c("season") == s)
                .join(q, on="cell", how="left")
                .with_columns(
                    [
                        pl.when(c("n") >= 30).then(c(z)).otherwise(pl.lit(v)).alias(z)
                        for z, v in a.items()
                    ]
                )
            )
            parts.append(
                te.with_columns(
                    [(c("f_champ") + c(f"r{z}")).clip(0, 1).alias(f"q{z}") for z in (10, 50, 90)]
                )
            )
        rr = pl.concat(parts)
        rr.select("gsis_id", "team", "season", "q10", "q50", "q90").write_parquet(
            K.cache_dir() / f"offseason_{m}.parquet"
        )
        sc = rr.filter(c("y").is_not_null())
        sc = sc.filter(
            (c("group") == "RB")
            if m == "carry"
            else c("group").is_in(list(K.SKILL) + (["OL", "DL"] if m == "snap" else []))
        )
        inn = (c("y") >= c("q10")) & (c("y") <= c("q90"))
        per = sc.with_columns(i=inn).group_by("group").agg(c("i").mean()).sort("group")
        rs = Lad.range_score(
            sc["y"].to_numpy(), sc["q10"].to_numpy(), sc["q50"].to_numpy(), sc["q90"].to_numpy()
        )
        out(f"  {m}: q10-q90 holds {100 * sc.select(inn.mean()).item():.1f}% of {sc.height:,} rows (aim 80%); range score "
            f"{rs:.3f}; " + ", ".join(f"{g} {100 * v:.0f}%" for g, v in per.iter_rows()))  # fmt: skip


def _offseason_obvious(out: K.Report, res: dict, inc: pl.DataFrame) -> None:
    out(
        "\n== The obvious-input check (skill stayers left empty; walk-forward linear stacks on earlier pairs):"
    )
    out(
        "   participation's rest-of-season share (snap), opportunity-quality's rest-of-season expected points (target,"
    )
    out("   carry), at his team's first game of s + 1; then + the plus-minus's change")
    fg = _first_games()
    for m, (st, _, _) in res.items():
        d = st.with_columns(s1=c("season") + 1).join(
            fg.rename({"season": "s1"}), on=["team", "s1"], how="left"
        )
        d = d.join(inc, on=["gsis_id", "game_id"], how="left")
        d = _off_rows(d.with_columns(season=c("season")), m, "empty").with_columns(
            dlt=c("f_pm") - c("f0")
        )
        incs = ["part_rest"] if m == "snap" else ["f0", "oq_rest"]
        d = d.drop_nulls(incs)
        allrows = st.filter(c("season") < min(OSC)).head(0)
        _ = allrows
        a = _ols_walk(d, incs, seasons=OSC, first=2015)
        b = _ols_walk(d, incs + ["dlt"], seasons=OSC, first=2015)
        d = d.with_columns(inc_=pl.Series(a), with_c=pl.Series(b)).filter(
            c("inc_").is_not_nan() & c("with_c").is_not_nan()
        )
        out(f"  {m}: {d.height} rows; the incumbent vs no change {_g(d, 'f0', 'inc_')}; the incumbent + the change "
            f"vs the incumbent {_g(d, 'inc_', 'with_c')}")  # fmt: skip


def _ols_walk_raw(df: pl.DataFrame, xcols: list[str], seasons) -> np.ndarray:
    """A walk-forward least-squares fit of `y` on `xcols` with no intercept (for residuals)."""
    pred = np.full(df.height, np.nan)
    s_arr = df["season"].to_numpy()
    X = np.column_stack([df[x].to_numpy() for x in xcols])
    y = df["y"].to_numpy()
    for s in seasons:
        tr, te = s_arr < s, s_arr == s
        if tr.sum() < 30 or te.sum() == 0:
            continue
        b, *_ = np.linalg.lstsq(X[tr], y[tr], rcond=None)
        pred[te] = X[te] @ b
    return pred


def _offseason_roles(out: K.Report, res: dict) -> None:
    """I126 and I136: does closeness on roles' table (season s) between a stayer and the departed
    player say who receives, where the group was left empty? Z: the departed shares weighted by a
    closeness kernel (mean 1), its slope on the plus-minus's residual fit on earlier pairs; P: the
    plus-minus alone (one pooled rate per pair of groups)."""
    from pcf.experts.vacated_opportunity import data as D

    out(
        "\n== I126 / I136: like-for-like on roles' table, skill stayers where the group was left empty"
    )
    ro = D.roles().select("gsis_id", "team", "season", *ROLE_COLS)
    for m, (st, deps, _) in res.items():
        x = pl.concat([st.filter(c("season") == s).select("gsis_id", "team", "season", "group", "pkey")
                       .join(dep, on=["team", "pkey"]) for s, dep in deps.items()])  # fmt: skip
        x = x.join(
            ro.rename({k: k + "_i" for k in ROLE_COLS}),
            on=["gsis_id", "team", "season"],
            how="inner",
        )
        x = x.join(
            ro.rename({"gsis_id": "j", **{k: k + "_j" for k in ROLE_COLS}}),
            on=["j", "team", "season"],
            how="inner",
        )
        x = x.with_columns(
            d=pl.sum_horizontal([(c(k + "_i") - c(k + "_j")) ** 2 for k in ROLE_COLS]).sqrt()
        )
        x = x.with_columns(k=(-c("d") / c("d").median()).exp())
        x = x.with_columns(k=c("k") / c("k").mean())
        z = x.group_by("gsis_id", "team", "season").agg(
            zx=(c("wj") * (c("k") - 1)).sum(), zd=c("d").min()
        )
        d = _off_rows(st.join(z, on=["gsis_id", "team", "season"], how="inner"), m, "empty")
        d = d.with_columns(y_obs=c("y"), y=c("y") - c("f_pm"))
        pz = _ols_walk_raw(d, ["zx"], OSC)
        d = d.with_columns(f_z=(c("f_pm") + pl.Series(pz)).clip(0, 1), y=c("y_obs")).filter(
            c("f_z").is_not_nan()
        )
        rk = (
            d.filter(c("season").is_in(OSC))
            .select(pl.corr(c("zd"), c("y") - c("f0"), method="spearman"))
            .item()
        )
        out(f"  {m}: {d.height} stayers with role tables; Z vs P {_g(d, 'f_pm', 'f_z')}; rank correlation of his "
            f"distance to the nearest departed player with his gain over no change {rk:+.3f}")  # fmt: skip


def _offseason_choice(out: K.Report, res: dict) -> None:
    """Method 3 in the offseason: the nested logit's diversion from season s's target (carry) and
    snap shares to the stayers' snap forecasts, the departed players' snaps set to 0."""
    from pcf.experts.vacated_opportunity import choice as C
    from pcf.experts.vacated_opportunity import data as D
    from pcf.experts.vacated_opportunity import rates as R

    out("\n== Method 3 in the offseason (the choice model's diversion), skill stayers left empty")
    t = choice_fits()
    ps = R.season_tops(D.player_games())
    snap_st = res["snap"][0].select("gsis_id", "team", "season", snap1="f_pm")
    nest_ix = {g: i for i, g in enumerate(C.NESTS)}
    for m in ("target", "carry"):
        st, deps, _ = res[m]
        ycol = {"target": "tgt_share", "carry": "car_share"}[m]
        d = t.filter(c("kind") == m)
        lams = C.walk_lams({r["season"]: np.array([r["lam_WR"], r["lam_TE"], r["lam_RB"]]) for r in d.iter_rows(named=True)},
                           [s + 1 for s in OSC])  # fmt: skip
        rows = []
        for s in OSC:
            stay = st.filter((c("season") == s) & c("group").is_in(list(C.NESTS))).select(
                "gsis_id", "team", "group", t0="f0"
            )
            dep = deps[s].select(gsis_id="j", team="team", group="group_j", t0="wj")
            mem = pl.concat(
                [stay.with_columns(gone=pl.lit(False)), dep.with_columns(gone=pl.lit(True))]
            )
            mem = mem.join(
                ps.filter(c("season") == s).select("gsis_id", "team", snap0="share"),
                on=["gsis_id", "team"],
                how="left",
            )
            mem = mem.join(
                snap_st.filter(c("season") == s).drop("season"), on=["gsis_id", "team"], how="left"
            )
            mem = mem.with_columns(snap0=c("snap0").fill_null(0.0),
                                   snap1=pl.when(c("gone")).then(0.0).otherwise(c("snap1").fill_null(c("snap0").fill_null(0.0))))  # fmt: skip
            for (_t,), g in mem.group_by("team"):
                nest = np.array([nest_ix[x] for x in g["group"].to_list()])
                new = C.divert(
                    g["t0"].to_numpy(),
                    g["snap0"].to_numpy(),
                    g["snap1"].to_numpy(),
                    nest,
                    lams[s + 1],
                )
                rows.append(
                    g.with_columns(f_choice=pl.Series(new), season=pl.lit(s, pl.Int32)).filter(
                        ~c("gone")
                    )
                )
        fc = (
            pl.concat(rows)
            .select("gsis_id", "team", "season", "f_choice")
            .unique(["gsis_id", "team", "season"])
        )
        sc = _off_rows(
            st.join(fc, on=["gsis_id", "team", "season"], how="left"), m, "empty"
        ).drop_nulls("f_choice")
        _ = ycol
        out(f"  {m}: {sc.height} rows; choice vs no change {_g(sc, 'f0', 'f_choice')}; choice vs the plus-minus "
            f"{_g(sc, 'f_pm', 'f_choice')}")  # fmt: skip


def _offseason_yardstick(out: K.Report, res: dict) -> None:
    from pcf.baselines.crude import yardstick as Y

    out(
        "\n== The yardstick (rest-of-season boards, scored on each team's first game of s + 1), beside participation;"
    )
    out(
        "   the input is the gated forecast's change (gated minus no change) for snap, target and carry share"
    )
    fg = _first_games()
    frame = None
    for m, (st, _, _) in res.items():
        d = st.with_columns(s1=c("season") + 1).join(
            fg.rename({"season": "s1"}), on=["team", "s1"], how="inner"
        )
        d = d.select("gsis_id", "game_id", (c("f_gate") - c("f0")).alias(f"off_{m}")).unique(
            ["gsis_id", "game_id"]
        )
        frame = (
            d
            if frame is None
            else frame.join(d, on=["gsis_id", "game_id"], how="full", coalesce=True)
        )
    for target in ("receiving", "rushing"):
        board = Y.load_board(target, "rest")
        assert set(board.keys) <= {"gsis_id", "game_id", "season", "week", "team"}, board.keys
        keys = board.features.select(board.keys)
        wk1 = keys.join(fg.select("game_id").unique(), on="game_id", how="semi")
        fr = keys.join(
            frame, on=[k for k in ("gsis_id", "game_id") if k in board.keys], how="left"
        ).fill_null(0.0)
        r = Y.score_input(
            board, fr, "vacated-offseason", fill=0.0, rows=wk1, beside=("participation",), copies=19
        )
        out(f"  {target}: {100 * r['alone']:+.2f}% (90% {100 * r['alone_lo']:+.2f} to {100 * r['alone_hi']:+.2f}) on "
            f"{r['rows']} week-1 rows; range score {100 * r['range_alone']:+.2f}%; copies' best "
            f"{100 * r['copies_max']:+.2f}%; counts: {r['counts']}")  # fmt: skip
        out.metric(f"off_yardstick_{target}", r["alone"])


def _offseason_history(res: dict) -> None:
    from pcf.core import tracking
    from pcf.core.contract import UTC_TIME, check_output
    from pcf.data.gateway import Gateway
    from pcf.data.timeline.moments import season_ends, season_moments

    cal = Gateway().calendar
    mom = season_moments(cal).select(
        s1=c("season").cast(pl.Int32), as_of=c("moment").cast(UTC_TIME)
    )
    ends = pl.DataFrame({"season": list(season_ends(cal).keys()), "train_end": list(season_ends(cal).values())}).with_columns(
        season=c("season").cast(pl.Int32), train_end=c("train_end").cast(UTC_TIME))  # fmt: skip
    parts = []
    for m, (st, _, _) in res.items():
        rr = pl.read_parquet(K.cache_dir() / f"offseason_{m}.parquet")
        d = st.filter(c("season").is_in(OSC)).join(rr, on=["gsis_id", "team", "season"], how="left")
        parts.append(d.select("gsis_id", "team", "season", "group", quantity=pl.lit(K.QUANTITY[m]), mean="f_champ", champion="champ",
                              q10="q10", q50="q50", q90="q90", no_change="f0", plus_minus="f_pm", change=c("f_gate") - c("f0"), intake="intake",
                              departed_share="V"))  # fmt: skip
    h = pl.concat(parts).with_columns(
        q10=pl.min_horizontal("q10", "mean"), q90=pl.max_horizontal("q90", "mean")
    )
    h = h.with_columns(q50=c("q50").clip(c("q10"), c("q90")))
    h = (
        h.join(ends, on="season", how="left")
        .with_columns(s1=c("season") + 1)
        .join(mom, on="s1", how="left")
    )
    h = h.rename({"season": "last_season"}).rename({"s1": "season"})
    with tracking.attempt(
        OFF, train_end=h["train_end"].max(), name="vacated-offseason v1 (gated plus-minus)"
    ) as run:
        rid = run.info.run_id
        h = h.with_columns(model=pl.lit(OFF), model_version=pl.lit("backtest"), run_id=pl.lit(rid),
                           cadence=pl.lit("offseason_events"))  # fmt: skip
        check_output(h, ["gsis_id", "team", "season"])
        folder = get_config().zone("outputs") / OFF / rid
        folder.mkdir(parents=True, exist_ok=True)
        h.write_parquet(folder / "history.parquet")
        import mlflow

        mlflow.log_artifact(str(K.report_dir() / "offseason.txt"))
        tracking.log_metrics({"rows": float(h.height)})
    print(f"offseason history: {folder / 'history.parquet'} ({h.height:,} rows); run {rid}")


# ---------------------------------------------------------------- the CEO's spot-check (2026-11-26)
def spot_target_shrink(copies: int = 19) -> None:
    """The shrink on target share, in depth (the CEO, 2026-11-26: "Can yo please spot check the
    shrink on target?"). Odds in `build/PREREG.md`, written first."""
    from pcf.experts.vacated_opportunity import offseason as O

    m = "target"
    out = K.Report("spot_target_shrink")
    out("The CEO's spot-check: vacated-offseason's shrunk target share (I165). Stayers 2017-2024 (pairs s -> s + 1);")
    out("gains are the share of the reference's squared error removed, 90% team bootstrap.")
    fits = offseason_fits(m)
    st, deps = O.build(m, fits)
    st, slopes = shrink(st, m)
    b = slopes["empty"]
    out("\n== 1. How the slope is fit and when it's known")
    out("  slope = sum(change x (actual - no change)) / sum(change^2), through the origin, over the skill stayers")
    out("  left empty of every earlier pair; the pair s -> s + 1 reads only pairs t -> t + 1 with t < s, whose")
    out("  season t + 1 <= s ended before season s + 1's week 1 (the event). Where a top player came in, no change.")
    for s in OSC:
        n = st.filter((c("season") < s) & c("y").is_not_null() & c("group").is_in(list(K.SKILL)) & ~c("intake")).height
        out(f"  {s + 1}: slope {b[s]:.3f}, fit on pairs {PAIRS_ALL[0]}->{PAIRS_ALL[0] + 1} to {s - 1}->{s} ({n} rows)")
    sc_all, sc_e = _off_rows(st, m, "all"), _off_rows(st, m, "empty")
    out("\n== 2. The result")
    out(f"  every stayer ({sc_all.height} rows): shrunk vs no change {_g(sc_all, 'f0', 'f_shr')}; unshrunk {_g(sc_all, 'f0', 'f_gate')}")
    out(f"  left empty ({sc_e.height} rows): shrunk vs no change {_g(sc_e, 'f0', 'f_shr')}; vs unshrunk {_g(sc_e, 'f_pm', 'f_shr')}")
    moved = sc_all.filter((c("f_shr") - c("f0")).abs() > 1e-9)
    out(f"  rows it moves: {moved.height} ({100 * moved.height / sc_all.height:.0f}%); mean change "
        f"{moved.select((c('f_shr') - c('f0')).mean()).item():+.4f}, mean |change| "
        f"{moved.select((c('f_shr') - c('f0')).abs().mean()).item():.4f} (target share); actual minus no change on "
        f"them {moved.select((c('y') - c('f0')).mean()).item():+.4f}")  # fmt: skip
    out("\n== 3. By season and by group (every stayer)")
    for s in OSC:
        d = sc_all.filter(c("season") == s)
        out(f"  {s + 1}: {d.height} rows, shrunk vs no change {_g(d, 'f0', 'f_shr')}")
    pos = sum(_gain(sc_all.filter(c("season") == s), "f0", "f_shr")[0] > 0 for s in OSC)
    out(f"  positive in {pos} of {len(OSC)} seasons")
    for grp in K.SKILL:
        d = sc_all.filter(c("group") == grp)
        e = sc_e.filter(c("group") == grp)
        out(f"  {grp}: every stayer {d.height} rows {_g(d, 'f0', 'f_shr')}; left empty {e.height} rows {_g(e, 'f0', 'f_shr')}")
    tot = ((sc_all["y"] - sc_all["f0"]) ** 2 - (sc_all["y"] - sc_all["f_shr"]) ** 2).sum()
    for grp in K.SKILL:
        d = sc_all.filter(c("group") == grp)
        part = ((d["y"] - d["f0"]) ** 2 - (d["y"] - d["f_shr"]) ** 2).sum()
        out(f"    {grp}'s share of the error removed: {100 * part / tot:.0f}%")
    out("\n== 4. How close to zero: each season dropped in turn (every stayer)")
    lows = []
    for s in OSC:
        g = _gain(sc_all.filter(c("season") != s), "f0", "f_shr")
        lows.append(g[1])
        out(f"  without {s + 1}: {K.fmt_gain(g)}")
    out(f"  interval above 0 in {sum(x > 0 for x in lows)} of {len(OSC)} drops")
    out("\n== 5. What the slope costs: walk-forward against hindsight and fixed slopes")
    sh, bh = shrink(st.drop("f_shr", "slope_"), m, hindsight=True)
    sh = _off_rows(sh, m, "all").select("gsis_id", "team", "season", f_hind="f_shr")
    d = sc_all.join(sh, on=["gsis_id", "team", "season"])
    out(f"  hindsight slope {bh['empty'][OSC[0]]:.3f} (every pair): vs no change {_g(d, 'f0', 'f_hind')}; "
        f"vs walk-forward {_g(d, 'f_shr', 'f_hind')}")  # fmt: skip
    for k in (0.25, 0.5, 0.75, 1.0):
        d2 = d.with_columns(f_k=pl.when(c("f_shr") != c("f0")).then((c("f0") + k * (c("f_pm") - c("f0"))).clip(0, 1))
                            .otherwise(c("f0")))  # fmt: skip
        out(f"  fixed slope {k:.2f}: vs no change {_g(d2, 'f0', 'f_k')}")
    out(f"\n== 6. No noise: {copies} copies, each season's departures moved to another team, the slope refit on them")
    real = _gain(sc_all, "f0", "f_shr")[0]
    real_e = _gain(sc_e, "f0", "f_shr")[0]
    nulls, nulls_e = [], []
    for k in range(copies):
        s2 = _reforecast(st, O.shuffled_departures(deps, get_config().seed + 900 + k), fits, m)
        s2, _ = shrink(s2, m)
        nulls.append(_gain(_off_rows(s2, m, "all"), "f0", "f_shr")[0])
        nulls_e.append(_gain(_off_rows(s2, m, "empty"), "f0", "f_shr")[0])
    out(f"  every stayer: real {100 * real:+.2f}%; copies' best {100 * max(nulls):+.2f}%, mean "
        f"{100 * np.mean(nulls):+.2f}%; beats {sum(real > v for v in nulls)} of {copies}")  # fmt: skip
    out(f"  left empty: real {100 * real_e:+.2f}%; copies' best {100 * max(nulls_e):+.2f}%, mean "
        f"{100 * np.mean(nulls_e):+.2f}%; beats {sum(real_e > v for v in nulls_e)} of {copies}")  # fmt: skip
    out.save()
