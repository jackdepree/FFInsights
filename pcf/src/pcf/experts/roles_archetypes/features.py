"""Role features from the on-field counts (exploration's terms; decision 0048).

- `snap_share`: the log-odds of his share of his team's plays, in the games he played.
- `adj_<d>`: team-adjusted own-snap shares: the share of his snaps that are `d` (runs, 11, 12 or
  heavy personnel, 3rd or 4th down, the red zone) minus his team's share of `d` in those games.
- `oo_<d>`: on/off tilts: logit(on | d) - logit(on | not d), within his team's plays.
- Usage rates, each pulled toward his group's pooled rate (from the reference rows only) by a
  prior worth `k` snaps or events: targets per pass snap, target depth, the deep, behind-the-line
  and middle shares, carries per run snap, the outside share (offense); tackles per snap, the
  solo share, tackle depth, rushes (sacks and hits) and passes defensed per pass snap (defense).
"""

from __future__ import annotations

import numpy as np
import polars as pl

from pcf.experts.roles_archetypes.counts import CELLS, KEYS

c = pl.col
DIMS = {  # each dimension: (is it, is it not) as tests on a cell's name
    "run": (lambda x: x.startswith("run"), lambda x: x.startswith("pass")),
    "p11": (lambda x: "_11_" in x, lambda x: "_11_" not in x),
    "p12": (lambda x: "_12_" in x, lambda x: "_12_" not in x),
    "heavy": (lambda x: "_heavy_" in x, lambda x: "_heavy_" not in x),
    "late": (lambda x: "_late_" in x, lambda x: "_early_" in x),
    "rz": (lambda x: x.endswith("_rz"), lambda x: x.endswith("_of")),
}
USAGE = {  # name: (numerator, denominator, prior weight)
    "tgt_per_pass": ("targets", "pass_snaps", 100), "adot": ("air", "air_n", 10),
    "deep": ("deep", "loc_n", 10), "behind": ("behind", "air_n", 10),
    "middle": ("middle", "loc_n", 10), "car_per_run": ("carries", "run_snaps", 100),
    "outside": ("outside", "run_loc_n", 10), "tkl_per_snap": ("tackles", "snaps", 100),
    "solo_share": ("solo", "tackles", 10), "tkl_depth": ("tackle_yds", "tackles", 10),
    "rush_per_pass": ("rush", "pass_snaps", 100), "pd_per_pass": ("pd", "pass_snaps", 100),
}  # fmt: skip
OO = [f"oo_{d}" for d in DIMS]
ADJ = [f"adj_{d}" for d in DIMS]
OFF_USAGE = ["tgt_per_pass", "adot", "deep", "behind", "middle", "car_per_run", "outside"]
DEF_USAGE = ["tkl_per_snap", "solo_share", "tkl_depth", "rush_per_pass", "pd_per_pass"]
SPACE = {  # the features inside each side's space: no position label, no measurables
    "offense": ["snap_share", *ADJ, *OO, *OFF_USAGE],
    "defense": ["snap_share", *ADJ, *OO, *DEF_USAGE],
}


def _logit(p: np.ndarray) -> np.ndarray:
    return np.log(p / (1 - p))


def _sum(df: pl.DataFrame, test) -> tuple[np.ndarray, np.ndarray]:
    on = sum(df[f"n_{x}"].to_numpy().astype(float) for x in CELLS if test(x))
    team = sum(df[f"tn_{x}"].to_numpy().astype(float) for x in CELLS if test(x))
    return on, team


def priors(ref: pl.DataFrame) -> pl.DataFrame:
    """Each group's pooled usage rates over the reference rows (full seasons): shrink targets."""
    full = ref.filter(c("half") == "all")
    return full.group_by("group").agg(
        (c(num).sum() / c(den).sum().clip(1)).alias(name) for name, (num, den, _) in USAGE.items()
    )


def features(counts: pl.DataFrame, prior: pl.DataFrame) -> pl.DataFrame:
    """Every feature per counts row (keys, `half`, `snaps`, `games` kept). `prior` from `priors`."""
    n_all, t_all = _sum(counts, lambda x: True)
    out: dict[str, np.ndarray] = {"snap_share": _logit((n_all + 1) / (t_all + 2))}
    for d, (isx, notx) in DIMS.items():
        nx, tx = _sum(counts, isx)
        nn, tn = _sum(counts, notx)
        own = nx / np.maximum(n_all, 1)
        out[f"adj_{d}"] = own - tx / np.maximum(t_all, 1)
        out[f"oo_{d}"] = _logit((nx + 1) / (tx + 2)) - _logit((nn + 1) / (tn + 2))
    m = counts.select("group").join(prior, on="group", how="left")
    for name, (num, den, k) in USAGE.items():
        mm = m[name].fill_null(0.0).to_numpy()
        out[name] = (counts[num].to_numpy().astype(float) + k * mm) / (
            counts[den].to_numpy().astype(float) + k
        )
    keep = counts.select(*KEYS, "half", "snaps", "games", "pass_snaps", "run_snaps", "targets",
                         "carries", "tackles", "rush")  # fmt: skip
    return pl.concat([keep, pl.DataFrame(out)], how="horizontal")
