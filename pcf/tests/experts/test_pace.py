"""Pace (`pcf.experts.pace`): the contract, per-moment features equal to the bulk ones, no future
games in a feature, and backtests on a synthetic league whose teams have real habits."""

from datetime import timedelta

import numpy as np
import polars as pl
import pytest
from polars.testing import assert_frame_equal

from pcf.core.contract import check_expert, find_all
from pcf.data.gateway import END_OF_TIME, FrameSource, Gateway
from pcf.data.tables.pace import DEFENSE, OFFENSE
from pcf.experts.pace import features as F
from pcf.experts.pace.model import VARIANTS
from pcf.validation import backtest
from pcf.validation.splits import steps

from ..validation import world

c = pl.col
UTC_T = pl.Datetime("us", "UTC")
# each team's true pass rate over expected and pace over expected (seconds; negative is fast)
PROE = dict(zip(world.TEAMS, [0.08, -0.08, 0.05, -0.05, 0.02, -0.02], strict=True))
PACE = dict(zip(world.TEAMS, [-3.0, 3.0, -2.0, 2.0, -1.0, 1.0], strict=True))
SEASONS = [2022, 2023]


def _frames(seed: int = 7, noise_only: bool = False) -> dict:
    sched = world.frames()[("game", "schedule")]
    sides = pl.concat(
        [
            sched.select("game_id", "season", "week", "game_type", "kickoff", "known_at",
                         team=c(a), opponent=c(b), home=pl.lit(a == "home_team"))
            for a, b in (("home_team", "away_team"), ("away_team", "home_team"))
        ]
    ).sort("game_id", "team")  # fmt: skip
    rng = np.random.default_rng(seed)
    n = sides.height
    proe = np.array([0.0 if noise_only else PROE[t] for t in sides["team"]])
    fast = np.array([0.0 if noise_only else PACE[t] for t in sides["team"]])
    spread = rng.normal(0, 5, n)
    # a fast team runs more plays, a passing team drops back more; favorites run more
    plays = np.rint(64 - 2.0 * fast + rng.normal(0, 6, n))
    pass_share = np.clip(0.58 + proe + 0.004 * spread + rng.normal(0, 0.05, n), 0.2, 0.9)
    dropbacks = np.rint(plays * pass_share)
    drives = rng.integers(9, 14, n)
    known = (sides["kickoff"] + pl.duration(hours=24)).cast(UTC_T)
    ints = lambda x: pl.Series(x).cast(pl.Int32)  # noqa: E731
    paced = sides.select("game_id", "team", "season").with_columns(
        plays=ints(plays), dropbacks=ints(dropbacks), runs=ints(plays - dropbacks),
        drives=ints(drives), plays_per_drive=pl.Series(plays / drives),
        proe=pl.Series(proe + rng.normal(0, 0.06, n)),
        proe_1st=pl.Series(proe + rng.normal(0, 0.09, n)),
        proe_2nd=pl.Series(proe + rng.normal(0, 0.10, n)),
        proe_3rd=pl.Series(0.5 * proe + rng.normal(0, 0.10, n)),
        downs_1st=ints(rng.integers(25, 32, n)), downs_2nd=ints(rng.integers(18, 24, n)),
        downs_3rd=ints(rng.integers(11, 16, n)),
        exp_pass_rate=pl.Series(rng.normal(0.58, 0.04, n)),
        pace_oe=pl.Series(fast + rng.normal(0, 2.0, n)), pace_snaps=ints(rng.integers(40, 60, n)),
        no_huddle=pl.Series(np.clip(0.08 - 0.02 * fast + rng.normal(0, 0.05, n), 0, 1)),
        epa_per_play=pl.Series(rng.normal(0, 0.15, n)),
        known_at=known,
    )  # fmt: skip
    # the defense's columns: what the opponent's offense did against it
    opp = paced.select(
        "game_id", c("team").alias("opponent_side"),
        def_plays="plays", def_dropbacks_all="dropbacks", def_runs="runs", def_drives="drives",
        def_plays_per_drive="plays_per_drive", def_proe="proe", def_pace_oe="pace_oe",
        def_pace_snaps="pace_snaps", def_epa_per_play="epa_per_play",
    )  # fmt: skip
    paced = (
        paced.join(sides.select("game_id", "team", "opponent"), on=F.KEYS)
        .join(opp, left_on=["game_id", "opponent"], right_on=["game_id", "opponent_side"])
        .select("game_id", "team", "season", *OFFENSE, *DEFENSE, "known_at")
    )
    tendencies = sides.select("game_id", "team", "season").with_columns(
        neutral_plays=ints(rng.integers(20, 50, n)),
        neutral_pass_oe=pl.Series(proe + rng.normal(0, 0.08, n)),
        tempo_plays=ints(rng.integers(5, 20, n)),
        tempo_seconds=pl.Series(30 + 0.5 * fast + rng.normal(0, 3, n)),
        known_at=known,
    )
    pregame = sides.select(
        "game_id", "team", "season",
        coach=pl.concat_str(pl.lit("Coach "), c("team")),
        spread=pl.Series(-spread), total_line=pl.lit(44.0),
        known_at=(c("kickoff") - pl.duration(days=3)).cast(UTC_T),
    )  # fmt: skip
    first = sides.filter(c("game_type") == "REG").group_by("season", "team").agg(c("week").min())
    start = sides.group_by("season").agg(c("kickoff").min().alias("first_kick"))
    opening = (
        sides.join(first, on=["season", "team", "week"], how="semi")
        .join(start, on="season")
        .select(
            "game_id", "team", "season",
            opening_coach=pl.concat_str(pl.lit("Coach "), c("team")),
            known_at=(c("first_kick") - pl.duration(days=3)).cast(UTC_T),
        )
    )  # fmt: skip
    return {
        ("game", "schedule"): sched,
        ("team_game", "schedule"): sides,
        ("team_game", "pregame"): pregame,
        ("team_game", "opening_coach"): opening,
        ("team_game", "tendencies"): tendencies,
        ("team_game", "pace"): paced,
    }


