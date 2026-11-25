"""The role table and the named roles (brief, method 1: the usual way and the simpler side;
decision 0048).

- **The role table:** six hand-picked features per side, the ones the exploration found carry the
  role and repeat (I113's next version, H107's table).
- **Named roles:** explicit rules on the table's features, read in order; the first that fits
  names the role. Positionless: a rule never reads the depth chart. Each rule cuts a feature at a
  value set once on the 2016-2020 seasons and frozen (`fit_cuts`), either at the thinnest point of
  its distribution (a valley, where few players sit, so few flip) or at a stated quantile.
- **How sure:** for each cut a rule's decision passed, the chance the player's true value is on
  the same side, from that feature's sampling noise at his snaps (split halves, as for the space's
  axes); the product over the deciding cuts. Its calibration is checked against flips between a
  season's halves.

The names are working names: what to call each role is the CEO's taste call.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import erf, sqrt

import numpy as np
import polars as pl

c = pl.col
TABLE = {
    "offense": ["snap_share", "tgt_per_pass", "car_per_run", "adot", "adj_run", "adj_p11"],
    "defense": ["snap_share", "rush_per_pass", "tkl_per_snap", "tkl_depth", "adj_p11", "adj_late"],
}
PAIR = ["gsis_id", "team", "season", "side", "group"]


@dataclass(frozen=True)
class Cut:
    """A frozen cut: `feature` at `value`, set on `rows` by `how` (valley, or a quantile)."""

    name: str
    feature: str
    value: float
    how: str


# How each cut is set on the 2016-2020 fit rows: (feature, the rows it's set on, how). The rows
# are a filter on earlier cuts (a role's region), so a cut's place depends only on its parent.
CUT_RULES: dict[str, tuple[str, str, str]] = {
    "carrier": ("car_per_run", "offense", "valley 0.2 0.8"),
    "in_tight": ("adj_p11", "offense non-carrier", "valley 0.2 0.8"),
    "run_tilt": ("adj_run", "offense carrier", "quantile 0.5"),
    "blocker": ("adj_run", "offense in-tight", "quantile 0.5"),
    "slot": ("adj_p11", "offense split", "quantile 0.8"),
    "deep": ("adot", "offense split", "valley 0.6 0.95"),
    "downfield": ("tkl_depth", "defense", "valley 0.15 0.85"),
    "rusher": ("rush_per_pass", "defense box", "valley 0.2 0.9"),
    "tackler": ("tkl_per_snap", "defense box", "quantile 0.67"),
    "nickel": ("adj_p11", "defense coverage", "valley 0.5 0.95"),
}


REGIONS: dict[str, list[tuple[str, bool]]] = {  # a region: the cuts that define it (cut, above?)
    "": [],
    "carrier": [("carrier", True)],
    "non-carrier": [("carrier", False)],
    "in-tight": [("carrier", False), ("in_tight", False)],
    "split": [("carrier", False), ("in_tight", True)],
    "box": [("downfield", False)],
    "coverage": [("downfield", True)],
}


def _region(rows: pl.DataFrame, region: str, cuts: dict[str, Cut]) -> pl.DataFrame:
    side, _, rest = region.partition(" ")
    r = rows.filter(c("side") == side)
    for name, above in REGIONS[rest]:
        cut = cuts[name]
        r = r.filter(c(cut.feature) >= cut.value if above else c(cut.feature) < cut.value)
    return r


def _valley(x: np.ndarray, lo: float, hi: float) -> float:
    """The thinnest point of x's smoothed distribution between its lo and hi quantiles."""
    a, b = np.quantile(x, [lo, hi])
    grid = np.linspace(a, b, 400)
    bw = 1.06 * x.std() * len(x) ** -0.2
    dens = np.array([np.exp(-0.5 * ((x - g) / bw) ** 2).sum() for g in grid])
    return float(grid[dens.argmin()])


def fit_cuts(fit_rows: pl.DataFrame) -> dict[str, Cut]:
    """Every cut, set on the fit rows (full seasons, 200+ snaps, 2016-2020) in `CUT_RULES` order."""
    cuts: dict[str, Cut] = {}
    for name, (feature, region, how) in CUT_RULES.items():
        x = _region(fit_rows, region, cuts)[feature].to_numpy()
        kind, *args = how.split()
        if kind == "valley":
            value = _valley(x, float(args[0]), float(args[1]))
        elif kind == "quantile":
            value = float(np.quantile(x, float(args[0])))
        else:
            value = float(args[0])
        cuts[name] = Cut(name, feature, value, f"{how} of {region}")
    return cuts


