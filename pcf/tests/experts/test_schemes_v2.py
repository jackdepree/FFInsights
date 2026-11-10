"""Schemes v2 traits (`pcf.experts.schemes_v2`): the contract, per-moment features equal to the
bulk ones, no future games in a feature, and a backtest on a synthetic league whose teams have
real styles."""

from datetime import timedelta

import numpy as np
import polars as pl
import pytest
from polars.testing import assert_frame_equal

from pcf.core.contract import check_expert, find_all
from pcf.data.gateway import END_OF_TIME, FrameSource, Gateway
from pcf.experts.schemes_v2 import features as F
from pcf.experts.schemes_v2.model import VARIANTS
from pcf.validation import backtest
from pcf.validation.splits import steps

from ..validation import world

c = pl.col
UTC_T = pl.Datetime("us", "UTC")
# each team's true pass rate over expected; coaches never change, so the coach's is the same
STYLE = dict(zip(world.TEAMS, [0.08, -0.08, 0.05, -0.05, 0.02, -0.02], strict=True))


def _frames(seed: int = 5, noise_only: bool = False) -> dict:
    sched = world.frames()[("game", "schedule")]
    sides = pl.concat(
        [
            sched.select("game_id", "season", "week", "game_type", "kickoff", "known_at",
                         team=c(a), opponent=c(b), home=pl.lit(a == "home_team"))
            for a, b in (("home_team", "away_team"), ("away_team", "home_team"))
        ]
    ).sort("game_id", "team")  # fmt: skip
    rng = np.random.default_rng(seed)
    style = np.array([0.0 if noise_only else STYLE[t] for t in sides["team"]])
    n = sides.height
    tendencies = sides.select("game_id", "team", "season").with_columns(
        neutral_plays=pl.Series(rng.integers(20, 50, n)).cast(pl.Int32),
        neutral_pass_oe=pl.Series(style + rng.normal(0, 0.06, n)),
        shotgun_rate=pl.Series(np.clip(0.6 + 3 * style + rng.normal(0, 0.1, n), 0, 1)),
        tempo_plays=pl.Series(rng.integers(5, 20, n)).cast(pl.Int32),
        tempo_seconds=pl.Series(38 - 20 * style + rng.normal(0, 2, n)),
        air_attempts=pl.Series(rng.integers(10, 30, n)).cast(pl.Int32),
        air_yards_per_att=pl.Series(8 + 30 * style + rng.normal(0, 2, n)),
        # what offenses do against the team's defense (rung 2's opponent bend): no style here
        def_neutral_plays=pl.Series(rng.integers(20, 50, n)).cast(pl.Int32),
        def_pass_oe=pl.Series(rng.normal(0, 0.06, n)),
        def_shotgun_rate=pl.Series(np.clip(0.6 + rng.normal(0, 0.1, n), 0, 1)),
        def_air_attempts=pl.Series(rng.integers(10, 30, n)).cast(pl.Int32),
        def_air_yards_per_att=pl.Series(8 + rng.normal(0, 2, n)),
        known_at=(sides["kickoff"] + pl.duration(hours=24)).cast(UTC_T),
    )
    pregame = sides.select(
        "game_id", "team", "season",
        coach=pl.concat_str(pl.lit("Coach "), c("team")),
        known_at=c("kickoff").cast(UTC_T),
    )  # fmt: skip
    # the coach each team opens its season with, known 3 days before the season's first kickoff
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
    }


def _gateway(**kw) -> Gateway:
    return Gateway(FrameSource(_frames(**kw)), world.cal())


def test_every_variant_meets_the_contract():
    found = {x.variant for x in find_all("schemes-v2")}
    assert set(VARIANTS) <= found  # with the anti-traits (test_schemes_v2_anti.py)
    assert set(VARIANTS) == {
        f"{t}_{p}" for t in F.TRAITS for p in ("league", "last4", "season", "shrunk", "rung2")
    }
    for cls in VARIANTS.values():
        check_expert(cls)
    blend = VARIANTS["pass_oe_shrunk"]
    assert [b.variant for b in blend.baselines()] == [
        "pass_oe_league", "pass_oe_last4", "pass_oe_season",
    ]  # fmt: skip


