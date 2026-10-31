from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from pcf.data.schemas import check_part
from pcf.data.tables.store import files, load, write_parts

KICK = datetime(2025, 9, 7, 17, tzinfo=UTC)


def _part(rows, **columns):
    """team_game rows (game_id, team, season, known_at) plus columns."""
    df = pl.DataFrame(rows, schema=["game_id", "team", "season", "known_at"], orient="row")
    return df.with_columns(pl.col("season").cast(pl.Int32), **columns)


def _toy(tmp_path):
    spine = _part(
        [
            ("2025_01_A", "KC", 2025, KICK - timedelta(days=5)),
            ("2025_01_A", "BUF", 2025, KICK - timedelta(days=5)),
            ("2024_01_A", "KC", 2024, KICK - timedelta(days=370)),
        ],
        opponent=pl.Series(["BUF", "KC", "BAL"]),
    )
    stats = _part(
        [
            ("2025_01_A", "KC", 2025, KICK + timedelta(days=1)),
            ("2024_01_A", "KC", 2024, KICK - timedelta(days=364)),
        ],
        passing_yards=pl.Series([250, 300]),
    )
    write_parts({"schedule": spine, "stats": stats}, "team_game", [2024, 2025], tmp_path)
    return spine, stats


def test_load_shows_each_part_only_once_it_is_known(tmp_path):
    _toy(tmp_path)
    before = load("team_game", at=KICK, parts=["stats"], root=tmp_path).sort("season", "team")
    assert before.height == 3  # every spine row known by then
    assert before["passing_yards"].to_list() == [300, None, None]  # 2025 stats not known yet
    after = load("team_game", at=KICK + timedelta(days=2), root=tmp_path, parts=["stats"])
    assert after.filter(pl.col("game_id") == "2025_01_A")["passing_yards"].sort().to_list() == [
        None,
        250,
    ]
    assert "stats_known_at" in after.columns
    early = load("team_game", at=KICK - timedelta(days=30), parts=[], root=tmp_path)
    assert early["season"].to_list() == [2024]  # 2025 spine rows not known yet


def test_deleting_rows_known_later_changes_nothing_known_earlier(tmp_path):
    spine, stats = _toy(tmp_path)
    at = KICK
    full = load("team_game", at=at, parts=["stats"], root=tmp_path)
    cut = tmp_path / "cut"
    write_parts(
        {"schedule": spine, "stats": stats.filter(pl.col("known_at") <= at)},
        "team_game",
        [2024, 2025],
        cut,
    )
    assert load("team_game", at=at, parts=["stats"], root=cut).equals(full)


def test_load_by_season_keeps_columns_of_parts_without_rows(tmp_path):
    spine, _ = _toy(tmp_path)
    old = spine.head(1).with_columns(game_id=pl.lit("2023_01_A"), season=pl.lit(2023, pl.Int32))
    write_parts({"schedule": old}, "team_game", [2023], tmp_path)
    out = load("team_game", seasons=[2023], parts=["stats"], root=tmp_path)
    assert out.height == 1 and out["passing_yards"].to_list() == [None]
    with pytest.raises(FileNotFoundError, match="pregame"):
        load("team_game", root=tmp_path)  # pregame was never built


def test_an_emptied_season_removes_its_file(tmp_path):
    spine, stats = _toy(tmp_path)
    write_parts({"schedule": spine, "stats": stats.head(0)}, "team_game", [2024], tmp_path)
    assert [p.parent.name for p in files("team_game", "stats", root=tmp_path)] == ["season=2025"]


def test_parts_are_checked_before_writing(tmp_path):
    spine, stats = _toy(tmp_path)
    with pytest.raises(ValueError, match="share their keys"):
        check_part(pl.concat([spine, spine]), "team_game", "schedule")
    with pytest.raises(ValueError, match="aren't on the spine"):
        write_parts({"schedule": spine.head(1), "stats": stats}, "team_game", [2025], tmp_path)
    with pytest.raises(ValueError, match="in both"):
        write_parts(
            {"schedule": spine, "stats": stats.with_columns(opponent=pl.lit("X"))},
            "team_game",
            [2025],
            tmp_path,
        )
    with pytest.raises(ValueError, match="UTC"):
        check_part(
            spine.with_columns(pl.col("known_at").dt.replace_time_zone(None)),
            "team_game",
            "schedule",
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        load("team_game", at=KICK.replace(tzinfo=None), root=tmp_path)