def _gateway(**kw) -> Gateway:
    return Gateway(FrameSource(_frames(**kw)), world.cal())


def test_every_variant_meets_the_contract():
    assert {x.variant for x in find_all("pace")} == set(VARIANTS)
    habits = {f"{h}_{p}" for h in F.HABITS for p in ("league", "last4", "season", "shrunk")}
    volume = {
        f"{v}_{p}" for v in F.VOLUME for p in ("league", "season", "last_season", "neutral", "full")
    }
    assert set(VARIANTS) == habits | volume
    for cls in VARIANTS.values():
        check_expert(cls)
    assert [b.variant for b in VARIANTS["plays_full"].baselines()] == [
        "plays_neutral", "plays_season", "plays_last_season",
    ]  # fmt: skip


@pytest.mark.parametrize("variant", ["proe_shrunk", "plays_full"])
def test_per_moment_features_equal_the_bulk_ones(variant):
    gw = _gateway()
    ex = VARIANTS[variant]()
    every = steps(gw.calendar, ex.cadence, world.SEASONS, ex.run)
    bulk = ex.features_history(
        gw.view(END_OF_TIME, ex.cadence, ex.inputs), pl.concat([s.games for s in every])
    )
    seen = 0
    for s in every:
        for (moment,), frame in s.games.group_by("moment", maintain_order=True):
            one = ex.features(gw.view(moment, ex.cadence, ex.inputs), frame.drop("moment"))
            other = bulk.join(one.select(F.KEYS), on=F.KEYS)
            assert_frame_equal(one.sort(F.KEYS), other.sort(F.KEYS), rel_tol=1e-9)
            seen += one.height
    assert seen == bulk.height > 0


def test_a_feature_never_uses_the_game_itself_or_later_ones():
    """Change every pace measure from one game on: that game's features stay the same, for the
    team and its opponent."""
    frames = _frames()
    sched = frames[("team_game", "schedule")]
    cut = sched.filter((c("season") == 2022) & (c("week") == 3))["kickoff"].min()
    later = sched.filter(c("kickoff") >= cut).select("game_id", "team")
    late = later.with_columns(late=pl.lit(True))
    changed = dict(frames)
    measures = [
        x for x in [*OFFENSE, *DEFENSE] if frames[("team_game", "pace")].schema[x].is_float()
    ]
    changed[("team_game", "pace")] = (
        frames[("team_game", "pace")]
        .join(late, on=F.KEYS, how="left")
        .with_columns(pl.when(c("late")).then(9.0).otherwise(c(x)).alias(x) for x in measures)
        .drop("late")
    )
    ex = VARIANTS["plays_full"]()
    games = (
        frames[("game", "schedule")]
        .filter((c("season") == 2022) & (c("week") == 3))
        .select("game_id", "season", "week", "kickoff")
    )
    moment = cut - timedelta(hours=1)
    rows = [
        ex.features(Gateway(FrameSource(f), world.cal()).view(moment, ex.cadence, ex.inputs), games)
        for f in (frames, changed)
    ]
    assert rows[0].height == 2 * games.height
    assert_frame_equal(rows[0], rows[1])


def _miss(bt) -> float:
    return float((bt.scored["y"] - bt.scored["mean"]).abs().mean())


@pytest.mark.parametrize("habit", ["proe", "pace_oe"])
def test_the_habit_blend_finds_real_habits(habit):
    gw = _gateway()
    blend = backtest.run(VARIANTS[f"{habit}_shrunk"](), gateway=gw, seasons=SEASONS)
    league = backtest.run(VARIANTS[f"{habit}_league"](), gateway=gw, seasons=SEASONS)
    assert _miss(blend) < 0.95 * _miss(league)


def test_the_volume_model_finds_pace_and_beats_the_league_average():
    gw = _gateway()
    full = backtest.run(VARIANTS["plays_full"](), gateway=gw, seasons=SEASONS)
    league = backtest.run(VARIANTS["plays_league"](), gateway=gw, seasons=SEASONS)
    assert _miss(full) < 0.97 * _miss(league)
    assert (full.scored["q10"] <= full.scored["q90"]).all()
    dropbacks = backtest.run(VARIANTS["dropbacks_full"](), gateway=gw, seasons=SEASONS)
    assert _miss(dropbacks) < _miss(
        backtest.run(VARIANTS["dropbacks_league"](), gateway=gw, seasons=SEASONS)
    )


def test_with_no_habits_the_volume_model_is_no_better_than_the_league():
    gw = _gateway(noise_only=True)
    full = backtest.run(VARIANTS["plays_full"](), gateway=gw, seasons=SEASONS)
    league = backtest.run(VARIANTS["plays_league"](), gateway=gw, seasons=SEASONS)
    assert _miss(full) > 0.97 * _miss(league)
