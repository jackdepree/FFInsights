"""The `play.xfp` and `player_game.opportunity` builders (decision 0041), on hand-made plays."""

import numpy as np
import polars as pl
import pytest

from pcf.data.tables import opportunity as O

c = pl.col
GAME = "2020_01_AAA_BBB"


def _pbp(rows: list[dict]) -> pl.DataFrame:
    base = {
        "game_id": GAME, "season": 2020, "season_type": "REG", "two_point_attempt": 0.0,
        "sack": 0.0, "rush": 0.0, "receiver_player_id": None, "rusher_player_id": None,
        "td_player_id": None, "touchdown": 0.0, "complete_pass": 0.0, "yards_gained": 0.0,
        "air_yards": None, "pass_location": None, "run_location": None, "run_gap": None,
        "yards_after_catch": None, "xyac_mean_yardage": None, "yardline_100": 50.0, "down": 1.0,
        "ydstogo": 10.0, "goal_to_go": 0.0, "shotgun": 1.0, "no_huddle": 0.0, "qtr": 1.0,
        "half_seconds_remaining": 900.0, "score_differential": 0.0,
    }  # fmt: skip
    return pl.DataFrame([{**base, "play_id": float(i + 1), **r} for i, r in enumerate(rows)],
                        schema_overrides={"receiver_player_id": pl.String,
                                          "rusher_player_id": pl.String,
                                          "td_player_id": pl.String,
                                          "pass_location": pl.String, "run_location": pl.String,
                                          "run_gap": pl.String})  # fmt: skip


ROSTER = pl.DataFrame({
    "gsis_id": ["wr", "rb", "qb", "te"], "game_id": [GAME] * 4,
    "position": ["WR", "RB", "QB", "TE"], "season": [2020] * 4,
})  # fmt: skip


def _plays() -> pl.DataFrame:
    return _pbp([
        # a 12-yard catch with 5 yards after it, 2 over nflverse's expectation
        {"play_type": "pass", "receiver_player_id": "wr", "complete_pass": 1.0,
         "yards_gained": 12.0, "air_yards": 7.0, "pass_location": "left",
         "yards_after_catch": 5.0, "xyac_mean_yardage": 3.0},
        # an incomplete end-zone target from the 8
        {"play_type": "pass", "receiver_player_id": "te", "air_yards": 9.0, "yardline_100": 8.0,
         "pass_location": "middle"},
        # a goal-line touchdown run
        {"play_type": "run", "rush": 1.0, "rusher_player_id": "rb", "yards_gained": 2.0,
         "touchdown": 1.0, "td_player_id": "rb", "yardline_100": 2.0, "run_location": "middle",
         "run_gap": "guard"},
        # a sack, a two-point try and a QB scramble aren't chances
        {"play_type": "pass", "receiver_player_id": "wr", "sack": 1.0},
        {"play_type": "pass", "receiver_player_id": "wr", "two_point_attempt": 1.0},
        {"play_type": "run", "rush": 1.0, "rusher_player_id": "qb", "yards_gained": 9.0},
        # a 40-yard deep target, caught: a touchdown by the receiver
        {"play_type": "pass", "receiver_player_id": "wr", "complete_pass": 1.0,
         "yards_gained": 40.0, "air_yards": 35.0, "touchdown": 1.0, "td_player_id": "wr",
         "yardline_100": 40.0, "yards_after_catch": 5.0, "xyac_mean_yardage": 6.0},
    ])  # fmt: skip


def test_only_rb_wr_te_targets_and_carries_are_chances():
    ch = O.chance_rows(_plays(), ROSTER)
    assert ch.select("play_id", "oq_gsis_id", "oq_kind").rows() == [
        (1, "wr", "target"), (2, "te", "target"), (3, "rb", "carry"), (7, "wr", "target"),
    ]  # fmt: skip
    wr = ch.filter(c("play_id") == 1).row(0, named=True)
    assert (wr["oq_catch"], wr["oq_yards"], wr["oq_td"], wr["oq_yac_oe"]) == (1.0, 12.0, 0.0, 2.0)
    assert ch.filter(c("play_id") == 2)["oq_yards"][0] == 0.0  # incomplete: no yards
    assert ch.filter(c("play_id") == 3)["oq_td"][0] == 1.0


