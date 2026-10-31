import polars as pl
import pytest

from pcf.data.clean.players import players_on_play, plays_with_players


def _pbp(**cols):
    base = {
        "game_id": ["g"],
        "play_id": [1.0],
        "play_type": ["pass"],
        "season": [2024],
        "week": [1],
        "season_type": ["REG"],
        "posteam": ["KC"],
        "defteam": ["DEN"],
    }
    return pl.DataFrame({**base, **cols})


def _part(offense="a;b", defense="x;y", play_id=1):
    return pl.DataFrame(
        {
            "nflverse_game_id": ["g"],
            "play_id": pl.Series([play_id], dtype=pl.Int32),
            "offense_players": [offense],
            "defense_players": [defense],
        }
    )


def test_join_aligns_play_id_types():
    plays = plays_with_players(_pbp(), _part())
    assert plays["play_id"].dtype == pl.Int64
    assert plays["offense_players"].to_list() == ["a;b"]


def test_join_refuses_a_play_listed_twice():
    with pytest.raises(ValueError, match="twice"):
        plays_with_players(_pbp(), pl.concat([_part(), _part()]))


def test_every_listed_player_gets_a_row_and_empty_slots_none():
    twelve = ";".join(f"p{i}" for i in range(12))
    players = players_on_play(plays_with_players(_pbp(), _part(offense=twelve, defense="x;;y")))
    offense = players.filter(pl.col("side") == "offense")
    assert offense.height == 12  # the old code cut this list at 11
    assert offense["team"].unique().to_list() == ["KC"]
    defense = players.filter(pl.col("side") == "defense")
    assert defense["gsis_id"].to_list() == ["x", "y"]
    assert defense["slot"].to_list() == [1, 3]  # the place in the list, gaps kept


def test_only_run_and_pass_plays_by_default():
    plays = plays_with_players(_pbp(play_type=["punt"]), _part())
    assert players_on_play(plays).height == 0
    assert players_on_play(plays, play_types=["punt"]).height == 4
