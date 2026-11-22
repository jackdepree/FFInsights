"""Whose is a measure? The skill-over-expected yardstick: does a player's season rate repeat the
next season, and does he keep it when he changes teams ("share kept")?

Moved from the explorations (skill-over-expected's first and third looks, context-v2's fourth
look) into the package for context-retro (decision 0040), with one fix: the main team and
position break ties the same way every run (the brief's call 4). Before, a player with as many
games for two teams got whichever came first, and the movers changed between runs.

- **Main team:** the team he was on the roster for in the most games; ties go to the team code
  first in the alphabet. **Main position:** the on-field position he played most snaps at, ties
  alphabetical; the roster's where he has no snaps.
- **Season pairs:** each player-season with at least `floor` of the denominator, joined to his
  next season; `moved` when his main team changed.
- **Share kept:** movers' repeat over stayers' repeat, with each season's league average taken
  out; the repeat's 90% interval from resampling players.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import polars as pl

c = pl.col
DRAWS = 2000
REPEAT_BAR = 0.2  # skill-over-expected's bars: repeats 0.2+ and movers keep half
KEPT_BAR = 0.5


def r(x: np.ndarray | pl.Series, y: np.ndarray | pl.Series) -> float:
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 4 or np.std(x[ok]) == 0 or np.std(y[ok]) == 0:
        return float("nan")
    return float(np.corrcoef(x[ok], y[ok])[0, 1])


def _most(frame: pl.DataFrame, by: list[str], value: str, name: str) -> pl.DataFrame:
    """Each group's most frequent `value`; ties to the value first in sort order."""
    counts = frame.group_by(*by, value).agg(n=pl.len())
    return (
        counts.sort([*by, "n", value], descending=[*([False] * len(by)), True, False])
        .group_by(by, maintain_order=True)
        .first()
        .select(*by, c(value).alias(name))
    )


def main_team(roster: pl.DataFrame, on_field: pl.DataFrame) -> pl.DataFrame:
    """pid, season, team, position: the main team from the roster's games (`gsis_id, season,
    team, position`, one row per game), the main position from the on-field snaps (`gsis_id,
    season, position`, one row per snap), else the roster's."""
    team = _most(roster, ["gsis_id", "season"], "team", "team")
    roster_pos = _most(roster, ["gsis_id", "season"], "position", "roster_pos")
    field_pos = _most(on_field, ["gsis_id", "season"], "position", "field_pos")
    out = team.join(roster_pos, on=["gsis_id", "season"], how="left").join(
        field_pos, on=["gsis_id", "season"], how="left"
    )
    position = pl.coalesce("field_pos", "roster_pos")
    return out.select(pid="gsis_id", season="season", team="team", position=position).sort(
        "pid", "season"
    )


def season_pairs(
    games: pl.DataFrame, sums: Sequence[str], floor_col: str, floor: float,
    rates: Mapping[str, tuple[str, str]], teams: pl.DataFrame,
) -> pl.DataFrame:  # fmt: skip
    """`games`: one row per player (`pid`) and game with `season` and the `sums`. Per
    player-season (with `floor_col` ≥ `floor`), the named `rates` (numerator, denominator), next
    season's (`<rate>_n`), and `moved` (his main team changed)."""
    s = games.group_by("pid", "season").agg(*[c(k).sum() for k in sums])
    s = s.filter(c(floor_col) >= floor)
    s = s.with_columns(**{k: c(a) / c(b) for k, (a, b) in rates.items()})
    nxt = s.select("pid", (c("season") - 1).alias("season"), *[c(k).alias(f"{k}_n") for k in rates])
    t = teams.select("pid", "season", "team")
    p = s.join(nxt, on=["pid", "season"]).join(t, on=["pid", "season"], how="left")
    p = p.join(t.select("pid", (c("season") - 1).alias("season"), new_team="team"),
               on=["pid", "season"], how="left")  # fmt: skip
    return p.with_columns(moved=(c("team") != c("new_team")).fill_null(False))


def _boot(p: pl.DataFrame, a: str, b: str, seed: int, draws: int) -> tuple[float, float]:
    """The repeat's 90% interval, resampling players (all their pairs together)."""
    rng = np.random.default_rng(seed)
    pid = p["pid"].to_numpy()
    u, inv = np.unique(pid, return_inverse=True)
    x, y = p[a].to_numpy().astype(float), p[b].to_numpy().astype(float)
    out = []
    for _ in range(draws):
        w = np.bincount(rng.integers(0, len(u), len(u)), minlength=len(u))[inv]
        idx = np.repeat(np.arange(len(pid)), w)
        out.append(r(x[idx], y[idx]))
    lo, hi = np.nanquantile(out, [0.05, 0.95])
    return float(lo), float(hi)


def passes(repeat: float, share: float) -> bool:
    return bool(repeat >= REPEAT_BAR and np.isfinite(share) and share >= KEPT_BAR)


def kept(p: pl.DataFrame, rate: str, seed: int = 0, draws: int = DRAWS) -> dict:
    """One rate's repeat (each season's league average out), its 90% interval, stayers' and
    movers' repeats, the share kept, and whether it passes both bars."""
    n = f"{rate}_n"
    p = p.filter(c(rate).is_finite() & c(n).is_finite())
    raw = r(p[rate], p[n])
    p = p.with_columns(c(rate) - c(rate).mean().over("season"), c(n) - c(n).mean().over("season"))
    st, mv = p.filter(~c("moved")), p.filter(c("moved"))
    rs, rm = r(st[rate], st[n]), r(mv[rate], mv[n])
    repeat = r(p[rate], p[n])
    lo, hi = _boot(p, rate, n, seed, draws)
    share = rm / rs if rs and np.isfinite(rs) else float("nan")
    return {"measure": rate, "pairs": p.height, "movers": mv.height, "raw_repeat": raw,
            "repeat": repeat, "lo90": lo, "hi90": hi, "stayers": rs, "movers_r": rm,
            "share_kept": share, "passes": passes(repeat, share)}  # fmt: skip


def kept_interval(p: pl.DataFrame, rate: str, seed: int = 0, draws: int = DRAWS) -> tuple:
    """The share kept's 90% interval, resampling players (movers and stayers together): wide
    when movers are few (idea I90 asked for it)."""
    n = f"{rate}_n"
    p = p.filter(c(rate).is_finite() & c(n).is_finite())
    p = p.with_columns(c(rate) - c(rate).mean().over("season"), c(n) - c(n).mean().over("season"))
    rng = np.random.default_rng(seed)
    pid = p["pid"].to_numpy()
    u, inv = np.unique(pid, return_inverse=True)
    x, y = p[rate].to_numpy().astype(float), p[n].to_numpy().astype(float)
    moved = p["moved"].to_numpy()
    out = []
    for _ in range(draws):
        w = np.bincount(rng.integers(0, len(u), len(u)), minlength=len(u))[inv]
        idx = np.repeat(np.arange(len(pid)), w)
        m = moved[idx]
        rs, rm = r(x[idx][~m], y[idx][~m]), r(x[idx][m], y[idx][m])
        out.append(rm / rs if rs and np.isfinite(rs) else np.nan)
    lo, hi = np.nanquantile(out, [0.05, 0.95])
    return float(lo), float(hi)
