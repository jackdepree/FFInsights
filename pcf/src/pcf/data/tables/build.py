"""Build the tables from the raw nflverse copy (`pcf tables build`), a season at a time.

The builders in `games`, `plays` and `player_game` are pure; this module reads their inputs with
`scan`, standardizes them, and writes the parts.
"""

import time
from collections.abc import Callable, Sequence
from functools import cache
from pathlib import Path

import polars as pl

from pcf.config import get_config
from pcf.core.log import get_logger
from pcf.data.clean import standard
from pcf.data.clean.depth_charts import (
    daily_depth_rows,
    depth_labels,
    drop_off_roster,
    weekly_depth_rows,
)
from pcf.data.sources.nflverse import DATASETS, files, scan
from pcf.data.tables import pace
from pcf.data.tables.charted import PARTICIPATION_COLUMNS, charted_rows
from pcf.data.tables.charted import PBP_COLUMNS as CHARTED_PBP
from pcf.data.tables.frames import on_spine
from pcf.data.tables.games import game_parts, team_game_parts
from pcf.data.tables.player_game import DAILY_CHARTS_FROM, player_game_parts
from pcf.data.tables.player_pace import ON_FIELD_COLUMNS, player_pace_rows, player_season_rows
from pcf.data.tables.plays import play_parts, player_play_parts
from pcf.data.tables.store import read_part, write_parts
from pcf.data.tables.team_season import PARTICIPATION_COLUMNS as SEASON_PARTICIPATION
from pcf.data.tables.team_season import team_season_parts
from pcf.data.tables.tendencies import PBP_COLUMNS, tendency_rows
from pcf.data.timeline import Calendar, calendar, known_at, team_kickoffs

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
    """A season's depth labels: weekly charts through 2024, daily snapshots from 2025 without the
    players off the 53-man roster (grain-tables#F15)."""
    charts = _season("depth_charts", season)
    if charts is None:
        return None
    if season >= DAILY_CHARTS_FROM:
        kickoffs = team_kickoffs(cal.games.filter(pl.col("season") == season))
        rows = daily_depth_rows(charts, kickoffs)
        rosters = _rosters(season)
        return depth_labels(rows if rosters is None else drop_off_roster(rows, rosters))
    return depth_labels(weekly_depth_rows(charts))


def _rosters(season: int) -> pl.DataFrame | None:
    rosters = _season("weekly_rosters", season)
    return None if rosters is None else standard.weekly_rosters(rosters)


def _players() -> pl.DataFrame:
    return scan("players").select("pfr_id", "gsis_id").collect()


def _ecr() -> tuple[pl.DataFrame | None, pl.DataFrame | None]:
    """The ECR archive and the id map, or (None, None) if either isn't in the raw copy."""
    if not files("ecr_archive") or not files("player_ids"):
        return None, None
    return scan("ecr_archive").collect(), scan("player_ids").collect()


def build_games(name: str, seasons: Sequence[int], cal: Calendar, root: Path | None) -> None:
    schedules = _schedules().filter(pl.col("season").is_in(list(seasons)))
    if name == "game":
        parts = game_parts(schedules, cal)
    else:
        stats = scan("team_stats", [s for s in seasons if s in local_seasons("team_stats")])
        # A season of play-by-play at a time, and only the columns the tendencies need
        tendencies = [
            tendency_rows(scan("pbp", [s]).select(PBP_COLUMNS).collect())
            for s in seasons
            if s in local_seasons("pbp")
        ]
        # Defenses' charted choices: seasons with participation
        charted = [
            charted_rows(
                scan("pbp", [s]).select(CHARTED_PBP).collect(),
                scan("participation", [s]).select(PARTICIPATION_COLUMNS).collect(),
            )
            for s in seasons
            if s in local_seasons("pbp") and s in local_seasons("participation")
        ]
        parts = team_game_parts(
            schedules,
            cal,
            stats.collect(),
            pl.concat(tendencies) if tendencies else None,
            pl.concat(charted) if charted else None,
        )
        paced = [pace_snaps(s) for s in seasons]
        paced = [pace.pace_rows(s) for s in paced if s is not None]
        if paced:
            rows = known_at("pbp", pl.concat(paced), cal)  # known when play-by-play is
            spine = parts["schedule"]
            parts["pace"] = on_spine(rows, spine, ["game_id", "team"], "team_game.pace")
    write_parts(parts, name, seasons, root)


@cache
def _snaps(season: int) -> pl.DataFrame:
    """A season's snaps for the pace measures (`pace.snap_rows`), kept for the process."""
    return pace.snap_rows(scan("pbp", [season]).select(pace.PBP_COLUMNS).collect())


