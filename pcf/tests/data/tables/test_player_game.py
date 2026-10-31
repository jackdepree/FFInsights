from datetime import timedelta

import polars as pl
import pytest

from pcf.data.schemas import check_parts
from pcf.data.tables import player_game
from pcf.data.tables.player_game import ROSTER_COLUMNS, player_game_parts
from pcf.data.tables.store import load, write_parts

from .toy import KICK, cal, utc

GAME = "2025_01_BUF_KC"
WEEK1_END = utc(2025, 9, 8, 4)  # midnight Eastern after the week's last game day


def _rosters():
    rows = [
        ("KC", "qb1", "QB", "ACT"),
        ("KC", "wr1", "WR", "ACT"),
        ("KC", "wr2", "WR", "INA"),  # a game-day inactive
        ("KC", "ps1", "WR", "DEV"),  # practice squad: not on the 53
        ("BUF", "rb1", "RB", "ACT"),
    ]
    df = pl.DataFrame(rows, schema=["team", "gsis_id", "position", "status"], orient="row")
    extra = [c for c in ROSTER_COLUMNS if c not in df.columns]
    return df.with_columns(
        *[pl.lit(None).alias(c) for c in extra],
        season=pl.lit(2025, pl.Int32),
        week=pl.lit(1, pl.Int32),
    )


def _snaps():
    rows = [("qb1", "KC", "QB", 60), ("wr1", "KC", "WR", 50), ("sub1", "BUF", "LB", 12)]
    df = pl.DataFrame(rows, schema=["gsis_id", "team", "position", "offense_snaps"], orient="row")
    return df.with_columns(
        game_id=pl.lit(GAME),
        season=pl.lit(2025),
        week=pl.lit(1),
        defense_snaps=pl.lit(0),
        st_snaps=pl.lit(0),
        offense_pct=pl.lit(0.9),
        defense_pct=pl.lit(0.0),
        st_pct=pl.lit(0.0),
    )


def _parts():
    stats = pl.DataFrame(
        {
            "gsis_id": ["qb1"],
            "game_id": [GAME],
            "season": [2025],
            "week": [1],
            "team": ["KC"],
            "position": ["QB"],
            "passing_yards": [280],
            "receptions": [0],
        }
    )
    stats = stats.with_columns(
        pl.lit(None).alias(c)
        for c in ["player_name", "player_display_name", "position_group", "headshot_url"]
    ).with_columns(season_type=pl.lit("REG"), opponent_team=pl.lit("BUF"))
    injuries = pl.DataFrame(
        {
            "season": [2025],
            "week": [1],
            "game_type": ["REG"],
            "team": ["KC"],
            "gsis_id": ["wr2"],
            "report_status": ["Out"],
            "date_modified": [utc(2025, 9, 5, 20)],
        }
    ).with_columns(
        pl.lit(None).alias(c)
        for c in [
            "report_primary_injury",
            "report_secondary_injury",
            "practice_primary_injury",
            "practice_secondary_injury",
            "practice_status",
        ]
    )
    labels = pl.DataFrame(
        {
            "season": [2025],
            "week": [1],
            "team": ["KC"],
            "gsis_id": ["qb1"],
            "position": ["QB"],
            "depth": [1],
            "depth_mean": [1.0],
            "weeks_listed": [1],
            "position_label": ["QB1"],
        },
        schema_overrides={"season": pl.Int32, "week": pl.Int32},
    )
    ffo = pl.DataFrame(
        {
            "gsis_id": ["wr1"],
            "game_id": [GAME],
            "season": ["2025"],  # ff_opportunity's season is text (grain-tables#F9)
            "week": [1],
            "team": ["KC"],
            "full_name": ["W R"],
            "position": ["WR"],
            "receptions": [6],
        }
    )
    ngs = pl.DataFrame(
        {
            "season": [2025, 2025],
            "week": [1, 0],  # week 0 is the season total: left out
            "player_gsis_id": ["qb1", "qb1"],
            "avg_time_to_throw": [2.7, 2.8],
        }
    ).with_columns(pl.lit(None).alias(c) for c in [
        "season_type", "player_display_name", "player_position", "team_abbr",
        "player_first_name", "player_last_name", "player_jersey_number", "player_short_name",
    ])  # fmt: skip
    pfr = pl.DataFrame(
        {
            "game_id": [GAME],
            "season": [2025],
            "week": [1],
            "pfr_player_id": ["QbbbQb00"],
            "times_pressured": [9],
        }
    ).with_columns(
        pl.lit(None).alias(c)
        for c in ["pfr_game_id", "game_type", "team", "opponent", "pfr_player_name"]
    )
    players = pl.DataFrame({"pfr_id": ["QbbbQb00"], "gsis_id": ["qb1"]})
    return player_game_parts(
        cal(),
        _rosters(),
        snaps=_snaps(),
        stats=stats,
        ff_opportunity=ffo,
        injuries=injuries,
        labels=labels,
        ngs={"passing": ngs},
        pfr={"pass": pfr},
        players=players,
    )


