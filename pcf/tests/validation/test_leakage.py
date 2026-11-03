"""Every blocking leakage check catches its planted leak and passes its honest twin (offline, on
the synthetic league in world.py)."""

from datetime import UTC, datetime

import polars as pl
import pytest

from pcf.core.contract import Expert
from pcf.data.gateway import Gateway
from pcf.validation import backtest, leakage
from pcf.validation.toy import RecentPoints

from . import planted, world

c = pl.col
TEST = [2022, 2023]
CUTS = 8


@pytest.fixture(scope="module")
def gw():
    return world.gateway()


def run(expert: Expert, gw: Gateway, **kw) -> backtest.Backtest:
    return backtest.run(expert, gw, TEST, half_life=None, **kw)


@pytest.fixture(scope="module")
def honest(gw):
    return run(RecentPoints(), gw)


@pytest.fixture(scope="module")
def cuts(gw):
    return leakage.cutoffs(gw.calendar, TEST, CUTS, seed=1)


# --- 1 and 7: the code ------------------------------------------------------------------------


def test_reading_around_the_gateway_is_caught_in_the_code():
    problems, _ = leakage.scan_code(planted.GATEWAY_LEAK)
    assert any("pcf.data.tables" in p for p in problems)
    assert any("read_parquet" in p for p in problems)
    assert leakage.scan_code(planted.GATEWAY_HONEST) == ([], [])


def test_random_splitters_are_caught_in_the_code():
    _, splitters = leakage.scan_code(planted.SPLITTER_LEAK)
    assert any("model_selection" in p for p in splitters)
    assert any("train_test_split" in p for p in splitters)
    assert leakage.scan_code(planted.SPLITTER_HONEST) == ([], [])


def test_the_toy_expert_code_passes_checks_1_and_7(honest):
    assert leakage.gateway_only_check(honest.expert).passed
    assert leakage.walk_forward_check(honest).passed


def test_a_prediction_trained_after_it_was_made_fails_check_7(honest):
    late = honest.history.with_columns(train_end=c("as_of") + pl.duration(days=1))
    bt = backtest.Backtest(**{**vars(honest), "history": late})
    assert not leakage.walk_forward_check(bt).passed


# --- 2 ----------------------------------------------------------------------------------------


def test_results_known_before_kickoff_fail_check_2(gw):
    assert leakage.known_at_sanity(RecentPoints(), gw).passed
    stats = world.frames()[("player_game", "stats")]
    early = stats.with_columns(known_at=c("known_at") - pl.duration(hours=30))
    bad = world.gateway(**{"player_game.stats": early})
    check = leakage.known_at_sanity(RecentPoints(), bad)
    assert not check.passed and "before kickoff" in check.detail


# --- 3 and 4 ----------------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["scramble", "delete"])
def test_honest_features_pass_the_future_checks(gw, honest, cuts, mode):
    assert leakage.future_check(honest, gw, cuts, mode).passed


@pytest.mark.parametrize("mode", ["scramble", "delete"])
def test_an_honest_bulk_version_passes_and_matches_per_moment(gw, cuts, mode):
    bt = run(planted.HonestBulk(), gw)  # per-moment features in the backtest
    check = leakage.future_check(bt, gw, cuts, mode)
    assert check.passed, check.detail


@pytest.mark.parametrize(
    "leaky", [planted.CurrentGameBulk, planted.EarlierGamesBulk], ids=["current", "monday"]
)
@pytest.mark.parametrize("mode", ["scramble", "delete"])
def test_leaky_bulk_features_fail_the_future_checks(gw, cuts, leaky, mode):
    bt = run(leaky(), gw)
    check = leakage.future_check(bt, gw, cuts, mode)
    assert not check.passed


def test_the_monday_night_leak_is_only_monday_night(gw):
    """ "Earlier games" differs from "known at the moment" only for players whose last game was
    a Monday night (validation-harness#F2)."""
    every = backtest.steps(gw.calendar, "in_season", TEST)
    games = pl.concat([s.games for s in every])
    view = gw.view(datetime(2100, 1, 1, tzinfo=UTC), "in_season", RecentPoints.inputs)
    honest = planted.HonestBulk().features_history(view, games)
    leaky = planted.EarlierGamesBulk().features_history(view, games)
    diff = honest.join(leaky, on=["gsis_id", "game_id"], suffix="_l").filter(
        c("last4") != c("last4_l")
    )
    monday_teams = world.schedules().filter(c("slot") == 2)
    assert diff.height > 0
    prev = diff.select("gsis_id", "game_id").join(
        world.frames()[("player_game", "roster")].select("gsis_id", "game_id", "team", "week"),
        on=["gsis_id", "game_id"],
    )
    played_monday = prev.join(
        monday_teams.select(
            team=pl.concat_list("home_team", "away_team"), season="season", week=c("week") + 1
        ).explode("team"),
        on=["team", "week"],
        how="semi",
    )
    assert played_monday.height == prev.height


