"""The brief's tests (roles-archetypes BRIEF.md, "Tests"; decision 0048).

1. `consistency`: the frozen 2016-2020 fit read on 2021-2024: each axis's split-half r, centred
   within position, and its season r for everyone and for movers.
2. and 3. `ladder`: next season's per-snap rates (targets and carries per snap; tackles and rushes
   per pass snap), walk-forward by target season (trained on earlier target seasons only, scored
   2021-2024), from position labels against the role table, the pooled coordinates, trees on them
   and the autoencoder's codes; and the same beyond his own last-season rates and snap share.
   Gains are the share of the simpler side's squared error removed, with 90% intervals from
   resampled players. A tie (interval across 0) goes to the simpler side.
   `signal`: the coordinates' model against 20 refits on targets shuffled within season and
   position (it must beat all 20).
4. `yardstick` (in `run`): the crude forecaster's rest-of-season boards.
5. `flips` and `substitutes`: named roles' flips between a season's halves, and like-for-like
   substitutes on the pooled space (H101's test on the build's walk-forward coordinates).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingRegressor

from pcf.baselines.lasso import fit_lasso, predict_lasso, weighted_mse
from pcf.config import get_config
from pcf.experts.roles_archetypes.counts import SIDES

c = pl.col
DRAWS = 2000
PAIR = ["gsis_id", "team", "season", "side", "group"]
ALPHAS = np.geomspace(0.3, 1e-4, 14)  # on a standardized target
TARGETS = {"offense": ("tps", "cps"), "defense": ("tkl", "rpp")}
TARGET_NAMES = {"tps": "targets per snap", "cps": "carries per snap", "tkl": "tackles per snap",
                "rpp": "rushes per pass snap"}  # fmt: skip
MIN_SNAPS = 200


def _r(x: np.ndarray, y: np.ndarray) -> float:
    return float(np.corrcoef(x, y)[0, 1])


def _centre(x: np.ndarray, g: np.ndarray) -> np.ndarray:
    out = x.copy()
    for k in np.unique(g):
        out[g == k] -= x[g == k].mean()
    return out


def main_rows(placed: pl.DataFrame) -> pl.DataFrame:
    """Each player-season's main team (most snaps), full seasons only."""
    return (placed.filter(c("half") == "all").sort("snaps", descending=True)
            .unique(["gsis_id", "season", "side"], keep="first"))  # fmt: skip


# ---------------------------------------------------------------- 1. consistency
def consistency(placed: pl.DataFrame, axes: Sequence[str], seasons: Sequence[int]) -> pl.DataFrame:
    """Per axis, on `seasons`: split-half r (raw and centred within position) on 200+ snap
    player-seasons, and season r (s to s + 1, both in `seasons`) for everyone and for movers."""
    full = placed.filter((c("half") == "all") & (c("snaps") >= MIN_SNAPS)
                         & c("season").is_in(list(seasons)))  # fmt: skip
    od, ev = placed.filter(c("half") == "odd"), placed.filter(c("half") == "even")
    sh = full.select(PAIR).join(od, on=PAIR).join(ev, on=PAIR, suffix="_e")
    m = main_rows(full)
    nxt = m.select("gsis_id", "side", season=c("season") - 1, team_n=c("team"),
                   **{f"{a}_n": c(a) for a in axes})  # fmt: skip
    pairs = m.join(nxt, on=["gsis_id", "season", "side"])
    movers = pairs.filter(c("team") != c("team_n"))
    g = sh["group"].to_numpy()
    rows = []
    for a in axes:
        x, y = sh[a].to_numpy(), sh[f"{a}_e"].to_numpy()
        rows.append({
            "axis": a, "split_half": _r(x, y),
            "split_half_centred": _r(_centre(x, g), _centre(y, g)),
            "season_r": _r(pairs[a].to_numpy(), pairs[f"{a}_n"].to_numpy()),
            "movers_r": _r(movers[a].to_numpy(), movers[f"{a}_n"].to_numpy()),
            "n_halves": sh.height, "n_pairs": pairs.height, "n_movers": movers.height,
        })  # fmt: skip
    return pl.DataFrame(rows).with_columns(kept=c("movers_r") / c("season_r"))


