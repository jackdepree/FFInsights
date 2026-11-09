"""`team_game.tendencies`: per-game scheme tendencies from play-by-play, in neutral situations."""

from datetime import timedelta

import polars as pl
import pytest

from pcf.data.schemas import check_parts
from pcf.data.tables.games import team_game_parts
from pcf.data.tables.tendencies import DEFENSE, OFFENSE, PBP_COLUMNS, tendency_rows

from .toy import KICK, cal, schedules

GAME = "2025_01_BUF_KC"


def _play(play_id, posteam, **over):
    """A neutral first-down run by default; `over` changes it."""
    row = {
        "game_id": GAME, "play_id": play_id, "season": 2025, "posteam": posteam,
        "defteam": "BUF" if posteam == "KC" else "KC", "down": 1, "qtr": 1, "wp": 0.5,
        "half_seconds_remaining": 1500, "game_seconds_remaining": 3300 - 30 * play_id,
        "pass": 0, "rush": 1, "xpass": 0.4, "shotgun": 0, "no_huddle": 0, "qb_dropback": 0,
        "qb_scramble": 0, "qb_kneel": 0, "qb_spike": 0, "air_yards": None, "pass_attempt": 0,
        "sack": 0, "qb_hit": 0, "penalty": 0, "out_of_bounds": 0, "fixed_drive": 1,
    }  # fmt: skip
    return row | over


def _throw(play_id, posteam, air, **over):
    return _play(play_id, posteam, rush=0, qb_dropback=1, pass_attempt=1, air_yards=air,
                 shotgun=1, **{"pass": 1} | over)  # fmt: skip


def _pbp(rows):
    return pl.DataFrame(rows, schema_overrides={"air_yards": pl.Float64, "season": pl.Int32})


def test_rates_count_only_neutral_plays():
    pbp = _pbp(
        [
            _play(1, "KC"),
            _throw(2, "KC", 25.0),
            _throw(3, "KC", 5.0, qb_hit=1),
            _throw(4, "KC", 40.0, wp=0.95),  # a blowout: not neutral
            _throw(5, "KC", 40.0, down=4),  # fourth down: not neutral
            _throw(6, "KC", 40.0, half_seconds_remaining=60),  # two-minute drill: not neutral
            _play(7, "KC", qb_kneel=1),
        ]
    )
    out = tendency_rows(pbp)
    assert out.columns == ["game_id", "team", "season", *OFFENSE, *DEFENSE]
    kc = out.row(by_predicate=pl.col("team") == "KC", named=True)
    assert kc["neutral_plays"] == 3
    assert kc["neutral_pass_oe"] == pytest.approx(2 / 3 - 0.4)
    assert kc["shotgun_rate"] == pytest.approx(2 / 3)
    assert kc["air_attempts"] == 2
    assert kc["air_yards_per_att"] == pytest.approx(15.0)
    assert kc["deep_rate"] == pytest.approx(0.5)
    assert kc["def_neutral_plays"] is None  # KC's defense faced no neutral play
    buf = out.row(by_predicate=pl.col("team") == "BUF", named=True)
    assert buf["neutral_plays"] is None
    assert buf["def_neutral_plays"] == 3
    assert buf["def_dropbacks"] == 2
    assert buf["def_pressure_rate"] == pytest.approx(0.5)
    assert buf["def_pass_oe"] == pytest.approx(2 / 3 - 0.4)


def test_tempo_is_the_clock_run_after_an_in_bounds_run_on_the_same_drive():
    pbp = _pbp(
        [
            _play(1, "KC", game_seconds_remaining=3000),
            _play(2, "KC", game_seconds_remaining=2965),  # 35 seconds after an in-bounds run
            _play(3, "KC", game_seconds_remaining=2940, out_of_bounds=1),  # 25 seconds
            _play(4, "KC", game_seconds_remaining=2930),  # after out of bounds: the clock stopped
            _play(5, "KC", game_seconds_remaining=2900, fixed_drive=2),  # a new drive
            _throw(6, "KC", 5.0, game_seconds_remaining=2860, fixed_drive=2),  # 40 seconds
            _play(7, "KC", game_seconds_remaining=2850, fixed_drive=2),  # after a pass
        ]
    )
    kc = tendency_rows(pbp).row(by_predicate=pl.col("team") == "KC", named=True)
    assert kc["tempo_plays"] == 3
    assert kc["tempo_seconds"] == pytest.approx((35 + 25 + 40) / 3)


def test_the_part_is_known_the_day_after_and_passes_the_table_contract():
    rows = tendency_rows(_pbp([_play(1, "KC"), _throw(2, "BUF", 8.0)]))
    parts = team_game_parts(schedules(), cal(), tendencies=rows)
    check_parts(parts, "team_game")
    ten = parts["tendencies"]
    assert ten.height == 2
    assert ten["known_at"].to_list() == [KICK + timedelta(days=1)] * 2


def test_every_needed_column_is_read():
    with pytest.raises(pl.exceptions.ColumnNotFoundError):
        tendency_rows(_pbp([_play(1, "KC")]).drop("xpass"))
    assert "xpass" in PBP_COLUMNS
