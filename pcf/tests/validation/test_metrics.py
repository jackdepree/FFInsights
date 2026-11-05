"""Scores, the "beats" comparison, the signal test, calibration and sanity rules."""

import numpy as np
import polars as pl
import pytest

from pcf.validation import calibration, nulls, sanity, scores
from pcf.validation.backtest import run
from pcf.validation.compare import block_interval, compare
from pcf.validation.toy import RecentPoints

from . import world

c = pl.col


# --- scores ---------------------------------------------------------------------------------


def test_pinball_and_the_amount_scores():
    df = pl.DataFrame({"y": [10.0], "q10": [4.0], "q50": [8.0], "q90": [14.0]})
    out = scores.row_losses(df, "amount")
    # q10: 0.1 * 6 = 0.6; q50: 0.5 * 2 = 1.0; q90: (0.9 - 1) * -4 = 0.4
    assert out["loss"][0] == pytest.approx((0.6 + 1.0 + 0.4) / 3)
    assert out["readable"][0] == 2.0


def test_log_loss_brier_and_hit_rate():
    df = pl.DataFrame({"y": [1.0, 0.0], "mean": [0.8, 0.3]})
    out = scores.row_losses(df, "probability")
    assert out["loss"].to_list() == pytest.approx([-np.log(0.8), -np.log(0.7)])
    assert out["readable"].to_list() == pytest.approx([0.04, 0.09])
    assert scores.summary(out, "probability")["hit_rate"] == 1.0


def test_points_gained_and_rank_correlation():
    df = pl.DataFrame(
        {"week": [1] * 4, "ours": [4, 3, 2, 1], "ecr": [1, 2, 3, 4], "pts": [20, 15, 5, 0]}
    )
    gained = scores.points_gained(df, "ours", "ecr", "pts", ["week"], n=2)
    assert gained["gained"].to_list() == [35 - 5]
    rho = scores.rank_correlation(df, "ours", "pts", ["week"])
    assert rho["rho"][0] == pytest.approx(1.0)


# --- beats ----------------------------------------------------------------------------------


def frame(losses, steps):
    return pl.DataFrame({"k": range(len(losses)), "step": steps, "loss": losses})


def test_a_clearly_better_model_beats_and_an_equal_one_ties():
    rng = np.random.default_rng(0)
    steps = np.repeat(np.arange(30), 20)
    base = rng.uniform(1, 2, steps.size)
    better = compare(frame(base - 0.2, steps), frame(base, steps), ["k"])
    assert better.beats and better.verdict == "better" and better.hi < 0
    same = compare(frame(base, steps), frame(base, steps), ["k"])
    assert same.diff == 0 and same.verdict == "tie"
    noisy = compare(frame(base + rng.normal(0, 0.5, base.size), steps), frame(base, steps), ["k"])
    assert noisy.lo < 0 < noisy.hi


def test_the_block_interval_resamples_whole_blocks():
    sums, counts = np.array([10.0, -10.0]), np.array([10.0, 10.0])
    lo, hi = block_interval(sums, counts, draws=500, seed=1)
    assert lo == -1.0 and hi == 1.0  # only whole blocks: all-first, all-second or mixed


# --- signal ---------------------------------------------------------------------------------


@pytest.mark.parametrize("noise_only, passes", [(False, True), (True, False)])
def test_the_signal_test_finds_skill_and_not_noise(noise_only, passes):
    bt = run(RecentPoints(), world.gateway(noise_only=noise_only), [2022, 2023])
    result = nulls.signal_test(bt, n=20, seed=3)
    assert result.needed == 20
    assert result.passed is passes


def test_the_signal_bar():
    assert nulls.needed(100) == 95 and nulls.needed(20) == 20


def test_no_noise_verdicts():
    steps = np.repeat(np.arange(30), 10)
    base = np.random.default_rng(1).uniform(1, 2, steps.size)
    assert nulls.no_noise(frame(base - 0.3, steps), frame(base, steps), ["k"])[0] == "adds value"
    assert nulls.no_noise(frame(base + 0.3, steps), frame(base, steps), ["k"])[0] == "adds noise"
    assert nulls.no_noise(frame(base, steps), frame(base, steps), ["k"])[0] == "neutral"


# --- calibration ----------------------------------------------------------------------------


