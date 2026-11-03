"""The football sanity check (rule h, docs/VALIDATION.md §10).

Automatic rules count violations; shared ones apply to every model and each expert adds its own.
The CEO's review gets the top and bottom 20 by the main output (and, once baselines exist, the
biggest disagreements with the market or ECR).
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import polars as pl

c = pl.col
TOL = 1e-9
REVIEW_N = 20


@dataclass(frozen=True)
class Rule:
    name: str
    violations: Callable[[pl.DataFrame], int]


def quantiles_ordered() -> Rule:
    return Rule(
        "q10 ≤ q50 ≤ q90",
        lambda df: df.filter((c("q10") > c("q50") + TOL) | (c("q50") > c("q90") + TOL)).height,
    )


def non_negative(*cols: str) -> Rule:
    """No negative yards, snaps, targets..."""
    return Rule(
        f"{', '.join(cols)} never negative",
        lambda df: df.filter(pl.any_horizontal(c(x) < -TOL for x in cols)).height,
    )


def probabilities_valid(col: str = "mean") -> Rule:
    return Rule(f"{col} is a probability", lambda df: df.filter(~c(col).is_between(0, 1)).height)


def sums_to_one(col: str, group: Sequence[str]) -> Rule:
    """Probabilities of one event add up to 1 (win, lose, tie)."""
    return Rule(
        f"{col} adds to 1 within {', '.join(group)}",
        lambda df: df.group_by(group).agg(t=c(col).sum()).filter((c("t") - 1).abs() > 1e-6).height,
    )


def shares_at_most_one(col: str, group: Sequence[str]) -> Rule:
    """A team's players' shares (targets, carries) add up to at most 100%."""
    return Rule(
        f"{col} adds to at most 1 within {', '.join(group)}",
        lambda df: df.group_by(group).agg(t=c(col).sum()).filter(c("t") > 1 + 1e-6).height,
    )


def shared(kind: str) -> list[Rule]:
    """The rules every model's output passes."""
    return [quantiles_ordered()] if kind == "amount" else [probabilities_valid()]


def run_rules(df: pl.DataFrame, rules: Sequence[Rule]) -> pl.DataFrame:
    """rule, violations, passed."""
    rows = [(r.name, r.violations(df)) for r in rules]
    return pl.DataFrame(rows, schema=["rule", "violations"], orient="row").with_columns(
        passed=c("violations") == 0
    )


def review_lists(df: pl.DataFrame, show: Sequence[str], by: str = "mean", n: int = REVIEW_N):
    """The top and bottom `n` rows by `by`, with the columns to show."""
    cols = [*show, by]
    return df.sort(by, descending=True).head(n).select(cols), df.sort(by).head(n).select(cols)