def interval_coverage(placed: pl.DataFrame, axes: Sequence[str], seasons: Sequence[int]) -> dict:
    """Do the intervals hold their stated 90%? Two halves of one season should differ by less than
    1.645 times the sd of their difference (each half's sd from its own snaps) 90% of the time."""
    full = placed.filter((c("half") == "all") & (c("snaps") >= MIN_SNAPS)
                         & c("season").is_in(list(seasons)))  # fmt: skip
    od, ev = placed.filter(c("half") == "odd"), placed.filter(c("half") == "even")
    sh = full.select(PAIR).join(od, on=PAIR).join(ev, on=PAIR, suffix="_e")
    out = {}
    for a in axes:
        # the half's 90% half-width over 1.645 is its sd (shrink_w is 1 at the halves' snaps or
        # the interval is narrower: the halves of a 200+ snap season are placed as they are)
        sd_o = (sh[f"{a}_hi"] - sh[f"{a}_lo"]).to_numpy() / (2 * 1.6449)
        sd_e = (sh[f"{a}_hi_e"] - sh[f"{a}_lo_e"]).to_numpy() / (2 * 1.6449)
        d = np.abs(sh[f"{a}_raw"].to_numpy() - sh[f"{a}_raw_e"].to_numpy())
        w = np.minimum(sh["shrink_w"].to_numpy(), sh["shrink_w_e"].to_numpy())
        ok = w == 1.0
        out[a] = float(np.mean(d[ok] <= 1.6449 * np.sqrt(sd_o[ok] ** 2 + sd_e[ok] ** 2)))
    return out


# ---------------------------------------------------------------- 2 and 3. the ladder
def season_totals(counts: pl.DataFrame) -> pl.DataFrame:
    """Each player-season-side's totals over every team (full seasons) and his per-snap rates."""
    t = (
        counts.filter(c("half") == "all")
        .group_by("gsis_id", "season", "side")
        .agg(c("snaps", "targets", "carries", "tackles", "rush", "pass_snaps").sum())
    )
    return t.with_columns(
        tps=c("targets") / c("snaps"), cps=c("carries") / c("snaps"),
        tkl=c("tackles") / c("snaps"), rpp=c("rush") / c("pass_snaps").clip(1),
    )  # fmt: skip


def pairs(main: pl.DataFrame, totals: pl.DataFrame, side: str) -> pl.DataFrame:
    """Consecutive-season pairs on `side` with 200+ snaps both seasons: season s's main row
    (inputs) and his own season-s rates (`own_*`), with season s + 1's rates (`y_*`)."""
    m = main.filter((c("side") == side) & (c("snaps") >= MIN_SNAPS))
    t = totals.filter(c("side") == side)
    rates = list(TARGETS[side])
    own = t.select("gsis_id", "season", **{f"own_{r}": c(r) for r in rates})
    nxt = t.filter(c("snaps") >= MIN_SNAPS).select(
        "gsis_id", season=c("season") - 1, **{f"y_{r}": c(r) for r in rates}
    )
    return (
        m.join(own, on=["gsis_id", "season"])
        .join(nxt, on=["gsis_id", "season"])
        .with_columns(target_season=c("season") + 1)
    )


def position_dummies(rows: pl.DataFrame, side: str) -> pl.DataFrame:
    return rows.select((c("group") == g).cast(pl.Float64).alias(f"is_{g}") for g in SIDES[side][1:])


@dataclass
class Fitter:
    """A model rung: `fit(x, y)` returns a predict function."""

    name: str
    fit: Callable[[np.ndarray, np.ndarray, np.ndarray], Callable[[np.ndarray], np.ndarray]]


