"""The `player_game` table (CEO decision 1A, grain-tables brief).

The spine is everyone on a team's 53-man roster for a game: dressed (`ACT`) and, from 2019, the
game-day inactives (`INA`), known at the start of the week. Players who played without a roster
row are added, known the day after the game (`on_roster` is false). Before 2019 inactives aren't
marked: they're the rostered players with no snap. Before 2016 a player's roster status is the
same all season (their last one: a player who went on injured reserve in December is `RES` from
week 1), so every roster row of the team-week is on the spine and status is ignored
(grain-tables#F11).

Parts, each with its own known-at rule (`timeline`):
- roster (the spine): who is on the team, and their position, age and draft facts;
- game_status: `ACT` or `INA` (2019→), 1 hour before kickoff (grain-tables#F4);
- injury: the week's injury report;
- depth: the depth-chart label going into the game (week start; daily charts, kickoff);
- stats, snaps, ff_opportunity: the day after the game;
- ngs: Next Gen Stats, the day after the week ends (2016→);
- pfr: PFR advanced stats, about 9 days after (2018→).
NGS, PFR and ff_opportunity columns are prefixed with their source, since their names clash with
player stats (`ngs_rec_targets`, `pfr_rush_carries`, `ffo_receptions`).
"""

from collections.abc import Mapping

import polars as pl

from pcf.core.log import get_logger
from pcf.data.clean.standard import ON_53
from pcf.data.tables.frames import merge, on_spine, prefixed, team_games
from pcf.data.timeline import Calendar, known_at

log = get_logger(__name__)

KEYS = ["gsis_id", "game_id"]
PART_KEEP = [*KEYS, "season", "known_at"]
ROSTER_COLUMNS = [
    "position",
    "depth_chart_position",
    "jersey_number",
    "full_name",
    "birth_date",
    "height",
    "weight",
    "college",
    "years_exp",
    "entry_year",
    "rookie_year",
    "draft_club",
    "draft_number",
]
INJURY_COLUMNS = [
    "report_primary_injury",
    "report_secondary_injury",
    "report_status",
    "practice_primary_injury",
    "practice_secondary_injury",
    "practice_status",
    "date_modified",
]
SNAP_COLUMNS = [
    "offense_snaps",
    "offense_pct",
    "defense_snaps",
    "defense_pct",
    "st_snaps",
    "st_pct",
]
# Player stats columns the roster already has, or that name the game.
STATS_DROP = [
    "player_name",
    "player_display_name",
    "position",
    "position_group",
    "headshot_url",
    "week",
    "season_type",
    "team",
    "opponent_team",
]
FFO_DROP = ["week", "team", "full_name", "position"]
NGS_PREFIX = {"passing": "ngs_pass_", "receiving": "ngs_rec_", "rushing": "ngs_rush_"}
NGS_DROP = [
    "season_type",
    "player_display_name",
    "player_position",
    "team_abbr",
    "player_first_name",
    "player_last_name",
    "player_jersey_number",
    "player_short_name",
]
PFR_PREFIX = {"pass": "pfr_pass_", "rush": "pfr_rush_", "rec": "pfr_rec_", "def": "pfr_def_"}
PFR_DROP = ["pfr_game_id", "week", "game_type", "team", "opponent", "pfr_player_name"]
# Before this season a roster status is the player's last of the season, not that week's.
WEEKLY_STATUS_FROM = 2016
# Depth charts are daily snapshots from 2025; the label is the chart at kickoff (timeline#F5).
DAILY_CHARTS_FROM = 2025


def _int_season_week(df: pl.DataFrame) -> pl.DataFrame:
    cols = [pl.col(c).cast(pl.Int32) for c in ("season", "week") if c in df.columns]
    return df.with_columns(cols)


def _spine(cal: Calendar, rosters: pl.DataFrame, played: pl.DataFrame) -> pl.DataFrame:
    """Roster rows for each team's game, plus anyone who played without one."""
    games = team_games(cal.games)
    on_53 = pl.col("status").is_in(ON_53) | (pl.col("season") < WEEKLY_STATUS_FROM)
    on_roster = (
        _int_season_week(rosters)
        .filter(on_53 & pl.col("gsis_id").is_not_null())
        .join(games, on=["season", "week", "team"])
        .select(*KEYS, "season", "week", "team", "opponent", *ROSTER_COLUMNS, "known_at")
        .with_columns(on_roster=pl.lit(True))
    )
    extra = played.join(on_roster, on=KEYS, how="anti").join(
        games.select("game_id", "team", "week", "opponent"), on=["game_id", "team"]
    )
    if extra.height:
        log.info("player_game: %d players played without a roster row", extra.height)
    return pl.concat(
        [on_roster, extra.with_columns(on_roster=pl.lit(False))], how="diagonal_relaxed"
    ).select(on_roster.columns)


def _played(snaps: pl.DataFrame | None, stats: pl.DataFrame | None) -> pl.DataFrame:
    """Player-games with a snap or a stat line: gsis_id, game_id, season, team, position,
    known_at (the day after the game)."""
    frames = []
    if snaps is not None:
        any_snap = pl.sum_horizontal("offense_snaps", "defense_snaps", "st_snaps") > 0
        frames.append(
            snaps.filter(any_snap).select(*KEYS, "season", "team", "position", "known_at")
        )
    if stats is not None:
        frames.append(stats.select(*KEYS, "season", "team", "position", "known_at"))
    if not frames:
        return pl.DataFrame(
            schema={**{k: pl.String for k in KEYS}, "team": pl.String, "position": pl.String}
        )
    return pl.concat(frames, how="vertical_relaxed").unique(KEYS, keep="first")


