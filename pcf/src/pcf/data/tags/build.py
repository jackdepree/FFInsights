"""Build the tags in the catalog from the built tables, and save them as table parts.

The frame builders are pure: each prepares one level's rows (plays, drives, team-games,
player-games) with the helper columns the catalog's rules use, then applies the rules. A tag
part's `known_at` is the latest of the parts it reads, so a tag is never known before its inputs.
"""

from collections import Counter
from collections.abc import Sequence
from pathlib import Path

import polars as pl

from pcf.core.log import get_logger
from pcf.data.tables.store import load, write_parts
from pcf.data.tags.catalog import Tag, tags_for

log = get_logger(__name__)

c = pl.col
SCRIMMAGE = ["run", "pass"]
PLAY_KEYS = ["game_id", "play_id"]
DRIVE_KEYS = ["game_id", "fixed_drive"]
TEAM_KEYS = ["game_id", "team"]
PLAYER_KEYS = ["gsis_id", "game_id"]
# Play-by-play columns that describe the result of a play, not the moment before it. The
# timing tests scramble them for a play and every later one: no before-snap tag may change.
OUTCOME_COLUMNS = [
    "yards_gained",
    "epa",
    "wpa",
    "success",
    "first_down",
    "touchdown",
    "interception",
    "fumble_lost",
    "sack",
    "cp",
    "cpoe",
    "air_yards",
    "yards_after_catch",
    "complete_pass",
    "qb_scramble",
    "fixed_drive_result",
    "play_type",
]


def apply_tags(frame: pl.DataFrame, tags: Sequence[Tag]) -> pl.DataFrame:
    """Add each tag's column, in catalog order, so a rule can use an earlier tag."""
    for tag in tags:
        value = tag.rule if tag.applies is None else pl.when(tag.applies).then(tag.rule)
        if tag.first_season > 1999:
            value = pl.when(c("season") >= tag.first_season).then(value)
        frame = frame.with_columns(value.alias(tag.column))
    return frame


def _part(frame: pl.DataFrame, keys: list[str], tags: Sequence[Tag]) -> pl.DataFrame:
    return frame.select(*keys, "season", "known_at", *(t.column for t in tags))


def play_frame(pbp: pl.DataFrame) -> pl.DataFrame:
    """Play-by-play rows → the columns play tags read: `earlier_snaps` counts the offense's run
    and pass plays before this one in the game."""
    snap = c("play_type").is_in(SCRIMMAGE).fill_null(False).cast(pl.Int32)
    return pbp.sort("game_id", "play_id").with_columns(
        earlier_snaps=(snap.cum_sum() - snap).over("game_id", "posteam")
    )


def play_tags(pbp: pl.DataFrame) -> pl.DataFrame:
    """The `play.tags` part, from the `pbp` part. Known when play-by-play is."""
    tags = tags_for("play")
    return _part(apply_tags(play_frame(pbp), tags), PLAY_KEYS, tags)


def drive_frame(pbp: pl.DataFrame) -> pl.DataFrame:
    """Play-by-play rows → one row per drive (`fixed_drive`), with the previous drive's result."""
    snap = c("play_type").is_in(SCRIMMAGE).fill_null(False)
    drives = (
        pbp.filter(c("fixed_drive").is_not_null() & c("posteam").is_not_null())
        .sort("game_id", "play_id")
        .group_by("game_id", "fixed_drive", maintain_order=True)
        .agg(
            season=c("season").first(),
            known_at=c("known_at").max(),
            posteam=c("posteam").first(),
            defteam=c("defteam").first(),
            result=c("fixed_drive_result").first(),
            plays=snap.sum().cast(pl.Int32),
            first_downs=c("first_down").filter(snap).sum().cast(pl.Int32),
            start_yardline=c("yardline_100").filter(snap).first(),
            start_qtr=c("qtr").first(),
            end_qtr=c("qtr").last(),
            end_half_seconds=c("half_seconds_remaining").last(),
            seconds=c("game_seconds_remaining").first() - c("game_seconds_remaining").last(),
            goal_inside_5=(
                (c("goal_to_go") == 1) & (c("down") == 1) & (c("yardline_100") <= 5)
            ).any(),
        )
        .with_columns(c("fixed_drive").cast(pl.Int32), c("season").cast(pl.Int32))
    )
    return drives.sort("game_id", "fixed_drive").with_columns(
        prev_result=c("result").shift(1).over("game_id"),
        prev_team=c("posteam").shift(1).over("game_id"),
    )


