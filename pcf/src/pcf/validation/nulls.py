"""Expert tests (docs/VALIDATION.md §5): signal (beats shuffled outcomes) and no noise.

**Signal:** refit on outcomes shuffled within each step (week, or season) `n` times and score each
on the same held-out rows. The expert has signal if it beats at least 95 of 100 (or all 20 for an
expensive model). This is also leakage check 9: a model that scores well on shuffled outcomes is
learning from something it shouldn't see.

**No noise:** a named downstream baseline with and without the expert's output, compared by §4.
"""

import math
from dataclasses import dataclass

import polars as pl

from pcf.validation.backtest import Backtest, shuffle_within_steps, walk
from pcf.validation.compare import Comparison, compare
from pcf.validation.scores import row_losses

c = pl.col
SHUFFLES = 100
CHEAP_SHUFFLES = 20


def needed(n: int) -> int:
    """How many shuffled refits the real model must beat: 95 of 100, all 20 (the same 5% bar)."""
    return n if n < 100 else math.ceil(0.95 * n)


@dataclass(frozen=True)
class SignalTest:
    real: float  # the real model's mean main score (a loss)
    nulls: tuple[float, ...]
    beaten: int
    needed: int

    @property
    def passed(self) -> bool:
        return self.beaten >= self.needed

    @property
    def n(self) -> int:
        return len(self.nulls)


def signal_test(bt: Backtest, n: int = SHUFFLES, seed: int = 0) -> SignalTest:
    """Refit the backtest `n` times on outcomes shuffled within each step. Each refit is scored
    against the real outcomes on the same rows as the real model."""
    keys = bt.expert.keys()
    real_rows = bt.scored.select(*keys, "loss")
    real = real_rows["loss"].mean()
    nulls = []
    for i in range(n):
        pred = walk(
            bt.expert,
            bt.features,
            bt.targets,
            bt.steps,
            bt.test,
            bt.refit,
            bt.half_life,
            train_transform=lambda pool, s=seed + i: shuffle_within_steps(pool, s),
        )
        scored = row_losses(
            pred.join(bt.targets.select(*keys, "y"), on=keys, how="inner"), bt.expert.kind
        ).join(real_rows.select(keys), on=keys, how="semi")
        nulls.append(float(scored["loss"].mean()))
    beaten = sum(real < x for x in nulls)
    return SignalTest(float(real), tuple(nulls), beaten, needed(n))


NO_NOISE = {"better": "adds value", "tie": "neutral", "worse": "adds noise"}


def no_noise(
    with_expert: pl.DataFrame,
    without: pl.DataFrame,
    keys: list[str],
    block: str = "step",
    seed: int = 0,
) -> tuple[str, Comparison]:
    """The downstream baseline scored with and without the expert. Fails only on "adds noise"."""
    comp = compare(with_expert, without, keys, block, ("with", "without"), seed=seed)
    return NO_NOISE[comp.verdict], comp
