"""What both vacated experts share: the groups, the top players, the seasons and the cache.

**Groups** (decision 0046, call 1): WR; TE; RB (with FB); OL (T, G, C, OL); DL (the roster's DL,
DE, DT, NT; edge rushers listed as LB aren't in it). A player's group in a game is his listed
position on that game's roster (known before kickoff).

**Top players:** his team's top k in his group by snaps: WR 2, TE 1, RB 1, OL 5, DL 3. In season
by snaps to date (games before this one); between seasons by last season's.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

from pcf.config import get_config

c = pl.col
GROUP = {
    "WR": "WR", "TE": "TE", "RB": "RB", "FB": "RB", "HB": "RB",
    "OL": "OL", "T": "OL", "OT": "OL", "G": "OL", "OG": "OL", "C": "OL",
    "DL": "DL", "DE": "DL", "DT": "DL", "NT": "DL",
}  # fmt: skip
TOPK = {"WR": 2, "TE": 1, "RB": 1, "OL": 5, "DL": 3}
GROUPS = tuple(TOPK)
SKILL = ("WR", "TE", "RB")
OFFENSE = ("WR", "TE", "RB", "OL")
FIRST = 2013  # snap counts begin
SCORED = tuple(range(2017, 2025))  # the brief's backtest; 2025 is the vault, kept closed
WARM = (2014, 2015, 2016)  # walked too, for the ranges' first residuals (never scored)
LAST = 2024
# the three shares: (name, column, the pool its rates are fit in, the absent player's column)
MEASURES = {
    "snap": ("share", "group"),
    "target": ("tgt_share", "skill"),
    "carry": ("car_share", "skill"),
}
QUANTITY = {"snap": "snap_share", "target": "target_share", "carry": "carry_share"}


def cache_dir() -> Path:
    path = get_config().zone("interim") / "vacated_build"
    path.mkdir(parents=True, exist_ok=True)
    return path


def report_dir() -> Path:
    path = Path(__file__).resolve().parents[4] / "projects" / "vacated-opportunity" / "build"
    path.mkdir(parents=True, exist_ok=True)
    return path


class Report:
    """Lines printed and kept, written to `projects/vacated-opportunity/build/<name>.txt`."""

    def __init__(self, name: str):
        self.name = name
        self.lines: list[str] = []
        self.metrics: dict[str, float] = {}

    def __call__(self, line: str = "") -> None:
        print(line, flush=True)
        self.lines.append(line)

    def metric(self, key: str, value: float) -> None:
        self.metrics[key] = float(value)

    def save(self) -> Path:
        path = report_dir() / f"{self.name}.txt"
        path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")
        return path


def team_weights(teams: list[str], draws: int = 2000, seed: int | None = None) -> np.ndarray:
    """Poisson(1) weights per team for the team bootstrap (decision 0046, call 5)."""
    rng = np.random.default_rng(get_config().seed if seed is None else seed)
    return rng.poisson(1.0, size=(draws, len(teams))).astype(float)


def gain(err0: np.ndarray, err1: np.ndarray, team: np.ndarray, weights: np.ndarray | None = None,
         index: dict[str, int] | None = None) -> tuple[float, float, float]:  # fmt: skip
    """The share of err0's squared error that err1 removes (positive: err1 is better), with a
    90% team-bootstrap interval."""
    if index is None:
        uniq = sorted(set(team.tolist()))
        index = {t: i for i, t in enumerate(uniq)}
    if weights is None:
        weights = team_weights(sorted(index, key=index.get))
    ti = np.array([index[t] for t in team])
    w = weights[:, ti]
    d = err0 - err1
    m0 = err0.mean()
    if m0 <= 0:
        return 0.0, 0.0, 0.0
    bs = (w @ d) / w.sum(1).clip(1e-9)
    lo, hi = np.percentile(bs, [5, 95])
    return float(d.mean() / m0), float(lo / m0), float(hi / m0)


def fmt_gain(g: tuple[float, float, float]) -> str:
    return f"{100 * g[0]:+.1f}% (90% {100 * g[1]:+.1f}% to {100 * g[2]:+.1f}%)"