def pace_snaps(season: int) -> pl.DataFrame | None:
    """A season's snaps with PCF's expected pass chance and expected gap, from models fit only
    on earlier seasons (cached in the interim zone), or None without play-by-play or enough
    earlier seasons."""
    have = local_seasons("pbp")
    if season not in have:
        return None
    cache_dir = get_config().zone("interim") / "pace" / "expected"
    models = pace.expected_for(season, have, _snaps, cache_dir)
    if models is None:
        return None
    t = time.time()
    out = pace.apply_expected(_snaps(season), models)
    log.info("pace %d: expected values on %d snaps in %.0fs", season, out.height, time.time() - t)
    return out


def build_play(season: int, cal: Calendar, root: Path | None) -> None:
    parts = play_parts(
        _season("pbp", season),
        cal,
        participation=_season("participation", season),
        ftn=_season("ftn_charting", season),
    )
    paced = pace_snaps(season)
    if paced is not None:
        rows = pace.play_rows(paced).with_columns(pl.col("play_id").cast(pl.Int64))
        parts["pace"] = known_at("pbp", rows, cal)  # every snap is a play on the spine
    write_parts(parts, "play", [season], root)


def build_team_season(season: int, cal: Calendar, root: Path | None) -> None:
    parts = team_season_parts(
        scan("pbp", [season]).select(CHARTED_PBP).collect(),
        scan("participation", [season]).select(SEASON_PARTICIPATION).collect(),
        cal,
    )
    write_parts(parts, "team_season", [season], root)


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
    ecr, ids = _ecr()
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
        ecr=ecr,
        ids=ids,
    )
    on_field = on_field_pace(season, root)
    if on_field is not None:
        parts["on_field_pace"] = on_spine(
            on_field, parts["roster"], ["gsis_id", "game_id"], "player_game.on_field_pace"
        )
    write_parts(parts, "player_game", [season], root)


def on_field_pace(season: int, root: Path | None) -> pl.DataFrame | None:
    """Each player's team rates on and off the field (`player_pace`), from the saved `play` and
    `player_play` parts, so those tables are built first (TABLE_ORDER). None without them."""
    try:
        on = read_part("player_play", "on_field", [season], root).select(ON_FIELD_COLUMNS)
        paced = read_part("play", "pace", [season], root).select(
            "game_id", "play_id", "pcf_pass_oe", "pace_oe"
        )
        pbp = read_part("play", "pbp", [season], root).select("game_id", "play_id", "posteam")
        pers = read_part("play", "participation", [season], root).select(
            "game_id", "play_id", "offense_personnel"
        )
        plays = (
            paced.join(pbp, on=["game_id", "play_id"])
            .join(pers, on=["game_id", "play_id"], how="left")
            .collect()
        )
        on = on.collect()
    except (FileNotFoundError, pl.exceptions.ComputeError):
        return None
    if plays.is_empty() or on.is_empty():
        return None
    plays = standard.standard_teams(plays, "posteam")
    return player_pace_rows(plays, on)


def build_player_season(season: int, cal: Calendar, root: Path | None) -> None:
    """`player_season.on_field_pace` from the saved `player_game` parts (built first)."""
    try:
        games = read_part("player_game", "on_field_pace", [season], root).collect()
        roster = read_part("player_game", "roster", [season], root).select(
            "gsis_id", "game_id", "team", "position"
        ).collect()
    except FileNotFoundError:
        return
    if games.is_empty():
        return
    rows = player_season_rows(games, roster, cal.games.select("game_id", "kickoff"))
    write_parts({"on_field_pace": rows}, "player_season", [season], root)


Builder = Callable[[int, Calendar, Path | None], None]
# Each table: the dataset that decides its seasons, and its builder (per season, or all at once).
PER_SEASON: dict[str, tuple[str, Builder]] = {
    "team_season": ("participation", build_team_season),
    "play": ("pbp", build_play),
    "player_play": ("participation", build_player_play),
    "player_game": ("weekly_rosters", build_player_game),
    "player_season": ("participation", build_player_season),
}
ALL_SEASONS = {"game", "team_game"}
TABLE_ORDER = [
    "game", "team_game", "team_season", "play", "player_play", "player_game", "player_season",
]  # fmt: skip


def build(
    names: Sequence[str] | None = None,
    seasons: Sequence[int] | None = None,
    root: Path | None = None,
) -> None:
    """Build tables (default: all) for `seasons` (default: every season their source has).

    Each table's tags (`pcf.data.tags`) are rebuilt right after it; `play` also builds `drive`.
    """
    from pcf.data.tags import build_tags

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
        build_tags(name, chosen, root)
        log.info("%s: %d seasons built in %.0fs", name, len(chosen), time.time() - started)
