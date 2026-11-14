"""The `team_game` part `efficiency` (team-efficiency project, decision 0032): what each offense did
on its plays in a game, summed so the efficiency expert can rate teams without reading plays.

**The plays:** passes and runs with an EPA and a WPA, without two-point tries (kneels and spikes
aren't passes or runs). Regular season and playoffs; the expert rates on the regular season.

**Fit on earlier seasons only** (the vintage rule; `TRAIN_SEASONS` before, at least
`MIN_TRAIN_SEASONS`), on their regular-season plays, cached per season (`models_for`):
- **the EPA-WPA gap model** (`GAP_X`): a play's usual WPA for its EPA at that moment. The gap is
  WPA less it (team-efficiency#F5);
- **the outcome model** (`X_STATE`): a play's expected EPA from its situation with the game
  state, DML's first step (team-efficiency#F7);
- **the representativeness weights** (H41 with H44's gap): every play gets a kind (win-chance band
  x pass or run, the last two minutes of a half, the top and bottom 5% of the gap), and each kind
  a weight for the offense and one for the defense: how much one play of that kind moves the
  team's EPA per play in its other games, shrunk toward equal by leaving one season out
  (team-efficiency#F4, F5).

**Per team-game** (the offense's view; a defense's rows are its opponents'), every column
prefixed `eff_` (team_game already has `plays`):
- `eff_plays`, `eff_epa`, `eff_epa_sq`: all plays, their EPA summed and squared-summed;
- `eff_usual_plays`, `eff_usual_epa`: the usual garbage-time rule (win chance 10-90%, not the last
  two minutes of a half), the yardstick it beat (team-efficiency#F1);
- `eff_pass_plays`, `eff_pass_epa`, `eff_run_plays`, `eff_run_epa`: passes and runs apart;
- `eff_series`, `eff_series_success`: series and those that made a first down or a touchdown
  (team-efficiency#F9);
- per situation bin `k` (`BINS`: win-chance band x half, DML's propensity cells): `eff_n_k` plays,
  `eff_r_k` EPA less the outcome model, and `eff_rwo_k`, `eff_rwd_k` the same times the offense's
  and the defense's weight.

The builders are pure: rows in, rows out. Fitting is deterministic (fixed seeds).
"""

from __future__ import annotations

import pickle
from collections.abc import Callable
from typing import Any

import numpy as np
import polars as pl

from pcf.data.clean import standard

c = pl.col
TRAIN_SEASONS = 10
MIN_TRAIN_SEASONS = 3
MODEL_VERSION = 1  # bump when the plays, the inputs or the fit settings change
CACHE_FILE = "models.pkl"
PBP_COLUMNS = [
    "game_id", "play_id", "season", "week", "season_type", "posteam", "defteam", "down",
    "ydstogo", "yardline_100", "qtr", "half_seconds_remaining", "game_seconds_remaining",
    "score_differential", "wp", "epa", "wpa", "play_type", "two_point_attempt", "series",
    "series_success",
]  # fmt: skip
GAP_X = [
    "epa", "wp", "score_differential", "game_seconds_remaining", "half_seconds_remaining", "qtr",
    "down", "ydstogo", "yardline_100",
]  # fmt: skip
X_STATE = [
    "down", "ydstogo", "yardline_100", "half_seconds_remaining", "game_seconds_remaining", "qtr",
    "score_differential", "wp",
]  # fmt: skip
WP_BANDS = (0.1, 0.25, 0.4, 0.6, 0.75, 0.9)  # 7 win-chance bands
BINS = 2 * (len(WP_BANDS) + 1)  # DML's situation cells: band x half (team-efficiency#F7)
GAP_TAILS = (0.05, 0.95)
LAST_TWO = 120  # seconds left in the half
SHRINK_GRID = (0.0, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 1e4)
SUMS = [
    "eff_plays", "eff_epa", "eff_epa_sq", "eff_usual_plays", "eff_usual_epa", "eff_pass_plays",
    "eff_pass_epa", "eff_run_plays", "eff_run_epa", "eff_series", "eff_series_success",
]  # fmt: skip
CELLS = ("n", "r", "rwo", "rwd")
COLUMNS = SUMS + [f"eff_{k}_{b}" for k in CELLS for b in range(BINS)]


