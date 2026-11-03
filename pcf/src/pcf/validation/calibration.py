"""Calibration and uncertainty (docs/VALIDATION.md §7).

Probabilities: a 10-bin calibration table, the calibration error (≤ 3 points) and slope
(0.9-1.1). Ranges: q10-q90 coverage (75-85% overall, 70-90% in each group of 200+ rows), the q50
balance (45-55% above it) and sharpness (the average q10-q90 width; narrower wins among models
that pass).
"""

import numpy as np
import polars as pl

c = pl.col
BINS = 10
MAX_ERROR = 3.0  # points
SLOPE = (0.9, 1.1)
COVERAGE = (0.75, 0.85)
GROUP_COVERAGE = (0.70, 0.90)
ABOVE_MEDIAN = (0.45, 0.55)
MIN_GROUP = 200


def probability_table(df: pl.DataFrame, p: str = "mean", y: str = "y") -> pl.DataFrame:
    """Predictions in 10 equal-width bins: bin, rows, predicted (mean p) and actual (rate)."""
    return (
        df.with_columns(bin=(c(p) * BINS).floor().clip(0, BINS - 1).cast(pl.Int32))
        .group_by("bin")
        .agg(rows=pl.len(), predicted=c(p).mean(), actual=c(y).mean())
        .sort("bin")
    )


def calibration_error(table: pl.DataFrame) -> float:
    """The row-weighted average gap between predicted and actual rates, in percentage points."""
    gap = (table["predicted"] - table["actual"]).abs() * table["rows"]
    return float(100 * gap.sum() / table["rows"].sum())


def calibration_slope(df: pl.DataFrame, p: str = "mean", y: str = "y", steps: int = 50) -> float:
    """The slope of a logistic fit of the outcome on logit(p): 1 is right, below 1 is
    over-confident, above 1 under-confident."""
    prob = df[p].to_numpy().clip(1e-6, 1 - 1e-6)
    x = np.log(prob / (1 - prob))
    yy = df[y].to_numpy().astype(float)
    design = np.column_stack([np.ones_like(x), x])
    beta = np.zeros(2)
    for _ in range(steps):  # Newton steps (IRLS)
        mu = 1 / (1 + np.exp(-(design @ beta)))
        w = mu * (1 - mu)
        hess = design.T @ (design * w[:, None]) + 1e-9 * np.eye(2)
        step = np.linalg.solve(hess, design.T @ (yy - mu))
        beta += step
        if np.abs(step).max() < 1e-10:
            break
    return float(beta[1])


def probability_report(df: pl.DataFrame) -> dict:
    table = probability_table(df)
    error = calibration_error(table)
    slope = calibration_slope(df)
    return {
        "table": table,
        "error": error,
        "slope": slope,
        "passed": error <= MAX_ERROR and SLOPE[0] <= slope <= SLOPE[1],
    }


def _inside() -> pl.Expr:
    return ((c("y") >= c("q10")) & (c("y") <= c("q90"))).cast(pl.Float64)


def coverage(df: pl.DataFrame, groups: list[str] | None = None) -> dict:
    """Range coverage overall and in each group, the q50 balance and sharpness."""
    overall = df.select(
        rows=pl.len(),
        inside=_inside().mean(),
        above=(c("y") > c("q50")).cast(pl.Float64).mean(),
        width=(c("q90") - c("q10")).mean(),
    ).row(0, named=True)
    by_group = []
    for g in groups or []:
        part = (
            df.group_by(g)
            .agg(rows=pl.len(), inside=_inside().mean())
            .sort(g)
            .select(group=pl.lit(g), value=c(g).cast(pl.String), rows="rows", inside="inside")
        )
        by_group.append(part)
    groups_df = (
        pl.concat(by_group)
        if by_group
        else pl.DataFrame(
            schema={"group": pl.String, "value": pl.String, "rows": pl.UInt32, "inside": pl.Float64}
        )
    )
    groups_df = groups_df.with_columns(judged=c("rows") >= MIN_GROUP).with_columns(
        ok=~c("judged") | c("inside").is_between(*GROUP_COVERAGE)
    )
    passed = (
        COVERAGE[0] <= overall["inside"] <= COVERAGE[1]
        and ABOVE_MEDIAN[0] <= overall["above"] <= ABOVE_MEDIAN[1]
        and bool(groups_df["ok"].all())
    )
    return {**overall, "groups": groups_df, "passed": passed}
