"""Build the tables from the raw nflverse copy (`pcf tables build`), a season at a time.

The builders in `games`, `plays` and `player_game` are pure; this module reads their inputs with
`scan`, standardizes them, and writes the parts.
"""

import time
from collections.abc import Callable, Sequence
from pathlib import Path

import polars as pl

from pcf.core.log import get_logger
from pcf.data.clean import standard
from pcf.data.clean.depth_charts import daily_depth_rows, depth_labels, weekly_depth_rows
from pcf.data.sources.nflverse import DATASETS, files, scan
from pcf.data.tables.games import game_parts, team_game_parts
from pcf.data.tables.player_game import DAILY_CHARTS_FROM, player_game_parts
from pcf.data.tables.plays import play_parts, player_play_parts
from pcf.data.tables.store import write_parts
from pcf.data.timeline import Calendar, calendar, team_kickoffs

log = get_logger(__name__)


def local_seasons(dataset: str) -> list[int]:
    """Seasons of a dataset in the raw copy."""
    ds = DATASETS[dataset]
    if ds.per_season:
        return sorted({int(ds.match(p.name)["season"]) for p in files(dataset)})
    seasons = scan(dataset).select(pl.col("season").cast(pl.Int32).unique()).collect()
    return sorted(seasons["season"].to_list())


def _season(dataset: str, season: int) -> pl.DataFrame | None:
    """One season of a dataset, or None if the raw copy has none."""
    if season not in local_seasons(dataset):
        return None
    lf = scan(dataset, [season])
    if not DATASETS[dataset].per_season:  # one file for every season (grain-tables#F9)
        lf = lf.filter(pl.col("season").cast(pl.Int32) == season)
    return lf.collect()


def _schedules() -> pl.DataFrame:
    return standard.schedules(scan("schedules").collect())


def depth_labels_for(season: int, cal: Calendar) -> pl.DataFrame | None:
    """A season's depth labels: weekly charts through 2024, daily snapshots from 2025."""
    charts = _season("depth_charts", season)
    if charts is None:
        return None
    if season >= DAILY_CHARTS_FROM:
        kickoffs = team_kickoffs(cal.games.filter(pl.col("season") == season))
        return depth_labels(daily_depth_rows(charts, kickoffs))
    return depth_labels(weekly_depth_rows(charts))


def _rosters(season: int) -> pl.DataFrame | None:
    rosters = _season("weekly_rosters", season)
    return None if rosters is None else standard.weekly_rosters(rosters)


def _players() -> pl.DataFrame:
    return scan("players").select("pfr_id", "gsis_id").collect()


def build_games(name: str, seasons: Sequence[int], cal: Calendar, root: Path | None) -> None:
    schedules = _schedules().filter(pl.col("season").is_in(list(seasons)))
    if name == "game":
        parts = game_parts(schedules, cal)
    else:
        stats = scan("team_stats", [s for s in seasons if s in local_seasons("team_stats")])
        parts = team_game_parts(schedules, cal, stats.collect())
    write_parts(parts, name, seasons, root)


def build_play(season: int, cal: Calendar, root: Path | None) -> None:
    parts = play_parts(
        _season("pbp", season),
        cal,
        participation=_season("participation", season),
        ftn=_season("ftn_charting", season),
    )
    write_parts(parts, "play", [season], root)


def build_player_play(season: int, cal: Calendar, root: Path | None) -> None:
    pbp = scan("pbp", [season]).select(
        "game_id", "play_id", "play_type", "season", "week", "season_type", "posteam", "defteam"
    )
    participation = scan("participation", [season]).select(
        "nflverse_game_id", "play_id", "offense_players", "defense_players"
    )
    parts = player_play_parts(
        pbp.collect(),
        participation.collect(),
        depth_labels_for(season, cal),
        _rosters(season),
        cal,
    )
    write_parts(parts, "player_play", [season], root)


def build_player_game(season: int, cal: Calendar, root: Path | None) -> None:
    players = _players()
    snaps = _season("snap_counts", season)
    stats = _season("player_stats", season)
    ffo = _season("ff_opportunity", season)
    injuries = _season("injuries", season)
    ngs = {k: _season(f"ngs_{k}", season) for k in ("passing", "receiving", "rushing")}
    pfr = {k: _season(f"pfr_week_{k}", season) for k in ("pass", "rush", "rec", "def")}
    parts = player_game_parts(
        cal,
        _rosters(season),
        snaps=None if snaps is None else standard.snap_counts(snaps, players),
        stats=None if stats is None else standard.player_stats(stats),
        ff_opportunity=None if ffo is None else standard.ff_opportunity(ffo),
        injuries=None if injuries is None else standard.injuries(injuries),
        labels=depth_labels_for(season, cal),
        ngs={k: df for k, df in ngs.items() if df is not None},
        pfr={k: df for k, df in pfr.items() if df is not None},
        players=players,
    )
    write_parts(parts, "player_game", [season], root)


Builder = Callable[[int, Calendar, Path | None], None]
# Each table: the dataset that decides its seasons, and its builder (per season, or all at once).
PER_SEASON: dict[str, tuple[str, Builder]] = {
    "play": ("pbp", build_play),
    "player_play": ("participation", build_player_play),
    "player_game": ("weekly_rosters", build_player_game),
}
ALL_SEASONS = {"game", "team_game"}
TABLE_ORDER = ["game", "team_game", "play", "player_play", "player_game"]


def build(
    names: Sequence[str] | None = None,
    seasons: Sequence[int] | None = None,
    root: Path | None = None,
) -> None:
    """Build tables (default: all) for `seasons` (default: every season their source has)."""
    names = list(names or TABLE_ORDER)
    unknown = set(names) - set(TABLE_ORDER)
    if unknown:
        raise ValueError(f"no tables {sorted(unknown)}. Tables: {', '.join(TABLE_ORDER)}")
    schedules = _schedules()
    cal = calendar(schedules)
    for name in names:
        source = "schedules" if name in ALL_SEASONS else PER_SEASON[name][0]
        have = (
            schedules["season"].unique().to_list()
            if source == "schedules"
            else local_seasons(source)
        )
        chosen = sorted(s for s in have if seasons is None or s in seasons)
        started = time.time()
        if name in ALL_SEASONS:
            build_games(name, chosen, cal, root)
        else:
            for season in chosen:
                t = time.time()
                PER_SEASON[name][1](season, cal, root)
                log.info("%s %d built in %.0fs", name, season, time.time() - t)
        log.info("%s: %d seasons built in %.0fs", name, len(chosen), time.time() - started)