def plays(pbp: pl.DataFrame) -> pl.DataFrame:
    """Play-by-play (`PBP_COLUMNS`) → the rated plays: passes and runs with an EPA and a WPA, no
    two-point tries, teams standardized, with `is_pass`."""
    p = pbp.select(PBP_COLUMNS).filter(
        c("play_type").is_in(["pass", "run"])
        & (c("two_point_attempt").fill_null(0) == 0)
        & c("epa").is_not_null()
        & ~c("epa").is_nan()
        & c("wpa").is_not_null()
        & ~c("wpa").is_nan()
        & c("posteam").is_not_null()
        & c("defteam").is_not_null()
    )
    p = standard.standard_teams(p, "posteam", "defteam")
    return p.with_columns(
        c("season").cast(pl.Int32),
        is_pass=(c("play_type") == "pass").cast(pl.Int8),
    ).sort("game_id", "play_id")


def _regular(p: pl.DataFrame) -> pl.DataFrame:
    return p.filter(c("season_type") == "REG")


def _x(p: pl.DataFrame, cols: list[str]) -> np.ndarray:
    return p.select(cols).to_numpy().astype(float)


def _band(wp: pl.Expr) -> pl.Expr:
    """The win-chance band, 0-6 (a missing win chance counts as even)."""
    w = wp.fill_null(0.5)
    out = pl.lit(len(WP_BANDS))
    for i, edge in reversed(list(enumerate(WP_BANDS))):
        out = pl.when(w < edge).then(pl.lit(i)).otherwise(out)
    return out.cast(pl.Int32)


def kinds(p: pl.DataFrame, gap_lo: float, gap_hi: float) -> pl.Expr:
    """A play's kind: the gap's tails first, then the last two minutes of a half, then its
    win-chance band; each split by pass or run (team-efficiency#F4, F5)."""
    band = pl.concat_str(pl.lit("wp"), _band(c("wp")).cast(pl.String))
    kind = (
        pl.when(c("gap") <= gap_lo).then(pl.lit("gap-low"))
        .when(c("gap") >= gap_hi).then(pl.lit("gap-high"))
        .when(c("half_seconds_remaining") <= LAST_TWO).then(pl.lit("last2min"))
        .otherwise(band)
    )  # fmt: skip
    split = pl.when(c("is_pass") == 1).then(pl.lit("|pass")).otherwise(pl.lit("|run"))
    return pl.concat_str(kind, split)


def _relative(p: pl.DataFrame) -> pl.DataFrame:
    """EPA relative to the league's per-play mean that week."""
    return p.with_columns(y_rel=c("epa") - c("epa").mean().over("season", "week"))


