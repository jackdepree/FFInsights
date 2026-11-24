"""How each kind of prediction is scored (docs/VALIDATION.md §3).

Proper scores decide; readable ones are reported alongside. Every function here works on Polars
expressions or frames, so a backtest scores each row once and compares models row by row.
"""

import numpy as np
import polars as pl
from scipy.special import gammaln

c = pl.col
QUANTILE_LEVELS = {"q10": 0.1, "q50": 0.5, "q90": 0.9}
EPS = 1e-15
# The main score per kind decides; the readable one is reported (lower is better for both).
MAIN = {"amount": "pinball", "probability": "log_loss", "count": "poisson_log_loss"}
READABLE = {"amount": "mae", "probability": "brier", "count": "squared_error"}
MIN_RATE = 1e-6  # a count forecast's smallest mean, so its log loss is finite


def pinball(y: pl.Expr, q: pl.Expr, level: float) -> pl.Expr:
    """Pinball (quantile) loss of one quantile."""
    diff = y - q
    return pl.max_horizontal(level * diff, (level - 1) * diff)


def mean_pinball(y: str = "y") -> pl.Expr:
    """Pinball loss averaged over q10, q50 and q90: the main score for amounts."""
    return pl.mean_horizontal(pinball(c(y), c(q), lvl) for q, lvl in QUANTILE_LEVELS.items())


def log_loss(y: str = "y", p: str = "mean") -> pl.Expr:
    """Log loss of a yes/no event: the main score for probabilities."""
    prob = c(p).clip(EPS, 1 - EPS)
    return -(c(y) * prob.log() + (1 - c(y)) * (1 - prob).log())


def poisson_log_loss(y: str = "y", mean: str = "mean") -> pl.Expr:
    """−log P(y) under a Poisson count with this mean: the main score for counts (decision
    0043). It rewards an honest mean and, through it, honest chances of 0, 1, 2+."""
    lam = c(mean).clip(MIN_RATE)
    log_fact = c(y).map_batches(
        lambda s: pl.Series(gammaln(s.to_numpy().astype(float) + 1.0)), return_dtype=pl.Float64
    )
    return lam - c(y) * lam.log() + log_fact


def squared_error(y: str = "y", mean: str = "mean") -> pl.Expr:
    return (c(y) - c(mean)) ** 2


def poisson_at_least(mean: np.ndarray, k: int) -> np.ndarray:
    """The chance a Poisson count with this mean is k or more."""
    from scipy.stats import poisson

    return poisson.sf(k - 1, np.maximum(mean, MIN_RATE))


# ---------------------------------------------------------------- a count wider than Poisson (I116)
# A negative binomial with variance mean + alpha * mean**power: power 2 is the usual one, a lower
# power spreads big means less (td-expert: a rest-of-season total). alpha 0 is Poisson.
def _negbin(mean, alpha, power):
    mu = np.maximum(np.asarray(mean, dtype=float), MIN_RATE)
    a = np.broadcast_to(np.asarray(alpha, dtype=float), mu.shape)
    pw = np.broadcast_to(np.asarray(power, dtype=float), mu.shape)
    wide = a > 1e-9
    n = np.full(mu.shape, np.inf)
    n[wide] = mu[wide] ** (2.0 - pw[wide]) / a[wide]
    return mu, wide, n


def negbin_at_least(mean, alpha, k: int, power=2.0) -> np.ndarray:
    """The chance a negative-binomial count with this mean and spread is k or more."""
    from scipy.stats import nbinom, poisson

    mu, wide, n = _negbin(mean, alpha, power)
    out = poisson.sf(k - 1, mu)
    out[wide] = nbinom.sf(k - 1, n[wide], n[wide] / (n[wide] + mu[wide]))
    return out


def negbin_log_loss(y, mean, alpha, power=2.0) -> np.ndarray:
    """−log P(y) under that negative binomial, per row (Poisson where alpha is 0)."""
    from scipy.stats import nbinom, poisson

    y = np.asarray(y, dtype=float)
    mu, wide, n = _negbin(mean, alpha, power)
    out = -poisson.logpmf(y, mu)
    out[wide] = -nbinom.logpmf(y[wide], n[wide], n[wide] / (n[wide] + mu[wide]))
    return out


