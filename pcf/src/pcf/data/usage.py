"""Each player-game's usage, weighted by the stakes of the snaps (snap-leverage: brief Terms,
exploration F3-F5, RESULTS; decisions 0033, 0034). Pure, and shared: the table part
`player_game.leverage_usage` is built with it from true participation, and a model may compute
the same measures live from participation-live's morning-after map (models can't import table
builders, leakage check 1, so it lives here, like `standings`).

`usage(on, plays)`: who was on the field, with a chance `p` (the map's on-field chance, or 1.0
from true participation), and each snap's `play.leverage` and expected pass chance → per
player-game and side:

- `snap_share`: his snaps over his side's;
- `lev_share`: his snaps weighted by leverage over his side's weighted snaps (leverage share);
- `hs_share`: his share of his side's high-stakes snaps (the top fifth by leverage);
- `role_gap`: `hs_share` minus `snap_share`, the passing-down role gap (the raw trust gap, renamed
  for what it is: F4, F10);
- `trust_oe`: his high-stakes snaps beyond what his on-field rate in each kind of situation
  predicts (fifths of the offense's expected pass chance), over his side's high-stakes snaps
  (trust over expected, F5).

The high-stakes measures are empty when the side had no high-stakes snap. `part_rows` turns true
participation into the part: one row per player-game, on the side he played most.
"""

from __future__ import annotations

import polars as pl

c = pl.col
SIDE = {"QB": "offense", "RB": "offense", "WR": "offense", "TE": "offense", "OL": "offense",
        "DL": "defense", "LB": "defense", "DB": "defense"}  # fmt: skip
GROUPS = tuple(SIDE)
MEASURES = ("snap_share", "lev_share", "hs_share", "role_gap", "trust_oe")
CELLS = 5  # fifths of the expected pass chance


def plays(play: pl.DataFrame) -> pl.DataFrame:
    """A view's `play` table → the snaps with a leverage: game_id, play_id, li, hs, cell."""
    return play.filter(c("leverage").is_not_null()).select(
        "game_id",
        "play_id",
        li="leverage",
        hs=c("high_stakes").cast(pl.Float64),
        cell=(c("pcf_xpass").fill_null(0.5) * CELLS).floor().clip(0, CELLS - 1).cast(pl.Int8),
    )


def usage(on: pl.DataFrame, snaps: pl.DataFrame) -> pl.DataFrame:
    """`on` (game_id, play_id, gsis_id, side, team, p) and `snaps` (from `plays`) → game_id,
    gsis_id, side, team and `MEASURES`, one row per player, game and side."""
    # In a fixed order, and every group summed in it: a parallel join's row order varies, and sums
    # in another order differ in the last digit, enough to flip a tree's split (leakage check 8)
    x = on.join(snaps, on=["game_id", "play_id"], how="inner").sort(
        "game_id", "play_id", "side", "gsis_id"
    )
    side = ["game_id", "team", "side"]
    # each side's snaps: every play the side was on the field for, counted once
    team_plays = x.select(*side, "play_id", "li", "hs", "cell").unique(
        [*side, "play_id"], keep="first", maintain_order=True
    )
    totals = team_plays.group_by(side, maintain_order=True).agg(
        t_n=pl.len(), t_li=c("li").sum(), t_hs=c("hs").sum()
    )
    cells = team_plays.group_by(*side, "cell", maintain_order=True).agg(
        c_n=pl.len(), c_hs=c("hs").sum()
    )
    # his on-field rate in each kind of situation, and the high-stakes snaps it predicts
    expected = (
        x.group_by(*side, "gsis_id", "cell", maintain_order=True)
        .agg(p_n=c("p").sum())
        .join(cells, on=[*side, "cell"], maintain_order="left")
        .sort(*side, "gsis_id", "cell")
        .group_by(*side, "gsis_id", maintain_order=True)
        .agg(exp_hs=(c("p_n") / c("c_n") * c("c_hs")).sum())
    )
    player = x.group_by(*side, "gsis_id", maintain_order=True).agg(
        snaps=c("p").sum(), lev=(c("p") * c("li")).sum(), hs_snaps=(c("p") * c("hs")).sum()
    )
    has_hs = c("t_hs") > 0
    return (
        player.join(totals, on=side)
        .join(expected, on=[*side, "gsis_id"])
        .with_columns(
            snap_share=c("snaps") / c("t_n"),
            lev_share=c("lev") / c("t_li"),
            hs_share=pl.when(has_hs).then(c("hs_snaps") / c("t_hs")),
            trust_oe=pl.when(has_hs).then((c("hs_snaps") - c("exp_hs")) / c("t_hs")),
        )
        .with_columns(role_gap=c("hs_share") - c("snap_share"))
        .select("game_id", "gsis_id", "side", "team", *MEASURES)
        .sort("game_id", "gsis_id", "side")
    )


PART_COLUMNS = ["lev_side", "lev_snaps", "lev_snap_share", "lev_share", "lev_hs_share",
                "lev_role_gap", "lev_trust_oe"]  # fmt: skip


def part_rows(on_field: pl.DataFrame, snaps: pl.DataFrame) -> pl.DataFrame:
    """`player_game.leverage_usage`: true participation (`player_play.on_field`: game_id, play_id,
    season, side, team, gsis_id, known_at) and `snaps` (from `plays`) → gsis_id, game_id, season,
    `PART_COLUMNS` and known_at (participation's), one row per player-game, on the side he played
    most (`lev_snaps` his snaps there)."""
    on = on_field.unique(["game_id", "play_id", "gsis_id"], keep="first", maintain_order=True)
    used = usage(on.select("game_id", "play_id", "gsis_id", "side", "team", p=pl.lit(1.0)), snaps)
    counts = (
        on.join(snaps.select("game_id", "play_id"), on=["game_id", "play_id"], how="semi")
        .group_by("game_id", "gsis_id", "side", maintain_order=True)
        .agg(lev_snaps=pl.len().cast(pl.Int32))
    )
    known = on.group_by("game_id", maintain_order=True).agg(
        c("season").first(), known_at=c("known_at").max()
    )
    return (
        used.join(counts, on=["game_id", "gsis_id", "side"])
        .sort("game_id", "gsis_id", "lev_snaps", "side", descending=[False, False, True, False])
        .unique(["gsis_id", "game_id"], keep="first", maintain_order=True)
        .join(known, on="game_id")
        .select(
            "gsis_id",
            "game_id",
            c("season").cast(pl.Int32),
            lev_side="side",
            lev_snaps="lev_snaps",
            lev_snap_share="snap_share",
            lev_share="lev_share",
            lev_hs_share="hs_share",
            lev_role_gap="role_gap",
            lev_trust_oe="trust_oe",
            known_at="known_at",
        )  # fmt: skip
        .sort("gsis_id", "game_id")
    )
