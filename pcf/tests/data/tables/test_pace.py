"""`team_game.pace` and `play.pace`: volume and habits against PCF's own expected values."""

import numpy as np
import polars as pl
import pytest

from pcf.data.schemas import check_part
from pcf.data.tables import pace
from pcf.data.timeline import known_at

from .toy import cal

GAME = "2025_01_BUF_KC"


def _snap(play_id, posteam="KC", **over):
    """A first-down run on drive 1 by default, 30 seconds after the previous play."""
    row = {
        "game_id": GAME, "play_id": play_id, "season": 2025, "posteam": posteam,
        "defteam": "BUF" if posteam == "KC" else "KC", "down": 1, "ydstogo": 10,
        "yardline_100": 75, "qtr": 1, "half_seconds_remaining": 1800 - 30 * play_id,
        "game_seconds_remaining": 3600 - 30 * play_id, "score_differential": 0, "wp": 0.5,
        "vegas_wp": 0.5, "ep": 1.0, "epa": 0.1, "pass": 0, "rush": 1, "qb_kneel": 0,
        "qb_spike": 0, "sack": 0, "no_huddle": 0, "incomplete_pass": 0, "out_of_bounds": 0,
        "penalty": 0, "timeout": 0, "play_type": "run", "fixed_drive": 1,
    }  # fmt: skip
    return row | over


def _pbp(rows):
    return pl.DataFrame(rows, schema_overrides={"season": pl.Int32, "vegas_wp": pl.Float64})


def test_snaps_measure_the_gap_within_a_drive_and_count_timeouts():
    rows = [
        _snap(1),
        _snap(2, incomplete_pass=1, play_type="pass", rush=0, **{"pass": 1}),
        _snap(3, game_seconds_remaining=3600 - 30 * 2 - 5),  # 5 s after an incompletion
        {**_snap(4), "play_type": "timeout", "down": None, "timeout": 1},  # not a snap
        _snap(5),
        _snap(6, posteam="BUF", fixed_drive=2),  # a new drive: no gap
        _snap(7, posteam="BUF", fixed_drive=2, qb_kneel=1, play_type="qb_kneel"),
    ]
    s = pace.snap_rows(_pbp(rows))
    assert s["play_id"].to_list() == [1, 2, 3, 5, 6, 7]
    gaps = dict(zip(s["play_id"], s["gap"], strict=True))
    assert gaps[1] is None and gaps[6] is None  # no previous snap in the drive
    assert gaps[2] == 30.0 and gaps[3] == 5.0
    assert gaps[5] is None  # 85 s: beyond the 60 s cap
    flags = s.row(by_predicate=pl.col("play_id") == 3, named=True)
    assert flags["prev_incomplete"] == 1.0
    assert s.row(by_predicate=pl.col("play_id") == 5, named=True)["timeouts_before"] == 1.0
    assert s.filter("scrimmage")["play_id"].to_list() == [1, 2, 3, 5, 6]  # no kneel


def _expected(s, exp_pass=0.5, exp_gap=30.0):
    return s.with_columns(
        exp_pass=pl.when("scrimmage").then(exp_pass),
        exp_gap=pl.when(pl.col("gap").is_not_null()).then(exp_gap),
    ).with_columns(
        pass_oe=pl.col("pass") - pl.col("exp_pass"), pace_oe=pl.col("gap") - pl.col("exp_gap")
    )


