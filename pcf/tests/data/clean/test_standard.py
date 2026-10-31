import polars as pl
import pytest

from pcf.data.clean import standard


def test_every_franchise_has_one_code():
    df = pl.DataFrame(
        {"team": ["OAK", "LVR", "SD", "STL", "LAR", "ARZ", "BLT", "JAC", "KC", "FA", "2TM"]}
    )
    out = standard.standard_teams(df, "team")
    assert out["team"].to_list() == [
        "LV",
        "LV",
        "LAC",
        "LA",
        "LA",
        "ARI",
        "BAL",
        "JAX",
        "KC",
        None,
        None,
    ]


def test_an_unknown_team_code_is_refused():
    with pytest.raises(ValueError, match="XYZ"):
        standard.standard_teams(pl.DataFrame({"team": ["XYZ"]}), "team")


def test_schedules_roof_rule_and_betting_style_spread():
    df = pl.DataFrame(
        {
            "home_team": ["KC", "OAK"],
            "away_team": ["SD", "DEN"],
            "roof": ["dome", ""],
            "spread_line": [3.5, -2.0],
        }
    )
    out = standard.schedules(df)
    assert out["roof"].to_list() == ["dome", None]  # as nflreadpy's load_schedules does
    assert out["home_spread"].to_list() == [-3.5, 2.0]  # home favored by 3.5 → -3.5
    assert out["spread_line"].to_list() == [3.5, -2.0]  # nflverse's own column unchanged
    assert out["home_team"].to_list() == ["KC", "LV"]


def test_ids_are_renamed():
    stats = standard.player_stats(
        pl.DataFrame(
            {
                "player_id": ["a", "0", None],
                "team": ["KC"] * 3,
                "opponent_team": ["OAK"] * 3,
            }
        )
    )
    assert stats.columns == ["gsis_id", "team", "opponent_team"]
    assert stats["opponent_team"].item() == "LV"
    part = standard.participation(
        pl.DataFrame({"nflverse_game_id": ["g"], "possession_team": ["SD"]})
    )
    assert part.row(0) == ("g", "LAC")


def test_expected_points_rows_without_a_player_are_dropped():
    out = standard.ff_opportunity(
        pl.DataFrame(
            {"player_id": ["a", None, "a"], "posteam": ["KC"] * 3, "game_id": ["g", "g", "g"]}
        )
    )
    assert out.rows() == [("a", "KC", "g")]
    assert out.columns == ["gsis_id", "team", "game_id"]


def test_snap_counts_get_a_gsis_id_from_the_players_file():
    snaps = pl.DataFrame(
        {
            "pfr_player_id": ["MahoPa00", "Nobody00"],
            "team": ["KC", "KC"],
            "opponent": ["OAK", "OAK"],
        }
    )
    ids = pl.DataFrame({"pfr_id": ["MahoPa00", None], "gsis_id": ["00-0033873", "x"]})
    out = standard.snap_counts(snaps, ids)
    assert out["gsis_id"].to_list() == ["00-0033873", None]
    assert out["opponent"].to_list() == ["LV", "LV"]


def test_injuries_keep_the_latest_report_per_team_and_week():
    t = pl.datetime(2024, 12, 14, 12, time_zone="UTC")
    df = pl.DataFrame(
        {
            "season": [2024.0, 2024.0, 2017.0, 2017.0],
            "week": [15.0, 15.0, 10.0, 10.0],
            "game_type": ["REG"] * 4,
            "team": ["NYJ", "NYJ", "GB", "NE"],
            "gsis_id": ["a", "a", "b", "b"],
            "report_status": ["Out", "Questionable", "Questionable", "Questionable"],
        }
    ).with_columns(
        date_modified=pl.select(
            pl.concat_list(t + pl.duration(days=1), t, t, t).explode()
        ).to_series()
    )
    out = standard.injuries(df)
    assert out.filter(pl.col("gsis_id") == "a")["report_status"].to_list() == ["Out"]
    assert out.filter(pl.col("gsis_id") == "b").height == 2  # traded: one row per team
    assert out["season"].dtype == pl.Int32


def test_weekly_rosters_keep_the_active_row():
    df = pl.DataFrame(
        {
            "season": [2002] * 4,
            "week": [1] * 4,
            "team": ["ARZ", "ARZ", "ARZ", "ARZ"],
            "gsis_id": ["a", "a", None, None],
            "status": ["TRD", "ACT", "ACT", "ACT"],
        }
    )
    out = standard.weekly_rosters(df)
    assert out.filter(pl.col("gsis_id") == "a")["status"].to_list() == ["ACT"]
    assert out.filter(pl.col("gsis_id").is_null()).height == 2  # no id: both kept
    assert out["team"].unique().to_list() == ["ARI"]
