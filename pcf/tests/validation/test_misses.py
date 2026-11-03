"""Where a model misses (miss-lenses): a planted pattern is found, noise isn't, and every report
is dated."""

import numpy as np
import polars as pl
import pytest

from pcf.data.gateway import FrameSource
from pcf.data.tags.catalog import BEFORE, TAGS
from pcf.validation import misses
from pcf.validation.misses import LENS_LIST, LENSES, METHOD, Lens, lens_frame, report

c = pl.col
POSITIONS = ["QB", "RB", "WR", "TE"]


def _world(seed: int = 1) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Player-games over 8 seasons with misses of pure noise, except +2 points for a planted
    group and for rookies."""
    rng = np.random.default_rng(seed)
    rows = [
        (f"P{p:03d}", f"{s}_{w:02d}_{p // 2:03d}", s, w, POSITIONS[p % 4])
        for s in range(2016, 2024) for w in range(1, 18) for p in range(80)
    ]  # fmt: skip
    frame = pl.DataFrame(
        rows, schema=["gsis_id", "game_id", "season", "week", "position"], orient="row"
    )
    n = frame.height
    frame = frame.with_columns(
        planted=pl.Series(rng.random(n) < 0.2),
        noise_id=pl.Series(rng.integers(0, 600, n)).cast(pl.String),
        tag_rookie=pl.Series(rng.random(n) < 0.1),
        tag_revenge_game=pl.Series(rng.random(n) < 0.1),
        offense_pct=pl.Series(rng.random(n)),
    )
    shift = (frame["planted"].cast(pl.Float64) + frame["tag_rookie"].cast(pl.Float64)) * 2
    scored = frame.select(
        "gsis_id", "game_id",
        mean=pl.lit(10.0),
        y=pl.Series(10 + shift + rng.normal(0, 5, n)),
    )  # fmt: skip
    return scored, frame


PLANTED = Lens("planted", "before", "a planted group", lambda d: c("planted").cast(pl.String),
               ("planted",))  # fmt: skip
NOISE = Lens("noise", "before", "600 groups of noise", lambda d: c("noise_id"), ("noise_id",))


@pytest.fixture(scope="module")
def m():
    scored, frame = _world()
    return report(scored, frame, lenses=[*LENSES, PLANTED, NOISE])


def _lens(m, name: str) -> dict:
    return m.lenses.filter(c("lens") == name).row(0, named=True)


def test_a_planted_lens_is_found(m):
    planted = _lens(m, "planted")
    assert planted["bias_share"] > 0.02
    assert planted["top_group"] == "true"
    # +2 planted, +0.2 from the rookies among them, give or take the noise
    assert planted["lo"] > 1.7 and planted["hi"] < 2.9


def test_noise_in_many_small_groups_is_not_rewarded(m):
    """Learned on the other half of the seasons, corrections for noise make misses worse."""
    assert _lens(m, "noise")["bias_share"] < 0.005
    assert _lens(m, "snap_share")["bias_share"] < 0.005


def test_a_tag_that_is_off_is_flagged_and_a_noise_tag_is_not(m):
    flagged = m.flagged["lens"].to_list()
    assert "tag_rookie" in flagged and "tag_revenge_game" not in flagged
    rookie = m.flagged.filter(c("lens") == "tag_rookie").row(0, named=True)
    assert rookie["top_group"] == "true" and rookie["avg_miss"] > 1.2  # vs the model's average


def test_lenses_without_their_inputs_are_listed_not_guessed(m):
    assert {"depth", "team_points", "margin", "qb_efficiency"} <= set(m.skipped)
    assert "snap_share" not in m.skipped


def test_after_game_lenses_are_labelled_diagnostic():
    fixed = {lens.name: lens.when for lens in LENSES}
    assert fixed == {"position": "before", "depth": "before", "week": "before",
                     "snap_share": "after", "team_points": "after", "margin": "after",
                     "qb_efficiency": "after"}  # fmt: skip
    timing = {t.column: t.timing for t in TAGS}
    for lens in misses._tag_lenses():
        assert lens.when == ("before" if timing[lens.name] in BEFORE else "after"), lens.name


def test_every_report_is_dated(m, tmp_path):
    out = m.frame("run1")
    assert (out["lens_list"] == LENS_LIST).all() and (out["method"] == METHOD).all()
    assert (out["run_id"] == "run1").all() and out["measured_at"].null_count() == 0
    assert set(out["kind"]) == {"fixed", "flagged"}
    path = misses.save(m, tmp_path, "run1")
    assert pl.read_parquet(path).height == out.height


def test_the_lens_frame_reads_what_the_source_has():
    roster = pl.DataFrame({
        "gsis_id": ["A", "B"], "game_id": ["G1", "G1"], "season": [2023, 2023], "week": [1, 1],
        "team": ["KC", "BUF"], "position": ["WR", "QB"],
    })  # fmt: skip
    sched = pl.DataFrame({"game_id": ["G1"], "home_team": ["KC"]})
    result = pl.DataFrame({"game_id": ["G1"], "home_score": [31], "away_score": [10]})
    frame = lens_frame(FrameSource({
        ("player_game", "roster"): roster, ("game", "schedule"): sched, ("game", "result"): result,
    }))  # fmt: skip
    got = dict(zip(frame["team"], zip(frame["team_points"], frame["margin"], strict=True),
                   strict=True))  # fmt: skip
    assert got == {"KC": (31, 21), "BUF": (10, -21)}
    assert "depth" not in frame.columns