def probs(n=20_000, sharpen=1.0, seed=0):
    rng = np.random.default_rng(seed)
    p = rng.uniform(0.02, 0.98, n)
    y = (rng.uniform(size=n) < p).astype(float)
    logit = np.log(p / (1 - p)) * sharpen
    return pl.DataFrame({"mean": 1 / (1 + np.exp(-logit)), "y": y})


def test_honest_probabilities_are_calibrated():
    report = calibration.probability_report(probs())
    assert report["error"] < 1.5 and 0.95 < report["slope"] < 1.05 and report["passed"]


def test_over_confident_probabilities_fail_on_slope():
    report = calibration.probability_report(probs(sharpen=1.6))
    assert report["slope"] < 0.9 and not report["passed"]


def test_range_coverage_overall_and_by_group():
    rng = np.random.default_rng(2)
    y = rng.normal(0, 1, 4000)
    df = pl.DataFrame(
        {"y": y, "q10": -1.2816, "q50": 0.0, "q90": 1.2816, "g": ["a", "b"] * 1999 + ["c", "c"]}
    )
    out = calibration.coverage(df, ["g"])
    assert 0.78 < out["inside"] < 0.82 and out["passed"]
    small = out["groups"].filter(c("value") == "c")
    assert not small["judged"][0] and small["ok"][0]  # under 200 rows: shown, not judged
    narrow = calibration.coverage(df.with_columns(q10=pl.lit(-0.5), q90=pl.lit(0.5)), ["g"])
    assert not narrow["passed"]


# --- sanity ---------------------------------------------------------------------------------


def test_sanity_rules_count_violations():
    df = pl.DataFrame(
        {
            "team": ["A", "A", "B"],
            "q10": [1.0, 5.0, 0.0],
            "q50": [2.0, 4.0, 1.0],
            "q90": [3.0, 6.0, 2.0],
            "yards": [10.0, -1.0, 0.0],
            "share": [0.6, 0.6, 0.5],
            "mean": [0.5, 0.5, 1.2],
        }
    )
    out = sanity.run_rules(
        df,
        [
            sanity.quantiles_ordered(),
            sanity.non_negative("yards"),
            sanity.shares_at_most_one("share", ["team"]),
            sanity.probabilities_valid(),
            sanity.sums_to_one("mean", ["team"]),
        ],
    )
    assert out["violations"].to_list() == [1, 1, 1, 1, 1]
    top, bottom = sanity.review_lists(df, ["team"], by="yards", n=1)
    assert top["yards"][0] == 10.0 and bottom["yards"][0] == -1.0


def _spike_rows(stretch: float, width: float, n: int = 20000) -> pl.DataFrame:
    """Each row's real chance of a result above 0 varies, and results above 0 spread evenly around
    0.6. `stretch` above 1 overstates how sure the chance is; `width` is the stated range's
    half-width."""
    rng = np.random.default_rng(3)
    real = rng.uniform(0.3, 0.95, n)
    y = np.where(rng.random(n) < real, 0.6 + rng.uniform(-0.3, 0.3, n), 0.0)
    logit = np.log(real / (1 - real)) * stretch
    return pl.DataFrame({
        "y": y, "p_nonzero": 1 / (1 + np.exp(-logit)),
        "q10": np.zeros(n), "q50": np.full(n, 0.5), "q90": np.full(n, 0.84),
        "if_nonzero_q10": np.full(n, 0.6 - width), "if_nonzero_q50": np.full(n, 0.6),
        "if_nonzero_q90": np.full(n, 0.6 + width),
    })  # fmt: skip


def test_an_honest_spike_forecast_passes_though_its_blend_over_covers():
    report = calibration.spike_report(_spike_rows(1.0, 0.24))
    assert report["chance"]["passed"] and report["share"]["passed"] and report["passed"]
    assert report["blend"]["inside"] > 0.85 and not report["blend"]["passed"]


def test_a_spike_forecast_fails_on_either_bad_part():
    sure = calibration.spike_report(_spike_rows(2.0, 0.24))  # too sure of who plays
    assert not sure["chance"]["passed"] and sure["share"]["passed"] and not sure["passed"]
    narrow = calibration.spike_report(_spike_rows(1.0, 0.05))  # too narrow if they do
    assert narrow["chance"]["passed"] and not narrow["share"]["passed"] and not narrow["passed"]
