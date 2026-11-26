"""I180 shipped for run snaps (decision 0052, call 36; the CEO, 2026-11-26: "For the run snap
problem I think we can try out the cheaper fix first").

The live run-snap stand-in (offensive snap share x the team's runs) undercounts a lead back's run
snaps: he is on the field for more of the runs than his share says, so his carries a run snap can
exceed 1. Each player-game's stand-in is multiplied by his ratio of exact to stand-in run snaps
**last season** (participation, a completed season: allowed in season as a prior, rule m), shrunk
toward his position's ratio that season with PRIOR attempts' weight; his position's ratio alone if
he had no last season; 1 before participation's first season has passed (2016 and earlier).

**The floor** (added after the first look, marked as such in decision 0052 call 36): a game's run
snaps are never fewer than his carries in it (every carry is on a run snap; participation's exact
rate never exceeds 0.97 for 150+ run snaps). Without it, 5 of 38 lead backs in 2024 still had a
corrected season rate above 1.
"""

from __future__ import annotations

import polars as pl

c = pl.col
PRIOR = 200.0  # attempts of weight on the position's ratio (as I180's test)
CORRECTED = {"car_per_run": "run_snaps"}  # measure -> participation's exact column
FLOOR = True  # run snaps >= carries in a game


def ratios(games: pl.DataFrame, exact: pl.DataFrame, col: str) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Each player-season's shrunk exact-over-stand-in ratio and his position's, keyed to the
    **next** season (the one it corrects), from participation's player-games."""
    g = games.join(
        exact.select("gsis_id", "game_id", exact=col), on=["gsis_id", "game_id"], how="inner"
    )
    s = g.group_by("gsis_id", "season", "pos").agg(
        E_=c("exact").fill_null(0).sum(), S_=c("den").sum()
    )
    ps = s.group_by("pos", "season").agg(rho_pos=c("E_").sum() / c("S_").sum())
    s = s.join(ps, on=["pos", "season"]).with_columns(
        ratio=(c("E_") + PRIOR * c("rho_pos")) / (c("S_") + PRIOR)
    )
    last = s.select("gsis_id", season=c("season") + 1, ratio_last="ratio")
    lastpos = ps.select("pos", season=c("season") + 1, rho_last="rho_pos")
    return last, lastpos


def corrected_games(
    games: pl.DataFrame, exact: pl.DataFrame, col: str, floor: bool = FLOOR
) -> pl.DataFrame:
    """The measure's player-games with `den` corrected (the plain stand-in kept as `den_plain`,
    the factor as `ratio_used`), floored at the game's `num` when `floor`."""
    last, lastpos = ratios(games, exact, col)
    return (
        games.join(last, on=["gsis_id", "season"], how="left")
        .join(lastpos, on=["pos", "season"], how="left")
        .with_columns(ratio_used=pl.coalesce("ratio_last", "rho_last", pl.lit(1.0)))
        .with_columns(den_plain=c("den"), den=c("den") * c("ratio_used"))
        .with_columns(den=pl.max_horizontal("den", "num") if floor else c("den"))
        .drop("ratio_last", "rho_last")
    )
