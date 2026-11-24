"""The count kind (decision 0043): its scores, calibration and output check."""

from __future__ import annotations

import math
from datetime import UTC, datetime

import numpy as np
import polars as pl
import pytest

from pcf.core.contract import KINDS, check_output
from pcf.validation import calibration, scores


def test_count_is_a_kind_with_its_scores():
    assert "count" in KINDS
    assert scores.MAIN["count"] == "poisson_log_loss"
    assert scores.READABLE["count"] == "squared_error"


def test_poisson_log_loss_is_minus_log_probability():
    df = pl.DataFrame({"y": [0.0, 2.0, 1.0], "mean": [0.5, 1.5, 0.0]})
    got = df.select(scores.poisson_log_loss().alias("l"))["l"].to_list()
    want = [0.5, -(2 * math.log(1.5) - 1.5 - math.log(2)), None]
    assert got[0] == pytest.approx(want[0]) and got[1] == pytest.approx(want[1])
    assert math.isfinite(got[2])  # a zero mean is clipped, not infinite


def test_row_losses_for_counts():
    df = pl.DataFrame({"y": [1.0], "mean": [1.0]})
    out = scores.row_losses(df, "count")
    assert out["loss"][0] == pytest.approx(1.0) and out["readable"][0] == 0.0


def test_poisson_at_least():
    assert scores.poisson_at_least(np.array([1.0]), 1)[0] == pytest.approx(1 - math.exp(-1))
    assert scores.poisson_at_least(np.array([1.0]), 2)[0] == pytest.approx(1 - 2 * math.exp(-1))


def test_count_report_passes_honest_poisson_and_fails_a_doubled_mean():
    rng = np.random.default_rng(0)
    lam = rng.uniform(0.05, 2.0, 40_000)
    y = rng.poisson(lam).astype(float)
    from scipy.stats import poisson

    def frame(m):
        return pl.DataFrame({"mean": m, "y": y, "q10": poisson.ppf(0.1, m),
                             "q50": poisson.ppf(0.5, m), "q90": poisson.ppf(0.9, m)})  # fmt: skip

    honest = calibration.count_report(frame(lam))
    assert honest["count"] and honest["passed"]
    assert honest["one"]["error"] < 1.0
    assert not calibration.count_report(frame(2 * lam))["passed"]


def test_check_output_orders_count_quantiles():
    t = datetime(2024, 9, 1, tzinfo=UTC)
    row = {"gsis_id": ["a"], "quantity": ["td"], "as_of": [t], "train_end": [t], "mean": [0.5],
           "q10": [0.0], "q50": [0.0], "q90": [1.0], "model": ["m"], "version": ["v"]}  # fmt: skip
    from pcf.core.contract import OUTPUT_SCHEMA

    df = pl.DataFrame(row).with_columns(
        [pl.col(k).cast(v) for k, v in OUTPUT_SCHEMA.items() if k in row]
    )
    missing = {k: v for k, v in OUTPUT_SCHEMA.items() if k not in df.columns}
    df = df.with_columns([pl.lit(None, dtype=v).alias(k) for k, v in missing.items()])
    check_output(df, ["gsis_id"], "count")
    with pytest.raises(ValueError, match="quantiles"):
        check_output(df.with_columns(q10=pl.lit(2.0)), ["gsis_id"], "count")
