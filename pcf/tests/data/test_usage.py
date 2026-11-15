"""`pcf.data.usage` and the `player_game.leverage_usage` part: each player-game's snaps weighted by
their stakes. A tiny game: four snaps, the last high-stakes. On offense A1 plays every snap and
A2 only the two ordinary ones; on defense B1 plays every snap and B2 only the high-stakes one."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import polars as pl
import pytest

from pcf.data import usage as U
from pcf.data.schemas import check_part, table

c = pl.col
LI = [0.5, 0.5, 1.0, 2.0]
HS = [False, False, False, True]
ON = {"A1": [1, 2, 3, 4], "A2": [1, 2], "B1": [1, 2, 3, 4], "B2": [4]}
TEAM = {"A1": ("A", "offense"), "A2": ("A", "offense"), "B1": ("B", "defense"),
        "B2": ("B", "defense")}  # fmt: skip
KNOWN = datetime(2022, 2, 14, tzinfo=UTC)


def _snaps() -> pl.DataFrame:
    return U.plays(
        pl.DataFrame(
            {
                "game_id": "g",
                "play_id": [1, 2, 3, 4],
                "leverage": LI,
                "high_stakes": HS,
                "pcf_xpass": [0.5, 0.5, 0.5, 0.5],
            }
        )  # fmt: skip
    )


def _on_field() -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "game_id": "g",
                "play_id": play,
                "season": 2021,
                "side": TEAM[p][1],
                "team": TEAM[p][0],
                "gsis_id": p,
                "known_at": KNOWN,
            }  # fmt: skip
            for p, plays in ON.items()
            for play in plays
        ]
    ).with_columns(c("season").cast(pl.Int32), c("known_at").cast(pl.Datetime("us", "UTC")))


def test_usage_weights_snaps_by_leverage_and_takes_out_the_situation():
    on = _on_field().select("game_id", "play_id", "gsis_id", "side", "team", p=pl.lit(1.0))
    u = {r["gsis_id"]: r for r in U.usage(on, _snaps()).to_dicts()}
    a2 = u["A2"]
    assert a2["snap_share"] == pytest.approx(0.5)
    assert a2["lev_share"] == pytest.approx(1.0 / 4.0)  # 0.5 + 0.5 of 4.0
    assert a2["hs_share"] == 0.0
    assert a2["role_gap"] == pytest.approx(-0.5)
    # on half the snaps in this kind of situation, so half a high-stakes snap expected
    assert a2["trust_oe"] == pytest.approx(-0.5)
    assert u["A1"]["trust_oe"] == pytest.approx(0.0)
    b2 = u["B2"]
    assert b2["lev_share"] == pytest.approx(0.5) and b2["trust_oe"] == pytest.approx(0.75)
    # a chance below 1 counts the snap partly (the morning-after map)
    half = U.usage(on.with_columns(p=pl.lit(0.5)), _snaps())
    assert half.filter(c("gsis_id") == "A1")["snap_share"].item() == pytest.approx(0.5)


def test_usage_is_the_same_to_the_last_digit_whatever_the_row_order():
    """Sums in another order differ in the last digit, enough to flip a tree's split (leakage
    check 8, snap-leverage#R8)."""
    rng = np.random.default_rng(1)
    n = 5000
    on = pl.DataFrame(
        {
            "game_id": rng.choice(["g1", "g2"], n),
            "play_id": rng.integers(1, 200, n),
            "gsis_id": rng.choice([f"P{i}" for i in range(40)], n),
            "side": "offense",
            "team": "A",
            "p": rng.random(n),
        }
    ).unique(["game_id", "play_id", "gsis_id"])
    snaps = U.plays(
        pl.DataFrame(
            {
                "game_id": ["g1"] * 199 + ["g2"] * 199,
                "play_id": list(range(1, 200)) * 2,
                "leverage": rng.random(398) * 3,
                "high_stakes": rng.random(398) > 0.8,
                "pcf_xpass": rng.random(398),
            }
        )
    )
    first = U.usage(on, snaps)
    for seed in range(3):
        again = U.usage(
            on.sample(fraction=1.0, shuffle=True, seed=seed),
            snaps.sample(fraction=1.0, shuffle=True, seed=seed),
        )
        assert again.equals(first)


def test_the_part_has_one_row_per_player_game_on_his_main_side_known_with_participation():
    on = _on_field()
    # B2 also takes two offensive snaps, more than his one on defense: offense is his main side
    extra = on.filter(c("gsis_id") == "A2").head(2).with_columns(gsis_id=pl.lit("B2"),
                                                                 team=pl.lit("A"))  # fmt: skip
    rows = U.part_rows(pl.concat([on, extra]), _snaps())
    assert rows.columns == ["gsis_id", "game_id", "season", *U.PART_COLUMNS, "known_at"]
    assert rows.height == 4 and not rows.select("gsis_id", "game_id").is_duplicated().any()
    r = {x["gsis_id"]: x for x in rows.to_dicts()}
    assert r["B2"]["lev_side"] == "offense" and r["B2"]["lev_snaps"] == 2
    assert r["A2"]["lev_share"] == pytest.approx(0.25) and r["A2"]["lev_snaps"] == 2
    assert (rows["known_at"] == KNOWN).all()
    check_part(rows, "player_game", "leverage_usage")
    t = table("player_game")
    assert "leverage_usage" in t.post_season and "leverage_usage" in t.after
