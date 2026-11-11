"""Player pace between seasons (`pcf.experts.player_pace_retro`; decision 0029): the contract,
and the features use only earlier seasons, decayed."""

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from pcf.core.contract import check_expert, find_all
from pcf.experts.player_pace_retro import model as R

c = pl.col


def test_every_variant_meets_the_contract():
    retro = {x.variant for x in find_all("player-pace-retro")}
    assert retro == {f"{m}_{v}" for m in R.MEASURES for v in ("group", "last", "shrunk")}
    for cls in find_all("player-pace-retro"):
        check_expert(cls)
        assert cls.cadence == "retrospective"
    assert [b.variant for b in R.VARIANTS["proe_shrunk"].baselines()] == [
        "proe_group", "proe_last",
    ]  # fmt: skip


def _season_rows() -> pl.DataFrame:
    rows = [
        ("te", 2019, "TE", 0.30, 100.0), ("te", 2020, "TE", 0.10, 50.0),
        ("te", 2021, "TE", 0.20, 80.0), ("te", 2022, "TE", 9.0, 80.0),
        ("rb", 2021, "RB", None, 0.0),
    ]  # fmt: skip
    df = pl.DataFrame(
        rows, schema=["gsis_id", "season", "onf_group", "onf_pm_proe", "onf_w_proe"], orient="row"
    )
    return df.with_columns(
        c("season").cast(pl.Int32),
        onf_pm_proe_pers=c("onf_pm_proe"),
        onf_pm_pace=pl.lit(None, pl.Float64),
        onf_w_pace=pl.lit(0.0),
    )


def test_features_use_earlier_seasons_only_with_decay():
    f = R.season_features(_season_rows(), 2022)
    te = f.filter(c("gsis_id") == "te").row(0, named=True)
    assert te["season"] == 2022 and te["group"] == "TE" and te["seasons_seen"] == 3
    w = [100 * 0.7**2, 50 * 0.7, 80.0]
    assert te["proe_w"] == pytest.approx(sum(w))
    assert te["proe_wd"] == pytest.approx(0.30 * w[0] + 0.10 * w[1] + 0.20 * w[2])
    assert te["proe_last"] == pytest.approx(0.20) and te["proe_last_w"] == pytest.approx(80.0)
    # the season itself (9.0) never enters; nor a later one
    later = _season_rows().with_columns(
        onf_pm_proe=pl.when(c("season") >= 2022).then(-5.0).otherwise(c("onf_pm_proe"))
    )
    assert_frame_equal(f, R.season_features(later, 2022))
    rb = f.filter(c("gsis_id") == "rb").row(0, named=True)
    assert rb["proe_w"] == 0.0 and rb["proe_last"] is None
