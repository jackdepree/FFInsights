"""The walks (decision 0052): every measure's walk-forward forecasts, next season and in season,
for players and teams, cached so the report, the copies and the history read one run.

- `next_season(measure)`: the season pairs with every rung (targets 2007-2024; scored 2018-2024).
- `in_season(measure)`: per test season T (2018-2024), the checkpoint rows fit on seasons
  before T, with every rung, for the next 4 games and the rest of the season; plus what the
  shuffled copies need (each T's full frame and fit).
"""

from __future__ import annotations

import numpy as np
import polars as pl

from pcf.experts.stabilization import common as K
from pcf.experts.stabilization import data as D
from pcf.experts.stabilization import evaluate as E
from pcf.experts.stabilization import inseason as I
from pcf.experts.stabilization import nextseason as N
from pcf.experts.stabilization import rates as R

c = pl.col
SHUFFLE_NEXT = ("x", "n", "m1", "trend", "layer_t")


# ---------------------------------------------------------------- inputs per measure
class Inputs:
    """The cached inputs, split by measure once."""

    def __init__(self) -> None:
        pg = D.player_games()
        self.games = {m.name: pg.filter(c("measure") == m.name) for m in K.MEASURES}
        self.rows = {m: R.season_rows(g) for m, g in self.games.items()}
        self.cond = D.conditions()
        tg = D.team_games()
        self.team_games = {
            (s, m): tg.filter((c("side") == s) & (c("measure") == m)).with_columns(
                gsis_id=c("team"), pos=c("side")
            )
            for s in ("off", "def")
            for m in K.TEAM_MEASURES
        }
        self.team_rows = {k: R.season_rows(g) for k, g in self.team_games.items()}
        self._sm: dict[str, pl.DataFrame] = {}

    def sm(self, m: str) -> pl.DataFrame:
        if m not in self._sm:
            self._sm[m] = N.season_m1(self.rows[m], self.games[m])
        return self._sm[m]


def others_of(m: K.Measure) -> list[str]:
    grp = list(K.GROUP_MEASURES[m.group])
    if m.group == "back":
        grp += [x for x in K.BORROW["back"] if x not in grp]
    return [x for x in grp if x != m.name]


def next_frame(
    inp: Inputs, m: K.Measure, open_last: bool = False
) -> tuple[pl.DataFrame, list[str], list[str], dict]:
    """Pairs with every candidate input, for one player measure (`open_last`: with the last
    season's rows, whose target isn't known yet)."""
    sm = inp.sm(m.name)
    p = N.pairs(
        sm, inp.rows[m.name], first_team=N.first_teams(inp.games[m.name]), open_last=open_last
    )
    oth = others_of(m)
    others = {o: inp.sm(o) for o in oth}
    ks = {o: N.pairs(inp.sm(o), inp.rows[o]) for o in oth}
    keys = K.COND_OF.get(m.name, ())
    cond = tcond = None
    if keys:
        cond, tcond = N.player_conditions(inp.cond, inp.games[m.name], keys)
    p = N.features(p, others, cond, tcond, sm, N.team_parts(sm), N.team_k(sm))
    cond_cols = [f"{p_}_{k}" for k in keys for p_ in ("cond", "chg")]
    return p, oth, cond_cols, ks


def next_rungs(
    p: pl.DataFrame, oth: list[str], cond_cols: list[str], ks: dict, seed: int | None = None
) -> pl.DataFrame:
    if seed is not None:
        cols = [*SHUFFLE_NEXT, *[f"o_{o}" for o in oth], *cond_cols]
        p = E.shuffled(p, [x for x in cols if x in p.columns], ("target", "pos"), seed)
    f = N.rungs(p, oth, ks, cond_cols)
    for r in ("m1", "pull", "ridge", "avg"):
        f = N.ranges(f, r)
    return f


# ---------------------------------------------------------------- in season
def in_frames(
    games: pl.DataFrame, rows: pl.DataFrame, ent: str, cls: str, lagged: bool, efficiency: bool
) -> dict[int, tuple[pl.DataFrame, dict]]:
    gc = I.centred_games(games, rows, ent, cls)
    first = int(rows["season"].min())
    out = {}
    # a test season needs a season before it to fit on (PFR's measures start in 2018, so they
    # are tested 2019-2024, as their next-season targets are; decision 0052, call 22)
    for T in (t for t in K.TEST if t > first):
        cp, info = I.season_frame(games, rows, T, ent, cls, lagged, efficiency, gc=gc)
        out[T] = (cp, info)
    return out


def in_rungs(
    frames: dict, horizon: str = "next", seed: int | None = None, cls: str = "pos"
) -> pl.DataFrame:
    out = []
    for T, (cp, info) in frames.items():
        if seed is not None:
            cols = [x for x in I.INPUTS if x in cp.columns]
            cp = E.shuffled(cp, cols, ("season", cls, "gi"), seed + T)
        a = I.rungs(cp, info, horizon).filter(c("season") == T)
        out.append(
            a.with_columns(
                q=pl.lit(info["par"]["q"]),
                qs=pl.lit(info["par"]["qs"]),
                phi=pl.lit(info["par_phi"]["phi"]),
                omega=pl.lit(info["par_om"]["omega"]),
                sigma2=pl.lit(info["sigma2"]),
                tau2=pl.lit(info["tau2"]),
            )
        )
    return pl.concat(out, how="diagonal_relaxed")


def gains_by(f: pl.DataFrame, new: str, base: str, ent: str, seed: int) -> E.Gain:
    return E.gain(f, new, base, ent, seed)


def nanmax(xs) -> float:
    xs = [x for x in xs if np.isfinite(x)]
    return max(xs) if xs else float("nan")
