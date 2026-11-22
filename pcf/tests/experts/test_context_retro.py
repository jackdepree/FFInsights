"""context-retro: the play table's rules, the provider rule, the ladder, the walk on synthetic
plays, the blame split and the season priors (no data)."""

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from pcf.experts.context_retro import outcomes, plays, priors, run, split

c = pl.col
T0 = datetime(2016, 9, 1, tzinfo=UTC)


def test_a_sack_counts_as_a_pressure():
    d = pl.DataFrame({"sack_y": [1.0, 1.0, 0.0, 0.0], "was_pressure": [None, 0.0, 1.0, None]})
    out = plays.with_pressure(d)["pressure_y"].to_list()
    # the old provider leaves the flag empty on sacks; an unflagged non-sack stays missing
    assert out == [1.0, 1.0, 1.0, None]


def test_zero_rushers_with_an_empty_box_is_uncharted():
    d = pl.DataFrame({"n_pass_rushers": [0.0, 0.0, 4.0], "n_defense_box": [2.0, 6.0, 1.0]})
    assert plays.uncharted_rushers(d)["n_pass_rushers"].to_list() == [None, 0.0, 4.0]


def test_coverage_is_one_column_per_code_and_missing_when_not_charted():
    part = pl.DataFrame({
        "game_id": ["g"] * 3, "play_id": [1, 2, 3], "was_pressure": [1, 0, None],
        "time_to_throw": [2.5, None, 3.0], "number_of_pass_rushers": [4, 5, None],
        "defenders_in_box": [6, 7, 6], "defense_coverage_type": ["COVER_3", None, "COVER_9"],
        "defense_man_zone_type": ["ZONE_COVERAGE", None, "MAN_COVERAGE"], "known_at": [T0] * 3,
    })  # fmt: skip
    out = plays.participation_fields(part)
    assert out["cov_COVER_3"].to_list() == [1.0, None, 0.0]
    assert out["cov_COVER_9"].to_list() == [0.0, None, 1.0]
    assert out["man"].to_list() == [0.0, None, 1.0]


def test_dropback_outcomes_read_coverage_only_from_2023_and_gaps_are_filled():
    later = T0 + timedelta(days=200)
    d = pl.DataFrame({
        "season": [2022, 2023], "as_of": [T0, T0], "known_at": [T0, T0],
        "known_at_targets": [later, None], "rushers_p": [None, 5.0], "box_p": [None, 7.0],
        **{x: [1.0, 1.0] for x in plays.COVERAGE},
    })  # fmt: skip
    out = plays.retro_columns(d)
    # the old provider leaves coverage empty on every sack: dropback outcomes don't read it
    assert out["dcov_COVER_3"].to_list() == [None, 1.0]
    assert out["cov_COVER_3"].to_list() == [1.0, 1.0]
    assert out["rushers_p"].to_list() == [plays.RUSHERS_FILL, 5.0]
    assert out["box_p"].to_list() == [plays.BOX_FILL, 7.0]
    # known once participation is out
    assert out["as_of"].to_list() == [later, T0]


def test_fields_by_population():
    assert set(plays.COVERAGE) <= set(plays.fields_for("attempt"))
    assert not set(plays.COVERAGE) & set(plays.fields_for("dropback"))
    assert set(plays.DROPBACK_COVERAGE) <= set(plays.fields_for("dropback"))
    sack = outcomes.BY_NAME["sack"]
    assert run.BY_RUNG["e1-2-trees"].field_list(sack)[-1] == plays.CONDITION
    assert run.BY_RUNG["e1-0-pressure"].field_list(sack) == [plays.CONDITION]
    assert run.BY_RUNG["e0-0-base"].field_list(sack) == []


def test_provider_rule():
    p, s = outcomes.BY_NAME["pressure"], outcomes.BY_NAME["sack"]
    assert run.train_window(p, "e0", 2023) == (2016, 2022)
    assert run.train_window(p, "e0", 2024) == (2023, 2023)
    assert run.train_window(p, "e0", 2025) == (2023, 2024)
    # the play-by-play's sack before the snap uses every earlier season; given the pressure, the
    # provider's
    assert run.train_window(s, "e0", 2024) == (2016, 2023)
    assert run.train_window(s, "e1", 2024) == (2023, 2023)
    assert run.train_window(s, "e1", 2020) == (2016, 2019)


