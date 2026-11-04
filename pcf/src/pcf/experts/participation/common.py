"""What the participation models share: the outcome and a player's known shares.

The share is `offense_pct`, and 0 for a player who was inactive or never on the field. A player
with no snap-count row has no `snaps_known_at`, so whether a game's shares are known is judged by
the game: once any player in it has a row, the rest with none played no snaps (exploration F1).
"""

from __future__ import annotations

from collections.abc import Sequence

import polars as pl

c = pl.col
FIRST_SEASON = 2013  # snap counts (grain-tables#F2)
# Game statuses start in 2019; before, a player with no snap-count row didn't play
ACTIVE = (
    pl.when(c("status").is_not_null())
    .then(c("status") != "INA")
    .otherwise(c("offense_snaps").is_not_null())
)
SHARE = pl.when(ACTIVE).then(c("offense_pct").fill_null(0.0)).otherwise(0.0)


def known_shares(pg: pl.DataFrame, extra: Sequence[str] = ()) -> pl.DataFrame:
    """A view's player-games whose game has snap counts, oldest first: gsis_id, game_id, season,
    week, share, active, when the shares were known, and the `extra` columns."""
    return (
        pg.with_columns(shares_known_at=c("snaps_known_at").max().over("game_id"))
        .filter(c("shares_known_at").is_not_null())
        .select("gsis_id", "game_id", "season", "week", *extra, share=SHARE, active=ACTIVE,
                known_at="shares_known_at")  # fmt: skip
        .sort("gsis_id", "season", "week")
    )


def target_share(pg: pl.DataFrame, keys: Sequence[str]) -> pl.DataFrame:
    """The outcome: each player-game's share, known when the game's snap counts are."""
    return known_shares(pg).select(*keys, y="share", known_at="known_at")
