"""The six dropback outcomes in the play's order (the brief's assumption: pressure, then time to
throw, then the sack or the throw, then depth, completion and yards), and the two modes.

- **E0** (`e0`): the outcome's chance or expected value before the snap, from the calls.
- **E1** (`e1`): the same, given whether the play had a pressure (every outcome after the
  pressure). Not for the pressure itself.
"""

from __future__ import annotations

from pcf.experts.context_live.outcomes import Outcome
from pcf.experts.context_retro.plays import FIRST

P, A = "probability", "amount"
OUTCOMES: tuple[Outcome, ...] = (
    Outcome("pressure", "pressure (a sack counts)", "dropback", "pressure_y", P, FIRST),
    Outcome("time_to_throw", "time to throw (s)", "dropback", "time_to_throw_y", A, FIRST),
    Outcome("sack", "sack", "dropback", "sack_y", P, FIRST),
    Outcome("air_yards", "depth of target (yards)", "attempt", "air_yards_y", A, FIRST,
            end_zone=10),
    Outcome("completion", "completion", "attempt", "complete_y", P, FIRST),
    Outcome("dropback_yards", "dropback yards", "dropback", "yards", A, FIRST, end_zone=0),
)  # fmt: skip
BY_NAME = {o.name: o for o in OUTCOMES}
MODES = ("e0", "e1")
# participation's outcomes: trained within their provider (the brief's call 2)
PARTICIPATION = ("pressure", "time_to_throw")
GIVEN = tuple(o.name for o in OUTCOMES if o.name != "pressure")


def quantity(name: str, mode: str) -> str:
    """The output's quantity: `<outcome>_e0` or `<outcome>_e1` (the brief's outputs)."""
    return f"{name}_{mode}"