def test_outcomes_and_quantities():
    assert [o.name for o in outcomes.OUTCOMES] == [
        "pressure",
        "time_to_throw",
        "sack",
        "air_yards",
        "completion",
        "dropback_yards",
    ]
    assert "pressure" not in outcomes.GIVEN
    assert outcomes.quantity("sack", "e1") == "sack_e1"
    assert [r.name for r in run.rungs_for(outcomes.BY_NAME["pressure"])] == list(run.LADDERS["e0"])
    assert max(run.TEST_SEASONS) == 2024  # the vault stays closed


def synthetic(n_per_season: int = 1500, seasons=range(2016, 2021), seed: int = 0) -> pl.DataFrame:
    """Dropbacks where a pressure raises the sack chance from 2% to 20% and shotgun lowers the
    pressure chance: E1 must beat E0 by a lot, and E0 must beat the mean a little."""
    rng = np.random.default_rng(seed)
    rows = []
    for s in seasons:
        n = n_per_season
        shot = rng.integers(0, 2, n).astype(float)
        pres = (rng.random(n) < np.where(shot == 1, 0.2, 0.45)).astype(float)
        sack = (rng.random(n) < np.where(pres == 1, 0.2, 0.02)).astype(float)
        week = rng.integers(1, 18, n)
        frame = {
            "game_id": [f"{s}_{w:02d}_g{i % 8}" for i, w in enumerate(week)],
            "play_id": np.arange(n), "season": np.full(n, s, dtype=np.int32),
            "season_type": ["REG"] * n, "week": week.astype(np.int32),
            "posteam": [f"T{i % 4}" for i in range(n)], "defteam": [f"D{i % 4}" for i in range(n)],
            "passer_id": [f"Q{i % 4}" for i in range(n)],
            "known_at": [datetime(s, 12, 1, tzinfo=UTC)] * n,
            "known_at_targets": [datetime(s + 1, 2, 10, tzinfo=UTC)] * n,
            "as_of": [datetime(s + 1, 2, 10, tzinfo=UTC)] * n,
            "is_dropback": [True] * n, "is_attempt": list(sack == 0),
            "pressure_y": pres, "time_to_throw_y": 2.7 + 0.3 * pres, "sack_y": sack,
            "air_yards_y": rng.normal(8, 5, n), "complete_y": (rng.random(n) < 0.65) * 1.0,
            "yards": rng.normal(6, 9, n),
        }  # fmt: skip
        for f in plays.FIELDS:
            frame[f] = (rng.integers(0, 3, n).astype(float) if f not in models_cat()
                        else pl.Series(f, ["S"] * n, pl.String))  # fmt: skip
        frame["shotgun"] = shot
        rows.append(pl.DataFrame(frame))
    return pl.concat(rows, how="diagonal_relaxed").select(plays.COLUMNS)


def models_cat():
    from pcf.experts.context_live import models

    return models.CATEGORIES


def test_the_walk_on_synthetic_plays_finds_the_pressure():
    data = synthetic()
    sack = outcomes.BY_NAME["sack"]
    frame, fitted = run.walk(data, sack, [2019, 2020], run.rungs_for(sack))
    # E1 rows only where the pressure is known; every train_end before the rows' as_of
    assert frame["e1-0-pressure:mean"].null_count() == 0
    assert all(end < datetime(2020, 2, 10, tzinfo=UTC) for (s, _), (_, end) in fitted.items()
               if s == 2019)  # fmt: skip
    top0, _ = run.ladder(frame, "e0")
    top1, _ = run.ladder(frame, "e1")
    # the pressure alone carries the given-pressure mode; the noise fields add nothing to it
    assert top1 == "e1-0-pressure"
    assert run.loss_gain(frame, top1, top0) > 10
    assert run.share_removed(frame, "e1-0-pressure") > 5