@pytest.mark.parametrize("mode", ["scramble", "delete"])
def test_reading_around_the_view_fails_the_future_checks(gw, cuts, mode):
    bt = run(planted.AroundTheView(), gw)
    assert not leakage.future_check(bt, gw, cuts, mode).passed


# --- 5 ----------------------------------------------------------------------------------------


def _misstamped_on_field():
    """Participation stamped as known the day after each game: wrong, as a source bug might be."""
    f = world.frames()
    on_field = f[("player_play", "on_field")].join(
        f[("game", "schedule")].select("game_id", "kickoff"), on="game_id"
    )
    return on_field.with_columns(known_at=c("kickoff") + pl.duration(days=1)).drop("kickoff")


class NoSeasonRule(Gateway):
    """A gateway that forgot the post-season rule (every season counts as finished)."""

    def finished(self, at):
        return world.SEASONS


def test_post_season_data_stays_hidden_in_season_even_when_misstamped(cuts):
    bad_data = world.gateway(**{"player_play.on_field": _misstamped_on_field()})
    bt = run(planted.OnField(), bad_data)
    assert leakage.cadence_check(bt.expert, bad_data, cuts).passed


def test_a_gateway_without_the_season_rule_fails_check_5(cuts):
    parts = world.frames()
    parts[("player_play", "on_field")] = _misstamped_on_field()
    from pcf.data.gateway import FrameSource

    broken = NoSeasonRule(FrameSource(parts), world.cal())
    check = leakage.cadence_check(planted.OnField(), broken, cuts)
    assert not check.passed and "unfinished season" in check.detail


def test_a_cadence_other_than_the_registry_fails_check_5(gw, cuts):
    class Elo(RecentPoints):
        id = "elo"  # in_season in the registry
        cadence = "retrospective"

    assert not leakage.cadence_check(Elo(), gw, cuts).passed


# --- 6 ----------------------------------------------------------------------------------------


def _upstream(train_late: bool):
    def outputs(project_id, version):
        as_of = datetime(2022, 10, 4, 14, tzinfo=UTC)
        end = datetime(2023, 3, 1, tzinfo=UTC) if train_late else datetime(2022, 10, 3, tzinfo=UTC)
        return pl.DataFrame(
            {"team": ["AAA"], "season": [2022], "as_of": [as_of], "train_end": [end],
             "mean": [0.6], "cadence": ["in_season"]},
            schema_overrides={"as_of": pl.Datetime("us", "UTC"),
                              "train_end": pl.Datetime("us", "UTC")},
        )  # fmt: skip

    return outputs


class UsesElo(RecentPoints):
    inputs = {"player_game": ("stats",), "elo": 1}


@pytest.mark.parametrize("late", [False, True])
def test_outputs_from_a_model_trained_later_fail_check_6(honest, late):
    gw = Gateway(world.gateway().source, world.cal(), _upstream(late))
    bt = backtest.Backtest(**{**vars(honest), "expert": UsesElo()})
    assert leakage.vintage_check(bt, gw).passed is not late


# --- 8 ----------------------------------------------------------------------------------------


def test_honest_refits_ignore_the_test_results(gw, honest):
    assert leakage.test_label_check(honest, gw, n_steps=3).passed


def test_a_model_that_keeps_every_outcome_fails_check_8(gw):
    bt = run(planted.CachedOutcomes(), gw)
    check = leakage.test_label_check(bt, gw, n_steps=3)
    assert not check.passed


# --- 10 ---------------------------------------------------------------------------------------


def test_a_feature_that_is_the_outcome_is_flagged(gw, honest):
    assert leakage.too_good(honest).passed
    flagged = leakage.too_good(run(planted.Peeks(), gw))
    assert not flagged.passed and not flagged.blocking and "peek" in flagged.detail


# --- the suite --------------------------------------------------------------------------------


def test_the_suite_passes_the_toy_and_names_every_blocking_check(gw, honest):
    checks = leakage.run_checks(honest, gw, n_cutoffs=CUTS)
    assert [ch.number for ch in checks] == [1, 2, 3, 4, 5, 6, 7, 8, 10]
    assert all(ch.passed for ch in checks), [ch for ch in checks if not ch.passed]
    assert set(leakage.results(checks)) == {
        "gateway_only", "known_at_sanity", "future_perturbation", "future_deletion", "cadence",
        "vintage", "walk_forward", "test_labels",
    }  # fmt: skip


def test_cutoffs_cover_the_calendar_moments(gw):
    cuts = leakage.cutoffs(gw.calendar, TEST, 25, seed=3)
    labels = [label for label, _ in cuts]
    assert len(cuts) == 25
    for name in ("week 1", "mid-season", "playoffs", "free agency", "draft", "combine"):
        assert any(name in label for label in labels), name