def _fake_season(season: int, n: int = 3000, seed: int = 0) -> pl.DataFrame:
    """Chances where a target's catch chance falls with depth and a carry's touchdown chance rises
    near the goal line."""
    rng = np.random.default_rng(seed + season)
    kind = rng.choice(["target", "carry"], n)
    yl = rng.uniform(1, 99, n)
    air = np.where(kind == "target", rng.uniform(-3, 40, n), np.nan)
    catch = np.where(kind == "target", rng.uniform(size=n) < 0.8 - air / 60, 0).astype(float)
    td = (rng.uniform(size=n) < np.where(yl < 3, 0.5, 0.02)).astype(float)
    yards = np.where(kind == "carry", rng.normal(4, 3, n), catch * (np.nan_to_num(air) + 4))
    df = pl.DataFrame({
        "game_id": [f"{season}_{i}" for i in range(n)], "play_id": np.arange(n, dtype=np.int64),
        "season": pl.Series([season] * n, dtype=pl.Int32), "season_type": "REG",
        "oq_gsis_id": "p", "oq_kind": kind, "oq_position": "WR",
        "air": air, "loc": rng.integers(0, 3, n).astype(float),
        "gap": np.where(kind == "carry", rng.integers(0, 3, n), np.nan).astype(float),
        "oq_catch": catch, "oq_yards": yards, "oq_td": td,
        "oq_yac_oe": np.full(n, np.nan),
    })  # fmt: skip
    return df.with_columns(
        yardline_100=pl.Series(yl),
        down=pl.lit(1.0),
        ydstogo=pl.lit(10.0),
        goal_to_go=pl.lit(0.0),
        shotgun=pl.lit(1.0),
        no_huddle=pl.lit(0.0),
        qtr=pl.lit(1.0),
        half_seconds_remaining=pl.lit(900.0),
        score_differential=pl.lit(0.0),
    )


def test_the_expected_models_learn_the_situation_and_only_from_earlier_seasons(tmp_path):
    have = [2009, 2010, 2011, 2012]
    seen = []

    def chances_of(season):
        seen.append(season)
        return _fake_season(season)

    assert O.fitted_for(2011, have, chances_of, tmp_path) is None  # fewer than 3 seasons before
    fitted = O.fitted_for(2012, have, chances_of, tmp_path)
    assert fitted["seasons"] == [2009, 2010, 2011] and 2012 not in seen
    out = O.apply(_fake_season(2012), fitted)
    near = out.join(_fake_season(2012).select("game_id", "play_id", "yardline_100"),
                    on=["game_id", "play_id"])  # fmt: skip
    carries = near.filter(c("oq_kind") == "carry")
    assert carries.filter(c("yardline_100") < 3)["oq_td_exp"].mean() > 0.3
    assert carries.filter(c("yardline_100") > 10)["oq_td_exp"].mean() < 0.06
    assert (near.filter(c("oq_kind") == "carry")["oq_catch_exp"] == 0).all()
    # the cache is reused, and a fit that saw its own season is refused
    seen.clear()
    assert O.fitted_for(2012, have, chances_of, tmp_path)["seasons"] == [2009, 2010, 2011]
    assert not seen
    with pytest.raises(ValueError, match="fit on"):
        O.check_fit(fitted, 2011)


def test_a_player_game_sums_his_chances_and_a_benched_player_gets_zeros():
    pbp = _plays()
    ch = O.chance_rows(pbp, ROSTER)
    plays = ch.with_columns(
        oq_catch_exp=pl.lit(0.5), oq_yards_exp=pl.lit(5.0), oq_td_exp=pl.lit(0.1)
    ).select(*ch.columns, "oq_catch_exp",
             "oq_yards_exp", "oq_td_exp")  # fmt: skip
    roster = pl.concat([ROSTER, ROSTER.head(1).with_columns(gsis_id=pl.lit("bench"))])
    pg = O.player_game_rows(plays, pbp, roster, True)
    assert set(pg["gsis_id"]) == {"wr", "rb", "te", "bench"}  # no QB
    wr = pg.filter(c("gsis_id") == "wr").row(0, named=True)
    assert wr["oq_targets"] == 2 and wr["oq_catches"] == 2 and wr["oq_rec_yards"] == 52
    assert wr["oq_rec_tds"] == 1 and wr["oq_deep_targets"] == 1 and wr["oq_yac_oe"] == 1.0
    assert wr["oq_yac_n"] == 2 and wr["oq_catch_exp"] == 1.0
    te = pg.filter(c("gsis_id") == "te").row(0, named=True)
    assert te["oq_ez_targets"] == 1 and te["oq_rz_targets"] == 1
    assert pg.filter(c("gsis_id") == "rb")["oq_gl_carries"][0] == 1
    bench = pg.filter(c("gsis_id") == "bench").row(0, named=True)
    assert bench["oq_chances"] == 0 and bench["oq_catch_exp"] == 0
    early = O.player_game_rows(plays, pbp, roster, False)
    assert early["oq_catch_exp"].null_count() == early.height  # no model yet: no expected values
