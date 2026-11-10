"""`team_game.charted`: each defense's coverage and blitz choices from participation, against the
league's usual choice for the look, and what they gained, known after the season."""

import polars as pl
import pytest

from pcf.data.schemas import check_parts, table
from pcf.data.tables.charted import COLUMNS, PARTICIPATION_COLUMNS, PBP_COLUMNS, charted_rows
from pcf.data.tables.games import team_game_parts

from .toy import cal, schedules, utc

GAME = "2025_01_BUF_KC"


def _drop(play_id, defteam="BUF", epa=0.0, **over):
    """A neutral first-and-10 shotgun dropback by default."""
    row = {
        "game_id": GAME, "play_id": play_id, "season": 2025,
        "posteam": "KC" if defteam == "BUF" else "BUF", "defteam": defteam, "down": 1,
        "ydstogo": 10, "qtr": 1, "wp": 0.5, "half_seconds_remaining": 1500, "pass": 1, "rush": 0,
        "shotgun": 1, "qb_dropback": 1, "qb_kneel": 0, "qb_spike": 0, "air_yards": 8.0,
        "pass_attempt": 1, "sack": 0, "epa": epa,
    }  # fmt: skip
    return {k: over.get(k, v) for k, v in row.items()}


def _chart(play_id, man=True, cover="COVER_1", rushers=4, personnel="1 RB, 1 TE, 3 WR"):
    return {
        "nflverse_game_id": GAME, "play_id": play_id, "offense_personnel": personnel,
        "number_of_pass_rushers": rushers,
        "defense_man_zone_type": "MAN_COVERAGE" if man else "ZONE_COVERAGE",
        "defense_coverage_type": cover,
    }  # fmt: skip


def _rows(plays, charts):
    pbp = pl.DataFrame(plays, schema_overrides={"season": pl.Int32})
    return charted_rows(pbp, pl.DataFrame(charts))


def test_rates_use_over_expected_and_gains():
    plays = [
        _drop(1, epa=-0.5),
        _drop(2, epa=0.5),
        _drop(3, epa=0.1),
        _drop(4, "KC", epa=0.3),
        _drop(5, epa=2.0, wp=0.97),  # a blowout: not neutral
    ]
    charts = [
        _chart(1, man=True, cover="COVER_1", rushers=6),
        _chart(2, man=False, cover="COVER_4"),
        _chart(3, man=False, cover="COVER_3"),
        _chart(4, man=True, cover="COVER_2"),
        _chart(5, man=True),
    ]
    out = _rows(plays, charts)
    assert out.columns == ["game_id", "team", "season", *COLUMNS]
    buf = out.row(by_predicate=pl.col("team") == "BUF", named=True)
    assert buf["man_plays"] == 3
    assert buf["man_rate"] == pytest.approx(1 / 3)
    # every play is the same look, so the league's usual choice is the 4-play rate: man 2 of 4
    assert buf["man_oe"] == pytest.approx(1 / 3 - 1 / 2)
    # EPA prevented: zone allowed 0.3 a play, man -0.5
    assert buf["man_gain"] == pytest.approx(0.3 - (-0.5))
    assert buf["man_gain_n"] == pytest.approx(1 * 2 / 3)
    assert buf["two_high_rate"] == pytest.approx(1 / 3)
    assert buf["blitz_rate"] == pytest.approx(1 / 3)
    kc = out.row(by_predicate=pl.col("team") == "KC", named=True)
    assert kc["man_gain"] is None  # only one side was seen


def test_the_usual_choice_depends_on_the_look():
    plays = [_drop(1), _drop(2), _drop(3, "KC"), _drop(4, "KC")]
    heavy = "2 RB, 2 TE, 1 WR"
    charts = [
        _chart(1, man=True, personnel=heavy),
        _chart(2, man=False),
        _chart(3, man=False, personnel=heavy),
        _chart(4, man=False),
    ]
    buf = _rows(plays, charts).row(by_predicate=pl.col("team") == "BUF", named=True)
    # heavy looks: man 1 of 2; three-receiver looks: man 0 of 2
    assert buf["man_oe"] == pytest.approx(((1 - 0.5) + (0 - 0)) / 2)


def test_a_play_listed_twice_raises():
    with pytest.raises(ValueError, match="twice"):
        _rows([_drop(1)], [_chart(1), _chart(1)])
    assert "epa" in PBP_COLUMNS and "defense_coverage_type" in PARTICIPATION_COLUMNS


def test_the_part_is_known_after_the_season_and_post_season_only():
    rows = _rows([_drop(1), _drop(2)], [_chart(1), _chart(2, man=False)])
    parts = team_game_parts(schedules(), cal(), charted=rows)
    check_parts(parts, "team_game")
    part = parts["charted"]
    assert part.height == 1
    assert part["known_at"].item() > utc(2026, 2, 8)  # the toy season's Super Bowl
    assert "charted" in table("team_game").post_season
