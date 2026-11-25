"""Shared pieces for the build's round-2 scripts (the CEO's spot-check and the backlog ideas,
2026-11-25): the saved history (run 696a3f0b) as priors, names and the report writer."""

# ruff: noqa: E501
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

from pcf.config import get_config

c = pl.col
RUN = "696a3f0b827f48549dfc9e3393655df1"
Z = [f"z{i}" for i in range(6)]
T_OFF = ["t0_snap_share", "t1_tgt_per_pass", "t2_car_per_run", "t3_adot", "t4_adj_run", "t5_adj_p11"]
T_DEF = ["t0_snap_share", "t1_rush_per_pass", "t2_tkl_per_snap", "t3_tkl_depth", "t4_adj_p11", "t5_adj_late"]


class Say:
    def __init__(self, path: Path) -> None:
        self.path, self.lines = path, []

    def __call__(self, *t: str) -> None:
        for x in t:
            self.lines.append(x)
            print(x, flush=True)

    def save(self) -> None:
        self.path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")


def history() -> pl.DataFrame:
    return pl.read_parquet(get_config().zone("outputs") / "roles-archetypes" / RUN / "history.parquet")


def main_rows(h: pl.DataFrame) -> pl.DataFrame:
    """Each player-season-side's main team (most snaps)."""
    return h.sort("snaps", descending=True).unique(["gsis_id", "season", "side"], keep="first")


def offense_prior(h: pl.DataFrame | None = None) -> pl.DataFrame:
    """Test 4's prior: each player-season's main-team row, as a prior for the next season."""
    m = main_rows(history() if h is None else h).filter(c("side") == "offense")
    return m.select("gsis_id", "group", "role", "coarse", "sure", "snaps", *Z, *T_OFF, season=c("season") + 1)


def shuffled(prior: pl.DataFrame, cols, seed: int) -> pl.DataFrame:
    """The prior's columns moved together to another player of the same season and group (test 4's copies)."""
    rng = np.random.default_rng(seed)
    key = (prior["season"].cast(pl.String) + prior["group"]).to_numpy()
    order = np.arange(prior.height)
    for k in np.unique(key):
        idx = np.flatnonzero(key == k)
        order[idx] = idx[rng.permutation(len(idx))]
    return pl.concat([prior.drop(cols), prior.select(cols)[order]], how="horizontal")


def names() -> pl.DataFrame:
    from pcf.experts.roles_archetypes.run import player_names

    return player_names()
