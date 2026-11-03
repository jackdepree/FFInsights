"""What "beats" means (docs/VALIDATION.md §4): a paired comparison resampled by whole weeks.

Both models are scored on the same rows. The difference in main score is averaged within each
block (a week, or a team or player for retrospective models), and the blocks are resampled 2,000
times. A model beats another only if the whole 90% interval of the difference is below zero
(scores are losses: lower is better).
"""

from dataclasses import dataclass

import numpy as np
import polars as pl

c = pl.col
DRAWS = 2000
LEVEL = 0.90


@dataclass(frozen=True)
class Comparison:
    """`diff` = a's mean loss − b's on the shared rows; negative means a is better."""

    a: str
    b: str
    diff: float
    lo: float
    hi: float
    rows: int
    blocks: int

    @property
    def beats(self) -> bool:
        """a beats b: the whole interval is below zero."""
        return self.hi < 0

    @property
    def verdict(self) -> str:
        """better, worse or tie (the interval includes zero). Ties go to the simpler model."""
        if self.hi < 0:
            return "better"
        if self.lo > 0:
            return "worse"
        return "tie"


def block_interval(
    sums: np.ndarray, counts: np.ndarray, draws: int = DRAWS, seed: int = 0
) -> tuple[float, float]:
    """The 90% interval of a row-weighted mean, resampling whole blocks."""
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(sums), size=(draws, len(sums)))
    means = sums[pick].sum(axis=1) / counts[pick].sum(axis=1)
    tail = (1 - LEVEL) / 2
    return float(np.quantile(means, tail)), float(np.quantile(means, 1 - tail))


def compare(
    a: pl.DataFrame,
    b: pl.DataFrame,
    keys: list[str],
    block: str = "step",
    names: tuple[str, str] = ("a", "b"),
    draws: int = DRAWS,
    seed: int = 0,
) -> Comparison:
    """Compare two scored frames (each with `keys`, `block` and `loss`) on the rows both have."""
    paired = a.select(*keys, block, "loss").join(
        b.select(*keys, loss_b="loss"), on=keys, how="inner"
    )
    paired = paired.filter(c("loss").is_not_null() & c("loss_b").is_not_null())
    if paired.is_empty():
        raise ValueError("the two models share no scored rows")
    per = paired.group_by(block).agg(total=(c("loss") - c("loss_b")).sum(), n=pl.len())
    sums = per["total"].to_numpy().astype(float)
    counts = per["n"].to_numpy().astype(float)
    lo, hi = block_interval(sums, counts, draws, seed)
    return Comparison(
        names[0], names[1], float(sums.sum() / counts.sum()), lo, hi, paired.height, per.height
    )