DRIVE_SUMMARY = [
    "posteam",
    "defteam",
    "result",
    "plays",
    "first_downs",
    "start_yardline",
    "start_qtr",
    "end_qtr",
    "seconds",
]


def drive_parts(pbp: pl.DataFrame) -> dict[str, pl.DataFrame]:
    """The `drive` table: its `summary` spine and its `tags`, both known when play-by-play is."""
    frame = apply_tags(drive_frame(pbp), tags_for("drive"))
    return {
        "summary": frame.select(*DRIVE_KEYS, "season", "known_at", *DRIVE_SUMMARY),
        "tags": _part(frame, DRIVE_KEYS, tags_for("drive")),
    }


def _usual_qb(team_games: pl.DataFrame) -> pl.Series:
    """Each game's 'usual starter': the team's most common starting QB in its earlier games that
    season (ties: the most recent). Empty for a team's first game. Uses earlier games only
    (tag-tables#F8)."""
    out = []
    order = team_games.with_row_index("i").sort("team", "season", "kickoff")
    for _, group in order.group_by("team", "season", maintain_order=True):
        counts: Counter[str] = Counter()
        last_seen: dict[str, int] = {}
        for n, (i, qb) in enumerate(zip(group["i"], group["qb_id"], strict=True)):
            usual = max(counts, key=lambda q: (counts[q], last_seen[q])) if counts else None
            out.append((i, usual))
            if qb is not None:
                counts[qb] += 1
                last_seen[qb] = n
    usual = dict(out)
    return pl.Series("usual_qb", [usual[i] for i in range(team_games.height)], pl.String)


def team_game_frame(team_games: pl.DataFrame, games: pl.DataFrame) -> pl.DataFrame:
    """Team-game rows (schedule and pregame parts) and game rows (roof, temp, wind) → the columns
    team-game tags read."""
    weather = games.select("game_id", "roof", "temp", "wind", "result_known_at")
    frame = team_games.join(weather, on="game_id", how="left", maintain_order="left")
    frame = frame.with_columns(_usual_qb(frame))
    reg = (
        frame.filter(c("game_type") == "REG")
        .sort("team", "season", "kickoff")
        .with_columns(next_reg_div=c("div_game").shift(-1).over("team", "season"))
        .select(*TEAM_KEYS, "next_reg_div")
    )
    return frame.join(reg, on=TEAM_KEYS, how="left", maintain_order="left").with_columns(
        et_hour=c("kickoff").dt.convert_time_zone("America/New_York").dt.hour()
    )


def team_game_tags(team_games: pl.DataFrame, games: pl.DataFrame) -> dict[str, pl.DataFrame]:
    """`team_game.tags` (known at the later of the schedule and the pregame part) and
    `team_game.tags_result` (known with the game's result: weather)."""
    frame = apply_tags(team_game_frame(team_games, games), tags_for("team_game"))
    before = frame.with_columns(known_at=pl.max_horizontal("known_at", "pregame_known_at"))
    after = frame.filter(c("result_known_at").is_not_null()).with_columns(
        known_at=c("result_known_at")
    )
    return {
        "tags": _part(before, TEAM_KEYS, tags_for("team_game", "tags")),
        "tags_result": _part(after, TEAM_KEYS, tags_for("team_game", "tags_result")),
    }