def test_per_moment_features_equal_the_bulk_ones():
    gw = _gateway()
    ex = VARIANTS["pass_oe_shrunk"]()
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
    """Change every tendency from one game on: that game's features stay the same."""
    frames = _frames()
    sched = frames[("team_game", "schedule")]
    cut = sched.filter((c("season") == 2022) & (c("week") == 3))["kickoff"].min()
    later = sched.filter(c("kickoff") >= cut).select("game_id", "team")
    changed = dict(frames)
    changed[("team_game", "tendencies")] = (
        frames[("team_game", "tendencies")]
        .join(later.with_columns(late=pl.lit(True)), on=F.KEYS, how="left")
        .with_columns(
            neutral_pass_oe=pl.when(c("late")).then(9.0).otherwise(c("neutral_pass_oe")),
            def_pass_oe=pl.when(c("late")).then(9.0).otherwise(c("def_pass_oe")),  # rung 2's
        )
        .drop("late")
    )
    ex = VARIANTS["pass_oe_shrunk"]()
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


def test_a_new_coach_counts_from_week_1_once_the_opening_coach_is_known():
    """AAA opens 2022 with BBB's coach: before AAA's first 2022 game, its coach history is BBB's
    coach's, but only from the moment the opening coach is known."""
    frames = _frames()
    oc = frames[("team_game", "opening_coach")]
    swapped = oc.with_columns(
        opening_coach=pl.when((c("team") == "AAA") & (c("season") == 2022))
        .then(pl.lit("Coach BBB"))
        .otherwise(c("opening_coach"))
    )
    frames = frames | {("team_game", "opening_coach"): swapped}
    gw = Gateway(FrameSource(frames), world.cal())
    ex = VARIANTS["pass_oe_shrunk"]()
    known = swapped.filter((c("team") == "AAA") & (c("season") == 2022))["known_at"][0]
    games = (
        frames[("game", "schedule")]
        .filter((c("season") == 2022) & (c("week") == 1))
        .select("game_id", "season", "week", "kickoff")
    )
    after = ex.features(gw.view(known + timedelta(hours=1), ex.cadence, ex.inputs), games)
    coach = dict(after.select("team", "pass_oe_coach").iter_rows())
    assert coach["AAA"] == pytest.approx(coach["BBB"])
    before = ex.features(gw.view(known - timedelta(hours=1), ex.cadence, ex.inputs), games)
    coach = dict(before.select("team", "pass_oe_coach").iter_rows())
    assert coach["AAA"] != pytest.approx(coach["BBB"])  # still AAA's own last coach


def test_the_season_average_shrinks_toward_the_league_early():
    gw = _gateway()
    ex = VARIANTS["pass_oe_shrunk"]()
    every = steps(gw.calendar, ex.cadence, world.SEASONS, ex.run)
    f = ex.features_history(
        gw.view(END_OF_TIME, ex.cadence, ex.inputs), pl.concat([s.games for s in every])
    )
    gap = (c("pass_oe_shrunk") - c("pass_oe_league")).abs()
    raw = (c("pass_oe_season") - c("pass_oe_league")).abs()
    one = f.filter(c("games") == 1)
    assert one.height > 0
    # after one game the league has PRIOR_GAMES games' weight: the gap is about a fifth of raw
    assert one.select((gap < 0.5 * raw).all()).item()
    none = f.filter((c("games") == 0) & (c("season") == world.SEASONS[0]))
    assert none.select((c("pass_oe_shrunk") == c("pass_oe_league")).all()).item()


@pytest.mark.parametrize("trait", list(F.TRAITS))
def test_the_blend_finds_real_styles_and_beats_the_league_average(trait):
    gw = _gateway()
    blend = backtest.run(VARIANTS[f"{trait}_shrunk"](), gateway=gw, seasons=[2022, 2023])
    league = backtest.run(VARIANTS[f"{trait}_league"](), gateway=gw, seasons=[2022, 2023])
    miss = lambda bt: float((bt.scored["y"] - bt.scored["mean"]).abs().mean())  # noqa: E731
    assert miss(blend) < 0.95 * miss(league)
    assert (blend.scored["q10"] <= blend.scored["q90"]).all()


def test_with_no_styles_the_blend_is_no_better_than_the_league():
    gw = _gateway(noise_only=True)
    blend = backtest.run(VARIANTS["pass_oe_shrunk"](), gateway=gw, seasons=[2022, 2023])
    league = backtest.run(VARIANTS["pass_oe_league"](), gateway=gw, seasons=[2022, 2023])
    miss = lambda bt: float((bt.scored["y"] - bt.scored["mean"]).abs().mean())  # noqa: E731
    assert miss(blend) > 0.97 * miss(league)