def kind_weights(p: pl.DataFrame, side: str) -> tuple[dict[str, float], float]:
    """Per kind: how much one play of it moves the team's EPA per play in its other games (odd
    weeks predict even weeks and back), across team-seasons of `p`; shrunk toward equal weights
    by a ridge whose strength is picked by leaving one season out. Scaled to a play-weighted mean
    of 1, clipped at 0. Returns the weights and the chosen strength."""
    team = "posteam" if side == "off" else "defteam"
    x = _relative(p).with_columns(par=c("week") % 2)
    names = sorted(x["kind"].unique().to_list())
    tot = x.group_by("season", team, "par").agg(N=pl.len(), Y=c("y_rel").sum())
    s = (
        x.group_by("season", team, "par", "kind")
        .agg(S=c("y_rel").sum())
        .pivot(on="kind", index=["season", team, "par"], values="S")
    )
    # only the kinds' columns: a fill over every column would turn `season` into a float
    s = s.with_columns(
        *[c(k).fill_null(0.0) if k in s.columns else pl.lit(0.0).alias(k) for k in names]
    )
    other = tot.select("season", team, par=1 - c("par"), F=c("Y") / c("N"))
    m = tot.join(s, on=["season", team, "par"]).join(other, on=["season", team, "par"])
    m = m.sort("season", team, "par")
    d = np.column_stack([(m[k] / m["N"]).to_numpy() for k in names])
    xx = np.column_stack([np.ones(m.height), d.sum(1), d])
    f = m["F"].to_numpy()
    seasons = m["season"].to_numpy()
    scale = float(np.mean(np.sum(d * d, 0)))

    def fit(rows: np.ndarray, lam: float) -> np.ndarray:
        pen = np.zeros(xx.shape[1])
        pen[2:] = lam * scale
        a = xx[rows].T @ xx[rows] + np.diag(pen) + 1e-12 * np.eye(xx.shape[1])
        return np.linalg.solve(a, xx[rows].T @ f[rows])

    cv = {}
    for lam in SHRINK_GRID:
        err = 0.0
        for held in np.unique(seasons):
            b = fit(seasons != held, lam)
            te = seasons == held
            err += float(((f[te] - xx[te] @ b) ** 2).sum())
        cv[lam] = err
    best = min(cv, key=lambda k: (cv[k], -k))
    b = fit(np.ones(len(f), bool), best)
    beta = np.clip(b[1] + b[2:], 0.0, None)
    share = x.group_by("kind").agg(n=pl.len())
    shares = dict(zip(share["kind"].to_list(), share["n"].to_list(), strict=True))
    mean = sum(beta[i] * shares[k] for i, k in enumerate(names)) / sum(shares.values())
    return {k: float(beta[i] / mean) for i, k in enumerate(names)}, float(best)


def fit_models(p: pl.DataFrame) -> dict[str, Any]:
    """The season's models from earlier seasons' regular-season plays (`plays` rows)."""
    from sklearn.ensemble import HistGradientBoostingRegressor as Trees

    reg = _regular(p)
    gap = Trees(max_iter=300, learning_rate=0.1, max_leaf_nodes=63, random_state=0)
    gap.fit(_x(reg, GAP_X), reg["wpa"].to_numpy())
    outcome = Trees(
        max_iter=300, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=500, random_state=0
    )
    outcome.fit(_x(reg, X_STATE), reg["epa"].to_numpy())
    reg = reg.with_columns(gap=c("wpa") - pl.Series(gap.predict(_x(reg, GAP_X))))
    lo, hi = (float(reg["gap"].quantile(q)) for q in GAP_TAILS)
    reg = reg.with_columns(kind=kinds(reg, lo, hi))
    w_off, s_off = kind_weights(reg, "off")
    w_def, s_def = kind_weights(reg, "def")
    return {
        "seasons": sorted(reg["season"].unique().to_list()),
        "gap": gap,
        "outcome": outcome,
        "gap_tails": (lo, hi),
        "w_off": w_off,
        "w_def": w_def,
        "shrink": {"off": s_off, "def": s_def},
    }


def apply_models(p: pl.DataFrame, models: dict[str, Any]) -> pl.DataFrame:
    """The season's plays with `gap`, `kind`, the weights `w_off` and `w_def` (a kind the training
    seasons never saw counts 1), the outcome model's `g`, `resid` (EPA less g) and `bin`."""
    p = p.with_columns(gap=c("wpa") - pl.Series(models["gap"].predict(_x(p, GAP_X))))
    lo, hi = models["gap_tails"]
    p = p.with_columns(
        kind=kinds(p, lo, hi),
        g=pl.Series(models["outcome"].predict(_x(p, X_STATE))),
        bin=_band(c("wp")) * 2 + (c("qtr") > 2).cast(pl.Int32),
    )
    return p.with_columns(
        w_off=c("kind").replace_strict(models["w_off"], default=1.0, return_dtype=pl.Float64),
        w_def=c("kind").replace_strict(models["w_def"], default=1.0, return_dtype=pl.Float64),
        resid=c("epa") - c("g"),
    )


