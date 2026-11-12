"""The on-field model: per position group, a player's chance of being on a snap given what's
known, and (the sequence rung) whether he was on the two snaps before.

    logit P(on_t | on_{t-1} = v, on_{t-2} = u) = base_t + memory_t(u, v)

- **base** (no memory): his snap share, the situation flags, the snap number in the drive, his
  own situational habits from earlier seasons (H32) and his team's from last season under the same
  head coach (H33).
- **memory** (the sequence rung, participation-live#F6, F8): the snap before and the one before
  that, whether they were in the same drive, no-huddle (F2), his own stay and return rates beyond
  his snap share (H35) and the snap number in the drive (fatigue, H34).

Trained on true histories of completed seasons (teacher forcing). In a game being reconstructed
the snaps before are unknown, so the chances come from `chain.infer`, which walks the team's snaps
forward and backward for every player at once.

Rungs (`KINDS`): `share` (no fit: the snap share), `league` (share and situation), `history`
(+ his and his team's habits; the exploration's bar), `sequence` (+ memory), `shuffled` (the
sequence rung fitted with its history and memory columns shuffled across rows: rule k's null).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression

from pcf.experts.participation_live.grid import FLAG_COLUMNS, FLAGS

c = pl.col
KINDS = ("share", "league", "history", "sequence", "shuffled")
MIN_ROWS = 2000  # a group with fewer training cells keeps the snap share
LEAGUE = ["ls", "ls2", *FLAG_COLUMNS, "dn"]
HISTORY = [*(f"ph_{k}_x" for k in FLAGS), *(f"th_{k}_x" for k in FLAGS), "phn"]
MEMORY = [
    "v_sd", "v_newdrive", "u_sd2", "uv_sd2", "v_nh", "start", "start2", "v_stay", "nv_ret",
    "v_dn", "v_ls",
]  # fmt: skip


def cell_columns(g: pl.DataFrame) -> pl.DataFrame:
    """The base columns of every cell (and what memory needs): `ls` (the share's log-odds),
    `ls2`, `dn` (snap in the drive / 5, capped at 3), the history terms (each habit times its
    flag) and `phn` (his history's size)."""
    s = c("share").clip(0.01, 0.99)
    ls = (s / (1 - s)).log()
    return g.with_columns(
        ls=ls,
        ls2=ls**2,
        dn=c("drive_n").clip(0, 15) / 5,
        phn=c("ph_n").clip(0, 3000) / 1000,
        **{f"ph_{k}_x": c(f"ph_{k}") * c(f"f_{k}") for k in FLAGS},
        **{f"th_{k}_x": c(f"th_{k}") * c(f"f_{k}") for k in FLAGS},
    )


def memory(cells: dict[str, np.ndarray], u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """The memory columns (MEMORY order) for states u (two snaps ago) and v (the snap before),
    each 0 or 1 per cell (or a scalar). `cells` holds sd, sd2, nh, start, start2, stay, ret, dn,
    ls as float arrays."""
    sd, sd2 = cells["sd"], cells["sd2"]
    first = 1 - cells["start"]
    cols = [
        v * sd,
        v * (1 - sd) * first,
        u * sd2,
        u * v * sd2,
        v * cells["nh"] * sd,
        cells["start"],
        cells["start2"],
        v * sd * cells["stay"],
        (1 - v) * sd * cells["ret"],
        v * sd * cells["dn"],
        v * sd * cells["ls"],
    ]
    n = len(sd)
    return np.column_stack([np.broadcast_to(np.asarray(x, dtype=np.float64), n) for x in cols])


def cell_arrays(g: pl.DataFrame) -> dict[str, np.ndarray]:
    """The per-cell inputs memory needs, as float arrays."""
    return {
        "sd": g["sd"].cast(pl.Float64).to_numpy(),
        "sd2": g["sd2"].cast(pl.Float64).to_numpy(),
        "nh": g["f_no_huddle"].cast(pl.Float64).to_numpy(),
        "start": g["start"].cast(pl.Float64).to_numpy(),
        "start2": g["start2"].cast(pl.Float64).to_numpy(),
        "stay": g["stay"].cast(pl.Float64).to_numpy(),
        "ret": g["ret"].cast(pl.Float64).to_numpy(),
        "dn": g["dn"].cast(pl.Float64).to_numpy(),
        "ls": g["ls"].cast(pl.Float64).to_numpy(),
    }


def true_states(g: pl.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """u, v: whether the player was truly on two snaps before and one snap before (0 at the
    game's start). `g` sorted by player-game and snap."""
    key = ["game_id", "side", "gsis_id"]
    s = g.select(
        v=c("on").shift(1).over(key).fill_null(0),
        u=c("on").shift(2).over(key).fill_null(0),
    )
    return s["u"].to_numpy().astype(np.float64), s["v"].to_numpy().astype(np.float64)


@dataclass
class GroupWeights:
    intercept: float = 0.0
    base: np.ndarray = field(default_factory=lambda: np.zeros(0))
    memory: np.ndarray = field(default_factory=lambda: np.zeros(len(MEMORY)))
    rows: int = 0


@dataclass
class OnFieldModel:
    """One rung's weights per position group. A group without weights keeps the snap share."""

    kind: str
    base_columns: list[str]
    groups: dict[str, GroupWeights]
    train_seasons: list[int]

    @property
    def uses_memory(self) -> bool:
        return self.kind in ("sequence", "shuffled")

    def base_logit(self, g: pl.DataFrame) -> np.ndarray:
        """Each cell's base log-odds (memory left out)."""
        out = g["ls"].to_numpy().astype(np.float64).copy()
        if self.kind == "share":
            return out
        x = g.select(self.base_columns).cast(pl.Float64).fill_null(0.0).to_numpy()
        grp = g["group"].to_numpy()
        for name, w in self.groups.items():
            idx = grp == name
            if idx.any():
                out[idx] = w.intercept + x[idx] @ w.base
        return out

    def memory_weights(self, g: pl.DataFrame) -> np.ndarray:
        """Each cell's memory weights (zeros without memory), shape (cells, len(MEMORY))."""
        out = np.zeros((g.height, len(MEMORY)))
        if not self.uses_memory:
            return out
        grp = g["group"].to_numpy()
        for name, w in self.groups.items():
            out[grp == name] = w.memory
        return out

    def explain(self) -> dict[str, dict[str, float]]:
        cols = [*self.base_columns, *(MEMORY if self.uses_memory else [])]
        return {
            name: {"intercept": w.intercept, **dict(zip(cols, [*w.base, *w.memory], strict=False))}
            for name, w in self.groups.items()
        }


def base_columns(kind: str) -> list[str]:
    return [] if kind == "share" else LEAGUE if kind == "league" else [*LEAGUE, *HISTORY]


def fit(train: pl.DataFrame, kind: str, seed: int = 0) -> OnFieldModel:
    """One rung from training cells (part-timers of completed seasons, with `on` and the cell
    columns), per position group. `shuffled` permutes the history and memory columns across rows
    (together, so their relations to each other survive and their link to `on` doesn't)."""
    if kind not in KINDS:
        raise ValueError(f"kind {kind!r} isn't one of {KINDS}")
    cols = base_columns(kind)
    seasons = sorted(train["season"].unique().to_list())
    model = OnFieldModel(kind, cols, {}, seasons)
    if kind == "share":
        return model
    train = train.sort("game_id", "side", "gsis_id", "n")
    u, v = true_states(train)
    mem = memory(cell_arrays(train), u, v) if kind in ("sequence", "shuffled") else None
    grp = train["group"].to_numpy()
    y_all = train["on"].to_numpy()
    x_all = train.select(cols).cast(pl.Float64).fill_null(0.0).to_numpy()
    rng = np.random.default_rng(seed)
    for name in sorted(set(grp)):
        idx = np.where(grp == name)[0]
        if len(idx) < MIN_ROWS or name == "OTHER":
            continue
        x = x_all[idx]
        if mem is not None:
            x = np.column_stack([x, mem[idx]])
        if kind == "shuffled":
            cut = len(LEAGUE)
            x[:, cut:] = x[rng.permutation(len(x)), cut:]
        m = LogisticRegression(max_iter=400).fit(x, y_all[idx])
        w = m.coef_[0]
        nb = len(cols)
        model.groups[name] = GroupWeights(
            intercept=float(m.intercept_[0]),
            base=w[:nb],
            memory=w[nb:] if mem is not None else np.zeros(len(MEMORY)),
            rows=len(idx),
        )
    return model
