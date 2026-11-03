"""The baselines (`baselines` project): the yardsticks every product must beat (rule k,
VALIDATION.md §6). Each is a variant of the one project id, validated with
`pcf backtest baselines --variant <name>`, and a product names the ones it must beat in its
`baselines()` classmethod.

| Variant | What | Run |
|---|---|---|
| `rolling4`, `season`, `last_season` | Fantasy points averages | Tuesday |
| `lasso` | Fantasy points from box-score history | Tuesday |
| `ecr` | FantasyPros' ranking as points (a benchmark) | Saturday |
| `market_margin`, `market_total`, `market_win` | The closing line (benchmarks) | Kickoff |
"""

from __future__ import annotations

from pcf.baselines.averages import LastSeason, RollingAverage, SeasonAverage
from pcf.baselines.common import SCORING
from pcf.baselines.ecr import Ecr
from pcf.baselines.lasso import Lasso
from pcf.baselines.market import MarketMargin, MarketTotal, MarketWin
from pcf.core.contract import Expert

FANTASY = (RollingAverage, SeasonAverage, LastSeason, Lasso)
VARIANTS: dict[str, type[Expert]] = {
    cls.variant: cls for cls in (*FANTASY, Ecr, MarketMargin, MarketTotal, MarketWin)
}


def scored(cls: type[Expert], scoring: str) -> type[Expert]:
    """A fantasy baseline in another scoring format (D2), e.g. `scored(RollingAverage, "half")`:
    variant `rolling4_half`, quantity `half_points`. ECR exists only in PPR."""
    if cls not in FANTASY:
        raise ValueError(f"{cls.__name__} has one scoring; the fantasy ones are {FANTASY}")
    if scoring not in SCORING:
        raise ValueError(f"no scoring {scoring!r}. Scorings: {', '.join(SCORING)}")
    if scoring == "ppr":
        return cls
    attrs = {"variant": f"{cls.variant}_{scoring}", "quantity": f"{scoring}_points",
             "scoring": scoring, "__module__": cls.__module__}  # fmt: skip
    return type(f"{cls.__name__}{scoring.title()}", (cls,), attrs)
