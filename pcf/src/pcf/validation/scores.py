"""How each kind of prediction is scored (docs/VALIDATION.md §3).

Proper scores decide; readable ones are reported alongside. Every function here works on Polars
expressions or frames, so a backtest scores each row once and compares models row by row.
"""

import polars as pl

c = pl.col
QUANTILE_LEVELS = {"q10": 0.1, "q50": 0.5, "q90": 0.9}
EPS = 1e-15
# The main score per kind decides; the readable one is reported (lower is better for both).
MAIN = {"amount": "pinball", "probability": "log_loss"}
READABLE = {"amount": "mae", "probability": "brier"}


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
