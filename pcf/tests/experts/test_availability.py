"""availability (decision 0047): the variants' contract, and the models' pieces on small worlds."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from pcf.core.contract import check_expert
from pcf.experts.availability import experts as X
from pcf.experts.availability import models as M
from pcf.experts.availability.common import part_group, practice_code
from pcf.experts.availability.measures import agl, weights

T0 = datetime(2024, 9, 10, tzinfo=UTC)


def test_every_variant_passes_the_contract():
    assert len(X.VARIANTS) == 20
    for name, cls in X.VARIANTS.items():
        check_expert(cls)
        assert cls.variant == name
        assert cls.grain == "roster_week" and cls.run == "saturday"
    for h in ("next3", "rest"):
        for m in ("table", "two", "chain", "chain_trees", "hmm"):
            assert X.VARIANTS[f"{h}_{m}"].spike


def test_report_codes():
    df = pl.DataFrame({"p": ["Did Not Participate In Practice", "Limited Participation in Practice",
                             "Full Participation in Practice", None],
                       "b": ["Hamstring", "right Knee", "Not injury related - resting player", None]})  # fmt: skip
    out = df.select(practice_code(pl.col("p")).alias("p"), part_group(pl.col("b")).alias("b"))
    assert out["p"].to_list() == [2, 1, 0, None]
    assert out["b"].to_list() == ["hamstring", "knee", "not_injury", None]


def test_distribution_summary_reads_a_count():
    d = np.array([[0.7, 0.2, 0.1, 0.0], [0.0, 0.0, 0.0, 1.0]])
    s = M.distribution_summary(d)
    assert np.allclose(s["mean"], [0.4, 3.0])
    assert s["q10"].tolist() == [0, 3] and s["q50"].tolist() == [0, 3] and s["q90"].tolist() == [1, 3]
    assert np.allclose(s["p_nonzero"], [0.3, 1.0])
    assert np.allclose(s["if_nonzero_mean"], [(0.2 + 0.2) / 0.3, 3.0])
    assert np.allclose(s["p_nonzero"] * s["if_nonzero_mean"], s["mean"])


def test_empirical_dist_maps_shares_to_the_window():
    out = M.empirical_dist(np.array([0.0, 0.5, 1.0]), np.array([2, 4]))
    assert out[0].tolist()[:3] == [1, 1, 1]  # 0, 1, 2 of 2 games
    assert out[1].tolist() == [1, 0, 1, 0, 1]  # 0, 2, 4 of 4


def test_table_model_shrinks_thin_cells_to_their_parent():
    df = pl.DataFrame({"a": ["x"] * 100 + ["y"] * 2, "y": [0.0] * 50 + [1.0] * 50 + [1.0, 1.0],
                       "weight": [1.0] * 102})  # fmt: skip
    m = M.TableModel([("a",)], m=20).fit(df)
    p = m.predict(pl.DataFrame({"a": ["x", "y", "z"]}))
    assert p[0] == pytest.approx((50 + 20 * m.overall) / 120)
    assert m.overall < p[1] < 1.0  # two rows can't move it far from the whole
    assert p[2] == pytest.approx(m.overall)


def _pool(n_players=60, weeks=10, seed=0):
    """A small world: each player is healthy (h) until a random week, then out (o) for two
    games (absent), then healthy again. Rows carry what the features would."""
    rng = np.random.default_rng(seed)
    rows = []
    for p in range(n_players):
        hurt = int(rng.integers(2, weeks - 2))
        states = ["h"] * weeks
        states[hurt] = states[hurt + 1] = "o"
        absent = [s == "o" for s in states]
        for w in range(1, weeks + 1):
            i = w - 1
            dur = 1
            while i - dur >= 0 and states[i - dur] == states[i]:
                dur += 1
            rows.append(dict(
                gsis_id=f"p{p}", game_id=f"g{w}_{p}", season=2024, week=w,
                next_week=w + 1 if w < weeks else None, last_week=w - 1 if w > 1 else 0,
                state=states[i], dur=float(dur), last_absent=float(absent[i - 1]) if w > 1 else 0.0,
                as_of=T0 + timedelta(days=7 * w), weight=1.0, grp="WR",
                obs_seq="".join("6" if a else "0" for a in absent[:i]),
                prac_seq="".join("2" if a else "3" for a in absent[:i]),
                practice=2.0 if states[i] == "o" else 0.0,
                no_practice=0.0 if states[i] == "o" else 1.0,
                f1=float(rng.normal()), n_window=float(min(3, weeks - i)),
            ))  # fmt: skip
    return pl.DataFrame(rows)


def test_next_pairs_reads_the_next_row():
    pool = _pool(n_players=3, weeks=6)
    pairs = M.next_pairs(pool)
    last = pairs.filter(pl.col("week") == 6)
    assert last["n_state"].null_count() == 3  # no next week in the pool
    hurt = pool.filter(pl.col("state") == "o").sort("week").group_by("gsis_id").first()
    got = pairs.join(hurt.select("gsis_id", "week"), on=["gsis_id", "week"])
    assert (got["n_state"] == "o").all() and (got["absent_now"] == 1).all()


def test_chain_learns_a_two_game_absence():
    pool = _pool()
    chain = M.Chain(["f1", "dur"], ["f1"]).fit(pool)
    rows = pool.filter((pl.col("state") == "o") & (pl.col("dur") == 1)).head(5)
    d = chain.distribution(rows.with_columns(n_window=pl.lit(3.0)))
    s = M.distribution_summary(d)
    # out now with one more game to go: about 2 absences in 3
    assert np.all(np.abs(s["mean"] - 2.0) < 0.35)


def test_hmm_fits_and_rolls_forward():
    pool = _pool()
    h = M.Hmm(k=3, iters=10).fit(pool)
    rows = pool.filter(pl.col("week") == 5).with_columns(n_window=pl.lit(3.0))
    d = h.distribution(rows)
    assert d.shape == (rows.height, 4) and np.allclose(d.sum(axis=1), 1.0)
    s = M.distribution_summary(d)
    out_now = rows["state"].to_numpy() == "o"
    assert s["mean"][out_now].mean() > s["mean"][~out_now].mean()


def test_agl_weights_use_only_earlier_games():
    rows = []
    for w, (played, share, absent) in enumerate([(True, 0.9, False), (True, 0.5, False),
                                                 (False, 0.0, True)], start=1):  # fmt: skip
        rows.append(dict(gsis_id="a", game_id=f"g{w}", team="A", season=2024, week=w,
                         position="WR", played=played, share=share, absent=absent))  # fmt: skip
    tl = pl.DataFrame(rows)
    w = weights(tl).sort("week")
    assert w["weight"][1] == pytest.approx(0.9) and w["weight"][2] == pytest.approx(0.7)
    a = agl(tl)
    assert a.filter(pl.col("game_id") == "g3")["agl"][0] == pytest.approx(0.7)