def test_the_spine_is_the_53_plus_anyone_who_played():
    parts = _parts()
    check_parts(parts, "player_game")
    spine = parts["roster"].sort("gsis_id")
    assert spine["gsis_id"].to_list() == ["qb1", "rb1", "sub1", "wr1", "wr2"]
    sub = spine.filter(pl.col("gsis_id") == "sub1").row(0, named=True)
    assert (sub["on_roster"], sub["team"], sub["opponent"], sub["position"]) == (
        False,
        "BUF",
        "KC",
        "LB",
    )
    assert sub["known_at"] == KICK + timedelta(days=1)  # known only from the box score
    assert spine.filter("on_roster")["known_at"].unique().to_list() == [utc(2025, 9, 5, 4)]


def test_each_part_has_its_own_known_at_and_prefix():
    parts = _parts()
    when = {p: df["known_at"].unique().to_list() for p, df in parts.items()}
    assert when["game_status"] == [KICK - timedelta(hours=1)]
    assert when["injury"] == [utc(2025, 9, 5, 20)]
    assert when["depth"] == [KICK]  # 2025 charts are daily: the chart at kickoff
    assert when["stats"] == when["snaps"] == when["ff_opportunity"] == [KICK + timedelta(days=1)]
    assert when["ngs"] == [WEEK1_END + timedelta(days=1)]
    assert parts["ngs"]["ngs_pass_avg_time_to_throw"].to_list() == [2.7]
    assert parts["pfr"]["pfr_pass_times_pressured"].to_list() == [9]
    assert parts["ff_opportunity"]["ffo_receptions"].to_list() == [6]
    status = dict(parts["game_status"].select("gsis_id", "status").iter_rows())
    assert status == {"qb1": "ACT", "wr1": "ACT", "wr2": "INA", "rb1": "ACT"}


def test_inactives_stay_hidden_until_an_hour_before_kickoff(tmp_path):
    write_parts(_parts(), "player_game", [2025], tmp_path)
    friday = load("player_game", at=KICK - timedelta(days=2), root=tmp_path)
    assert friday.height == 4  # the 53, not yet the player who'll come off the street
    assert friday["status"].null_count() == 4
    assert friday["passing_yards"].null_count() == 4
    pregame = load("player_game", at=KICK - timedelta(minutes=30), root=tmp_path)
    assert dict(pregame.select("gsis_id", "status").iter_rows())["wr2"] == "INA"
    after = load("player_game", at=KICK + timedelta(days=1), root=tmp_path)
    assert after.height == 5
    assert after.filter(pl.col("gsis_id") == "qb1")["passing_yards"].item() == 280


def test_pfr_needs_the_players_file():
    with pytest.raises(ValueError, match="players file"):
        player_game_parts(cal(), _rosters(), pfr={"pass": pl.DataFrame()})


def test_before_2016_every_roster_row_is_on_the_spine(monkeypatch):
    # Old rosters give each player their last status of the season (grain-tables#F11).
    monkeypatch.setattr(player_game, "WEEKLY_STATUS_FROM", 2026)
    spine = player_game_parts(cal(), _rosters())["roster"]
    assert sorted(spine["gsis_id"].to_list()) == ["ps1", "qb1", "rb1", "wr1", "wr2"]


def test_a_player_on_both_teams_lists_keeps_their_own_teams_label():
    labels = pl.DataFrame(
        {
            "season": [2025, 2025],
            "week": [1, 1],
            "team": ["KC", "BUF"],  # traded between the two opponents that week
            "gsis_id": ["qb1", "qb1"],
            "position": ["QB", "QB"],
            "depth": [1, 3],
            "depth_mean": [1.0, 3.0],
            "weeks_listed": [1, 1],
            "position_label": ["QB1", "QB3"],
        },
        schema_overrides={"season": pl.Int32, "week": pl.Int32},
    )
    depth = player_game_parts(cal(), _rosters(), labels=labels)["depth"]
    assert depth.select("gsis_id", "position_label").rows() == [("qb1", "QB1")]