def _lasso(x: np.ndarray, y: np.ndarray, season: np.ndarray) -> Callable:
    """The lasso on a standardized target, its penalty chosen inside the window: fit on the
    earlier target seasons, scored on the window's last, then refit on all of it."""
    mu, sd = y.mean(), y.std() or 1.0
    ys = (y - mu) / sd
    w = np.ones(len(y))
    last = season.max()
    early, late = season < last, season == last
    alpha = ALPHAS[-1]
    if early.sum() > 50 and late.sum() > 20:
        fits = fit_lasso(x[early], ys[early], w[early], ALPHAS)
        errs = [weighted_mse(predict_lasso(m, x[late]), ys[late], w[late]) for m in fits]
        alpha = ALPHAS[int(np.argmin(errs))]
    (model,) = fit_lasso(x, ys, w, [alpha])
    return lambda z: mu + sd * predict_lasso(model, z)


def _trees(seed: int = 0) -> Callable:
    def fit(x: np.ndarray, y: np.ndarray, season: np.ndarray) -> Callable:
        m = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
                                          min_samples_leaf=20, early_stopping=False,
                                          random_state=seed).fit(x, y)  # fmt: skip
        return m.predict

    return fit


LASSO = Fitter("lasso", _lasso)
TREES = Fitter("trees", _trees(0))


def walk(rows: pl.DataFrame, cols: Sequence[str], target: str, fitter: Fitter,
         scored: Sequence[int], y: np.ndarray | None = None) -> np.ndarray:  # fmt: skip
    """Walk-forward predictions for the rows whose target season is in `scored` (NaN elsewhere):
    each target season's model is fit on earlier target seasons only. `y` overrides the target
    (shuffled nulls)."""
    x = rows.select(cols).to_numpy().astype(float)
    y = rows[target].to_numpy().astype(float) if y is None else y
    ts = rows["target_season"].to_numpy()
    out = np.full(len(y), np.nan)
    for t in scored:
        tr, te = ts < t, ts == t
        if te.sum() == 0:
            continue
        out[te] = fitter.fit(x[tr], y[tr], ts[tr])(x[te])
    return out


@dataclass
class Gain:
    share: float
    lo: float
    hi: float
    n: int

    @property
    def verdict(self) -> str:
        return "better" if self.lo > 0 else "worse" if self.hi < 0 else "tie"

    def line(self) -> str:
        return (f"{100 * self.share:+.1f}% (90% {100 * self.lo:+.1f} to {100 * self.hi:+.1f}); "
                f"{self.verdict}")  # fmt: skip


def gain(y: np.ndarray, p0: np.ndarray, p1: np.ndarray, ids: np.ndarray, seed: int | None = None
         ) -> Gain:  # fmt: skip
    """Share of p0's squared error p1 removes, with a 90% interval from Poisson-resampled ids."""
    ok = ~(np.isnan(p0) | np.isnan(p1))
    y, p0, p1, ids = y[ok], p0[ok], p1[ok], ids[ok]
    e0, e1 = (y - p0) ** 2, (y - p1) ** 2
    _, inv = np.unique(ids, return_inverse=True)
    rng = np.random.default_rng(get_config().seed if seed is None else seed)
    w = rng.poisson(1.0, size=(DRAWS, inv.max() + 1))[:, inv].astype(float)
    bs = (w @ (e0 - e1)) / (w @ e0)
    lo, hi = np.percentile(bs, [5, 95])
    return Gain(float((e0 - e1).sum() / e0.sum()), float(lo), float(hi), int(ok.sum()))


def shuffled_target(rows: pl.DataFrame, target: str, seed: int) -> np.ndarray:
    """The target shuffled within each target season and position (VALIDATION §5, retrospective)."""
    rng = np.random.default_rng(seed)
    y = rows[target].to_numpy().astype(float).copy()
    key = (rows["target_season"].cast(pl.String) + rows["group"]).to_numpy()
    for k in np.unique(key):
        idx = np.flatnonzero(key == k)
        y[idx] = y[rng.permutation(idx)]
    return y