def test_team_game_rows_count_volume_and_split_habits_by_down():
    rows = [
        _snap(1),
        _snap(2, rush=0, play_type="pass", no_huddle=1, **{"pass": 1}),
        _snap(3, down=2, rush=0, play_type="pass", **{"pass": 1}),
        _snap(4, down=3, fixed_drive=3),
        _snap(5, posteam="BUF", fixed_drive=2, rush=0, play_type="pass", **{"pass": 1}),
    ]
    out = pace.pace_rows(_expected(pace.snap_rows(_pbp(rows))))
    assert out.columns == ["game_id", "team", "season", *pace.OFFENSE, *pace.DEFENSE]
    kc = out.row(by_predicate=pl.col("team") == "KC", named=True)
    assert (kc["plays"], kc["dropbacks"], kc["runs"], kc["drives"]) == (4, 2, 2, 2)
    assert kc["plays_per_drive"] == 2.0
    assert kc["proe"] == pytest.approx(0.0)
    assert kc["proe_1st"] == pytest.approx(0.0)  # a run and a pass at 0.5
    assert kc["proe_2nd"] == pytest.approx(0.5) and kc["proe_3rd"] == pytest.approx(-0.5)
    assert (kc["downs_1st"], kc["downs_2nd"], kc["downs_3rd"]) == (2, 1, 1)
    assert kc["pace_oe"] == pytest.approx(0.0)  # two 30 s gaps against 30 s expected
    assert kc["pace_snaps"] == 2
    assert kc["no_huddle"] == pytest.approx(0.25)
    assert kc["def_plays"] == 1 and kc["def_proe"] == pytest.approx(0.5)  # BUF's one pass
    buf = out.row(by_predicate=pl.col("team") == "BUF", named=True)
    assert buf["def_plays"] == 4 and buf["def_dropbacks_all"] == 2


def test_play_rows_fit_the_play_table_contract():
    s = _expected(pace.snap_rows(_pbp([_snap(1), _snap(2)])))
    rows = known_at("pbp", pace.play_rows(s).with_columns(pl.col("play_id").cast(pl.Int64)), cal())
    check_part(rows, "play", "pace")
    assert rows.columns[:3] == ["game_id", "play_id", "season"]


def test_training_seasons_are_earlier_only_and_capped():
    have = list(range(1999, 2027))
    assert pace.training_seasons(2026, have) == list(range(2016, 2026))
    assert pace.training_seasons(2001, have) == []  # two earlier seasons: too few
    assert pace.training_seasons(2002, have) == [1999, 2000, 2001]


def _random_snaps(seasons, n=400, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for season in seasons:
        for i in range(n):
            down = int(rng.integers(1, 4))
            passed = int(rng.random() < 0.3 + 0.15 * down)
            rows.append(
                _snap(
                    i + 1,
                    season=season,
                    down=down,
                    rush=1 - passed,
                    play_type="pass" if passed else "run",
                    game_id=f"{season}_01_BUF_KC",
                    fixed_drive=i // 6,
                    vegas_wp=None if i % 50 == 0 else 0.5,
                    game_seconds_remaining=3600 - 30 * i - int(rng.integers(0, 10)),
                    **{"pass": passed},
                )  # fmt: skip
            )
    return pace.snap_rows(_pbp(rows))


def test_fit_and_apply_keep_every_play_and_give_sane_values():
    train = _random_snaps([2021, 2022, 2023])
    models = pace.fit_expected(train)
    assert models["seasons"] == [2021, 2022, 2023]
    out = pace.apply_expected(_random_snaps([2024], seed=1), models)
    sc = out.filter("scrimmage")
    assert sc["exp_pass"].null_count() == 0  # missing Vegas win chance is kept
    assert sc["exp_pass"].is_between(0, 1).all()
    assert sc.group_by("down").agg(pl.col("exp_pass").mean()).sort("down")["exp_pass"].is_sorted()
    assert out.filter(pl.col("gap").is_not_null())["exp_gap"].null_count() == 0
    pace.check_fit(models, 2024)
    with pytest.raises(ValueError, match="fit on"):
        pace.check_fit(models, 2023)


def test_expected_for_caches_and_refits_when_the_seasons_change(tmp_path):
    snaps = {s: _random_snaps([s], n=200, seed=s) for s in range(2019, 2024)}
    calls = []

    def snaps_of(s):
        calls.append(s)
        return snaps[s]

    first = pace.expected_for(2023, [2019, 2020, 2021, 2022, 2023], snaps_of, tmp_path)
    assert first["seasons"] == [2019, 2020, 2021, 2022]
    calls.clear()
    again = pace.expected_for(2023, [2019, 2020, 2021, 2022, 2023], snaps_of, tmp_path)
    assert calls == [] and again["seasons"] == first["seasons"]  # read from the cache
    fewer = pace.expected_for(2023, [2020, 2021, 2022, 2023], snaps_of, tmp_path)
    assert fewer["seasons"] == [2020, 2021, 2022] and calls == [2020, 2021, 2022]
    assert pace.expected_for(2021, [2019, 2020, 2021], snaps_of, tmp_path) is None
