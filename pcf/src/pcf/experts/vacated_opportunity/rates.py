"""The CEO's plus-minus for all players (method 2): the transfer rates, fit on completed seasons.

Every player-game's share, measured against his own player-team-season average, is regressed on
each absent top teammate's share (that teammate's season share, times 1 if he missed the game):

- **the pooled part**, one rate per pair of groups (`WR>WR`: how much a WR's share rises per unit
  of an absent top WR's share), the standing table;
- **the pair part**, one value per stayer and same-group top teammate in a season (I49), shrunk by
  the same penalty;
- optionally **a team or coach part** (the structured rung, H37): a same-group rate per team (or
  head coach) and group, shrunk toward the pooled rate by the penalty.

An absence (decision 0046, call 2): a team game between a top player's first and last game for
that team that season in which he had no snap. Completed seasons only (rule m): in season s the
rates come from fits on seasons before s.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import polars as pl
import scipy.sparse as sp
from scipy.sparse.linalg import lsqr

from pcf.experts.vacated_opportunity import common as K

c = pl.col
GRID = (0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0)  # decision 0046, call 12: extended below 1


def pool_keys(groups: Sequence[str]) -> list[str]:
    return [f"{a}>{b}" for a in groups for b in groups]


def season_tops(pg: pl.DataFrame) -> pl.DataFrame:
    """Each player-team-season's games, snaps, mean shares, first and last week, and whether he
    was among his team's top k in his group by snaps (his most-listed group that season)."""
    grp = pg.group_by("gsis_id", "team", "season").agg(group=c("group").mode().first())
    ps = (
        pg.drop("group").join(grp, on=["gsis_id", "team", "season"])
        .group_by("gsis_id", "team", "season", "group")
        .agg(games=pl.len(), snaps=c("snaps").sum(), share=c("share").mean(),
             tgt_share=c("tgt_share").mean(), car_share=c("car_share").mean(),
             first_wk=c("week").min(), last_wk=c("week").max())
    )  # fmt: skip
    ps = ps.with_columns(
        rank=c("snaps").rank("ordinal", descending=True).over("team", "season", "group")
    )
    k = c("group").replace_strict(K.TOPK, return_dtype=pl.Int64)
    return ps.with_columns(top=c("rank") <= k)


def absences(pg: pl.DataFrame, tg: pl.DataFrame) -> pl.DataFrame:
    """Every top player's team-games between his first and last game for the team that season in
    which he had no snap, with his season shares (`w_share`, `w_tgt`, `w_car`)."""
    ps = season_tops(pg).filter(c("top"))
    a = ps.select(
        j="gsis_id", team="team", season="season", group_j="group", w_share="share",
        w_tgt="tgt_share", w_car="car_share", first_wk="first_wk", last_wk="last_wk",
    ).join(tg.select("game_id", "team", "season", "week"), on=["team", "season"])  # fmt: skip
    a = a.filter(c("week").is_between(c("first_wk"), c("last_wk")))
    return a.join(pg.select(j="gsis_id", game_id="game_id"), on=["j", "game_id"], how="anti")


@dataclass
class Design:
    """One season block's within-player-season design."""

    X: sp.csr_matrix
    y: np.ndarray
    keys: list[str]
    rows: pl.DataFrame


def design(rows: pl.DataFrame, ab: pl.DataFrame, ycol: str, wcol: str, groups: Sequence[str],
           extra: str | None = None, pair: bool = True) -> Design:  # fmt: skip
    """rows: player-games (gsis_id, team, season, game_id, group, ycol[, coach]); ab: absences
    (j, team, game_id, group_j, wcol). `extra`: "team" or "coach" adds the structured part's
    columns (same group only). Each column and y are demeaned within the player-team-season."""
    rows = rows.with_row_index("idx").with_columns(
        psk=pl.concat_str(c("gsis_id"), c("team"), c("season").cast(pl.Utf8), separator="|")
    )
    cols = ["idx", "gsis_id", "team", "season", "game_id", "group", "psk"]
    if extra == "coach":
        cols.append("coach")
    pr = (
        rows.select(cols)
        .join(ab.select("j", "team", "game_id", "group_j", w=c(wcol)), on=["team", "game_id"])
        .filter(c("j") != c("gsis_id"))
    )
    parts = [pr.select("idx", "psk", key=c("group") + ">" + c("group_j"), val="w")]
    same = pr.filter(c("group") == c("group_j"))
    if pair:
        parts.append(same.select(
            "idx", "psk",
            key=c("gsis_id") + ">" + c("j") + ">" + c("season").cast(pl.Utf8), val="w",
        ))  # fmt: skip
    if extra:
        who = c("team") if extra == "team" else c("coach").fill_null("?")
        parts.append(
            same.select("idx", "psk", key=pl.lit(extra + "|") + who + "|" + c("group"), val="w")
        )
    L = pl.concat(parts).group_by("idx", "psk", "key").agg(c("val").sum())
    n = rows.group_by("psk").agg(n=pl.len())
    M = (
        L.group_by("psk", "key")
        .agg(s=c("val").sum())
        .join(n, on="psk")
        .with_columns(m=c("s") / c("n"))
    )
    D = (
        rows.select("idx", "psk").join(M.select("psk", "key", "m"), on="psk")
        .join(L.select("idx", "key", "val"), on=["idx", "key"], how="left")
        .with_columns(v=c("val").fill_null(0.0) - c("m"))
    )  # fmt: skip
    base = pool_keys(groups)
    other = sorted(set(D["key"].unique().to_list()) - set(base))
    keys = base + other
    kix = pl.DataFrame({"key": keys, "col": np.arange(len(keys), dtype=np.int64)})
    D = D.join(kix, on="key")
    X = sp.csr_matrix(
        (D["v"].to_numpy(), (D["idx"].to_numpy(), D["col"].to_numpy())),
        shape=(rows.height, len(keys)),
    )
    y = rows[ycol].to_numpy() - rows.select(c(ycol).mean().over("psk")).to_series().to_numpy()
    return Design(X, y, keys, rows)


