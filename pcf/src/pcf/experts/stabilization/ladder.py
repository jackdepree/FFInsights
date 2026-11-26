"""The ladder's verdicts (decision 0052, calls 15-18): which rung each measure ships, by rule k.

- A rung is kept only where it clears the rung below (90% interval above 0, entities resampled);
  a tie goes to the simpler rung.
- **Next season:** M1 must clear the position's average; the second pull must clear M1; the ridge
  must clear the second pull's winner.
- **In season:** M1 clears the average; the second pull clears M1; the filter (plain for usage
  and mixed rates and team tendencies; with I154's factor for efficiency rates) clears the
  winner below it.
- **The expert's bar:** the champion beats the position's average and all 19 shuffled-entity
  copies (each the walk rerun with every input moved to another entity of the same season and
  class).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np
import polars as pl

from pcf.experts.stabilization import common as K
from pcf.experts.stabilization import evaluate as E

c = pl.col


def climb(f: pl.DataFrame, steps: Sequence[tuple[str, str]], ent: str, seed: int) -> tuple[str, dict]:
    """`steps`: (rung, the rung it must clear) in order; a rung named as the one to clear is
    replaced by the current champion. Returns the champion and every gain."""
    gains, champ = {}, "avg"
    for new, below in steps:
        base = champ if below == "champ" else below
        g = E.gain(f, new, base, ent, seed)
        gains[(new, base)] = g
        if g.clear and (below == "champ" or base == champ):
            champ = new
    return champ, gains


def copies(make: Callable[[int], pl.DataFrame], rung: str, ent: str, n: int = K.COPIES,
           seed: int = 0) -> list[float]:  # fmt: skip
    """The champion's gain over the position's average on `n` shuffled copies (`make(i)` reruns
    the walk with the inputs moved)."""
    out = []
    for i in range(n):
        f = make(seed + 7000 + i)
        out.append(E.sse_gain(f, rung, "avg"))
    return out


def bar(f: pl.DataFrame, rung: str, cp: list[float], ent: str, seed: int) -> dict:
    g = E.gain(f, rung, "avg", ent, seed)
    best = float(np.nanmax(cp)) if cp else float("nan")
    return {"gain": g, "best_copy": best, "beats_copies": bool(cp) and g.gain > best,
            "passes": bool(cp) and g.gain > best and g.clear}  # fmt: skip