# The rules, in order: (role, side, [(cut, above?)]). The first rule whose every test passes
# names the role.
RULES: list[tuple[str, str, list[tuple[str, bool]]]] = [
    ("early-down back", "offense", [("carrier", True), ("run_tilt", True)]),
    ("passing-down back", "offense", [("carrier", True), ("run_tilt", False)]),
    ("blocking tight end", "offense", [("carrier", False), ("in_tight", False), ("blocker", True)]),
    ("inline tight end", "offense", [("carrier", False), ("in_tight", False), ("blocker", False)]),
    ("slot receiver", "offense", [("carrier", False), ("in_tight", True), ("slot", True)]),
    (
        "deep threat",
        "offense",
        [("carrier", False), ("in_tight", True), ("slot", False), ("deep", True)],
    ),  # fmt: skip
    (
        "outside receiver",
        "offense",
        [("carrier", False), ("in_tight", True), ("slot", False), ("deep", False)],
    ),  # fmt: skip
    ("pass rusher", "defense", [("downfield", False), ("rusher", True)]),
    ("box linebacker", "defense", [("downfield", False), ("rusher", False), ("tackler", True)]),
    ("run defender", "defense", [("downfield", False), ("rusher", False), ("tackler", False)]),
    ("slot defender", "defense", [("downfield", True), ("nickel", True)]),
    ("base defensive back", "defense", [("downfield", True), ("nickel", False)]),
]
ROLES = {side: [r for r, s, _ in RULES if s == side] for side in TABLE}
# The coarse level: the first cut(s) only, which the stricter names refine.
COARSE = {
    "early-down back": "back", "passing-down back": "back",
    "blocking tight end": "in tight", "inline tight end": "in tight",
    "slot receiver": "split out", "deep threat": "split out", "outside receiver": "split out",
    "pass rusher": "front", "box linebacker": "front", "run defender": "front",
    "slot defender": "coverage", "base defensive back": "coverage",
}  # fmt: skip


def feature_noise(feats: pl.DataFrame, fit_rows: pl.DataFrame, names: Sequence[str]) -> dict:
    """Each feature's a, from the fit rows' split halves: sd of a season of n snaps sqrt(a / n)."""
    halves = feats.join(fit_rows.select(PAIR), on=PAIR, how="semi")
    od = halves.filter(c("half") == "odd")
    ev = halves.filter(c("half") == "even")
    j = od.join(ev, on=PAIR, suffix="_e").filter((c("snaps") > 0) & (c("snaps_e") > 0))
    inv = 1 / j["snaps"].to_numpy() + 1 / j["snaps_e"].to_numpy()
    return {f: float(((j[f].to_numpy() - j[f + "_e"].to_numpy()) ** 2).sum() / inv.sum())
            for f in names}  # fmt: skip


def _phi(z: np.ndarray) -> np.ndarray:
    return 0.5 * (1 + np.vectorize(erf)(z / sqrt(2)))


def name_roles(rows: pl.DataFrame, cuts: dict[str, Cut], noise: dict) -> pl.DataFrame:
    """Each row's named role, its coarse role, how sure (0.5 to 1) and the deciding margin (in sd
    units of the closest cut). Keys, `half`, `snaps` kept."""
    n = np.maximum(rows["snaps"].to_numpy().astype(float), 1)
    side = rows["side"].to_numpy()
    role = np.full(rows.height, None, dtype=object)
    sure = np.full(rows.height, np.nan)
    margin = np.full(rows.height, np.nan)
    for name, s, tests in RULES:
        ok = (side == s) & (role == None)  # noqa: E711
        p, m = np.ones(rows.height), np.full(rows.height, np.inf)
        for cut, above in tests:
            ct = cuts[cut]
            x = rows[ct.feature].to_numpy().astype(float)
            ok &= (x >= ct.value) if above else (x < ct.value)
            z = np.abs(x - ct.value) / np.sqrt(noise[ct.feature] / n)
            p *= _phi(z)
            m = np.minimum(m, z)
        role[ok] = name
        sure[ok] = p[ok]
        margin[ok] = m[ok]
    return rows.select(*PAIR, "half", "snaps").with_columns(
        role=pl.Series(role, dtype=pl.String),
        coarse=pl.Series([COARSE.get(r) for r in role], dtype=pl.String),
        sure=pl.Series(sure),
        margin=pl.Series(margin),
    )