def ridge(X: sp.spmatrix, y: np.ndarray, alpha: float) -> np.ndarray:
    """Ridge without an intercept (the design is demeaned): argmin |y - Xb|^2 + alpha |b|^2."""
    return lsqr(X, y, damp=float(np.sqrt(alpha)), atol=1e-8, btol=1e-8, iter_lim=5000)[0]


def stack(blocks: Sequence[Design]) -> tuple[sp.csr_matrix, np.ndarray, list[str]]:
    """Season blocks into one design over the union of their columns."""
    keys: list[str] = []
    seen: dict[str, int] = {}
    for b in blocks:
        for k in b.keys:
            if k not in seen:
                seen[k] = len(keys)
                keys.append(k)
    mats = []
    for b in blocks:
        m = np.array([seen[k] for k in b.keys])
        coo = b.X.tocoo()
        mats.append(
            sp.csr_matrix((coo.data, (coo.row, m[coo.col])), shape=(b.X.shape[0], len(keys)))
        )
    return sp.vstack(mats).tocsr(), np.concatenate([b.y for b in blocks]), keys


@dataclass
class Fit:
    """One refit: the coefficients by key, the penalty, and the last season it saw."""

    coef: dict[str, float]
    alpha: float
    through: int
    inner: dict[float, float] = field(default_factory=dict)

    def pooled(self, groups: Sequence[str]) -> dict[str, float]:
        return {k: self.coef.get(k, 0.0) for k in pool_keys(groups)}


def choose_alpha(
    blocks: dict[int, Design], seasons: Sequence[int], grid=GRID
) -> tuple[float, dict]:
    """The penalty by a time-ordered inner split (decision 0050, call 4): fit on all but the
    last training season, score the last one's demeaned shares (its own pair columns unseen)."""
    if len(seasons) < 2:
        return 1.0, {}
    X, y, keys = stack([blocks[s] for s in seasons[:-1]])
    test = blocks[seasons[-1]]
    ix = {k: i for i, k in enumerate(keys)}
    errs = {}
    for a in grid:
        b = ridge(X, y, a)
        bt = np.array([b[ix[k]] if k in ix else 0.0 for k in test.keys])
        errs[a] = float(((test.y - test.X @ bt) ** 2).mean())
    return min(errs, key=errs.get), errs


def fit_through(blocks: dict[int, Design], through: int, choose: bool = True,
                alpha: float | None = None) -> Fit:  # fmt: skip
    seasons = sorted(s for s in blocks if s <= through)
    inner = {}
    if alpha is None:
        alpha, inner = choose_alpha(blocks, seasons) if choose else (1.0, {})
    X, y, keys = stack([blocks[s] for s in seasons])
    b = ridge(X, y, alpha)
    return Fit(dict(zip(keys, b.tolist(), strict=True)), alpha, through, inner)


def blocks_for(pg: pl.DataFrame, ab: pl.DataFrame, measure: str, seasons: Sequence[int],
               extra: str | None = None, tg: pl.DataFrame | None = None) -> dict[int, Design]:  # fmt: skip
    """One design per season for a measure (`snap`, `target`, `carry`)."""
    ycol, pool = K.MEASURES[measure]
    wcol = {"share": "w_share", "tgt_share": "w_tgt", "car_share": "w_car"}[ycol]
    groups = K.GROUPS if pool == "group" else K.SKILL
    rows = pg.filter(c("group").is_in(list(groups)))
    if extra == "coach":
        rows = rows.join(tg.select("game_id", "team", "coach"), on=["game_id", "team"], how="left")
    a = ab.filter(c("group_j").is_in(list(groups)))
    cols = ["gsis_id", "team", "season", "game_id", "group", ycol] + (
        ["coach"] if extra == "coach" else []
    )
    return {s: design(rows.filter(c("season") == s).select(cols), a.filter(c("season") == s), ycol, wcol,
                      groups, extra) for s in seasons}  # fmt: skip


def rate_table(fits: dict[int, Fit], groups: Sequence[str], measure: str) -> pl.DataFrame:
    """The standing transfer-rate table: one row per refit (the last completed season it saw) and
    pair of groups."""
    out = []
    for through, f in sorted(fits.items()):
        for k, v in f.pooled(groups).items():
            a, b = k.split(">")
            out.append({"measure": measure, "through": through, "group": a, "absent_group": b,
                        "rate": v, "alpha": f.alpha})  # fmt: skip
    return pl.DataFrame(out)
