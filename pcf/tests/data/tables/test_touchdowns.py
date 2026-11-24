"""The touchdown parts' pure builders (td-expert, decision 0043)."""

from __future__ import annotations

import itertools

import numpy as np
import polars as pl
import pytest

from pcf.data.tables import touchdowns as T


def brute_at_least(p: list[float], k: int) -> float:
    total = 0.0
    for hits in itertools.product((0, 1), repeat=len(p)):
        if sum(hits) >= k:
            total += float(np.prod([q if h else 1 - q for q, h in zip(p, hits)]))
    return total


def test_at_least_matches_brute_force():
    rng = np.random.default_rng(3)
    groups = [list(rng.uniform(0, 0.6, n)) for n in (1, 4, 7, 2)]
    ks = np.array([1, 2, 0, 3])
    p = np.concatenate([np.array(g) for g in groups])
    gid = np.concatenate([np.full(len(g), i) for i, g in enumerate(groups)])
    order = rng.permutation(len(p))  # groups needn't be sorted
    got = T.at_least(p[order], gid[order], ks)
    want = [brute_at_least(g, int(k)) for g, k in zip(groups, ks)]
    assert got == pytest.approx(want, abs=1e-12)
    assert got[2] == 1.0  # at least 0 is certain
    assert got[3] == 0.0  # 3 from 2 chances can't happen


def test_luck_is_zero_without_dice():
    df = pl.DataFrame({"td": [1.0, 2.0], "x": [0.5, 2.0], "v": [0.25, 0.0]})
    z = df.select(z=T.luck(pl.col("td"), pl.col("x"), pl.col("v")))["z"].to_list()
    assert z == pytest.approx([1.0, 0.0])


def _pbp(rows: list[dict]) -> pl.DataFrame:
    base = {col: None for col in T.PBP_COLUMNS}
    base.update(game_id="2023_01_A_B", season=2023, season_type="REG", two_point_attempt=0.0,
                sack=0.0, posteam="A", home_team="B", away_team="A", fixed_drive=1.0,
                fixed_drive_result="Touchdown", yardline_100=5.0, down=1.0, ydstogo=5.0,
                goal_to_go=1.0, shotgun=0.0, no_huddle=0.0, qtr=1.0, half_seconds_remaining=900.0,
                score_differential=0.0, touchdown=0.0, qb_scramble=0.0, rush=0.0)  # fmt: skip
    schema = {col: pl.Float64 for col in T.PBP_COLUMNS}
    for col in ("game_id", "season_type", "play_type", "receiver_player_id", "rusher_player_id",
                "passer_player_id", "td_player_id", "posteam", "home_team", "away_team",
                "fixed_drive_result", "pass_location", "run_location", "run_gap"):  # fmt: skip
        schema[col] = pl.String
    schema["season"] = pl.Int32
    return pl.DataFrame([{**base, **r} for r in rows], schema=schema)


def test_chance_rows_counts_scrambles_as_carries():
    """nflverse marks a scramble rush 0, pass 1: it is still a carry (the scramble trap)."""
    pbp = _pbp([
        dict(play_id=1.0, play_type="run", rush=1.0, rusher_player_id="RB1"),
        dict(play_id=2.0, play_type="run", rush=0.0, qb_scramble=1.0, rusher_player_id="QB1",
             touchdown=1.0, td_player_id="QB1"),
        dict(play_id=3.0, play_type="pass", receiver_player_id="WR1", passer_player_id="QB1",
             air_yards=5.0, pass_location="left"),
        dict(play_id=4.0, play_type="pass", receiver_player_id="WR1", passer_player_id="QB1",
             two_point_attempt=1.0),
    ])  # fmt: skip
    roster = pl.DataFrame({"gsis_id": ["RB1", "QB1"], "game_id": ["2023_01_A_B"] * 2,
                           "position": ["RB", "QB"]})  # fmt: skip
    rows = T.chance_rows(pbp, roster).sort("play_id")
    assert rows["tdx_kind"].to_list() == ["carry", "carry", "target"]  # the 2-point try is out
    qb = rows.filter(pl.col("tdx_gsis_id") == "QB1").row(0, named=True)
    assert qb["tdx_td"] == 1.0 and qb["scramble"] == 1.0
    assert rows.filter(pl.col("tdx_gsis_id") == "WR1")["tdx_position"].to_list() == [""]