def test_the_null_shuffles_within_weeks():
    d = pl.DataFrame({"season": [1] * 6, "week": [1, 1, 1, 2, 2, 2], "y": [1, 2, 3, 10, 20, 30]})
    out = run.shuffle_outcomes(3)(d)
    assert sorted(out.filter(c("week") == 1)["y"].to_list()) == [1, 2, 3]
    assert sorted(out.filter(c("week") == 2)["y"].to_list()) == [10, 20, 30]


def history_for(data: pl.DataFrame) -> pl.DataFrame:
    e0 = data.select(*plays.KEYS, "season", "week", "as_of", quantity=pl.lit("sack_e0"),
                     mean=pl.lit(0.06))  # fmt: skip
    e1 = data.filter(c("pressure_y").is_not_null()).select(
        *plays.KEYS, "season", "week", "as_of", quantity=pl.lit("sack_e1"),
        mean=pl.when(c("pressure_y") == 1).then(0.2).otherwise(0.02))  # fmt: skip
    out = pl.concat([e0, e1]).with_columns(
        q10=c("mean"), q50=c("mean"), q90=c("mean"), model=pl.lit("context-retro"),
        model_version=pl.lit("x"), run_id=pl.lit("r"), cadence=pl.lit("retrospective"),
        train_end=pl.lit(datetime(2000, 1, 1, tzinfo=UTC)))  # fmt: skip
    return out


def test_the_split_adds_up_to_the_sack_over_expected():
    data = synthetic(300, seasons=[2018])
    data = data.with_columns(pressure_y=pl.when(c("play_id") == 0).then(None)
                             .otherwise(c("pressure_y")))  # fmt: skip
    hist = history_for(data)
    rows = run.split_rows(hist, data)
    assert set(rows["quantity"].unique()) == {"sack_pressure_part", "sack_after_part"}
    parts = split.play_parts(hist, data)
    both = parts.filter(c("split"))
    assert both.height == data.height - 1  # the play with no pressure flag has E0 only
    gap = (both["pressure_part"] + both["after_part"] - (both["sack_y"] - both["sack_e0"])).abs()
    assert float(gap.max()) < 1e-12
    linemen = pl.DataFrame({"game_id": data["game_id"][:5], "play_id": data["play_id"][:5],
                            "gsis_id": ["OL1"] * 5})  # fmt: skip
    pg = split.player_game(parts, linemen)
    ol = pg.filter(c("role") == "lineman")
    assert int(ol["dropbacks"].sum()) == 5
    qb = pg.filter(c("role") == "passer")
    assert int(qb["dropbacks"].sum()) == data.height
    assert float(qb["sacks"].sum()) == float(data["sack_y"].sum())


def test_season_priors_are_shrunk_and_only_used_once_known():
    data = synthetic(400, seasons=[2018, 2019])
    hist = history_for(data)
    exp = priors.expectations(hist, {"sack": "sack_e0"})
    rates = priors.season_rates(data, exp, "passer_id")
    q0 = rates.filter((c("passer_id") == "Q0") & (c("season") == 2018))
    d0 = data.filter((c("passer_id") == "Q0") & (c("season") == 2018))
    want = float((d0["sack_y"] - 0.06).sum()) / (d0.height + priors.SHRINK)
    assert q0["sack_oe"].item() == pytest.approx(want)
    # no expectation for an outcome: missing, not 0
    assert q0["pressure_oe"].item() is None
    feats = pl.DataFrame({
        "gsis_id": ["Q0", "Q0"], "game_id": ["a", "b"], "season": [2019, 2019],
        "as_of": [datetime(2019, 2, 1, tzinfo=UTC), datetime(2019, 9, 7, tzinfo=UTC)],
    })  # fmt: skip
    out = priors.attach(feats, rates, "passer_id", ["gsis_id", "game_id"], "retro")
    # 2018's priors are known on 2019-02-10: not on a row before that moment
    assert out.sort("game_id")["retro_sack_oe"].to_list() == [None, pytest.approx(want)]