def efficiency_rows(p: pl.DataFrame) -> pl.DataFrame:
    """Plays with their models applied (`apply_models`) → one row per game and offense:
    game_id, team, season and `COLUMNS`."""
    usual = (c("wp").is_between(0.1, 0.9) & (c("half_seconds_remaining") > LAST_TWO)).fill_null(
        False
    )
    is_pass = c("is_pass") == 1
    keys = ["game_id", "season", "posteam"]
    sums = p.group_by(keys).agg(
        eff_plays=pl.len().cast(pl.Int32),
        eff_epa=c("epa").sum(),
        eff_epa_sq=(c("epa") ** 2).sum(),
        eff_usual_plays=usual.sum().cast(pl.Int32),
        eff_usual_epa=c("epa").filter(usual).sum(),
        eff_pass_plays=is_pass.sum().cast(pl.Int32),
        eff_pass_epa=c("epa").filter(is_pass).sum(),
        eff_run_plays=(~is_pass).sum().cast(pl.Int32),
        eff_run_epa=c("epa").filter(~is_pass).sum(),
    )
    series = (
        p.filter(c("series").is_not_null())
        .group_by(*keys, "series")
        .agg(ok=c("series_success").first().fill_null(0).cast(pl.Float64))
        .group_by(keys)
        .agg(eff_series=pl.len().cast(pl.Int32), eff_series_success=c("ok").sum())
    )
    cells = p.group_by(*keys, "bin").agg(
        n=pl.len().cast(pl.Float64),
        r=c("resid").sum(),
        rwo=(c("resid") * c("w_off")).sum(),
        rwd=(c("resid") * c("w_def")).sum(),
    )
    wide = cells.pivot(on="bin", index=keys, values=list(CELLS))
    rename = {f"{k}_{b}": f"eff_{k}_{b}" for k in CELLS for b in range(BINS)}
    wide = wide.rename({k: v for k, v in rename.items() if k in wide.columns})
    for col in rename.values():
        if col not in wide.columns:
            wide = wide.with_columns(pl.lit(0.0).alias(col))
    out = sums.join(series, on=keys, how="left").join(wide, on=keys, how="left")
    out = out.with_columns(
        c("eff_series").fill_null(0),
        c("eff_series_success").fill_null(0.0),
        *[c(v).fill_null(0.0).cast(pl.Float64) for v in rename.values()],
    )
    return (
        out.rename({"posteam": "team"})
        .select("game_id", "team", "season", *COLUMNS)
        .sort("game_id", "team")
    )


def training_seasons(season: int, have: list[int]) -> list[int]:
    """The seasons a season's models are fit on: up to `TRAIN_SEASONS` before it. Empty when
    fewer than `MIN_TRAIN_SEASONS` exist."""
    before = sorted(s for s in have if s < season)[-TRAIN_SEASONS:]
    return before if len(before) >= MIN_TRAIN_SEASONS else []


def check_fit(models: dict[str, Any], season: int) -> None:
    """The models were fit only on seasons before `season` (the vintage rule)."""
    late = [s for s in models["seasons"] if s >= season]
    if late:
        raise ValueError(f"efficiency models for {season} were fit on {late}")


def cache_key(season: int, train: list[int]) -> str:
    return f"v{MODEL_VERSION}:{season}:{','.join(map(str, train))}"


def models_for(
    season: int,
    have: list[int],
    plays_of: Callable[[int], pl.DataFrame],
    cache_dir: Any,
) -> dict[str, Any] | None:
    """The models for `season`, from `cache_dir/season=<season>` or fit on the training seasons'
    plays (`plays_of(season)`) and cached. None when too few earlier seasons exist."""
    train = training_seasons(season, have)
    if not train:
        return None
    key = cache_key(season, train)
    path = cache_dir / f"season={season}" / CACHE_FILE
    if path.exists():
        with path.open("rb") as f:
            cached = pickle.load(f)  # PCF's own interim files
        if cached.get("key") == key:
            check_fit(cached["models"], season)
            return cached["models"]
    models = fit_models(pl.concat([plays_of(s) for s in train], how="diagonal_relaxed"))
    check_fit(models, season)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("wb") as f:
        pickle.dump({"key": key, "models": models}, f)
    tmp.replace(path)
    return models
