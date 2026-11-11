"""Shared loaders for the player-pace exploration (2026-11-11). Discovery only: 2016-2024, the
2025 vault and 2026 are never read.

- `plays()`: every regular-season pass or run snap with PCF's pass rate over expected
  (`pcf_pass_oe`) and pace over expected (`pace_oe`, null where the gap isn't measured), from
  `play.pace`, with the offense, defense and week from `play.pbp`.
- `player_game()`: one row per player, side and team-game: the plays he was on the field for
  (`player_play.on_field`, post-season data) and the team's rates on and off them. For a defender
  the rates are the opponent offense's. Cached in `interim/player_pace/`.
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl

from pcf.config import get_config

c = pl.col
SEASONS = list(range(2016, 2025))  # participation's years before the vault
CACHE = get_config().zone("interim") / "player_pace"
TABLES = get_config().zone("tables")
MEASURES = {"proe": "pcf_pass_oe", "pace": "pace_oe"}


def _part(table: str, part: str, seasons=SEASONS, columns=None) -> pl.DataFrame:
    files = [TABLES / table / part / f"season={s}" / "data.parquet" for s in seasons]
    lf = pl.scan_parquet([f for f in files if f.exists()], extra_columns="ignore", missing_columns="insert")
    return (lf.select(columns) if columns else lf).collect()


def plays(seasons=SEASONS) -> pl.DataFrame:
    p = _part("play", "pace", seasons, ["game_id", "play_id", "season", "pcf_pass_oe", "pace_oe"])
    b = _part("play", "pbp", seasons, ["game_id", "play_id", "season_type", "week", "posteam", "defteam", "down", "qb_dropback", "rusher_player_id", "passer_player_id"])
    b = b.with_columns(c("play_id").cast(pl.Int64))
    out = p.join(b, on=["game_id", "play_id"]).filter(
        (c("season_type") == "REG") & c("pcf_pass_oe").is_not_null()
    )
    from pcf.data.clean import standard

    return standard.standard_teams(out, "posteam").pipe(standard.standard_teams, "defteam")


def player_game(rebuild: bool = False) -> pl.DataFrame:
    path = CACHE / "player_game.parquet"
    if path.exists() and not rebuild:
        return pl.read_parquet(path)
    p = plays()
    on = _part("player_play", "on_field", SEASONS, ["game_id", "play_id", "side", "team", "gsis_id", "position"])
    rows = on.join(p.select("game_id", "play_id", "season", "week", "posteam", "defteam", "pcf_pass_oe", "pace_oe"), on=["game_id", "play_id"])
    # the offense's team for both sides: a defender's rates are what the offense did against him
    rows = rows.with_columns(off_team=c("posteam"))
    keys = ["gsis_id", "side", "game_id", "season", "week"]
    per = rows.group_by(*keys).agg(
        team=c("team").mode().first(),
        off_team=c("off_team").mode().first(),
        position=c("position").drop_nulls().mode().first(),
        n_on=pl.len(),
        s_proe_on=c("pcf_pass_oe").sum(),
        n_pace_on=c("pace_oe").count(),
        s_pace_on=c("pace_oe").sum(),
    )
    team = p.group_by("game_id", off_team=c("posteam")).agg(
        n_team=pl.len(),
        s_proe_team=c("pcf_pass_oe").sum(),
        n_pace_team=c("pace_oe").count(),
        s_pace_team=c("pace_oe").sum(),
    )
    out = per.join(team, on=["game_id", "off_team"]).with_columns(
        n_off=c("n_team") - c("n_on"),
        n_pace_off=c("n_pace_team") - c("n_pace_on"),
    ).with_columns(
        proe_on=c("s_proe_on") / c("n_on"),
        pace_on=c("s_pace_on") / c("n_pace_on"),
        proe_team=c("s_proe_team") / c("n_team"),
        pace_team=c("s_pace_team") / c("n_pace_team"),
        proe_off=pl.when(c("n_off") > 0).then((c("s_proe_team") - c("s_proe_on")) / c("n_off")),
        pace_off=pl.when(c("n_pace_off") > 0).then((c("s_pace_team") - c("s_pace_on")) / c("n_pace_off")),
        share=c("n_on") / c("n_team"),
    )
    CACHE.mkdir(parents=True, exist_ok=True)
    out.write_parquet(path)
    return out


def group(position: str | None) -> str:
    g = {
        "QB": "QB", "RB": "RB", "FB": "RB", "WR": "WR", "TE": "TE",
        "T": "OL", "G": "OL", "C": "OL", "OL": "OL", "OT": "OL", "OG": "OL", "LT": "OL", "RT": "OL", "LG": "OL", "RG": "OL",
        "DE": "DL", "DT": "DL", "NT": "DL", "DL": "DL",
        "OLB": "LB", "ILB": "LB", "MLB": "LB", "LB": "LB",
        "CB": "DB", "SS": "DB", "FS": "DB", "S": "DB", "DB": "DB",
    }
    return g.get(position or "", "other")


def with_group(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(group=c("position").map_elements(group, return_dtype=pl.Utf8))


def boot_r(x: np.ndarray, y: np.ndarray, blocks: np.ndarray, n: int = 300, seed: int = 7) -> tuple[float, float, float]:
    """Correlation with a 90% interval from resampling whole blocks (teams or players)."""
    ok = ~(np.isnan(x) | np.isnan(y))
    x, y, blocks = x[ok], y[ok], blocks[ok]
    est = float(np.corrcoef(x, y)[0, 1])
    keys, inv = np.unique(blocks, return_inverse=True)
    idx = [np.flatnonzero(inv == k) for k in range(len(keys))]
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n):
        pick = np.concatenate([idx[k] for k in rng.integers(0, len(keys), len(keys))])
        vals.append(np.corrcoef(x[pick], y[pick])[0, 1])
    lo, hi = np.nanpercentile(vals, [5, 95])
    return est, float(lo), float(hi)
