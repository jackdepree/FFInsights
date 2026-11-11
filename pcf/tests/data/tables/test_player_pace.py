"""`player_game.on_field_pace` and `player_season.on_field_pace`: each player's team rates on and
off the field, and his season's plus-minus (decision 0029)."""

from datetime import UTC, datetime

import polars as pl
import pytest

from pcf.data.schemas import check_part
from pcf.data.tables.player_pace import player_pace_rows, player_season_rows

KNOWN = datetime(2017, 2, 6, 23, 30, tzinfo=UTC)
GAME = "2016_01_BUF_BAL"


def _plays():
    """BAL's 4 snaps: two passes (PROE +0.4 each) and two runs (-0.6 each); pace over expected
    +2, +2, -2 and unmeasured. Passes from 11 personnel, runs from 12."""
    return pl.DataFrame(
        {
            "game_id": [GAME] * 4,
            "play_id": [1, 2, 3, 4],
            "posteam": ["BAL"] * 4,
            "pcf_pass_oe": [0.4, 0.4, -0.6, -0.6],
            "pace_oe": [2.0, 2.0, -2.0, None],
            "offense_personnel": ["11", "11", "12", "12"],
        }
    )


def _on_field():
    """The QB on every snap; a receiver on the passes; a tight end on the runs; a corner on
    defense for snaps 1 and 3; a two-way player on offense once and defense twice."""
    rows = [("qb", "offense", p) for p in (1, 2, 3, 4)]
    rows += [("wr", "offense", p) for p in (1, 2)]
    rows += [("te", "offense", p) for p in (3, 4)]
    rows += [("cb", "defense", p) for p in (1, 3)]
    rows += [("two", "offense", 1), ("two", "defense", 2), ("two", "defense", 3)]
    return pl.DataFrame(
        {
            "game_id": [GAME] * len(rows),
            "play_id": [p for *_, p in rows],
            "season": pl.Series([2016] * len(rows), dtype=pl.Int32),
            "side": [s for _, s, _ in rows],
            "gsis_id": [g for g, *_ in rows],
            "known_at": pl.Series([KNOWN] * len(rows), dtype=pl.Datetime("us", "UTC")),
        }
    )


def test_on_and_off_rates_and_their_weights():
    out = player_pace_rows(_plays(), _on_field())
    check_part(out, "player_game", "on_field_pace")
    by = {r["gsis_id"]: r for r in out.iter_rows(named=True)}
    wr = by["wr"]
    assert wr["onf_plays"] == 2 and wr["onf_team_plays"] == 4
    assert wr["onf_proe_on"] == pytest.approx(0.4)
    assert wr["onf_proe_off"] == pytest.approx(-0.6)
    assert wr["onf_pm_proe"] == pytest.approx(1.0)
    assert wr["onf_w_proe"] == pytest.approx(2 * 2 / 4)
    # pace: on +2, +2; off -2 (snap 4 unmeasured)
    assert wr["onf_pm_pace"] == pytest.approx(4.0)
    assert wr["onf_w_pace"] == pytest.approx(2 * 1 / 3)
    assert by["te"]["onf_pm_proe"] == pytest.approx(-1.0)
    # a player who never sat out has no plus-minus and no weight
    assert by["qb"]["onf_pm_proe"] is None and by["qb"]["onf_w_proe"] == 0.0


def test_within_personnel_the_package_is_taken_out():
    """The receiver is on exactly the 11-personnel snaps, so within personnel he's 0."""
    out = player_pace_rows(_plays(), _on_field())
    wr = out.filter(pl.col("gsis_id") == "wr").row(0, named=True)
    assert wr["onf_pm_proe_pers"] == pytest.approx(0.0)


def test_a_defenders_rates_are_the_offense_against_him_and_a_two_way_player_keeps_his_main_side():
    out = player_pace_rows(_plays(), _on_field())
    by = {r["gsis_id"]: r for r in out.iter_rows(named=True)}
    assert by["cb"]["onf_side"] == "defense"
    assert by["cb"]["onf_proe_on"] == pytest.approx((0.4 - 0.6) / 2)
    assert by["two"]["onf_side"] == "defense" and by["two"]["onf_plays"] == 2
    assert out.select("gsis_id", "game_id").is_duplicated().sum() == 0


def test_a_season_is_its_games_weighted_by_what_measures_them():
    games = pl.DataFrame(
        {
            "gsis_id": ["wr", "wr"],
            "game_id": ["g1", "g2"],
            "season": pl.Series([2016, 2016], dtype=pl.Int32),
            "onf_side": ["offense", "offense"],
            "onf_plays": pl.Series([10, 30], dtype=pl.Int32),
            "onf_team_plays": pl.Series([60, 60], dtype=pl.Int32),
            "onf_proe_on": [0.1, 0.0],
            "onf_proe_off": [0.0, 0.0],
            "onf_pm_proe": [0.1, -0.1],
            "onf_w_proe": [1.0, 3.0],
            "onf_pm_proe_pers": [0.2, 0.0],
            "onf_pace_on": [None, 1.0],
            "onf_pace_off": [None, 0.0],
            "onf_pm_pace": [None, 1.0],
            "onf_w_pace": [0.0, 2.0],
            "known_at": pl.Series([KNOWN, KNOWN], dtype=pl.Datetime("us", "UTC")),
        }
    )
    roster = pl.DataFrame(
        {"gsis_id": ["wr", "wr"], "game_id": ["g1", "g2"], "team": ["BAL", "NYJ"],
         "position": ["WR", "WR"]}
    )  # fmt: skip
    kickoffs = pl.DataFrame(
        {
            "game_id": ["g1", "g2"],
            "kickoff": pl.Series([KNOWN, KNOWN], dtype=pl.Datetime("us", "UTC")),
        }
    )
    out = player_season_rows(games, roster, kickoffs)
    check_part(out, "player_season", "on_field_pace")
    row = out.row(0, named=True)
    assert row["onf_pm_proe"] == pytest.approx((0.1 * 1 - 0.1 * 3) / 4)
    assert row["onf_w_proe"] == pytest.approx(4.0)
    assert row["onf_pm_pace"] == pytest.approx(1.0)
    assert row["onf_proe_on"] == pytest.approx(0.1 * 10 / 40)
    assert row["onf_team"] == "NYJ" and row["onf_group"] == "WR" and row["onf_games"] == 2
    assert row["last_kickoff"] == KNOWN