def signal(rows: pl.DataFrame, cols: Sequence[str], target: str, scored: Sequence[int],
           n: int = 20) -> dict:  # fmt: skip
    """The model on `cols` against `n` refits on shuffled targets, scored on the real held-out
    target. It has signal when it beats all `n`."""
    y = rows[target].to_numpy().astype(float)
    real = walk(rows, cols, target, LASSO, scored)
    ok = ~np.isnan(real)
    mse = float(((y[ok] - real[ok]) ** 2).mean())
    nulls = []
    for k in range(n):
        p = walk(rows, cols, target, LASSO, scored, y=shuffled_target(rows, target, 1000 + k))
        nulls.append(float(((y[ok] - p[ok]) ** 2).mean()))
    return {"mse": mse, "null_best": min(nulls), "beaten": int(sum(m > mse for m in nulls)), "n": n}


# ---------------------------------------------------------------- 5. named roles
def flips(labels: pl.DataFrame, seasons: Sequence[int], level: str = "role") -> pl.DataFrame:
    """Per depth-chart group, the share of 200+ snap player-seasons in `seasons` whose `level`
    (role or coarse) differs between the season's odd-week and even-week halves."""
    full = labels.filter((c("half") == "all") & (c("snaps") >= MIN_SNAPS)
                         & c("season").is_in(list(seasons)))  # fmt: skip
    od, ev = labels.filter(c("half") == "odd"), labels.filter(c("half") == "even")
    j = full.select(PAIR).join(od, on=PAIR).join(ev, on=PAIR, suffix="_e")
    j = j.with_columns(flip=(c(level) != c(f"{level}_e")).cast(pl.Float64))
    return j.group_by("group").agg(flip=c("flip").mean(), n=pl.len()).sort("group")


def sure_calibration(labels: pl.DataFrame, seasons: Sequence[int]) -> pl.DataFrame:
    """Is "how sure" honest? The chance both halves agree, by the product of their sure values,
    against how often they did."""
    full = labels.filter((c("half") == "all") & (c("snaps") >= MIN_SNAPS)
                         & c("season").is_in(list(seasons)))  # fmt: skip
    od, ev = labels.filter(c("half") == "odd"), labels.filter(c("half") == "even")
    j = full.select(PAIR).join(od, on=PAIR).join(ev, on=PAIR, suffix="_e")
    j = j.with_columns(p=c("sure") * c("sure_e"), agree=(c("role") == c("role_e")).cast(pl.Float64))
    edges = [0.0, 0.6, 0.75, 0.9, 1.01]
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        b = j.filter((c("p") >= lo) & (c("p") < hi))
        if b.height:
            rows.append({"from": lo, "to": min(hi, 1.0), "said": b["p"].mean(),
                         "held": b["agree"].mean(), "n": b.height})  # fmt: skip
    return pl.DataFrame(rows)


