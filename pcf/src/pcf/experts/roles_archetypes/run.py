"""The build's run (decision 0048): both role spaces walk-forward, the named roles, every brief
test, the saved history and the report.

    python -m pcf.experts.roles_archetypes.run            # everything, logged to MLflow
    python -m pcf.experts.roles_archetypes.run --no-log   # the report only

The history (`outputs/roles-archetypes/<run_id>/history.parquet`, pinned in the registry's
`history_runs`) has one row per player-team-season and side, 2016-2024: the six coordinates of his
side's space with 90% intervals, the shrinkage weight, the named role, its coarse role and how
sure, the role table's features, the space's version, and `as_of` / `train_end` (when the
season's participation was known) and `cadence` (retrospective), so an in-season model reads a
season only once it's finished (rule m).
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.core.log import get_logger
from pcf.experts.roles_archetypes import data as D
from pcf.experts.roles_archetypes import embed as E
from pcf.experts.roles_archetypes import evaluate as V
from pcf.experts.roles_archetypes import features as F
from pcf.experts.roles_archetypes import named as N
from pcf.experts.roles_archetypes import space as S
from pcf.experts.roles_archetypes.counts import SIDES

log = get_logger(__name__)
c = pl.col
PROJECT = "roles-archetypes"
SEEDS = (0, 1, 2)
COPIES = 19
REPORT = Path(__file__).resolve().parents[4] / "projects" / PROJECT / "build" / "report.txt"


class Report:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.metrics: dict[str, float] = {}

    def __call__(self, *text: str) -> None:
        for t in text:
            self.lines.append(t)
            print(t, flush=True)

    def metric(self, name: str, value: float) -> None:
        self.metrics[name] = float(value)


# ---------------------------------------------------------------- the spaces
def build_spaces(fe: pl.DataFrame, out: Report) -> dict:
    """Both sides: the walk-forward PCA, the frozen 2016-2020 PCA, the autoencoders (walk-forward
    and frozen, `SEEDS` averaged)."""
    res = {}
    for side in SIDES:
        placed, fits = S.walk(fe, side, F.SPACE[side], D.SEASONS)
        frozen = S.fit_space(fe, side, F.SPACE[side], D.FIT)
        frozen_placed = S.place(frozen, fe.filter(c("side") == side))
        ae = E.walk(fe, fits, SEEDS)
        ae_frozen = [E.fit_embedding(fe, frozen, s) for s in SEEDS]
        res[side] = dict(placed=placed, fits=fits, frozen=frozen, frozen_placed=frozen_placed,
                         ae=ae, ae_frozen=ae_frozen)  # fmt: skip
        out(f"\n== {side}: the pooled space (frozen fit 2016-2020; {', '.join(SIDES[side])})")
        out("  explained share per axis: " + ", ".join(f"{v:.2f}" for v in frozen.explained)
            + f" (total {frozen.explained.sum():.2f}); the autoencoder reconstructs "
            + ", ".join(f"{E.explained(a):.2f}" for a in ae_frozen) + " (seeds)")  # fmt: skip
        for i, a in enumerate(frozen.axes):
            load = frozen.loadings[i]
            top = np.argsort(-np.abs(load))[:5]
            out(f"  {a}: " + ", ".join(f"{frozen.features[j]} {load[j]:+.2f}" for j in top))
        congr = []
        vs = sorted(fits)
        for a, b in zip(vs[:-1], vs[1:], strict=True):
            la, lb = fits[a].loadings, fits[b].loadings
            congr.append(np.abs((la * lb).sum(1)))
        cg = np.array(congr)
        out(
            "  refits rotated to the last (Procrustes): each axis's loading congruence with the "
            "previous fit, min over 2017-2024: " + ", ".join(f"{v:.2f}" for v in cg.min(0))
        )
        out("  and against the frozen 2016-2020 fit, the 2024 fit: " + ", ".join(
            f"{v:.2f}" for v in np.abs((fits[2024].loadings * frozen.loadings).sum(1))
        ))  # fmt: skip
        last = fits[max(fits)]
        out(f"  the published axes (the walk's {last.version} fit, every refit rotated to the one "
            "before; how the history's z0-z5 read):")  # fmt: skip
        for i, a in enumerate(last.axes):
            load = last.loadings[i]
            top = np.argsort(-np.abs(load))[:5]
            out(f"    {a}: " + ", ".join(f"{last.features[j]} {load[j]:+.2f}" for j in top))
        out("  group means (frozen fit, 200+ snaps):")
        for g, m in sorted(frozen.group_means.items()):
            out(f"    {g:4} " + " ".join(f"{v:+.2f}" for v in m))
    return res


def ae_place_frozen(fe: pl.DataFrame, embs: Sequence[E.Embedding], side: str) -> pl.DataFrame:
    rows = fe.filter(c("side") == side)
    placed = [E.place(e, rows) for e in embs]
    axes = embs[0].axes
    mean = np.mean([p.select(axes).to_numpy() for p in placed], axis=0)
    return placed[0].with_columns(pl.Series(a, mean[:, i]) for i, a in enumerate(axes))


# ---------------------------------------------------------------- test 1
def test_consistency(fe: pl.DataFrame, sp: dict, out: Report) -> None:
    out("\n== Test 1: consistency, held out (the frozen 2016-2020 fit read on 2021-2024)")
    out("  pass: 4+ of 6 axes at split-half 0.5+ centred within position, and movers keep at "
        "least half of the season r of each axis that repeats (the CEO's reading, "
        "2026-11-25)")  # fmt: skip
    for side in SIDES:
        s = sp[side]
        axes = s["frozen"].axes
        t = V.consistency(s["frozen_placed"], axes, D.SCORED)
        ae = V.consistency(ae_place_frozen(fe, s["ae_frozen"], side), s["ae_frozen"][0].axes,
                           D.SCORED)  # fmt: skip
        table = V.consistency(fe.filter(c("side") == side), N.TABLE[side], D.SCORED)
        n_ok = int((t["split_half_centred"] >= 0.5).sum())
        # the CEO's reading (2026-11-25, settled after run 696a3f0b): movers keep at least half of
        # the season r of each component that repeats (centred split-half 0.5+)
        kept_ok = bool((t.filter(c("split_half_centred") >= 0.5)["kept"] >= 0.5).all())
        strict = bool((t["kept"] >= 0.5).all())
        out(f"  {side} PCA ({t['n_halves'][0]} player-seasons with halves, {t['n_pairs'][0]} "
            f"pairs, {t['n_movers'][0]} movers):")  # fmt: skip
        for r in t.iter_rows(named=True):
            out(f"    {r['axis']}: split-half {r['split_half']:.2f}, centred "
                f"{r['split_half_centred']:.2f}; season r {r['season_r']:.2f}, movers "
                f"{r['movers_r']:.2f} (kept {r['kept']:.0%})")  # fmt: skip
        out(f"    -> {n_ok} of 6 centred at 0.5+; movers keep half on every repeating axis: "
            f"{kept_ok} (on every axis: {strict}); "
            f"TEST 1 {'PASSES' if n_ok >= 4 and kept_ok else 'FAILS'}")  # fmt: skip
        out("    autoencoder (3 seeds averaged), centred split-half: "
            + ", ".join(f"{v:.2f}" for v in ae["split_half_centred"]) + "; movers r: "
            + ", ".join(f"{v:.2f}" for v in ae["movers_r"]))  # fmt: skip
        out("    role table, centred split-half: " + ", ".join(
            f"{a} {v:.2f}" for a, v in zip(table["axis"], table["split_half_centred"],
                                           strict=True)) + "; movers r: " + ", ".join(
            f"{v:.2f}" for v in table["movers_r"]))  # fmt: skip
        out.metric(f"t1_{side}_centred_ok", n_ok)
        cov = V.interval_coverage(s["frozen_placed"], axes, D.SCORED)
        out("    interval check (two halves inside their combined 90%, should be ~90%): "
            + ", ".join(f"{a} {v:.0%}" for a, v in cov.items()))  # fmt: skip


# ---------------------------------------------------------------- tests 2 and 3
def ladder_rows(fe: pl.DataFrame, cnt: pl.DataFrame, sp: dict, labels: pl.DataFrame, side: str
                ) -> tuple[pl.DataFrame, dict[str, list[str]]]:  # fmt: skip
    """The season pairs with every input set (walk-forward coordinates and codes)."""
    s = sp[side]
    base = fe.filter((c("side") == side) & (c("half") == "all"))
    z = s["placed"].filter(c("half") == "all").select(*S.PAIR, *s["frozen"].axes)
    ae_axes = [a for a in s["ae"].columns if a[1:2] == "e" and a[2:].isdigit()]
    e = s["ae"].filter(c("half") == "all").select(*S.PAIR, *ae_axes)
    roles = N.ROLES[side]
    lab = (
        labels.filter(c("half") == "all")
        .select(*S.PAIR, "role")
        .with_columns(
            (c("role") == r).cast(pl.Float64).alias(f"r_{i}") for i, r in enumerate(roles)
        )
        .drop("role")
    )
    rows = base.join(z, on=S.PAIR).join(e, on=S.PAIR).join(lab, on=S.PAIR)
    rows = V.pairs(V.main_rows(rows), V.season_totals(cnt), side)
    rows = pl.concat([rows, V.position_dummies(rows, side)], how="horizontal")
    own = [f"own_{t}" for t in V.TARGETS[side]] + ["snap_share"]
    sets = {
        "P": [f"is_{g}" for g in SIDES[side][1:]],
        "T": [*N.TABLE[side], *[f"r_{i}" for i in range(len(roles))]],
        "Z": s["frozen"].axes,
        "E": ae_axes,
        "O": own,
    }
    return rows, sets


def test_ladder(rows: pl.DataFrame, sets: dict, side: str, out: Report) -> dict:
    P, T, Z, Ev, Own = (sets[k] for k in "PTZEO")
    ids = rows["gsis_id"].to_numpy()
    sc = D.SCORED
    res = {}
    n = rows.filter(c("target_season").is_in(list(sc))).height
    out(f"\n== Tests 2 and 3, {side}: next season's per-snap rates, walk-forward, scored on "
        f"target seasons 2021-2024 ({n} pairs; {rows.height} with training)")  # fmt: skip
    for tgt in V.TARGETS[side]:
        y = rows[f"y_{tgt}"].to_numpy()
        L = lambda cols, f=V.LASSO, t=tgt: V.walk(rows, cols, f"y_{t}", f, sc)  # noqa: E731
        p = {
            "P": L(P), "T": L([*P, *T]), "Z": L(Z), "PZ": L([*P, *Z]), "Ztrees": L(Z, V.TREES),
            "E": L(Ev), "B": L([*P, *Own]), "BT": L([*P, *Own, *T]), "BZ": L([*P, *Own, *Z]),
            "BZtrees": L([*P, *Own, *Z], V.TREES), "BE": L([*P, *Own, *Ev]),
        }  # fmt: skip
        g = lambda a, b, y=y, p=p: V.gain(y, p[a], p[b], ids)  # noqa: E731
        name = V.TARGET_NAMES[tgt]
        rows_ = [
            ("test 2: position labels -> coordinates", "P", "Z"),
            ("  rung 1: position labels -> labels + role table and named roles", "P", "T"),
            ("  rung 2: role table -> coordinates (a tie goes to the table)", "T", "Z"),
            ("  rung 3: coordinates -> trees on the coordinates (a tie goes to the lasso)", "Z",
             "Ztrees"),
            ("  rung 4: coordinates -> the autoencoder's codes (a tie goes to PCA)", "Z", "E"),
            ("test 3: labels + his own rates -> + coordinates (the no-noise target)", "B", "BZ"),
            ("  labels + own rates -> + role table", "B", "BT"),
            ("  + role table -> + coordinates instead (a tie goes to the table)", "BT", "BZ"),
            ("  + coordinates -> trees on them (a tie goes to the lasso)", "BZ", "BZtrees"),
            ("  + coordinates -> + autoencoder instead (a tie goes to PCA)", "BZ", "BE"),
        ]  # fmt: skip
        out(f"  {name} (error of the labels alone {np.nanmean((y - p['P']) ** 2):.3g}):")
        for label, a, b in rows_:
            r = g(a, b)
            res[(tgt, a, b)] = r
            out(f"    {label}: {r.line()}")
            out.metric(f"t23_{tgt}_{a}_{b}", r.share)
        sig = V.signal(rows, Z, f"y_{tgt}", sc)
        out(f"    signal: the coordinates' lasso error {sig['mse']:.4g} against 20 refits on "
            f"targets shuffled within season and position (best {sig['null_best']:.4g}): beats "
            f"{sig['beaten']} of {sig['n']} (needs 20)")  # fmt: skip
        res[(tgt, "signal")] = sig
    return res


# ---------------------------------------------------------------- test 4: the yardstick
def priors(sp: dict, fe: pl.DataFrame, side: str = "offense") -> pl.DataFrame:
    """Each player-season's main-team coordinates and table features as a prior for the next
    season (season = the season it's a prior for)."""
    s = sp[side]
    z = s["placed"].filter(c("half") == "all").select(*S.PAIR, "snaps", *s["frozen"].axes)
    t = fe.filter((c("side") == side) & (c("half") == "all")).select(*S.PAIR, *N.TABLE[side])
    m = V.main_rows(z.join(t, on=S.PAIR).with_columns(half=pl.lit("all")))
    return m.select("gsis_id", "group", *s["frozen"].axes,
                    *[c(x).alias(f"t_{x}") for x in N.TABLE[side]],
                    season=c("season") + 1)  # fmt: skip


def _shuffled_prior(prior: pl.DataFrame, cols: Sequence[str], seed: int) -> pl.DataFrame:
    """The prior's columns moved together to another player of the same season and group."""
    rng = np.random.default_rng(seed)
    key = (prior["season"].cast(pl.String) + prior["group"]).to_numpy()
    order = np.arange(prior.height)
    for k in np.unique(key):
        idx = np.flatnonzero(key == k)
        order[idx] = idx[rng.permutation(len(idx))]
    moved = prior.select(cols)[order]
    return pl.concat([prior.select("gsis_id", "season"), moved], how="horizontal")


def test_yardstick(prior: pl.DataFrame, axes: Sequence[str], out: Report) -> dict:
    from pcf.baselines.crude import yardstick as Y

    out("\n== Test 4: the yardstick (crude forecaster, rest-of-season boards, beside "
        "participation; 19 copies shuffled within season and position)")  # fmt: skip
    res = {}
    table = [f"t_{x}" for x in N.TABLE["offense"]]
    for target in ("receiving", "rushing"):
        board = Y.load_board(target, "rest")
        keys = board.keys
        rows = board.features.select(*keys, "season")
        for name, cols in (("coordinates", list(axes)), ("role table", table)):
            frame = rows.join(prior.select("gsis_id", "season", *cols), on=["gsis_id", "season"],
                              how="left").drop("season")  # fmt: skip
            r = Y.score_input(board, frame, f"roles {name}", beside=("participation",))
            nulls = []
            for k in range(COPIES):
                sh = _shuffled_prior(prior, cols, get_config().seed + 5000 + k)
                fr = rows.join(sh, on=["gsis_id", "season"], how="left").drop("season")
                nulls.append(
                    Y.score_input(board, fr, f"copy {k}", beside=("participation",))["alone"]
                )
            counts = r["alone_lo"] > 0 and r["alone"] > max(nulls)
            out(f"  {target:9} {name:12}: {100 * r['alone']:+.2f}% of the squared error "
                f"(90% {100 * r['alone_lo']:+.2f} to {100 * r['alone_hi']:+.2f}); range score "
                f"{100 * r['range_alone']:+.2f}%; copies' best {100 * max(nulls):+.2f}%; "
                f"{r['verdict']}; counts: {counts} ({r['rows']} rows)")  # fmt: skip
            res[(target, name)] = (r, max(nulls), counts)
            out.metric(f"t4_{target}_{name.replace(' ', '_')}", r["alone"])
    return res


# ---------------------------------------------------------------- test 5: named roles
def test_named(fe: pl.DataFrame, games: pl.DataFrame, sp: dict, out: Report
               ) -> tuple[pl.DataFrame, dict]:  # fmt: skip
    fit = fe.filter((c("half") == "all") & (c("snaps") >= S.MIN_SNAPS) & c("season").is_in(D.FIT))
    cuts = N.fit_cuts(fit)
    noise = N.feature_noise(fe, fit, sorted({x.feature for x in cuts.values()}))
    labels = N.name_roles(fe, cuts, noise)
    out("\n== Test 5: named roles (rules set on 2016-2020, frozen)")
    for k in cuts.values():
        out(f"  cut {k.name}: {k.feature} at {k.value:.4g} ({k.how})")
    full = labels.filter((c("half") == "all") & (c("snaps") >= S.MIN_SNAPS))
    pivot = (full.group_by("role", "group").len()
             .pivot(on="group", index="role", values="len").fill_null(0))  # fmt: skip
    groups = [g for side in SIDES.values() for g in side if g in pivot.columns]
    out("  player-seasons (200+ snaps, 2016-2024) by role and depth-chart group:")
    out("    " + " ".join(f"{g:>5}" for g in groups))
    for r in [x for side in N.ROLES.values() for x in side]:
        row = pivot.filter(c("role") == r)
        if row.height:
            out("    " + " ".join(f"{row[g][0]:5d}" for g in groups) + f"  {r}")
    res = {}
    for level in ("role", "coarse"):
        f = V.flips(labels, D.SCORED, level)
        med = float(f["flip"].median())
        res[level] = med
        out(f"  flips between halves, {level}, 2021-2024, median group {med:.1%} (bar 14%): "
            + ", ".join(f"{g} {v:.0%}" for g, v in zip(f["group"], f["flip"], strict=True))
            + f" -> {'PASSES' if med < 0.14 else 'FAILS'}")  # fmt: skip
        out.metric(f"t5_flips_{level}", med)
    cal = V.sure_calibration(labels, D.SCORED)
    out(
        "  how sure, calibrated? (both halves' sure multiplied against how often they agreed, "
        "2021-2024): "
        + "; ".join(
            f"{r['from']:.2f}-{r['to']:.2f}: said {r['said']:.2f}, held "
            f"{r['held']:.2f} (n {r['n']})"
            for r in cal.iter_rows(named=True)
        )
    )
    for side in SIDES:
        s = sp[side]
        axes = s["frozen"].axes
        prior = V.main_rows(s["placed"]).select("gsis_id", *axes, season=c("season") + 1)
        sub = V.substitutes(games.filter(c("side") == side), prior, axes)
        res[f"subs_{side}"] = sub
        # sensitivity (reported, not the verdict): each axis scaled to unit sd within position,
        # so the axes that separate positions don't dominate a within-position distance
        sd = prior.join(V.main_rows(s["placed"]).select("gsis_id", "group", season=c("season") + 1),
                        on=["gsis_id", "season"])  # fmt: skip
        scaled = sd.with_columns((c(a) / c(a).std().over("group")).alias(a) for a in axes)
        alt = V.substitutes(games.filter(c("side") == side), scaled.drop("group"), axes)
        out(f"    sensitivity, axes scaled within position: rank {alt['rank']:.3f} (90% "
            f"{alt['lo']:.3f} to {alt['hi']:.3f})")  # fmt: skip
        out(f"  like-for-like substitutes, {side} (prior-season coordinates; chance 0.5): rank "
            f"{sub['rank']:.3f} (90% {sub['lo']:.3f} to {sub['hi']:.3f}), {sub['events']} "
            f"events; " + ", ".join(f"{g} {v:.2f}" for g, v in sub["by_group"].items())
            + f" -> {'PASSES' if sub['hi'] < 0.5 else 'FAILS'}")  # fmt: skip
        out.metric(f"t5_subs_{side}", sub["rank"])
    return labels, res


# ---------------------------------------------------------------- the history
def history(fe: pl.DataFrame, cnt: pl.DataFrame, sp: dict, labels: pl.DataFrame) -> pl.DataFrame:
    """The published rows: one per player-team-season and side, 2016-2024 (module docstring)."""
    known = cnt.group_by("season").agg(as_of=c("known_at").max())
    out = []
    for side in SIDES:
        s = sp[side]
        axes = s["frozen"].axes
        cols = [x for a in axes for x in (a, f"{a}_lo", f"{a}_hi")]
        z = s["placed"].filter(c("half") == "all").select(*S.PAIR, "snaps", *cols, "shrink_w",
                                                          "version")  # fmt: skip
        z = z.rename(
            {a: f"z{i}" for i, a in enumerate(axes)}
            | {f"{a}_{e}": f"z{i}_{e}" for i, a in enumerate(axes) for e in ("lo", "hi")}
        )
        t = fe.filter((c("side") == side) & (c("half") == "all")).select(
            *S.PAIR, *[c(x).alias(f"t{i}_{x}") for i, x in enumerate(N.TABLE[side])]
        )
        lab = labels.filter(c("half") == "all").select(*S.PAIR, "role", "coarse", "sure")
        out.append(z.join(t, on=S.PAIR).join(lab, on=S.PAIR))
    h = pl.concat(out, how="diagonal_relaxed").join(known, on="season")
    return h.with_columns(train_end=c("as_of"), cadence=pl.lit("retrospective"),
                          season=c("season").cast(pl.Int32)).sort("season", "side", "team",
                                                                   "gsis_id")  # fmt: skip


def sanity(h: pl.DataFrame, names: pl.DataFrame, out: Report, season: int = 2024) -> None:
    """The CEO's lists: each axis's top and bottom 10 in the last season (200+ snaps)."""
    out(f"\n== Sanity lists: each axis's top and bottom 10, {season}, 200+ snaps")
    h = h.filter((c("season") == season) & (c("snaps") >= S.MIN_SNAPS)).join(
        names, on="gsis_id", how="left"
    )
    for side in SIDES:
        hs = h.filter(c("side") == side)
        for i in range(S.K):
            z = f"z{i}"
            top = hs.sort(z, descending=True).head(10)
            bot = hs.sort(z).head(10)
            out(f"  {side[0]}z{i} top: {_names(top)}")
            out(f"  {side[0]}z{i} bottom: {_names(bot)}")


def _names(d: pl.DataFrame) -> str:
    return ", ".join(f"{n} ({g} {t})" for n, g, t in zip(d["name"], d["group"], d["team"],
                                                         strict=True))  # fmt: skip


def player_names() -> pl.DataFrame:
    from pcf.data.gateway import END_OF_TIME, Gateway, TableSource

    out = []
    for s in D.SEASONS:
        v = Gateway(TableSource(seasons=[s])).view(END_OF_TIME, "retrospective",
                                                   {"player_game": ("roster",)})  # fmt: skip
        out.append(v.table("player_game", seasons=[s]).select("gsis_id", name="full_name"))
    return pl.concat(out).drop_nulls().unique("gsis_id", keep="last")


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-log", action="store_true", help="the report only: no MLflow run")
    ap.add_argument("--no-yardstick", action="store_true")
    args = ap.parse_args(argv)
    out = Report()
    cnt, games = D.counts()
    fe = D.walk_features(cnt)
    out(f"roles-archetypes build: {cnt.filter(c('half') == 'all').height:,} player-team-seasons, "
        f"{fe.filter((c('half') == 'all') & (c('snaps') >= S.MIN_SNAPS)).height:,} with 200+ "
        f"snaps, 2016-2024 (the 2025 vault untouched)")  # fmt: skip
    sp = build_spaces(fe, out)
    test_consistency(fe, sp, out)
    labels, named_res = test_named(fe, games, sp, out)
    ladder = {}
    for side in SIDES:
        rows, sets = ladder_rows(fe, cnt, sp, labels, side)
        ladder[side] = test_ladder(rows, sets, side, out)
    if not args.no_yardstick:
        test_yardstick(priors(sp, fe), sp["offense"]["frozen"].axes, out)
    h = history(fe, cnt, sp, labels)
    sanity(h, player_names(), out)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(out.lines) + "\n", encoding="utf-8")
    if args.no_log:
        return
    from pcf.core import tracking

    train_end = h["train_end"].max()
    with tracking.attempt(PROJECT, train_end=train_end, name="roles-retro v1",
                          params={"k": S.K, "min_snaps": S.MIN_SNAPS, "seeds": len(SEEDS),
                                  "fit": "2016-2020 frozen; walk 2016-2024"}) as run:  # fmt: skip
        folder = get_config().zone("outputs") / PROJECT / run.info.run_id
        folder.mkdir(parents=True, exist_ok=True)
        h.write_parquet(folder / "history.parquet")
        tracking.log_metrics(out.metrics)
        tracking.log_text("\n".join(out.lines), "report.txt")
        print(f"\nhistory: {folder / 'history.parquet'} ({h.height:,} rows); run {run.info.run_id}")


if __name__ == "__main__":
    main()
