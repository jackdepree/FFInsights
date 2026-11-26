"""The shared pull toward the average: k, the shrink and the second pull (decision 0052, call 1).

Owned by `stabilization` (the CEO, 2026-11-26: "stabilization should own the code for pulling rates
toward the average, but that does not necessarily mean other experts can not use that code. The
code should be consistent between projects unless there is a good football reason"). Moved here
from `pcf.experts.skill_over_expected.traits` (decision 0051, call 32), unchanged in its math.

A rate is `num / den` per player-season (or team-season), with `den` its attempts (chances).
- **Centring** (`centre`): each rate less its group's mean, the **pull target**. `target="same"`
  takes the same season's mean (a retrospective table reading a finished season);
  `target="last"` takes last season's (in season, where this season's mean isn't known yet). The
  mean is over the rows that pass the **floor** (attempts at least `floor` in `volume`), which each
  project's brief sets.
- **The noise and the true spread** (`components`): sigma2, the noise per attempt (each player's
  games scattered around his season rate, `den`-weighted, per degree of freedom), and tau2, the
  true spread of centred season rates (their `den`-weighted variance less the average noise).
- **k = sigma2 / tau2**, the 50% point (the CEO's LD50): reliability at n attempts is n / (n + k).
- **The shrink (M1)**: n / (n + k) of the way from the target to his rate (`shrink`).
- **The second pull** (`walk_slopes`): M1 times one slope, fit by weighted least squares on season
  pairs whose target season is earlier (the drift between seasons a season's reliability can't
  see). The same walk fits any small linear design (no intercept: rates are centred).

Nothing here reads data: callers pass the rows, so every fit is only as point-in-time as the rows
it's given.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import polars as pl

c = pl.col
MIN_PAIRS = 30  # earlier pairs a slope needs before it's fit


# ---------------------------------------------------------------- the pull target and the floor
def centre(
    rows: pl.DataFrame,
    by: Sequence[str] = ("group",),
    target: str = "same",
    floor: float = 0.0,
    volume: str = "den",
) -> pl.DataFrame:
    """Rows with `rate`, `mu` (the pull target: the group's mean, `num` over `den` summed) and `x`
    (the centred rate). Only rows with `volume` at least `floor` are kept, and the mean is over
    them. `target`: "same" (that season's mean) or "last" (last season's; a group-season with no
    last season falls back to its own, so the first season isn't lost; `mu_last_known` says which).
    """
    if target not in ("same", "last"):
        raise ValueError(f"target must be 'same' or 'last', not {target!r}")
    by = list(by)
    s = rows.filter(c(volume) >= floor).with_columns(rate=c("num") / c("den"))
    mu = (c("num").sum() / c("den").sum()).over(*by, "season")
    if target == "same":
        return s.with_columns(mu=mu).with_columns(x=c("rate") - c("mu"))
    own = s.group_by(*by, "season").agg(mu_own=c("num").sum() / c("den").sum())
    last = own.select(*by, season=c("season") + 1, mu_last="mu_own")
    s = s.join(own, on=[*by, "season"], how="left").join(last, on=[*by, "season"], how="left")
    return s.with_columns(
        mu=pl.coalesce("mu_last", "mu_own"), mu_last_known=c("mu_last").is_not_null()
    ).drop("mu_own", "mu_last").with_columns(x=c("rate") - c("mu"))


# ---------------------------------------------------------------- the noise and the true spread
def noise(games: pl.DataFrame, key: Sequence[str] = ("gsis_id", "season")) -> float:
    """sigma2, the noise per attempt: each player's games (`num`, `den`) around his season `rate`,
    `den`-weighted, per degree of freedom, averaged over player-seasons with 2+ games
    (`n_games`)."""
    gg = games.filter(c("n_games") >= 2).with_columns(
        dev=c("den") * (c("num") / c("den") - c("rate")) ** 2
    )
    per = gg.group_by(*key).agg(ss=c("dev").sum(), G=c("n_games").first())
    return float((per["ss"] / (per["G"] - 1)).mean())


def spread(n: np.ndarray, x: np.ndarray, sigma2: float) -> float:
    """tau2, the true spread: the `n`-weighted variance of centred rates `x` less the average
    noise sigma2 / n (floored just above 0)."""
    w = n / n.sum()
    xm = float(np.sum(w * x))
    tau2 = float(np.sum(w * (x - xm) ** 2) - sigma2 * np.sum(w / n))
    return max(tau2, 1e-12)


def components(rows: pl.DataFrame, games: pl.DataFrame,
               key: Sequence[str] = ("gsis_id", "season")) -> tuple[float, float]:  # fmt: skip
    """(sigma2, tau2) from season rows (`den`, `x`) and their games (`num`, `den`, `rate`,
    `n_games`). k = sigma2 / tau2."""
    sigma2 = noise(games, key)
    return sigma2, spread(rows["den"].to_numpy(), rows["x"].to_numpy(), sigma2)


def k_of(sigma2: float, tau2: float) -> float:
    return sigma2 / tau2


def reliability(n, k):
    """n / (n + k): the share of the observed spread that is real at n attempts."""
    return n / (n + k)


# ---------------------------------------------------------------- the shrink (M1)
def shrink(x, n, k, target=0.0):
    """M1: n / (n + k) of the way from `target` to `x` (numbers, arrays, or polars expressions)."""
    return target + n / (n + k) * (x - target)


def shrink_expr(x: str = "x", n: str = "n", k: str = "k") -> pl.Expr:
    """M1 on a centred rate, as a polars expression: n / (n + k) * x."""
    return c(n) / (c(n) + c(k)) * c(x)


def posterior_sd(sigma2: float, n, k):
    """The spread of his true rate around M1: sqrt(sigma2 / (n + k))."""
    return (sigma2 / (n + k)) ** 0.5


# ---------------------------------------------------------------- the second pull
def wls(X: np.ndarray, y: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Weighted least squares, no intercept."""
    sw = np.sqrt(w)
    return np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0]


def walk_slopes(
    X: np.ndarray, y: np.ndarray, w: np.ndarray, season: np.ndarray, min_rows: int = MIN_PAIRS
) -> tuple[np.ndarray, np.ndarray]:
    """Each target season's forecast X @ b, with b fit (weighted, no intercept) on rows with an
    earlier season only. Seasons with fewer than `min_rows` earlier rows get NaN. Returns
    (forecast, coefficients per row)."""
    X = X.reshape(len(y), -1)
    fc = np.full(len(y), np.nan)
    coef = np.full(X.shape, np.nan)
    for t in np.unique(season):
        tr, te = season < t, season == t
        if tr.sum() < min_rows:
            continue
        b = wls(X[tr], y[tr], w[tr])
        fc[te] = X[te] @ b
        coef[te] = b
    return fc, coef


def second_pull(m1: np.ndarray, y: np.ndarray, w: np.ndarray, season: np.ndarray,
                min_rows: int = MIN_PAIRS) -> tuple[np.ndarray, np.ndarray]:  # fmt: skip
    """The second pull: M1 times one slope per target season, fit on earlier pairs. Returns
    (forecast, slope per row)."""
    fc, coef = walk_slopes(m1, y, w, season, min_rows)
    return fc, coef[:, 0]
