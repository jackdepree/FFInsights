"""skill-over-expected: the noise and spread, the season pairs, the ladder's rungs, the gains,
the ranges and the published table, on a synthetic world with known true rates."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import polars as pl
import pytest

from pcf.experts.skill_over_expected import evaluate as E
from pcf.experts.skill_over_expected import table as H
from pcf.experts.skill_over_expected import traits as T

c = pl.col
SEASONS = range(2016, 2022)
P, TRUE_SD, GAMES, DROPBACKS = 0.07, 0.02, 16, 35


def _world(players: int = 48, seed: int = 0, groups: tuple[str, ...] = ("QB",)):
    """Players with a fixed true sack rate (mean 0.07, sd 0.02), 16 games of 35 dropbacks a
    season, sacks binomial; a few change teams each season. Returns games, teams, truths."""
    rng = np.random.default_rng(seed)
    true = np.clip(rng.normal(P, TRUE_SD, players), 0.01, 0.2)
    team = rng.integers(0, 8, players)
    games, teams = [], []
    for s in SEASONS:
        move = rng.random(players) < 0.15
        team = np.where(move, rng.integers(0, 8, players), team)
        for i in range(players):
            pos = groups[i % len(groups)]
            pid = f"p{i:02d}"
            teams.append({"pid": pid, "season": s, "team": f"T{team[i]}", "position": pos})
            sacks = rng.binomial(DROPBACKS, true[i], GAMES)
            for w in range(GAMES):
                games.append({"gsis_id": pid, "game_id": f"{s}_{w}_{team[i]}", "season": s,
                              "week": w + 1, "team": f"T{team[i]}", "trait": "qb_sack_rate",
                              "num": float(sacks[w]), "den": float(DROPBACKS)})  # fmt: skip
    return (
        pl.DataFrame(games),
        pl.DataFrame(teams),
        dict(zip([f"p{i:02d}" for i in range(players)], true, strict=True)),
    )


@pytest.fixture(scope="module")
def world():
    games, teams, true = _world()
    rows = T.season_rows(games, teams, T.BY_NAME["qb_sack_rate"])
    return games, teams, true, rows


def test_season_rows_centre_on_the_group_season_mean(world):
    _, _, _, rows = world
    assert rows.height == 48 * len(SEASONS)
    by = rows.group_by("season").agg(m=(c("x") * c("den")).sum() / c("den").sum())
    assert by["m"].abs().max() < 1e-12


def test_components_recover_the_noise_and_the_true_spread(world):
    games, _, _, rows = world
    sigma2, tau2 = T.components(rows, T.game_rows(games, rows, T.BY_NAME["qb_sack_rate"]))
    assert sigma2 == pytest.approx(P * (1 - P), rel=0.15)
    assert tau2 == pytest.approx(TRUE_SD**2, rel=0.5)


def test_pairs_link_next_season_and_fit_k_on_past_seasons_only(world):
    games, _, _, rows = world
    p = T.pairs(rows, games)
    assert p["season"].max() == max(SEASONS) - 1
    one = p.filter((c("gsis_id") == "p00") & (c("season") == 2017))
    nxt = rows.filter((c("gsis_id") == "p00") & (c("season") == 2018))
    assert one["y"][0] == pytest.approx(nxt["x"][0])
    assert one["moved"][0] == (one["team"][0] != one["team_next"][0])
    # point-in-time: changing the last season's games leaves earlier seasons' k alone
    later = games.with_columns(num=pl.when(c("season") == max(SEASONS)).then(0.0)
                               .otherwise(c("num")))  # fmt: skip
    rows2 = T.season_rows(later, world[1], T.BY_NAME["qb_sack_rate"])
    p2 = T.pairs(rows2, later)
    k1 = p.group_by("season").agg(c("k").first()).sort("season")
    k2 = p2.group_by("season").agg(c("k").first()).sort("season")
    assert np.allclose(k1["k"].to_numpy(), k2["k"].to_numpy())


def test_pooled_k_uses_every_group(world):
    games, teams, _, _ = world
    teams2 = teams.with_columns(
        position=pl.when(c("pid").str.slice(1).cast(pl.Int32) % 2 == 0).then(pl.lit("DE"))
        .otherwise(pl.lit("OLB")))  # fmt: skip
    games2 = games.with_columns(trait=pl.lit("press_rate"))
    games2 = pl.concat([games2, games2.with_columns(trait=pl.lit("on_dropbacks"),
                                                    num=c("den"))])  # fmt: skip
    rows = T.season_rows(games2, teams2, T.BY_NAME["press_rate"])
    dl = rows.filter(c("group") == "DL")
    alone, pooled = T.pairs(dl, games2), T.pairs(dl, games2, rows)
    assert alone.height == pooled.height
    assert not np.allclose(alone["k"].to_numpy(), pooled["k"].to_numpy())
    full = T.pairs(rows, games2)
    k_full = full.group_by("season").agg(c("k").first()).sort("season")["k"].to_numpy()
    k_pool = pooled.group_by("season").agg(c("k").first()).sort("season")["k"].to_numpy()
    assert np.allclose(k_full, k_pool)


def test_rungs_shrink_by_chances_and_stayers_have_no_team_change(world):
    games, _, _, rows = world
    p = T.rungs(T.pairs(rows, games))
    m1 = p["n"] / (p["n"] + p["k"]) * p["x"]
    assert np.allclose(p["m1"].to_numpy(), m1.to_numpy())
    assert (p.filter(~c("moved"))["team_change"] == 0).all()
    assert p["avg"].abs().max() == 0


def test_gain_is_zero_for_the_same_forecast_and_one_for_a_perfect_one():
    p = pl.DataFrame({"gsis_id": ["a", "b", "c", "d"], "y": [0.1, -0.2, 0.3, 0.0],
                      "w": [1.0, 2.0, 1.0, 3.0], "base": [0.0] * 4})  # fmt: skip
    p = p.with_columns(same=c("base"), perfect=c("y"))
    assert E.gain(p, "same", "base", draws=50).share == pytest.approx(0.0)
    g = E.gain(p, "perfect", "base", draws=50)
    assert g.share == pytest.approx(1.0) and g.clear()


def test_shrinking_beats_the_raw_rate_and_the_ranges_cover(world):
    games, _, _, rows = world
    q = E.scored(T.rungs(T.pairs(rows, games)))
    assert E.gain(q, "m1", "raw", draws=200).clear()
    rr = E.range_report(q, "m1")
    assert 0.65 < rr["coverage"] < 0.95
    assert rr["range_gain"] > 0


def test_pinball_is_zero_when_every_quantile_is_the_outcome():
    y = np.array([1.0, 2.0])
    assert np.allclose(E.pinball(y, y, y, y), 0)
    assert (E.pinball(y, y - 1, y, y + 1) > 0).all()


def test_the_published_rows(world):
    games, _, true, rows = world
    p = T.walk(rows, games)
    at = [datetime(s + 1, 2, 15, tzinfo=UTC) for s in SEASONS]
    known = pl.DataFrame({"season": list(SEASONS), "known_at": at})
    h = H.rows_for(rows, games, p, "m1", "player", 0.9, known)
    assert h.height == rows.height
    assert ((h["reliability"] > 0) & (h["reliability"] < 1)).all()
    assert ((h["shrunk_lo"] < h["shrunk"]) & (h["shrunk"] < h["shrunk_hi"])).all()
    assert h["next_q10"].is_nan().sum() == 0  # no range is null, never NaN
    assert h["next_q10"].null_count() > 0  # the first seasons have no earlier pairs
    fc = h.drop_nulls("next_q10")
    assert ((fc["next_q10"] < fc["next_c"]) & (fc["next_c"] < fc["next_q90"])).all()
    assert (h["as_of"] == h["train_end"]).all() and h["as_of"].null_count() == 0
    assert set(h["cadence"].unique()) == {"retrospective"}
    # the shrunk rate sits closer to the truth than the raw rate, on the whole
    tr = h["gsis_id"].replace_strict(true, return_dtype=pl.Float64)
    assert ((h["shrunk"] - tr) ** 2).mean() < ((h["rate"] - tr) ** 2).mean()


def test_kept_label():
    assert E.kept_label(0.6) == "player"
    assert E.kept_label(0.3) == "team"
    assert E.kept_label(float("nan")) == "team"
