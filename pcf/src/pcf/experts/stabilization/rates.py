"""Season rows, the pull target and k for one measure (decision 0052, calls 3-4), on the shared
shrink (`pcf.validation.stabilize`).

- Each measure is read per entity (a player, or a team's side) and **class**: a player's position
  (the pull target's class), or a team's side.
- **The pull target** is the class's mean (num over den summed over entity-seasons with at least
  `MIN_DEN` attempts and classes with at least `MIN_CLASS` of them). A forecast for season T is
  read against season T-1's mean, which is known before T (the brief: "League shifts are removed by
  centring on last season's position mean").
- **k** is pooled over a measure's classes, each entity-season centred by its own class-season
  mean (the exploration's `fit_m1`), fit on seasons up to the input season only.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from pcf.validation import stabilize as S

c = pl.col
MIN_DEN = 10.0  # attempts an entity-season needs to count toward the means and k
MIN_CLASS = 20  # entity-seasons a class-season needs for its own mean


def season_rows(games: pl.DataFrame, ent: str = "gsis_id", cls: str = "pos") -> pl.DataFrame:
    """Per entity-season: num, den, n_games, its class (the most attempts) and its main team (the
    most attempts; ties alphabetical)."""
    by_cls = games.group_by(ent, "season", cls).agg(d=c("den").sum()).sort(
        [ent, "season", "d", cls], descending=[False, False, True, False]
    ).group_by(ent, "season", maintain_order=True).first().select(ent, "season", cls)
    by_team = games.group_by(ent, "season", "team").agg(d=c("den").sum()).sort(
        [ent, "season", "d", "team"], descending=[False, False, True, False]
    ).group_by(ent, "season", maintain_order=True).first().select(ent, "season", "team")
    s = games.group_by(ent, "season").agg(num=c("num").sum(), den=c("den").sum(),
                                          n_games=pl.len())  # fmt: skip
    return s.join(by_cls, on=[ent, "season"]).join(by_team, on=[ent, "season"], how="left")


def class_means(rows: pl.DataFrame, cls: str = "pos") -> pl.DataFrame:
    """Per class-season: mu (num over den over entity-seasons with MIN_DEN+ attempts), for classes
    with MIN_CLASS such rows (a team's side always has 32): the shared `means`."""
    need = MIN_CLASS if cls != "side" else 1
    return S.means(rows.filter(c(cls).is_not_null()), by=(cls,), floor=MIN_DEN, min_rows=need)


def centred(rows: pl.DataFrame, cls: str = "pos", target: str = "same") -> pl.DataFrame:
    """Rows with MIN_DEN+ attempts, with `rate`, `mu` (the pull target: its class's mean that
    season, or last season's for `target="last"`) and `x` = rate - mu: the shared `centre`."""
    need = MIN_CLASS if cls != "side" else 1
    return S.centre(rows.filter(c(cls).is_not_null()), by=(cls,), target=target, floor=MIN_DEN,
                    min_rows=need)  # fmt: skip


def game_rows(games: pl.DataFrame, rows: pl.DataFrame, ent: str = "gsis_id") -> pl.DataFrame:
    """His games, with his season's rate, for the noise (the shared `noise`)."""
    return games.filter(c("den") > 0).select(ent, "season", "num", "den").join(
        rows.select(ent, "season", "rate", "n_games"), on=[ent, "season"]
    )


def fit_k(rows: pl.DataFrame, games: pl.DataFrame, upto: int, ent: str = "gsis_id",
          cls: str = "pos") -> dict:  # fmt: skip
    """sigma2, tau2 and k from entity-seasons up to `upto` with MIN_DEN+ attempts, centred by their
    own class-season means, pooled over classes (the shared `components`)."""
    tr = centred(rows.filter(c("season") <= upto), cls)
    g = game_rows(games.filter(c("season") <= upto), tr, ent)
    sigma2, tau2 = S.components(tr, g, key=(ent, "season"))
    return {"sigma2": sigma2, "tau2": tau2, "k": S.k_of(sigma2, tau2)}


def season_r(pairs: pl.DataFrame, k: float) -> float:
    """The true rate's season-to-season correlation: the observed r of centred rates (weighted by
    1 / (1/n1 + 1/n2)) over the square root of the two seasons' average reliabilities."""
    if pairs.height < 30:
        return float("nan")
    x, y = pairs["x"].to_numpy(), pairs["y"].to_numpy()
    n1, n2 = pairs["n"].to_numpy(), pairs["w"].to_numpy()
    w = 1 / (1 / n1 + 1 / n2)
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    cov = np.average((x - mx) * (y - my), weights=w)
    r = cov / np.sqrt(np.average((x - mx) ** 2, weights=w) * np.average((y - my) ** 2, weights=w))
    rel = np.sqrt(np.average(S.reliability(n1, k), weights=w)
                  * np.average(S.reliability(n2, k), weights=w))  # fmt: skip
    return float(r / rel)
