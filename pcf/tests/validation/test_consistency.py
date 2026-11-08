"""The consistency check tells a team trait from luck, on synthetic team-games."""

import numpy as np
import polars as pl

from pcf.validation.consistency import consistency


def _world(seed: int = 7) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    teams = [f"T{i}" for i in range(32)]
    trait = dict(zip(teams, rng.normal(0, 1, 32), strict=True))  # carries across seasons
    for season in range(2010, 2018):
        drift = {t: 0.8 * trait[t] + rng.normal(0, 0.6) for t in teams}
        spell = {t: rng.normal(0, 1) for t in teams}  # this season only
        for t in teams:
            for week in range(1, 18):
                rows.append(
                    {
                        "team": t,
                        "season": season,
                        "week": week,
                        "trait": drift[t] + rng.normal(0, 2),
                        "luck": rng.normal(0, 2),
                        "same_for_all": 1.0,
                        "state": spell[t] + rng.normal(0, 1),
                    }
                )
    return pl.DataFrame(rows)


def test_trait_is_consistent_and_luck_is_noise():
    out = consistency(_world(), ["trait", "luck"]).rows_by_key("measure", named=True, unique=True)
    assert out["trait"]["verdict"] == "trait"
    assert out["trait"]["week_r"] > 0.5
    assert out["trait"]["season_r"] > 0.3
    assert out["luck"]["verdict"] == "noise"
    assert out["luck"]["week_lo"] <= 0 <= out["luck"]["week_hi"]
    assert out["trait"]["unit_seasons"] == 32 * 8
    assert out["trait"]["season_pairs"] == 32 * 7


def test_a_measure_every_team_shares_is_noise():
    out = consistency(_world(), ["same_for_all"])
    assert out["verdict"][0] == "noise"


def test_missing_values_are_skipped():
    w = _world().with_columns(
        trait=pl.when(pl.col("week") == 3).then(None).otherwise(pl.col("trait"))
    )
    out = consistency(w, ["trait"])
    assert out["verdict"][0] == "trait"


def test_a_measure_that_repeats_only_within_a_season_is_a_state():
    out = consistency(_world(), ["state"])
    assert out["verdict"][0] == "state"
    assert out["week_r"][0] > 0.5
