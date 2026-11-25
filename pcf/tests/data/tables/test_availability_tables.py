"""availability's table parts (decision 0047): roster_week and the named in-game injuries."""

from __future__ import annotations

from datetime import UTC, datetime

import polars as pl

from pcf.data.schemas import check_part
from pcf.data.tables import availability as A

T0 = datetime(2024, 9, 10, tzinfo=UTC)


def _games():
    return pl.DataFrame({
        "game_id": ["g1", "g1"], "season": [2024, 2024], "week": [1, 1], "team": ["A", "B"],
    }).with_columns(pl.col("season", "week").cast(pl.Int32))  # fmt: skip


def test_roster_week_keeps_the_53_and_health_reserve_lists_only():
    rosters = pl.DataFrame({
        "gsis_id": ["a", "b", "c", "d", "e", "f", None],
        "season": [2024] * 7, "week": [1] * 7, "team": ["A"] * 6 + ["B"],
        "position": ["WR"] * 7,
        "status": ["ACT", "INA", "RES", "RES", "CUT", "PUP", "ACT"],
        "status_description_abbr": ["A01", "A01", "R01", "R02", None, None, None],
        "known_at": [T0] * 7,
    })  # fmt: skip
    out = A.roster_week_rows(rosters, _games())
    assert sorted(out["gsis_id"].to_list()) == ["a", "b", "c", "f"]  # retired (R02), cut, no id out
    assert out.filter(pl.col("reserve"))["gsis_id"].sort().to_list() == ["c", "f"]
    check_part(out, "roster_week", "status")


def test_roster_week_prefers_the_active_row_when_listed_twice():
    rosters = pl.DataFrame({
        "gsis_id": ["a", "a"], "season": [2024, 2024], "week": [1, 1], "team": ["A", "A"],
        "position": ["WR", "WR"], "status": ["RES", "ACT"],
        "status_description_abbr": ["R01", "A01"], "known_at": [T0, T0],
    })  # fmt: skip
    out = A.roster_week_rows(rosters, _games())
    assert out.height == 1 and out["status"][0] == "ACT" and not out["reserve"][0]


def test_named_injuries_match_team_jersey_and_last_name():
    pbp = pl.DataFrame({
        "game_id": ["g1", "g1", "g1"], "play_id": [10, 20, 30], "season": [2024] * 3,
        "week": [1] * 3, "season_type": ["REG"] * 3, "play_type": ["run", "pass", "run"],
        "desc": [
            "(1:00) J.Smith left end for 3 yards. BAL-21-J.Smith was injured during the play.",
            "Pass incomplete. KC-90-K.Jones was injured during the play. BAL-21-J.Smith was injured during the play.",
            "No one named here. BAL-99-Z.Nobody was injured during the play.",
        ],
    }).with_columns(pl.col("season").cast(pl.Int32))  # fmt: skip
    roster = pl.DataFrame({
        "gsis_id": ["p1", "p2"], "game_id": ["g1", "g1"], "team": ["BAL", "KC"],
        "jersey_number": [21, 90], "full_name": ["John Smith", "Kyle Jones"],
    })  # fmt: skip
    out = A.injured_rows(pbp, roster).sort("gsis_id")
    assert out["gsis_id"].to_list() == ["p1", "p2"]  # the unmatched name is dropped
    assert out["injured_play"].to_list() == [10, 20]  # the first named play
    assert out["n_injured"].to_list() == [2, 1]
