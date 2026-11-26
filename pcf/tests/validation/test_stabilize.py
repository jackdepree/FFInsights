"""The shared shrink (`pcf.validation.stabilize`, owned by stabilization; decision 0052 call 1),
on synthetic rows with known answers."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from pcf.validation import stabilize as S

c = pl.col


def _world(
    players: int = 300,
    games: int = 16,
    att: int = 30,
    p: float = 0.3,
    sd: float = 0.05,
    seasons=(2018, 2019, 2020),
    seed: int = 0,
):
    """Players with fixed true rates (mean p, sd `sd`), binomial games."""
    rng = np.random.default_rng(seed)
    true = np.clip(rng.normal(p, sd, players), 0.01, 0.99)
    rows = []
    for s in seasons:
        for i in range(players):
            k = rng.binomial(att, true[i], games)
            for g in range(games):
                rows.append(
                    {
                        "gsis_id": f"p{i}",
                        "season": s,
                        "week": g + 1,
                        "group": "A",
                        "num": float(k[g]),
                        "den": float(att),
                    }
                )
    return pl.DataFrame(rows), true


def _season(g: pl.DataFrame) -> pl.DataFrame:
    return g.group_by("gsis_id", "season", "group").agg(
        num=c("num").sum(), den=c("den").sum(), n_games=pl.len()
    )


def test_shrink_and_its_expression_agree():
    assert S.shrink(0.2, 30, 10) == pytest.approx(0.15)
    assert S.shrink(0.2, 30, 10, target=0.1) == pytest.approx(0.175)
    df = pl.DataFrame({"x": [0.2, -0.1], "n": [30.0, 10.0], "k": [10.0, 10.0]})
    got = df.select(S.shrink_expr())["n"].to_list()
    assert got == pytest.approx([0.15, -0.05])
    assert S.reliability(30, 10) == pytest.approx(0.75)
    assert S.posterior_sd(4.0, 3, 1) == pytest.approx(1.0)


def test_centre_same_season_is_the_group_mean():
    rows = pl.DataFrame(
        {
            "group": ["A", "A", "B"],
            "season": [2020] * 3,
            "num": [3.0, 1.0, 5.0],
            "den": [10.0, 10.0, 10.0],
        }
    )
    out = S.centre(rows, target="same").sort("num")
    assert out.filter(c("group") == "A")["mu"].to_list() == pytest.approx([0.2, 0.2])
    assert out.filter(c("group") == "B")["x"].to_list() == pytest.approx([0.0])


def test_centre_last_season_uses_only_last_seasons_mean():
    rows = pl.DataFrame(
        {
            "group": ["A"] * 4,
            "season": [2019, 2019, 2020, 2020],
            "num": [1.0, 3.0, 9.0, 9.0],
            "den": [10.0] * 4,
        }
    )
    out = S.centre(rows, target="last").sort("season")
    s20 = out.filter(c("season") == 2020)
    assert s20["mu"].to_list() == pytest.approx([0.2, 0.2])  # 2019's mean, not 2020's 0.9
    assert s20["mu_last_known"].all()
    s19 = out.filter(c("season") == 2019)  # the first season falls back to its own mean
    assert s19["mu"].to_list() == pytest.approx([0.2, 0.2])
    assert not s19["mu_last_known"].any()
    with pytest.raises(ValueError):
        S.centre(rows, target="next")


def test_centre_floor_and_min_rows():
    rows = pl.DataFrame(
        {
            "group": ["A", "A", "A"],
            "season": [2020] * 3,
            "num": [1.0, 2.0, 50.0],
            "den": [10.0, 10.0, 2.0],
        }
    )
    out = S.centre(rows, floor=5.0)
    assert out.height == 2 and out["mu"][0] == pytest.approx(0.15)  # the thin row isn't in it
    assert S.centre(rows, floor=5.0, min_rows=3).height == 0


def test_components_recover_the_noise_and_the_true_spread():
    g, true = _world()
    s = _season(g)
    rows = S.centre(s, target="same")
    games = g.join(rows.select("gsis_id", "season", "rate", "n_games"), on=["gsis_id", "season"])
    sigma2, tau2 = S.components(rows, games)
    assert sigma2 == pytest.approx(0.3 * 0.7, rel=0.08)
    assert tau2 == pytest.approx(np.var(true), rel=0.25)
    assert S.k_of(sigma2, tau2) == pytest.approx(0.21 / np.var(true), rel=0.3)


def test_walk_slopes_use_earlier_seasons_only():
    rng = np.random.default_rng(1)
    season = np.repeat([2018, 2019, 2020], 100)
    x = rng.normal(size=300)
    y = 0.6 * x + rng.normal(scale=0.3, size=300)
    w = np.ones(300)
    fc, b = S.second_pull(x, y, w, season)
    assert np.isnan(fc[season == 2018]).all()  # nothing earlier to fit on
    assert np.nanmean(b) == pytest.approx(0.6, abs=0.1)
    y2 = y.copy()
    y2[season == 2020] = 99.0  # a later season's outcomes change nothing earlier
    fc2, _ = S.second_pull(x, y2, w, season)
    np.testing.assert_allclose(fc2[season <= 2020], fc[season <= 2020])


def test_wls_matches_the_weighted_formula():
    X = np.array([[1.0], [2.0], [3.0]])
    y = np.array([1.0, 2.0, 9.0])
    w = np.array([1.0, 1.0, 0.0])
    assert S.wls(X, y, w)[0] == pytest.approx(1.0)
