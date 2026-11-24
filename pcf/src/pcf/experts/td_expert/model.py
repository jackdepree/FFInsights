"""The touchdown forecasts (decision 0043): count forecasts (the harness's `count` kind) whose
chance of 0, 1, 2+ is a Poisson count around the mean (EXPLORATION F18).

Three families, each with the same rungs:

| Family | Rows | Outcome |
|---|---|---|
| `skill` | every rostered QB, RB, WR, TE | his rushing + receiving touchdowns |
| `thrown` | every rostered QB | his thrown touchdowns |
| `team` | every team | its rushing + receiving touchdowns |

and two horizons: next game (`_next`: assumes he plays, the brief) and the rest of the regular
season (`_rest`: his touchdowns over his team's games from this one on, an absence counting 0;
the number of games left is the exposure).

| Rung | Variant | Method |
|---|---|---|
| 0 | `rate` | Touchdowns a game over this season and last, pulled toward the position's rate by 4 games, times the exposure, scaled to the training rows |
| 1 | `volume` (method B) | Poisson regression on volume (`features.VOLUME`, `_THROWN`, `TEAM_VOLUME`) |
| 1 | `chances` (method A) | Stage 1: next game's expected touchdowns (`features.STAGE1`...) by Poisson regression; stage 2: touchdowns = exposure × stage 1 × exp(corrections) (`features.CORRECTIONS`...) |
| 3 | `volume_trees` | Boosted trees with a Poisson loss on B's inputs (players, next game) |

**Stage 1's outcome** is a later row's `last_xtd`: the expected touchdowns of the game a row
predicts appear as the "last game" of his next row. So stage 1 learns from training rows only,
and the latest rows (with no next row yet) sit it out.

Poisson regressions standardize their inputs on the training rows, and pick their penalty on the
latest 20% of the training window from fits on the earlier 80% (the baselines' rule), then refit.
"""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import polars as pl
from scipy.stats import poisson

from pcf.core.contract import Expert
from pcf.experts.td_expert import features as F
from pcf.experts.td_expert.common import FIRST_SEASON, known_player_games, known_team_games

c = pl.col
HOLDOUT = 0.2
ALPHAS = (1e-4, 1e-3, 1e-2, 3e-2, 1e-1, 3e-1, 1.0)
SHRINK_GAMES = 4.0  # rung 0's pull toward the position's rate
MIN_RATE = 1e-4
TREES = {"max_iter": 200, "learning_rate": 0.05, "max_leaf_nodes": 15, "min_samples_leaf": 200,
         "l2_regularization": 1.0, "random_state": 0, "loss": "poisson"}  # fmt: skip


# ---------------------------------------------------------------- Poisson regression
def _deviance(y: np.ndarray, mu: np.ndarray, w: np.ndarray) -> float:
    mu = np.maximum(mu, MIN_RATE)
    with np.errstate(divide="ignore", invalid="ignore"):
        term = np.where(y > 0, y * np.log(y / mu), 0.0) - (y - mu)
    return float(np.sum(w * 2 * term) / max(np.sum(w), 1e-12))