def _by_team_week(df: pl.DataFrame, cal: Calendar) -> pl.DataFrame:
    """Rows keyed by season, week and team → the same rows with that team's `game_id`."""
    games = team_games(cal.games).select("season", "week", "team", "game_id", "kickoff")
    return _int_season_week(df).join(games, on=["season", "week", "team"])


def _ngs(ngs: Mapping[str, pl.DataFrame], spine: pl.DataFrame, cal: Calendar) -> pl.DataFrame:
    """NGS weeks (season totals left out) → player-games, by the player's game that week. NGS
    numbers the Super Bowl one past the schedule (timeline#F11)."""
    last = cal.weeks.group_by("season").agg(last=pl.col("week").max())
    games = spine.select(*KEYS, "season", "week")
    frames = []
    for kind, df in ngs.items():
        weekly = df.filter(pl.col("week") > 0)
        rows = (
            _int_season_week(known_at(f"ngs_{kind}", weekly, cal))
            .join(last, on="season", how="left")
            .with_columns(week=pl.min_horizontal("week", "last"))
            .rename({"player_gsis_id": "gsis_id"})
            .join(games, on=["gsis_id", "season", "week"])
            .drop("last", "week", *NGS_DROP)
        )
        frames.append(prefixed(rows, NGS_PREFIX[kind], PART_KEEP))
    return merge(frames, KEYS)


def _pfr(pfr: Mapping[str, pl.DataFrame], players: pl.DataFrame, cal: Calendar) -> pl.DataFrame:
    """PFR weekly files → player-games, with gsis_id from the players file (as snap counts)."""
    ids = (
        players.select(pfr_player_id="pfr_id", gsis_id="gsis_id")
        .drop_nulls()
        .unique("pfr_player_id", keep="first", maintain_order=True)
    )
    frames = []
    for kind, df in pfr.items():
        rows = (
            _int_season_week(known_at(f"pfr_week_{kind}", df, cal))
            .join(ids, on="pfr_player_id")
            .drop("pfr_player_id", *PFR_DROP)
        )
        frames.append(prefixed(rows, PFR_PREFIX[kind], PART_KEEP))
    return merge(frames, KEYS)


def player_game_parts(
    cal: Calendar,
    rosters: pl.DataFrame,
    *,
    snaps: pl.DataFrame | None = None,
    stats: pl.DataFrame | None = None,
    ff_opportunity: pl.DataFrame | None = None,
    injuries: pl.DataFrame | None = None,
    labels: pl.DataFrame | None = None,
    ngs: Mapping[str, pl.DataFrame] | None = None,
    pfr: Mapping[str, pl.DataFrame] | None = None,
    players: pl.DataFrame | None = None,
) -> dict[str, pl.DataFrame]:
    """One season's standardized sources (`pcf.data.clean.standard`; NGS and PFR raw, keyed by
    kind; `labels` from `depth_labels`; `players` for PFR's ids) → the `player_game` parts."""
    roster_rows = known_at("weekly_rosters", rosters, cal)
    if snaps is not None:
        snaps = _int_season_week(known_at("snap_counts", snaps.drop_nulls("gsis_id"), cal))
    if stats is not None:
        stats = _int_season_week(known_at("player_stats", stats, cal))
    spine = _spine(cal, roster_rows, _played(snaps, stats))
    parts = {"roster": spine}

    def attach(name: str, df: pl.DataFrame, by_team: bool = False) -> None:
        """Keep the part's rows on the spine. Parts listed by team must match the player's
        team too: a player traded between two opponents can be on both teams' lists."""
        keys = [*KEYS, "team"] if by_team else KEYS
        parts[name] = on_spine(df, spine, keys, f"player_game.{name}").drop(
            "team" if by_team else []
        )

    if (roster_rows["status"] == "INA").any():  # marked from 2019
        status = _by_team_week(roster_rows, cal).filter(pl.col("status").is_in(ON_53))
        status = status.select(*KEYS, "team", "season", "status", known_at="status_known_at")
        attach("game_status", status, by_team=True)
    if injuries is not None:
        inj = _by_team_week(known_at("injuries", injuries.drop_nulls("gsis_id"), cal), cal)
        attach("injury", inj.select(*KEYS, "team", "season", *INJURY_COLUMNS, "known_at"), True)
    if labels is not None:
        week_start = cal.weeks.select("season", "week", start="start")
        depth = _by_team_week(labels, cal).join(week_start, on=["season", "week"], how="left")
        daily = pl.col("season") >= DAILY_CHARTS_FROM
        attach(
            "depth",
            depth.select(
                *KEYS,
                "team",
                "season",
                "depth",
                "depth_mean",
                "weeks_listed",
                "position_label",
                depth_position="position",
                known_at=pl.when(daily).then("kickoff").otherwise("start"),
            ),
            by_team=True,
        )
    if stats is not None:
        attach("stats", stats.drop(STATS_DROP))
    if snaps is not None:
        attach("snaps", snaps.select(*KEYS, "season", *SNAP_COLUMNS, "known_at"))
    if ff_opportunity is not None:
        ffo = _int_season_week(known_at("ff_opportunity", ff_opportunity, cal)).drop(FFO_DROP)
        attach("ff_opportunity", prefixed(ffo, "ffo_", PART_KEEP))
    if ngs:
        attach("ngs", _ngs(ngs, spine, cal))
    if pfr:
        if players is None:
            raise ValueError("PFR needs the players file to map its ids")
        attach("pfr", _pfr(pfr, players, cal))
    return parts