def negbin_quantile(mean, alpha, level: float, power=2.0) -> np.ndarray:
    """That negative binomial's quantile at `level` (Poisson's where alpha is 0)."""
    from scipy.stats import nbinom, poisson

    mu, wide, n = _negbin(mean, alpha, power)
    out = poisson.ppf(level, mu)
    out[wide] = nbinom.ppf(level, n[wide], n[wide] / (n[wide] + mu[wide]))
    return out.astype(float)


def fit_spread(y, mean, power: float | None = 2.0) -> tuple[float, float]:
    """The spread (alpha, power) that best fits outcomes `y` around forecasts `mean` taken as
    given, by maximum likelihood: alpha between 0 and 20; `power` fixed, or fit between 1 and 2.5
    when None. Poisson (alpha 0) when no spread fits better."""
    from scipy.optimize import minimize, minimize_scalar

    y, mean = np.asarray(y, dtype=float), np.asarray(mean, dtype=float)
    if len(y) == 0:
        return 0.0, 2.0 if power is None else power
    poisson_loss = negbin_log_loss(y, mean, 0.0).mean()
    if power is not None:
        res = minimize_scalar(lambda la: negbin_log_loss(y, mean, np.exp(la), power).mean(),
                              bounds=(-12.0, 3.0), method="bounded")  # fmt: skip
        best = (float(np.exp(res.x)), float(power))
    else:
        def loss(t):
            return negbin_log_loss(y, mean, np.exp(t[0]), 1 + 1.5 / (1 + np.exp(-t[1]))).mean()

        res = minimize(loss, x0=[np.log(0.3), 0.0], method="Nelder-Mead",
                       options={"xatol": 1e-3, "fatol": 1e-6})  # fmt: skip
        best = (float(np.exp(res.x[0])), float(1 + 1.5 / (1 + np.exp(-res.x[1]))))
    if negbin_log_loss(y, mean, *best).mean() < poisson_loss:
        return best
    return 0.0, best[1]


def brier(y: str = "y", p: str = "mean") -> pl.Expr:
    return (c(p) - c(y)) ** 2


def absolute_error(y: str = "y", q: str = "q50") -> pl.Expr:
    """|y − q50|: averaged, the mean absolute error of the median."""
    return (c(y) - c(q)).abs()


def row_losses(df: pl.DataFrame, kind: str) -> pl.DataFrame:
    """Add `loss` (the main score) and `readable` to every row with an outcome `y`."""
    if kind == "amount":
        return df.with_columns(loss=mean_pinball(), readable=absolute_error())
    if kind == "probability":
        return df.with_columns(loss=log_loss(), readable=brier())
    if kind == "count":
        return df.with_columns(loss=poisson_log_loss(), readable=squared_error())
    raise ValueError(f"no scores for kind {kind!r}")


def hit_rate(y: str = "y", p: str = "mean") -> pl.Expr:
    """Share of yes/no calls on the right side of 50%. Never the headline (§3)."""
    return ((c(p) >= 0.5) == (c(y) >= 0.5)).mean()


def points_gained(
    df: pl.DataFrame, ours: str, theirs: str, points: str, group: list[str], n: int
) -> pl.DataFrame:
    """The ranking score: in each group (a position-week), the points of our top `n` by `ours`
    minus the points of their top `n` by `theirs`."""

    def top(col: str) -> pl.DataFrame:
        ranked = df.with_columns(rank=c(col).rank("ordinal", descending=True).over(group))
        return ranked.filter(c("rank") <= n).group_by(group).agg(c(points).sum().alias(col))

    return (
        top(ours)
        .join(top(theirs), on=group, how="full", coalesce=True)
        .select(*group, gained=c(ours).fill_null(0) - c(theirs).fill_null(0))
    )


def rank_correlation(df: pl.DataFrame, a: str, b: str, group: list[str]) -> pl.DataFrame:
    """Spearman rank correlation of two columns within each group."""
    return (
        df.with_columns(ra=c(a).rank("average").over(group), rb=c(b).rank("average").over(group))
        .group_by(group)
        .agg(rho=pl.corr("ra", "rb"), rows=pl.len())
        .sort(group)
    )


def summary(df: pl.DataFrame, kind: str) -> dict[str, float]:
    """The headline numbers of scored rows: main and readable score, and the row count."""
    out = {
        MAIN[kind]: df["loss"].mean(),
        READABLE[kind]: df["readable"].mean(),
        "rows": float(df.height),
    }
    if kind == "probability":
        out["hit_rate"] = df.select(hit_rate()).item()
    return out
