"""The expert contract: checked against the registry, and the standard output schema."""

from datetime import UTC, datetime

import polars as pl
import pytest

from pcf.core.contract import OUTPUT_SCHEMA, check_expert, check_output, find
from pcf.validation.toy import LastFour, RecentPoints

c = pl.col


def test_the_toy_expert_meets_the_contract_and_is_found_by_id():
    check_expert(RecentPoints)
    assert find("validation-harness") is RecentPoints  # its baseline isn't listed under the id


def test_unknown_ids_are_refused():
    with pytest.raises(KeyError):
        find("no-such-model")


class Elo(RecentPoints):
    id = "elo"  # in the registry: in_season, depends on grain-tables and validation-harness
    grain = "team_game"
    inputs = {"team_game": ("result",)}


def test_a_model_matching_its_registry_entry_passes():
    check_expert(Elo)


@pytest.mark.parametrize(
    "change, message",
    [
        ({"cadence": "retrospective"}, "registry"),
        ({"cadence": "weekly"}, "cadence"),
        ({"grain": "team_week"}, "grain"),
        ({"run": "sunday"}, "run"),
        ({"inputs": {"team_game": ("nope",)}}, "no parts"),
        ({"inputs": {"team_game": ("tags",)}}, "tag-tables"),
        ({"inputs": {"team_game": ("result",), "team-efficiency": 2}}, "team-efficiency"),
        ({"kind": "rank"}, "kind"),
        ({"run": "kickoff"}, "only a benchmark"),
    ],
)
def test_contract_problems_are_named(change, message):
    bad = type("Bad", (Elo,), change)
    with pytest.raises(ValueError, match=message):
        check_expert(bad)


def test_a_benchmark_may_run_at_kickoff():
    check_expert(type("Close", (Elo,), {"run": "kickoff", "benchmark": True}))


def test_a_model_that_skips_a_model_it_depends_on_is_refused():
    class GameScript(Elo):
        id = "game-script"  # depends on elo, team-efficiency and pace
        inputs = {"team_game": ("result",), "elo": 1}

    with pytest.raises(ValueError, match="team-efficiency"):
        check_expert(GameScript)


def output(**changes):
    at = datetime(2024, 11, 5, 15, tzinfo=UTC)
    row = {
        "gsis_id": "00-1", "game_id": "2024_10_DEN_KC", "as_of": at, "quantity": "ppr_points",
        "mean": 12.0, "q10": 5.0, "q50": 11.0, "q90": 20.0, "model": "toy", "model_version": "1",
        "run_id": "r", "train_end": at, "cadence": "in_season",
    }  # fmt: skip
    row |= changes
    return pl.DataFrame([row]).with_columns(*(c(k).cast(v) for k, v in OUTPUT_SCHEMA.items()))


def test_a_standard_output_passes():
    check_output(output(), ["gsis_id", "game_id"])


@pytest.mark.parametrize(
    "change",
    [
        {"train_end": datetime(2025, 1, 1, tzinfo=UTC)},
        {"q10": 30.0},
        {"q90": None},
        {"gsis_id": None},
    ],
)
def test_bad_outputs_are_refused(change):
    with pytest.raises(ValueError):
        check_output(output(**change), ["gsis_id", "game_id"])


def test_probabilities_need_only_a_mean():
    check_output(output(q10=None, q50=None, q90=None, mean=0.4), ["gsis_id", "game_id"],
                 "probability")  # fmt: skip


def test_the_baseline_shares_the_toy_s_contract():
    assert LastFour.keys() == RecentPoints.keys() == ["gsis_id", "game_id"]
    assert RecentPoints.tables() == {"player_game": ("stats",)}
    assert RecentPoints.upstream() == {}
