"""Schemes v2 anti-traits (`pcf.experts.schemes_v2.anti_model`): the contract, per-moment features
equal to the bulk ones, no game's own or later data in a feature (a defense's season not before
it's over), and backtests on a synthetic league where low use of an option means a low gain."""

from datetime import timedelta

import numpy as np
import polars as pl
import pytest
from polars.testing import assert_frame_equal

from pcf.core.contract import check_expert, find_all
from pcf.data.gateway import END_OF_TIME, FrameSource, Gateway
from pcf.experts.schemes_v2 import anti_features as A
from pcf.experts.schemes_v2.anti_model import OPTIONS, VARIANTS
from pcf.validation import backtest
from pcf.validation.splits import steps

from ..validation import world
from .test_schemes_v2 import _frames as trait_frames

c = pl.col
UTC_T = pl.Datetime("us", "UTC")
# each team's true use of every option; in the signal world its gain moves with it
USE = dict(zip(world.TEAMS, [0.10, -0.10, 0.06, -0.06, 0.02, -0.02], strict=True))
GAIN_PER_USE = 3.0


def _frames(seed: int = 3, noise_only: bool = False) -> dict:
    frames = trait_frames()
    sides = frames[("team_game", "schedule")]
    rng = np.random.default_rng(seed)
    use = np.array([USE[t] for t in sides["team"]])
    gain = 0.0 if noise_only else GAIN_PER_USE * use
    n = sides.height
    plays = lambda: pl.Series(rng.integers(20, 50, n)).cast(pl.Int32)  # noqa: E731
    noisy = lambda base, sd: pl.Series(base + rng.normal(0, sd, n))  # noqa: E731
    ten = frames[("team_game", "tendencies")].with_columns(
        neutral_pass_oe=noisy(use, 0.05),
        shotgun_rate=noisy(0.6 + use, 0.05),
        def_neutral_plays=plays(),
        def_pass_oe=noisy(0.0, 0.05),
        def_shotgun_rate=noisy(0.6, 0.05),
        pass_gain=noisy(0.15 + gain, 0.1),
        pass_gain_n=noisy(8.0, 0.0),
        shotgun_gain=noisy(gain, 0.1),
        shotgun_gain_n=noisy(6.0, 0.0),
    )
    # a defense's season is known the day after its Super Bowl
    sb = frames[("game", "schedule")].filter(c("game_type") == "SB")
    ends = sb.select("season", known_at=(c("kickoff") + pl.duration(days=1)).cast(UTC_T))
    charted = sides.select("game_id", "team", "season").join(ends, on="season")
    for o in A.DEFENSE:
        charted = charted.with_columns(
            pl.lit(18, pl.Int32).alias(f"{o}_plays"),
            noisy(use, 0.05).alias(f"{o}_oe"),
            noisy(gain, 0.1).alias(f"{o}_gain"),
            pl.lit(4.0).alias(f"{o}_gain_n"),
        )
    return frames | {("team_game", "tendencies"): ten, ("team_game", "charted"): charted}


def _gateway(frames: dict | None = None, **kw) -> Gateway:
    return Gateway(FrameSource(frames or _frames(**kw)), world.cal())


def test_every_variant_meets_the_contract():
    found = {x.variant for x in find_all("schemes-v2")}
    assert set(VARIANTS) <= found
    own = {o: "season" if o in A.OFFENSE else "last_season" for o in OPTIONS}
    assert set(VARIANTS) == {
        f"{o}_gain_{k}" for o in OPTIONS for k in ("league", own[o], "avoid", "blend")
    }
    for cls in VARIANTS.values():
        check_expert(cls)
    assert [b.variant for b in VARIANTS["man_gain_blend"].baselines()] == [
        "man_gain_league", "man_gain_last_season", "man_gain_avoid",
    ]  # fmt: skip
    assert VARIANTS["pass_gain_avoid"].inputs == A.OFFENSE_INPUTS
    assert VARIANTS["blitz_gain_avoid"].inputs == A.DEFENSE_INPUTS


@pytest.mark.parametrize("variant", ["pass_gain_blend", "man_gain_blend"])
def test_per_moment_features_equal_the_bulk_ones(variant):
    gw = _gateway()
    ex = VARIANTS[variant]()
    every = steps(gw.calendar, ex.cadence, world.SEASONS, ex.run)
    bulk = ex.features_history(
        gw.view(END_OF_TIME, ex.cadence, ex.inputs), pl.concat([s.games for s in every])
    )
    keys = A.F.KEYS
    seen = 0
    for s in every:
        for (moment,), frame in s.games.group_by("moment", maintain_order=True):
            one = ex.features(gw.view(moment, ex.cadence, ex.inputs), frame.drop("moment"))
            other = bulk.join(one.select(keys), on=keys)
            assert_frame_equal(one.sort(keys), other.sort(keys), rel_tol=1e-9)
            seen += one.height
    assert seen == bulk.height > 0