def _scale(x: np.ndarray, w: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = np.average(x, axis=0, weights=w)
    sd = np.sqrt(np.average((x - mean) ** 2, axis=0, weights=w))
    return mean, np.where(sd > 1e-9, sd, 1.0)


def _glm(x, y, w, alpha: float):
    from sklearn.linear_model import PoissonRegressor

    return PoissonRegressor(alpha=alpha, max_iter=500).fit(x, y, sample_weight=w)


def fit_poisson(x: np.ndarray, y: np.ndarray, w: np.ndarray, exposure: np.ndarray) -> dict:
    """A Poisson regression of `y` with log(`exposure`) as an offset (fit as the rate y/exposure
    weighted by exposure, which has the same likelihood), its penalty picked on the latest 20%."""
    keep = exposure > 0
    x, y, w, e = x[keep], y[keep], w[keep], exposure[keep]
    mean, sd = _scale(x, w)
    xs = (x - mean) / sd
    rate, rw = y / e, w * e
    cut = int(len(y) * (1 - HOLDOUT))
    errors = []
    for a in ALPHAS:
        m = _glm(xs[:cut], rate[:cut], rw[:cut], a)
        errors.append(_deviance(y[cut:], e[cut:] * m.predict(xs[cut:]), w[cut:]))
    alpha = float(ALPHAS[int(np.argmin(errors))])
    return {"glm": _glm(xs, rate, rw, alpha), "mean": mean, "sd": sd, "alpha": alpha}


def predict_poisson(model: dict, x: np.ndarray, exposure: np.ndarray) -> np.ndarray:
    if "trees" in model:
        return exposure * model["trees"].predict(x)
    rate = model["glm"].predict((x - model["mean"]) / model["sd"])
    return np.maximum(exposure * rate, 0.0)


def fit_trees(x: np.ndarray, y: np.ndarray, w: np.ndarray, exposure: np.ndarray) -> dict:
    from sklearn.ensemble import HistGradientBoostingRegressor

    keep = exposure > 0
    e = exposure[keep]
    trees = HistGradientBoostingRegressor(**TREES).fit(
        x[keep], y[keep] / e, sample_weight=w[keep] * e
    )
    return {"trees": trees}


def fit_recalibration(mean: np.ndarray, y: np.ndarray, w: np.ndarray, steps: int = 50) -> dict:
    """The mean's recalibration (decision 0043): a Poisson fit of y on L = log(mean) and L^2 with
    log(mean) as the offset, so the result is mean x exp(a + bL + cL^2). Fit on rows the model
    didn't see (the latest 20% of its training window); L is held inside the range it saw."""
    lam = np.maximum(mean, MIN_RATE)
    big = np.log(lam)
    lo, hi = np.quantile(big, [0.005, 0.995])
    centre = float(np.average(big, weights=w))
    z = np.clip(big, lo, hi) - centre
    d = np.column_stack([np.ones_like(z), z, z * z])
    beta = np.zeros(3)
    for _ in range(steps):  # Newton steps; a small ridge keeps it near no change
        mu = lam * np.exp(d @ beta)
        step = np.linalg.solve(d.T @ (d * (w * mu)[:, None]) + 1.0 * np.eye(3),
                               d.T @ (w * (y - mu)) - 1.0 * beta)  # fmt: skip
        beta += step
        if np.abs(step).max() < 1e-10:
            break
    return {"beta": beta, "lo": float(lo), "hi": float(hi), "centre": centre}


def recalibrate(model: dict | None, mean: np.ndarray) -> np.ndarray:
    if model is None:
        return mean
    lam = np.maximum(mean, MIN_RATE)
    z = np.clip(np.log(lam), model["lo"], model["hi"]) - model["centre"]
    return mean * np.exp(model["beta"][0] + model["beta"][1] * z + model["beta"][2] * z * z)


def calibrated(fit, predict, train: pl.DataFrame) -> dict:
    """`fit(rows) -> model` and `predict(model, rows) -> mean`, with the mean's recalibration
    fit on the latest 20% of `train` (in its time order) from a model fit on the earlier 80%,
    then the model refit on all of it."""
    cut = int(train.height * (1 - HOLDOUT))
    early, late = train[:cut], train[cut:]
    recal = None
    if cut > 100 and late.height > 100:
        m = predict(fit(early), late)
        recal = fit_recalibration(m, late["y"].to_numpy().astype(float),
                                  late["weight"].to_numpy())  # fmt: skip
    return {"model": fit(train), "recal": recal}


def ranges(mean: np.ndarray) -> dict[str, np.ndarray]:
    lam = np.maximum(mean, MIN_RATE)
    return {q: poisson.ppf(lvl, lam).astype(float) for q, lvl in
            (("q10", 0.1), ("q50", 0.5), ("q90", 0.9))}  # fmt: skip


def stage_one(train: pl.DataFrame, key: str, last: str) -> pl.DataFrame:
    """Training rows with `y1`, the expected touchdowns of the game each row predicts, read from
    the same player's (team's) next row's `last` column; rows without one are dropped. In the
    training rows' own order: the penalty is picked on the latest 20% by position, so an order
    that changed from run to run would change the fit (leakage check 8 caught it)."""
    nxt = train.select(c(key), game_id=c("last_game_id"), y1=c(last)).unique(
        [key, "game_id"], keep="first", maintain_order=True
    )
    return train.join(nxt, on=[key, "game_id"], how="inner", maintain_order="left")


# ---------------------------------------------------------------- the shared base
class _Base(Expert):
    id = "td-expert"
    cadence = "in_season"
    grain = "player_game"  # the players' defaults (as opportunity-quality's base): _TeamBase overrides
    inputs = F.INPUTS
    groups = ("position",)
    run = "saturday"
    kind = "count"
    first_train = FIRST_SEASON
    family: ClassVar[str] = "skill"
    horizon: ClassVar[str] = "next"  # or "rest"
    columns: ClassVar[list[str]] = []

    # the family's pieces
    @property
    def key(self) -> str:
        return "team" if self.family == "team" else "gsis_id"

    def exposure(self, rows: pl.DataFrame) -> np.ndarray:
        if self.horizon == "rest":
            return rows["games_left"].to_numpy().astype(float)
        return np.ones(rows.height)

    def _x(self, rows: pl.DataFrame, columns: list[str] | None = None) -> np.ndarray:
        return rows.select(columns or self.columns).to_numpy().astype(float)

    def _out(self, rows: pl.DataFrame, mean: np.ndarray) -> pl.DataFrame:
        mean = np.maximum(mean, 0.0)
        r = ranges(mean)
        return rows.select(*self.keys()).with_columns(
            mean=pl.Series(mean), **{k: pl.Series(v) for k, v in r.items()}
        )


class _PlayerBase(_Base):
    grain = "player_game"
    inputs = F.INPUTS
    groups = ("position",)

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        if self.horizon == "rest":
            games = _regular(view, games)
            if games.is_empty():
                return pl.DataFrame(schema={k: pl.String for k in self.keys()})
        rows = F.features(view, games, self.keys())
        if self.family == "thrown":
            rows = rows.filter(c("position") == "QB")
        return rows

    def target(self, view) -> pl.DataFrame:
        known = known_player_games(view.table("player_game"))
        value = "thrown_td" if self.family == "thrown" else "td"
        if self.family == "thrown":
            known = known.filter(c("position") == "QB")
        if self.horizon == "rest":
            sched = view.table("team_game").select("game_id", "season", "week", "game_type",
                                                   "team")  # fmt: skip
            return window_sum(known, sched, value, "gsis_id")
        played = (c("throws") > 0) if self.family == "thrown" else c("played")
        return known.filter(played).select(*self.keys(), y=value, known_at="known_at")


class _TeamBase(_Base):
    grain = "team_game"
    inputs = F.TEAM_INPUTS
    family = "team"
    groups = ("home",)

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        if self.horizon == "rest":
            games = _regular(view, games)
            if games.is_empty():
                return pl.DataFrame(schema={k: pl.String for k in self.keys()})
        return F.team_features(view, games, self.keys())

    def target(self, view) -> pl.DataFrame:
        known = known_team_games(view.table("team_game"))
        if self.horizon == "rest":
            sched = view.table("team_game").select("game_id", "season", "week", "game_type",
                                                   "team")  # fmt: skip
            return window_sum(known, sched, "td", "team")
        return known.select(*self.keys(), y="td", known_at="known_at")


def _regular(view, games: pl.DataFrame) -> pl.DataFrame:
    season = int(games["season"].max())
    reg = view.table("team_game", seasons=[season]).filter(c("game_type") == "REG")
    return games.filter(c("game_id").is_in(reg["game_id"].implode()))


def window_sum(known: pl.DataFrame, schedule: pl.DataFrame, value: str, key: str) -> pl.DataFrame:
    """Known rows (key, game_id, season, week, team, `value`, known_at) → for each row in a
    regular-season game: y, the sum of `value` over its team's regular-season games from this one
    to the season's end (a week with no row for him counts 0), and known_at (when the last of
    them was known). Rows whose window isn't fully known are left out."""
    reg = schedule.filter(c("game_type") == "REG").select(
        "season", "team", window_game="game_id", w_week="week"
    )
    start = known.join(reg.select(game_id="window_game").unique(), on="game_id").select(
        *dict.fromkeys([key, "game_id", "season", "team"]), start="week"
    )
    window = start.join(reg, on=["season", "team"]).filter(c("w_week") >= c("start"))
    vals = known.select(key, "season", w_week="week", w_value=value).unique(
        [key, "season", "w_week"]
    )
    game_known = known.group_by("game_id").agg(g_known=c("known_at").max())
    window = window.join(vals, on=[key, "season", "w_week"], how="left").join(
        game_known, left_on="window_game", right_on="game_id", how="left"
    )
    keys = [key, "game_id"]
    return (
        window.group_by(keys)
        .agg(y=c("w_value").fill_null(0.0).sum(), complete=c("g_known").is_not_null().all(),
             known_at=c("g_known").max())  # fmt: skip
        .filter(c("complete"))
        .drop("complete")
    )


# ---------------------------------------------------------------- the rungs
class _Rate:
    """Rung 0: (touchdowns over this season and last + 4 games at the position's rate) / (games
    + 4), times the exposure, scaled per position so the training rows' total is right."""

    columns: ClassVar[list[str]] = []

    def _base(self, rows: pl.DataFrame, rates: dict[str, float]) -> np.ndarray:
        td = "thrown_td2" if self.family == "thrown" else "td2"
        group = rows["position"].to_numpy() if "position" in rows.columns else np.full(
            rows.height, "team")  # fmt: skip
        prior = np.array([rates.get(str(g), rates["_all"]) for g in group])
        r = (rows[td].to_numpy() + SHRINK_GAMES * prior) / (rows["games2"].to_numpy()
                                                            + SHRINK_GAMES)
        return r * self.exposure(rows), group

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        td = "thrown_td2" if self.family == "thrown" else "td2"
        group = train["position"].to_numpy() if "position" in train.columns else np.full(
            train.height, "team")  # fmt: skip
        g2 = train["games2"].to_numpy()
        t2 = train[td].to_numpy()
        rates = {"_all": float(t2.sum() / max(g2.sum(), 1.0))}
        for g in np.unique(group):
            on = group == g
            rates[str(g)] = float(t2[on].sum() / max(g2[on].sum(), 1.0))
        base, group = self._base(train, rates)
        y, w = train["y"].to_numpy().astype(float), train["weight"].to_numpy()
        scale = {str(g): float((w * y)[group == g].sum() / max((w * base)[group == g].sum(),
                                                                 1e-9))  # fmt: skip
                 for g in np.unique(group)}
        return {"rates": rates, "scale": scale}

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        base, group = self._base(rows, model["rates"])
        s = np.array([model["scale"].get(str(g), 1.0) for g in group])
        return self._out(rows, base * s)


class _Volume:
    """Method B: a Poisson regression on volume, its mean recalibrated (`calibrated`)."""

    method: ClassVar[str] = "glm"

    def _fit_raw(self, train: pl.DataFrame) -> dict[str, Any]:
        x, y = self._x(train), train["y"].to_numpy().astype(float)
        w, e = train["weight"].to_numpy(), self.exposure(train)
        if self.method == "trees":
            return fit_trees(x, y, w, e)
        return fit_poisson(x, y, w, e)

    def _mean(self, model: dict[str, Any], rows: pl.DataFrame) -> np.ndarray:
        return predict_poisson(model, self._x(rows), self.exposure(rows))

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        return calibrated(self._fit_raw, self._mean, train)

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        return self._out(rows, recalibrate(model["recal"], self._mean(model["model"], rows)))

    def explain(self, model: dict[str, Any]) -> dict[str, Any]:
        raw, recal = model["model"], model["recal"]
        out = {"recal": np.round(recal["beta"], 4).tolist() if recal else None}
        if "glm" not in raw:
            return out
        coef = np.round(raw["glm"].coef_, 4).tolist()
        return {**out, "alpha": raw["alpha"], **dict(zip(self.columns, coef, strict=True))}


class _Chances:
    """Method A: next game's expected touchdowns from his chances (stage 1), times small
    corrections (stage 2)."""

    stage1: ClassVar[list[str]]
    corrections: ClassVar[list[str]]
    last: ClassVar[str] = "last_xtd"

    def _fit_raw(self, train: pl.DataFrame) -> dict[str, Any]:
        s1 = stage_one(train, self.key, self.last)
        one = fit_poisson(self._x(s1, self.stage1), s1["y1"].to_numpy().astype(float),
                          s1["weight"].to_numpy(), np.ones(s1.height))  # fmt: skip
        xhat = np.maximum(predict_poisson(one, self._x(train, self.stage1),
                                          np.ones(train.height)), MIN_RATE)  # fmt: skip
        two = fit_poisson(self._x(train, self.corrections), train["y"].to_numpy().astype(float),
                          train["weight"].to_numpy(), self.exposure(train) * xhat)  # fmt: skip
        return {"one": one, "two": two, "stage1_rows": s1.height}

    def _mean(self, model: dict[str, Any], rows: pl.DataFrame) -> np.ndarray:
        xhat = np.maximum(predict_poisson(model["one"], self._x(rows, self.stage1),
                                          np.ones(rows.height)), MIN_RATE)  # fmt: skip
        return predict_poisson(model["two"], self._x(rows, self.corrections),
                               self.exposure(rows) * xhat)  # fmt: skip

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        return calibrated(self._fit_raw, self._mean, train)

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        return self._out(rows, recalibrate(model["recal"], self._mean(model["model"], rows)))

    def explain(self, model: dict[str, Any]) -> dict[str, Any]:
        two, recal = model["model"]["two"], model["recal"]
        return {"stage1_rows": model["model"]["stage1_rows"], "alpha2": two["alpha"],
                "recal": np.round(recal["beta"], 4).tolist() if recal else None,
                **dict(zip(self.corrections, np.round(two["glm"].coef_, 4).tolist(),
                           strict=True))}  # fmt: skip


# ---------------------------------------------------------------- the variants
FAMILY_COLUMNS = {
    "skill": {"volume": F.VOLUME, "stage1": F.STAGE1, "corrections": F.CORRECTIONS,
              "last": "last_xtd"},
    "thrown": {"volume": F.VOLUME_THROWN, "stage1": F.STAGE1_THROWN,
               "corrections": F.CORRECTIONS_THROWN, "last": "last_thrown_xtd"},
    "team": {"volume": F.TEAM_VOLUME, "stage1": F.TEAM_STAGE1, "corrections": F.TEAM_CORRECTIONS,
             "last": "last_xtd"},
}  # fmt: skip
QUANTITY = {"skill": "td_rush_rec", "thrown": "td_thrown", "team": "td_team"}
VARIANTS: dict[str, type[Expert]] = {}


def _make(family: str, horizon: str, rung: str, **extra) -> type[Expert]:
    base = _TeamBase if family == "team" else _PlayerBase
    cols = FAMILY_COLUMNS[family]
    name = f"{family}_{horizon}_{rung}"
    mixin = {"rate": _Rate, "volume": _Volume, "volume_trees": _Volume, "chances": _Chances}[
        rung.split("+")[0].split("-")[0]
    ]
    attrs: dict[str, Any] = {
        "variant": name, "family": family, "horizon": horizon, "__module__": __name__,
        "quantity": QUANTITY[family] + ("_rest" if horizon == "rest" else ""),
    }  # fmt: skip
    if rung == "volume":
        attrs["columns"] = cols["volume"]
    elif rung == "volume_trees":
        attrs |= {"columns": cols["volume"], "method": "trees"}
    elif rung == "chances":
        attrs |= {"stage1": cols["stage1"], "corrections": cols["corrections"],
                  "last": cols["last"], "columns": sorted({*cols["stage1"],
                                                           *cols["corrections"]})}  # fmt: skip
    attrs |= extra
    safe = name.replace("+", "_with_").replace("-", "_without_")
    cls = type(f"TD_{safe}", (mixin, base), attrs)
    VARIANTS[name] = cls
    return cls


for _family in ("skill", "thrown", "team"):
    for _horizon in ("next", "rest"):
        _make(_family, _horizon, "rate")
        _make(_family, _horizon, "volume")
        _make(_family, _horizon, "chances")
_make("skill", "next", "volume_trees")
# The build's side tests, walked on saved features (checks.py): B plus one set of inputs
_make("skill", "next", "volume+qb_rz", columns=[*F.VOLUME, *F.QB_RZ])  # I58
_make("skill", "rest", "volume+qb_rz", columns=[*F.VOLUME, *F.QB_RZ])  # I58
_make("skill", "rest", "volume+red_zone", columns=[*F.VOLUME, *F.RED_ZONE])  # H68
_make("skill", "next", "volume-calling",
      columns=[x for x in F.VOLUME if x not in F.CALLING])  # H67  # fmt: skip
_make("skill", "rest", "volume-calling",
      columns=[x for x in F.VOLUME if x not in F.CALLING])  # H67  # fmt: skip

_make("team", "next", "volume+line", columns=[*F.TEAM_VOLUME, *F.LINE])  # I118: the opener


def _with_baselines() -> None:
    for name, cls in VARIANTS.items():
        family, horizon, rung = name.split("_", 2)
        if "+" in rung or "-" in rung:
            cls.baselines = classmethod(  # type: ignore[method-assign]
                lambda k, f=family, h=horizon: [VARIANTS[f"{f}_{h}_volume"]]
            )
        elif rung == "volume":
            cls.baselines = classmethod(  # type: ignore[method-assign]
                lambda k, f=family, h=horizon: [VARIANTS[f"{f}_{h}_rate"]]
            )
        elif rung == "chances":  # the no-noise test: A against B, on the same rows
            cls.baselines = classmethod(  # type: ignore[method-assign]
                lambda k, f=family, h=horizon: [VARIANTS[f"{f}_{h}_rate"],
                                                VARIANTS[f"{f}_{h}_volume"]]
            )
        elif rung == "volume_trees":
            cls.baselines = classmethod(  # type: ignore[method-assign]
                lambda k: [VARIANTS["skill_next_volume"]]
            )
        else:
            cls.baselines = classmethod(lambda k: [])  # type: ignore[method-assign]


_with_baselines()
globals().update({cls.__name__: cls for cls in VARIANTS.values()})