def player_game_frame(
    player_games: pl.DataFrame, history: pl.DataFrame, team_games: pl.DataFrame
) -> pl.DataFrame:
    """Player-game rows (roster, game status, injury and stats parts) → the columns player-game
    tags read.

    `history` is (gsis_id, season, week, team) for every earlier player-game, from the spine.
    `team_games` gives each team's game order in the season (from the schedule).
    """
    when = c("season") * 100 + c("week")
    first_on = history.group_by("gsis_id", "team").agg(first_on=when.min())
    season_last = (
        history.sort("gsis_id", "season", "week")
        .group_by("gsis_id", "season", maintain_order=True)
        .agg(season_team=c("team").last())
        .with_columns(last_team=c("season_team").shift(1).over("gsis_id"))
        .select("gsis_id", "season", "last_team")
    )
    game_no = (
        team_games.sort("team", "season", "kickoff")
        .with_columns(game_no=pl.int_range(1, pl.len() + 1).over("team", "season"))
        .select(*TEAM_KEYS, "game_no")
    )
    frame = (
        player_games.join(season_last, on=["gsis_id", "season"], how="left", maintain_order="left")
        .join(
            first_on.rename({"team": "opponent"}),
            on=["gsis_id", "opponent"],
            how="left",
            maintain_order="left",
        )
        .with_columns(
            faced_former=(c("first_on") < when).fill_null(False) & (c("opponent") != c("team"))
        )
        .join(game_no, on=TEAM_KEYS, how="left", maintain_order="left")
        .sort("gsis_id", "season", "team", "game_no")
        .with_columns(
            prev_game_no=c("game_no").shift(1).over("gsis_id", "season", "team"),
            prev_report=c("report_status").shift(1).over("gsis_id", "season", "team"),
        )
    )
    return frame


def player_game_tags(
    player_games: pl.DataFrame, history: pl.DataFrame, team_games: pl.DataFrame
) -> dict[str, pl.DataFrame]:
    """`player_game.tags` (known at the latest of the roster, game status and injury parts) and
    `player_game.tags_result` (known with the stats)."""
    frame = apply_tags(
        player_game_frame(player_games, history, team_games), tags_for("player_game")
    )
    before = frame.with_columns(
        known_at=pl.max_horizontal(
            "known_at", *(k for k in ("game_status_known_at", "injury_known_at") if k in frame)
        )
    )
    after = frame.filter(c("stats_known_at").is_not_null()).with_columns(
        known_at=c("stats_known_at")
    )
    return {
        "tags": _part(before, PLAYER_KEYS, tags_for("player_game", "tags")),
        "tags_result": _part(after, PLAYER_KEYS, tags_for("player_game", "tags_result")),
    }


def build_tags(name: str, seasons: Sequence[int], root: Path | None = None) -> None:
    """Build the tag parts of one table (and the `drive` table, from `play`) for `seasons`."""
    if name == "play":
        for season in seasons:
            pbp = load("play", seasons=[season], parts=[], root=root)
            write_parts({"tags": play_tags(pbp)}, "play", [season], root)
            write_parts(drive_parts(pbp), "drive", [season], root)
    elif name == "team_game":
        team_games = load("team_game", seasons=seasons, parts=["pregame"], root=root)
        games = load("game", seasons=seasons, parts=["result"], root=root)
        write_parts(team_game_tags(team_games, games), "team_game", seasons, root)
    elif name == "player_game":
        history = load("player_game", parts=[], root=root).select(
            "gsis_id", "season", "week", "team"
        )
        for season in seasons:
            pg = load(
                "player_game",
                seasons=[season],
                parts=["game_status", "injury", "stats"],
                root=root,
            )
            team_games = load("team_game", seasons=[season], parts=[], root=root)
            parts = player_game_tags(pg, history.filter(c("season") <= season), team_games)
            write_parts(parts, "player_game", [season], root)
    else:
        return
    log.info("%s tags built for %d seasons", name, len(seasons))