def substitutes(games: pl.DataFrame, prior: pl.DataFrame, axes: Sequence[str],
                seed: int | None = None) -> dict:  # fmt: skip
    """H101's test on prior-season coordinates (known before the season): when a regular (50%+
    snap share over 2+ earlier games) misses a team game, the replacement (the teammate in his
    group whose share rose most above his own earlier average) is ranked by role distance to the
    absent player among the non-regular teammates in his group who played and have a prior
    season (0 closest, 1 farthest; chance 0.5). `prior`: gsis_id, season (the season it's a prior
    for) and `axes`. 90% interval from resampled team-seasons."""
    g = games.with_columns(share=c("snaps") / c("team_plays")).sort(
        "gsis_id", "team", "season", "week"
    )
    team_games = g.select("team", "side", "season", "game_id", "week").unique()
    g = g.with_columns(
        n_before=c("week").cum_count().over("gsis_id", "team", "season") - 1,
        avg_before=((c("share").cum_sum() - c("share"))
                    / (c("week").cum_count() - 1).clip(1)).over("gsis_id", "team", "season"),
    )  # fmt: skip
    players = g.select("gsis_id", "team", "side", "season", "group").unique()
    cand = players.join(team_games, on=["team", "side", "season"])
    played = g.select("gsis_id", "team", "season", "game_id", p=pl.lit(1))
    cand = cand.join(played, on=["gsis_id", "team", "season", "game_id"], how="left").filter(
        c("p").is_null()
    )
    last = g.select(
        "gsis_id", "team", "season", "week", "n_before", "share", "avg_before"
    ).with_columns(
        avg_incl=(c("avg_before") * c("n_before") + c("share")) / (c("n_before") + 1),
        n_incl=c("n_before") + 1,
    )
    cand = cand.sort("week").join_asof(
        last.sort("week").rename({"week": "wk_last"}), left_on="week", right_on="wk_last",
        by=["gsis_id", "team", "season"], strategy="backward",
    )  # fmt: skip
    absent = cand.filter((c("n_incl") >= 2) & (c("avg_incl") >= 0.5)).select(
        "gsis_id", "team", "season", "group", "game_id"
    )
    mates = g.select(
        "gsis_id", "team", "season", "group", "game_id", "share", "avg_before", "n_before"
    ).with_columns(  # fmt: skip
        rise=c("share") - pl.when(c("n_before") > 0).then(c("avg_before")).otherwise(0.0),
        was_regular=(c("n_before") >= 2) & (c("avg_before") >= 0.5),
    )
    ev = absent.join(mates.rename({"gsis_id": "mate"}), on=["team", "season", "group", "game_id"])
    a_ = prior.select("gsis_id", "season", **{f"a{i}": c(a) for i, a in enumerate(axes)})
    p_ = prior.select(
        mate=c("gsis_id"), season="season", **{f"p{i}": c(a) for i, a in enumerate(axes)}
    )
    e = ev.join(a_, on=["gsis_id", "season"], how="inner").join(
        p_, on=["mate", "season"], how="left"
    )
    rep = (e.sort("rise", descending=True).unique(["gsis_id", "game_id"], keep="first")
           .select("gsis_id", "game_id", rep=c("mate"), rep_reg=c("was_regular")))  # fmt: skip
    e = e.join(rep, on=["gsis_id", "game_id"]).filter(
        ~c("rep_reg") & ~c("was_regular") & c("p0").is_not_null()
    )
    k = len(axes)
    e = e.with_columns(dist=pl.sum_horizontal([(c(f"a{i}") - c(f"p{i}")) ** 2 for i in range(k)]))
    st = (e.group_by("gsis_id", "game_id", "team", "season", "group")
          .agg(n=pl.len(), has=(c("mate") == c("rep")).any(),
               d_rep=c("dist").filter(c("mate") == c("rep")).first(), dists=c("dist"))
          .filter(c("has") & (c("n") >= 2)))  # fmt: skip
    ranks = []
    for d_rep, ds in zip(st["d_rep"].to_list(), st["dists"].to_list(), strict=True):
        ds = np.array(ds)
        ranks.append(((ds < d_rep).sum() + 0.5 * ((ds == d_rep).sum() - 1)) / (len(ds) - 1))
    rk = np.array(ranks)
    ts = (st["team"] + st["season"].cast(pl.String)).to_numpy()
    _, inv = np.unique(ts, return_inverse=True)
    rng = np.random.default_rng(get_config().seed if seed is None else seed)
    w = rng.poisson(1.0, size=(DRAWS, inv.max() + 1))[:, inv].astype(float)
    lo, hi = np.percentile((w @ rk) / w.sum(1), [5, 95])
    by = {gg: float(rk[st["group"].to_numpy() == gg].mean())
          for gg in np.unique(st["group"].to_numpy())}  # fmt: skip
    return {
        "rank": float(rk.mean()),
        "lo": float(lo),
        "hi": float(hi),
        "events": len(rk),
        "by_group": by,
    }
