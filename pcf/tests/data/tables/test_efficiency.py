"""`team_game.efficiency`: the rated plays, the per-game sums and cells, the kinds and their
weights, and the vintage rule for the season's models."""

import numpy as np
import polars as pl
import pytest

from pcf.data.tables import efficiency as E

c = pl.col
GAME = "2025_01_BUF_KC"


def _play(play_id, **over):
    row = {
        "game_id": GAME, "play_id": play_id, "season": 2025, "week": 1, "season_type": "REG",
        "posteam": "KC", "defteam": "BUF", "down": 1, "ydstogo": 10, "yardline_100": 75,
        "qtr": 1, "half_seconds_remaining": 1500, "game_seconds_remaining": 3300,
        "score_differential": 0, "wp": 0.5, "epa": 0.2, "wpa": 0.01, "play_type": "run",
        "two_point_attempt": 0, "series": 1, "series_success": 1,
    }  # fmt: skip
    return row | over


def _pbp(rows):
    return pl.DataFrame(rows, schema_overrides={"season": pl.Int32, "wp": pl.Float64,
                                                "epa": pl.Float64, "wpa": pl.Float64})  # fmt: skip


def test_only_passes_and_runs_with_an_epa_count():
    p = E.plays(
        _pbp([
            _play(1),
            _play(2, play_type="pass"),
            _play(3, play_type="qb_kneel"),
            _play(4, two_point_attempt=1),
            _play(5, epa=None),
            _play(6, wpa=float("nan")),
            _play(7, posteam="OAK", defteam="SD"),  # old codes, standardized
        ])
    )  # fmt: skip
    assert p["play_id"].to_list() == [1, 2, 7]
    assert p.filter(c("play_id") == 7)["posteam"][0] == "LV"
    assert p["is_pass"].to_list() == [0, 1, 0]


def _rated(rows):
    p = E.plays(_pbp(rows))
    return p.with_columns(
        gap=pl.lit(0.0), kind=pl.lit("wp3|run"), g=pl.lit(0.05), resid=c("epa") - 0.05,
        w_off=pl.lit(2.0), w_def=pl.lit(0.5),
        bin=E._band(c("wp")) * 2 + (c("qtr") > 2).cast(pl.Int32),
    )  # fmt: skip


def test_sums_cells_and_series_per_offense_and_game():
    rows = [
        _play(1, epa=1.0),
        _play(2, epa=-0.5, play_type="pass", series=1),
        _play(3, epa=0.3, wp=0.95, qtr=3, series=2, series_success=0),  # garbage time
        _play(4, epa=0.1, half_seconds_remaining=100, series=2, series_success=0),
        _play(5, posteam="BUF", defteam="KC", epa=-1.0, series=1),
    ]
    out = E.efficiency_rows(_rated(rows))
    kc = out.filter(c("team") == "KC").row(0, named=True)
    assert kc["eff_plays"] == 4 and kc["eff_epa"] == pytest.approx(0.9)
    assert kc["eff_usual_plays"] == 2 and kc["eff_usual_epa"] == pytest.approx(0.5)
    assert kc["eff_pass_plays"] == 1 and kc["eff_run_epa"] == pytest.approx(1.4)
    assert kc["eff_series"] == 2 and kc["eff_series_success"] == 1.0
    cells_n = sum(kc[f"eff_n_{k}"] for k in range(E.BINS))
    assert cells_n == 4
    assert kc["eff_n_13"] == 1  # win chance above .90, second half
    assert kc["eff_r_6"] == pytest.approx(1.0 - 0.5 + 0.1 - 0.05 * 3)  # even band, first half
    assert kc["eff_rwo_6"] == pytest.approx(2 * kc["eff_r_6"])
    assert kc["eff_rwd_6"] == pytest.approx(0.5 * kc["eff_r_6"])
    assert out.columns == ["game_id", "team", "season", *E.COLUMNS]


def test_kinds_put_the_gap_tails_first_then_the_last_two_minutes():
    p = pl.DataFrame({
        "gap": [-0.2, 0.2, 0.0, 0.0, 0.0],
        "half_seconds_remaining": [1000, 1000, 100, 1000, 1000],
        "wp": [0.5, 0.5, 0.5, 0.05, None],
        "is_pass": [1, 0, 1, 0, 1],
    })  # fmt: skip
    got = p.select(k=E.kinds(p, -0.1, 0.1))["k"].to_list()
    assert got == ["gap-low|pass", "gap-high|run", "last2min|pass", "wp0|run", "wp3|pass"]


def _league(seed=0, seasons=(2010, 2011, 2012)):
    """Plays where every kind is equally representative: each team's EPA per play is its own."""
    rng = np.random.default_rng(seed)
    teams = [f"T{i}" for i in range(8)]
    rows = []
    for s in seasons:
        skill = rng.normal(0, 0.1, len(teams))
        for w in range(1, 9):
            for i, t in enumerate(teams):
                for k in range(40):
                    rows.append((s, w, t, teams[(i + w) % 8], f"wp{k % 7}|run",
                                 skill[i] + rng.normal(0, 1.2)))  # fmt: skip
    return pl.DataFrame(
        rows, schema=["season", "week", "posteam", "defteam", "kind", "epa"], orient="row"
    ).with_columns(c("season").cast(pl.Int32))


def test_kind_weights_shrink_to_equal_when_every_kind_is_alike():
    w, lam = E.kind_weights(_league(), "off")
    assert set(w) == {f"wp{k}|run" for k in range(7)}
    assert np.mean(list(w.values())) == pytest.approx(1.0, abs=0.05)
    assert max(w.values()) - min(w.values()) < 0.5
    assert all(v >= 0 for v in w.values())


def test_models_are_fit_only_on_earlier_seasons():
    assert E.training_seasons(2005, list(range(1999, 2026))) == list(range(1999, 2005))
    assert E.training_seasons(2001, [1999, 2000, 2001]) == []
    assert E.training_seasons(2016, list(range(1999, 2026))) == list(range(2006, 2016))
    with pytest.raises(ValueError, match="fit on"):
        E.check_fit({"seasons": [2014, 2015, 2016]}, 2016)
    E.check_fit({"seasons": [2014, 2015]}, 2016)