def _changed_from(frames: dict, part: str, column: str, cut) -> dict:
    sched = frames[("team_game", "schedule")]
    later = sched.filter(c("kickoff") >= cut).select("game_id", "team").with_columns(late=True)
    out = dict(frames)
    out[("team_game", part)] = (
        frames[("team_game", part)]
        .join(later, on=A.F.KEYS, how="left")
        .with_columns(pl.when(c("late")).then(9.0).otherwise(c(column)).alias(column))
        .drop("late")
    )
    return out


@pytest.mark.parametrize(
    ("variant", "part", "column", "week"),
    [
        ("pass_gain_blend", "tendencies", "pass_gain", 3),
        ("pass_gain_blend", "tendencies", "def_pass_oe", 3),
        # a defense's whole season stays unseen until it's over, so change it from week 1
        ("man_gain_blend", "charted", "man_oe", 1),
        ("man_gain_blend", "charted", "man_gain", 1),
    ],
)
def test_a_feature_never_uses_the_game_itself_or_later_ones(variant, part, column, week):
    frames = _frames()
    sched = frames[("team_game", "schedule")]
    cut = sched.filter((c("season") == 2022) & (c("week") == week))["kickoff"].min()
    changed = _changed_from(frames, part, column, cut)
    ex = VARIANTS[variant]()
    games = (
        frames[("game", "schedule")]
        .filter((c("season") == 2022) & (c("week") == 3))
        .select("game_id", "season", "week", "kickoff")
    )
    moment = games["kickoff"].min() - timedelta(hours=1)
    rows = [
        ex.features(_gateway(f).view(moment, ex.cadence, ex.inputs), games)
        for f in (frames, changed)
    ]
    assert rows[0].height == 2 * games.height
    assert_frame_equal(rows[0], rows[1])


def test_a_defense_reads_its_last_finished_season():
    frames = _frames()
    ex = VARIANTS["man_gain_avoid"]()
    games = (
        frames[("game", "schedule")]
        .filter((c("season") == 2022) & (c("week") == 4))
        .select("game_id", "season", "week", "kickoff")
    )
    moment = games["kickoff"].min() - timedelta(hours=1)
    got = ex.features(_gateway(frames).view(moment, ex.cadence, ex.inputs), games)
    ch = frames[("team_game", "charted")].filter(c("season") == 2021)
    want = ch.group_by("team").agg(
        man_use=(c("man_oe") * c("man_plays")).sum() / c("man_plays").sum()
    )
    both = got.join(want, on="team", suffix="_want")
    assert both.height == got.height > 0
    assert np.allclose(both["man_use"], both["man_use_want"])


def test_the_opponents_part_removes_what_opponents_allow():
    """Every opponent allowing more passing than the league makes a team look like a heavier
    passer than it is: the use drops below the raw use."""
    frames = _frames()
    ten = frames[("team_game", "tendencies")]
    frames[("team_game", "tendencies")] = ten.with_columns(
        def_pass_oe=pl.when(c("team") == "BBB").then(0.3).otherwise(0.0)
    )
    ex = VARIANTS["pass_gain_avoid"]()
    gw = _gateway(frames)
    every = steps(gw.calendar, ex.cadence, [2022], ex.run)
    f = ex.features_history(
        gw.view(END_OF_TIME, ex.cadence, ex.inputs), pl.concat([s.games for s in every])
    )
    sched = frames[("team_game", "schedule")]
    faced = (
        sched.filter((c("season") == 2022) & (c("opponent") == "BBB"))["team"].unique().to_list()
    )
    late = f.filter(c("games") >= 3)
    hit = late.filter(c("team").is_in(faced))
    assert hit.height > 0
    # BBB's opponents passed against a soft pass defense, so their use is below the raw use
    assert (hit["pass_use"] < hit["pass_use_raw"]).mean() > 0.8


@pytest.mark.parametrize("option", ["pass", "man"])
def test_the_anti_trait_finds_real_avoidance_and_beats_the_league(option):
    gw = _gateway()
    seasons = [2022, 2023]
    avoid = backtest.run(VARIANTS[f"{option}_gain_avoid"](), gateway=gw, seasons=seasons)
    league = backtest.run(VARIANTS[f"{option}_gain_league"](), gateway=gw, seasons=seasons)
    miss = lambda bt: float((bt.scored["y"] - bt.scored["mean"]).abs().mean())  # noqa: E731
    assert miss(avoid) < 0.9 * miss(league)
    assert (avoid.scored["q10"] <= avoid.scored["q90"]).all()


def test_with_no_avoidance_the_anti_trait_is_no_better_than_the_league():
    gw = _gateway(noise_only=True)
    seasons = [2022, 2023]
    avoid = backtest.run(VARIANTS["pass_gain_avoid"](), gateway=gw, seasons=seasons)
    league = backtest.run(VARIANTS["pass_gain_league"](), gateway=gw, seasons=seasons)
    miss = lambda bt: float((bt.scored["y"] - bt.scored["mean"]).abs().mean())  # noqa: E731
    assert miss(avoid) > 0.97 * miss(league)
