"""td-expert (decision 0043): the variants, the rest-of-season window and the Poisson fits."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import polars as pl
import pytest

from pcf.core.contract import check_expert
from pcf.experts.td_expert import model as M

T0 = datetime(2024, 9, 10, tzinfo=UTC)


def test_every_variant_passes_the_contract():
    assert len(M.VARIANTS) >= 18
    for name, cls in M.VARIANTS.items():
        check_expert(cls)
        assert cls.variant == name and cls.kind == "count"
    for family in ("skill", "thrown", "team"):
        for horizon in ("next", "rest"):
            chances = M.VARIANTS[f"{family}_{horizon}_chances"]
            names = {b.variant for b in chances.baselines()}
            assert names == {f"{family}_{horizon}_rate", f"{family}_{horizon}_volume"}


def _schedule() -> pl.DataFrame:
    rows = []
    for week in (1, 2, 3):
        rows += [dict(game_id=f"g{week}", season=2024, team="A", week=week, game_type="REG"),
                 dict(game_id=f"g{week}", season=2024, team="B", week=week, game_type="REG")]  # fmt: skip
    rows.append(dict(game_id="p1", season=2024, team="A", week=19, game_type="WC"))
    return pl.DataFrame(rows)


def test_window_sum_counts_missed_games_as_zero_and_skips_playoffs():
    known = pl.DataFrame({
        "gsis_id": ["x", "x", "y", "y", "y", "x"],
        "game_id": ["g1", "g3", "g1", "g2", "g3", "p1"],
        "season": [2024] * 6, "week": [1, 3, 1, 2, 3, 19], "team": ["A"] * 6,
        "td": [1.0, 2.0, 0.0, 1.0, 1.0, 5.0],
        "known_at": [T0] * 6,
    })  # fmt: skip
    out = M.window_sum(known, _schedule(), "td", "gsis_id").sort("gsis_id", "game_id")
    got = {(r["gsis_id"], r["game_id"]): r["y"] for r in out.iter_rows(named=True)}
    assert got[("x", "g1")] == 3.0  # weeks 1-3, week 2 missed counts 0, the playoff game not in
    assert got[("x", "g3")] == 2.0
    assert got[("y", "g2")] == 2.0
    assert ("x", "p1") not in got


def test_window_sum_leaves_out_windows_not_yet_known():
    known = pl.DataFrame({"gsis_id": ["x", "x"], "game_id": ["g1", "g2"], "season": [2024] * 2,
                          "week": [1, 2], "team": ["A", "A"], "td": [1.0, 0.0],
                          "known_at": [T0, T0]})  # fmt: skip
    assert M.window_sum(known, _schedule(), "td", "gsis_id").is_empty()  # week 3 not played


def test_stage_one_reads_the_next_rows_last_value():
    train = pl.DataFrame({"gsis_id": ["x", "x", "x"], "game_id": ["g1", "g2", "g3"],
                          "last_game_id": [None, "g1", "g2"], "last_xtd": [None, 0.4, 0.9]})  # fmt: skip
    out = M.stage_one(train, "gsis_id", "last_xtd").sort("game_id")
    assert out["game_id"].to_list() == ["g1", "g2"]  # g3's own game isn't known to its successor
    assert out["y1"].to_list() == [0.4, 0.9]


def test_stage_one_keeps_the_training_order():
    """The penalty is picked on the latest 20% by position: a row order that changed from run to
    run changed the fit (leakage check 8 caught it on thrown touchdowns)."""
    n = 2_000
    rng = np.random.default_rng(0)
    ids = [f"p{i % 40}" for i in range(n)]
    games = [f"g{i:05d}" for i in range(n)]
    lasts = [None, *games[:-1]]
    train = pl.DataFrame({"gsis_id": ids, "game_id": games, "last_game_id": lasts,
                          "last_xtd": rng.uniform(0, 1, n)})  # fmt: skip
    for _ in range(3):
        out = M.stage_one(train, "gsis_id", "last_xtd")
        assert out["game_id"].to_list() == sorted(out["game_id"].to_list())


def test_poisson_fit_recovers_a_rate_with_exposure():
    rng = np.random.default_rng(1)
    n = 20_000
    x = rng.normal(size=(n, 1))
    e = rng.integers(1, 6, n).astype(float)
    y = rng.poisson(e * np.exp(-1.0 + 0.5 * x[:, 0])).astype(float)
    model = M.fit_poisson(x, y, np.ones(n), e)
    mean = M.predict_poisson(model, x, e)
    assert mean.sum() == pytest.approx(y.sum(), rel=0.02)
    lo, hi = mean[x[:, 0] < -1].mean() / e[x[:, 0] < -1].mean(), mean[x[:, 0] > 1].mean() / e[
        x[:, 0] > 1].mean()  # fmt: skip
    assert hi > 2.5 * lo  # exp(0.5 * ~3 apart) is about 4.5; regularized, still well above


def test_ranges_are_ordered():
    r = M.ranges(np.array([0.0, 0.3, 2.5, 20.0]))
    assert (r["q10"] <= r["q50"]).all() and (r["q50"] <= r["q90"]).all()


# ---------------------------------------------------------------- "Yes, where calibrated" (I116)
def _rows():
    return pl.DataFrame({
        "gsis_id": ["qb", "rb1", "rb2", "rb3", "wr", "te1", "te2"],
        "game_id": ["g"] * 7,
        "position": ["QB", "RB", "RB", "RB", "WR", "TE", "TE"],
        "games_left": [3.0, 5.0, 8.0, 14.0, 2.0, 1.0, 12.0],
    })  # fmt: skip


def test_windows_by_games_left():
    assert M.window_of(np.array([1, 5, 6, 11, 12, 17])).tolist() == [
        "1-5", "1-5", "6-11", "6-11", "12+", "12+"]  # fmt: skip


def test_chances_are_published_only_in_the_calibrated_cells():
    rows = _rows()
    spread = {k: (0.5, 1.5) for k in M.spread_cells(rows)}
    out = M.chances(rows, np.full(rows.height, 2.0), spread)
    one = ~np.isnan(out["p_one"])
    two = ~np.isnan(out["p_two"])
    # QB rushing: average only; RB 1-5 both; RB 6-11 and 12+ none; WR 1-5 1+ only;
    # TE 1-5 both; TE 12+ none
    assert one.tolist() == [False, True, False, False, True, True, False]
    assert two.tolist() == [False, True, False, False, False, True, False]
    assert (out["p_two"][two] < out["p_one"][two]).all()
    assert (out["alpha"] == 0.5).all() and (out["q10"] <= out["q90"]).all()


def test_a_cell_without_a_spread_fit_publishes_nothing_and_falls_back_to_poisson():
    rows = _rows()
    out = M.chances(rows, np.full(rows.height, 2.0), {})
    assert np.isnan(out["p_one"]).all() and (out["alpha"] == 0).all()


def test_the_champion_outputs_the_count_parts_with_nulls_where_unpublished():
    from pcf.core.contract import COUNT_PARTS, check_count_parts

    champ = M.VARIANTS["skill_rest_volume+qb_rz"]()
    assert champ.spread and not M.VARIANTS["skill_rest_volume"].spread
    rows = _rows()
    out = champ._out(rows, np.full(rows.height, 2.0), {k: (0.4, 1.2) for k in M.spread_cells(rows)})
    assert set(COUNT_PARTS) <= set(out.columns)
    assert out["p_one"].null_count() == 4 and out["p_two"].null_count() == 5
    check_count_parts(out)
    with pytest.raises(ValueError, match="p_two"):
        check_count_parts(out.with_columns(p_two=pl.col("p_one") + 0.1))
    with pytest.raises(ValueError, match="where p_one"):
        check_count_parts(out.with_columns(p_one=pl.lit(None, pl.Float64)))


def test_the_spread_is_fit_on_the_latest_rows_per_cell():
    rng = np.random.default_rng(3)
    n = 4_000
    pos = rng.choice(["RB", "WR"], n)
    left = rng.integers(1, 17, n).astype(float)
    mu = rng.uniform(0.5, 6.0, n)
    k = 1 / 0.6
    y = rng.negative_binomial(k, k / (k + mu)).astype(float)
    cells = M.spread_cells(pl.DataFrame({"position": pos, "games_left": left}))
    fits = M.fit_spreads(mu, y, cells)
    assert set(fits) == set(cells)
    assert all(0.2 < a < 1.5 for a, _ in fits.values())
