"""Walk-forward splits and the backtest runner, on the synthetic league."""

from datetime import UTC, datetime

import polars as pl
import pytest

from pcf.config import get_config
from pcf.validation import backtest
from pcf.validation.splits import assert_walk_forward, steps
from pcf.validation.toy import LastFour, RecentPoints

from . import world

c = pl.col
TEST = [2022, 2023]


@pytest.fixture(scope="module")
def gw():
    return world.gateway()


@pytest.fixture(scope="module")
def bt(gw):
    return backtest.run(RecentPoints(), gw, TEST)


def test_in_season_steps_are_weeks_in_time_order(gw):
    s = steps(gw.calendar, "in_season", world.SEASONS)
    assert len(s) == len(world.SEASONS) * (world.WEEKS + 1)
    assert [x.at for x in s] == sorted(x.at for x in s)
    for x in s:
        assert x.at == x.games["moment"].min()
        assert (x.games["moment"] < x.games["kickoff"]).all()


def test_retrospective_and_event_steps_are_one_per_season(gw):
    retro = steps(gw.calendar, "retrospective", world.SEASONS)
    draft = steps(gw.calendar, "offseason_events", world.SEASONS, event="draft")
    assert [x.season for x in retro] == world.SEASONS == [x.season for x in draft]
    assert all(x.at < x.games["kickoff"].min() for x in retro)


def test_the_history_is_standard_and_every_prediction_trained_on_its_past(bt):
    h = bt.history
    assert h.height and h.filter(c("y").is_not_null()).height
    assert h.filter(c("train_end") > c("as_of")).is_empty()
    assert set(h["model"]) == {"validation-harness"}
    seasons = bt.features.join(h.select("gsis_id", "game_id"), on=["gsis_id", "game_id"])
    assert set(seasons["step_season"]) == set(TEST)


def test_the_toy_learns_from_skill(bt):
    """The synthetic points follow each player's skill, so the toy should get close to the noise
    (pinball ≈ 0.8 for normal noise with sd 4, against about 3 for a constant guess)."""
    assert bt.scored["loss"].mean() < 1.4


def test_predictions_don_t_change_when_later_outcomes_are_removed(gw, bt):
    later = bt.targets.join(
        bt.features.filter(c("step_season") == 2023).select("gsis_id", "game_id"),
        on=["gsis_id", "game_id"],
        how="anti",
    )
    first = [s for s in bt.test if s < min(x for x in bt.test) + 3]
    a = backtest.walk(bt.expert, bt.features, bt.targets, bt.steps, first)
    b = backtest.walk(bt.expert, bt.features, later, bt.steps, first)
    assert a.sort("gsis_id", "game_id").equals(b.sort("gsis_id", "game_id"))


def test_a_training_row_from_the_future_stops_the_walk():
    at = datetime(2022, 10, 1, tzinfo=UTC)
    train = pl.DataFrame(
        {"as_of": [datetime(2022, 10, 2, tzinfo=UTC)], "known_at": [at]}
    ).with_columns(c("as_of", "known_at").cast(pl.Datetime("us", "UTC")))
    with pytest.raises(AssertionError):
        assert_walk_forward(train, at)


def test_the_vault_stays_closed_unless_opened(gw):
    vault = get_config().seasons.vault
    with pytest.raises(backtest.VaultClosed):
        backtest.check_seasons([vault - 1, vault], open_vault=False)
    backtest.check_seasons([vault], open_vault=True)
    with pytest.raises(ValueError, match="live"):
        backtest.check_seasons([get_config().seasons.live], open_vault=True)
    assert backtest.test_seasons()[-1] == vault - 1


def test_refit_once_a_season_uses_one_model_per_season(gw, bt):
    seasonal = backtest.run(RecentPoints(), gw, TEST, refit="season")
    per_season = (
        seasonal.history.join(
            seasonal.features.select("gsis_id", "game_id", "step_season"),
            on=["gsis_id", "game_id"],
        )
        .group_by("step_season")
        .agg(c("train_end").n_unique())
    )
    assert per_season["train_end"].to_list() == [1, 1]


def test_a_baseline_with_the_same_features_walks_the_same_rows(bt):
    pred = backtest.walk(LastFour(), bt.features, bt.targets, bt.steps, bt.test)
    assert pred.height == bt.history.height
    assert (pred["mean"] == pred.join(bt.features, on=["gsis_id", "game_id"])["last4"]).all()


def test_write_history_saves_the_standard_schema(tmp_path, bt):
    path = backtest.write_history(bt, "run123", tmp_path)
    saved = pl.read_parquet(path)
    assert path == tmp_path / "validation-harness" / "run123" / "history.parquet"
    assert set(saved["run_id"]) == {"run123"}
    assert "y" not in saved.columns and "loss" not in saved.columns
