"""participation-late: FTN's inputs and the model's extra columns, on small synthetic rows."""

import numpy as np
import polars as pl

from pcf.experts.participation_late import ftn
from pcf.experts.participation_live import model

c = pl.col


def _play(rows):
    cols = ["game_id", "play_id", *ftn.RAW]
    return pl.DataFrame(rows, schema=cols, orient="row")


def test_features_centre_cap_and_drop_uncharted_plays():
    p = _play([
        ("g", 1, 2, 6, 4, 0, True, False, False),
        ("g", 2, 7, 12, 0, 9, False, True, True),
        ("g", 3, None, None, None, None, None, None, None),  # not charted
    ])  # fmt: skip
    f = ftn.features(p).sort("play_id")
    assert f["play_id"].to_list() == [1, 2]
    a, b = f.row(0, named=True), f.row(1, named=True)
    assert (a["bf"], a["box"], a["rush"], a["blitz"], a["motion"]) == (1.0, 0.0, 1.0, 0.0, 1.0)
    assert (b["bf"], b["box"], b["blitz"], b["pa"], b["screen"]) == (2.0, 3.0, 4.0, 1.0, 1.0)


def test_join_marks_uncharted_plays_missing():
    g = pl.DataFrame({"game_id": ["g"] * 3, "play_id": [1, 2, 3], "x": [0, 0, 0]})
    p = _play([("g", 1, 2, 6, 4, 0, True, False, False)])
    out = ftn.join(g, ftn.features(p)).sort("play_id")
    assert out["fmiss"].to_list() == [0.0, 1.0, 1.0]
    assert out["bf"].to_list() == [1.0, 0.0, 0.0]
    assert set(ftn.COLUMNS) <= set(out.columns)


def test_fit_learns_an_extra_column():
    """A back's chance rises with the backfield count when the data say so."""
    rng = np.random.default_rng(0)
    n = 6000
    bf = rng.integers(-1, 3, n).astype(float)
    share = rng.uniform(0.2, 0.8, n)
    on = (rng.random(n) < 1 / (1 + np.exp(-(np.log(share / (1 - share)) + 1.5 * bf)))).astype(int)
    rows = pl.DataFrame({
        "game_id": [f"g{i // 60}" for i in range(n)], "side": "offense", "team": "KC",
        "gsis_id": [f"p{i % 3}" for i in range(n)], "n": [i % 60 for i in range(n)],
        "season": 2023, "group": "RB", "share": share, "on": on, "bf": bf,
        "drive_n": 0, "ph_n": 0.0, "named": False, "full": False,
    })  # fmt: skip
    rows = rows.with_columns(
        *[pl.lit(False).alias(f) for f in model.FLAG_COLUMNS],
        *[pl.lit(0.0).alias(f"ph_{k}") for k in model.FLAGS],
        *[pl.lit(0.0).alias(f"th_{k}") for k in model.FLAGS],
        pn=pl.lit(0.0),
    )
    old = model.MIN_ROWS
    model.MIN_ROWS = 100
    try:
        m = model.fit(model.cell_columns(rows), "history", extra=["bf"])
    finally:
        model.MIN_ROWS = old
    assert m.base_columns[-1] == "bf"
    assert m.explain()["RB"]["bf"] > 1.0
