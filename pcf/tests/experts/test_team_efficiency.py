"""Team efficiency (`pcf.experts.team_efficiency`): the contract, per-moment features equal to the
bulk ones, no game's own plays (or later ones) in its features, ratings that find the teams' real
strengths, the prior's walk, and backtests on a synthetic league."""

from datetime import timedelta

import numpy as np
import polars as pl
import pytest
from polars.testing import assert_frame_equal

from pcf.core.contract import check_expert, find_all
from pcf.data.gateway import END_OF_TIME, FrameSource, Gateway
from pcf.data.tables.efficiency import BINS, COLUMNS
from pcf.experts.team_efficiency import changes as X
from pcf.experts.team_efficiency import features as F
from pcf.experts.team_efficiency import ratings as R
from pcf.experts.team_efficiency.model import LADDER, VARIANTS
from pcf.validation import backtest
from pcf.validation.splits import steps

from ..validation import world

c = pl.col
UTC_T = pl.Datetime("us", "UTC")
# each team's true offense (EPA per play it gains) and defense (EPA per play it allows)
OFF = dict(zip(world.TEAMS, [0.15, -0.15, 0.10, -0.10, 0.05, -0.05], strict=True))
DEF = dict(zip(world.TEAMS, [-0.10, 0.10, 0.05, -0.05, 0.0, 0.0], strict=True))
SEASONS = [2022, 2023]


def _round_robin(sched: pl.DataFrame) -> pl.DataFrame:
    """The world's games with a round-robin's teams (the world always pairs the same teams with
    the same one at home, which leaves home field and team strength tangled): each week a new
    round, home and away swapping every other week."""
    t = world.TEAMS
    rows = []
    for g in sched.sort("season", "week", "kickoff").iter_rows(named=True):
        r = (g["week"] - 1) % 5
        ring = [t[0], *(t[1:][r:] + t[1:][:r])]
        pairs = [(ring[0], ring[5]), (ring[1], ring[4]), (ring[2], ring[3])]
        h, a = pairs[g["slot"] % 3] if g["game_type"] == "REG" else (t[1], t[0])
        if g["week"] % 2:
            h, a = a, h
        rows.append({"game_id": g["game_id"], "home_team": h, "away_team": a})
    return sched.drop("home_team", "away_team").join(pl.DataFrame(rows), on="game_id")


def _frames(seed: int = 3, noise_only: bool = False) -> dict:
    sched = world.frames()[("game", "schedule")]
    games = _round_robin(sched)
    sides = pl.concat(
        [
            games.select("game_id", "season", "week", "game_type", "kickoff", "known_at",
                         team=c(a), opponent=c(b), home=pl.lit(a == "home_team"))
            for a, b in (("home_team", "away_team"), ("away_team", "home_team"))
        ]
    ).sort("game_id", "team")  # fmt: skip
    rng = np.random.default_rng(seed)
    n = sides.height
    plays = rng.integers(55, 70, n)
    true = np.array(
        [
            0.0 if noise_only else OFF[t] + DEF[o]
            for t, o in zip(sides["team"], sides["opponent"], strict=True)
        ]  # fmt: skip
    )
    per_play = true + rng.normal(0, 1.4 / np.sqrt(plays))
    epa = per_play * plays
    share = rng.dirichlet(np.ones(BINS), n)
    cells_n = np.floor(share * plays[:, None])
    cells_n[:, 0] += plays - cells_n.sum(1)
    cells_r = cells_n * per_play[:, None]
    ints = lambda x: pl.Series(x).cast(pl.Int32)  # noqa: E731
    usual = np.rint(plays * 0.7)
    eff = sides.select("game_id", "team", "season", "kickoff").with_columns(
        eff_plays=ints(plays), eff_epa=pl.Series(epa), eff_epa_sq=pl.Series(epa**2 / plays + 1.9),
        eff_usual_plays=ints(usual), eff_usual_epa=pl.Series(per_play * usual),
        eff_pass_plays=ints(plays // 2), eff_pass_epa=pl.Series(per_play * (plays // 2)),
        eff_run_plays=ints(plays - plays // 2),
        eff_run_epa=pl.Series(per_play * (plays - plays // 2)),
        eff_series=ints(np.full(n, 20)),
        eff_series_success=pl.Series(np.clip(10 + 20 * per_play, 0, 20)),
        **{f"eff_n_{k}": pl.Series(cells_n[:, k]) for k in range(BINS)},
        **{f"eff_{p}_{k}": pl.Series(cells_r[:, k]) for p in ("r", "rwo", "rwd")
           for k in range(BINS)},
        known_at=(c("kickoff") + pl.duration(hours=24)).cast(UTC_T),
    ).select("game_id", "team", "season", *COLUMNS, "known_at")  # fmt: skip
    return {
        ("game", "schedule"): sched,
        ("team_game", "schedule"): sides,
        ("team_game", "efficiency"): eff,
        **_people(sides),
    }


NEW_QB = ("AAA", 2023)  # AAA starts 2023 with a new quarterback
NEW_COACH = ("BBB", 2022)  # BBB hires a new head coach for 2022


def _people(sides: pl.DataFrame) -> dict:
    """Each team's QB and head coach per game (P3's inputs): the same every season but for
    `NEW_QB` and `NEW_COACH`. The pregame QB and coach are known at kickoff; the opening coach and
    the week-1 depth chart at the start of the season's first week."""
    reg = sides.filter(c("game_type") == "REG")
    qb = pl.when((c("team") == NEW_QB[0]) & (c("season") >= NEW_QB[1]))
    coach = pl.when((c("team") == NEW_COACH[0]) & (c("season") >= NEW_COACH[1]))
    start = reg.group_by("season").agg(start=(c("kickoff").min() - pl.duration(days=3)))
    people = reg.join(start, on="season").with_columns(
        qb_id=qb.then(pl.lit("QB_") + c("team") + "2").otherwise(pl.lit("QB_") + c("team")),
        coach=coach.then(pl.lit("HC_") + c("team") + "2").otherwise(pl.lit("HC_") + c("team")),
        start=c("start").cast(UTC_T),
    )
    first = people.join(
        people.group_by("season", "team").agg(c("week").min()), on=["season", "team", "week"]
    )
    return {
        ("team_game", "pregame"): people.select(
            "game_id", "team", "season", "qb_id", "coach", known_at=c("kickoff").cast(UTC_T)
        ),
        ("team_game", "opening_coach"): first.select(
            "game_id", "team", "season", known_at="start", opening_coach="coach"
        ),
        ("player_game", "roster"): people.select(
            "game_id",
            "season",
            "week",
            "team",
            gsis_id="qb_id",
            position=pl.lit("QB"),
            known_at="start",
        ),  # fmt: skip
        ("player_game", "depth"): people.select(
            "game_id",
            "season",
            gsis_id="qb_id",
            depth=pl.lit(1, pl.Int32),
            depth_mean=pl.lit(1.0),
            depth_position=pl.lit("QB"),
            known_at="start",
        ),  # fmt: skip
    }


def _gateway(**kw) -> Gateway:
    return Gateway(FrameSource(_frames(**kw)), world.cal())


def test_the_walk_reads_the_part_s_bins():
    assert R.BINS == BINS


def test_every_variant_meets_the_contract():
    assert {x.variant for x in find_all("team-efficiency")} == set(VARIANTS)
    expected = {f"{s}_{h}_{r}" for s in F.SIDES for h in F.HORIZONS for r in LADDER}
    expected -= {f"def_{h}_change" for h in F.HORIZONS}  # P3 is offense only
    assert set(VARIANTS) == expected
    for cls in VARIANTS.values():
        check_expert(cls)
    assert [b.variant for b in VARIANTS["def_rest_combo"].baselines()] == [
        "def_rest_dml", "def_rest_ridge", "def_rest_league",
    ]  # fmt: skip
    assert VARIANTS["off_next3_ridge"].publishes == F.PUBLISHED
    assert not VARIANTS["off_next3_combo"].publishes
    assert not VARIANTS["off_rest_ridge"].publishes


def test_per_moment_features_equal_the_bulk_ones():
    gw = _gateway()
    ex = VARIANTS["off_next3_combo"]()
    every = steps(gw.calendar, ex.cadence, world.SEASONS, ex.run)
    bulk = ex.features_history(
        gw.view(END_OF_TIME, ex.cadence, ex.inputs), pl.concat([s.games for s in every])
    )
    seen = 0
    for s in every:
        for (moment,), frame in s.games.group_by("moment", maintain_order=True):
            one = ex.features(gw.view(moment, ex.cadence, ex.inputs), frame.drop("moment"))
            if one.is_empty():
                continue
            other = bulk.join(one.select(F.KEYS), on=F.KEYS)
            assert_frame_equal(one.sort(F.KEYS), other.select(one.columns).sort(F.KEYS),
                               rel_tol=1e-9)  # fmt: skip
            seen += one.height
    assert seen == bulk.height > 0


def test_a_feature_never_uses_the_game_itself_or_later_ones():
    """Change every efficiency number from one game on: that week's features stay the same."""
    frames = _frames()
    sched = frames[("team_game", "schedule")]
    cut = sched.filter((c("season") == 2022) & (c("week") == 3))["kickoff"].min()
    late = sched.filter(c("kickoff") >= cut).select("game_id", "team", late=pl.lit(True))
    changed = dict(frames)
    eff = frames[("team_game", "efficiency")]
    nums = [x for x in COLUMNS if eff.schema[x].is_float()]
    changed[("team_game", "efficiency")] = (
        eff.join(late, on=F.KEYS, how="left")
        .with_columns(pl.when(c("late")).then(c(x) * 3 + 5).otherwise(c(x)).alias(x) for x in nums)
        .drop("late")
    )
    ex = VARIANTS["off_rest_combo"]()
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


def test_ratings_find_the_teams_real_strengths():
    frames = _frames()
    tg = frames[("team_game", "schedule")].join(
        frames[("team_game", "efficiency")].rename({"known_at": "efficiency_known_at"}),
        on=[*F.KEYS, "season"],
    )
    names = R.teams(tg)
    x = R.prepare(tg, names)
    req = pl.DataFrame({"season": [2023], "week": [7]}).with_columns(
        moment=pl.lit(END_OF_TIME).cast(UTC_T)
    )
    rat = R.ratings(x, req, ["ridge", "dml", "combo"], names)
    for m in ("ridge", "dml", "combo"):
        o = rat[f"{m}_o"].to_numpy()
        d = rat[f"{m}_d"].to_numpy()
        assert np.corrcoef(o, [OFF[t] for t in names])[0, 1] > 0.9, m
        # defenses differ less, and the combination's defense pulls harder toward its prior
        assert np.corrcoef(d, [DEF[t] for t in names])[0, 1] > 0.7, m
        assert (rat[f"{m}_o_sd"] > 0).all()


def test_a_season_with_no_games_yet_is_its_prior_and_a_team_with_none_is_left_out():
    rows = np.array([[1, 0, 1, 1, 60, 6.0], [1, 1, 0, 0, 60, -6.0]])
    po, pd_ = np.array([0.1, -0.1, 0.3]), np.zeros(3)
    o, d, o_sd, _ = R._ridge_fit(rows[:0], 1.0, po, pd_, R.MEASURES["ridge"].off, 60.0, 1.9)
    assert np.allclose(o, po) and np.allclose(d, pd_) and (o_sd > 0).all()
    o, _, _, _ = R._ridge_fit(rows, 2.0, po, pd_, R.MEASURES["ridge"].off, 60.0, 1.9)
    assert o[0] > o[1]
    assert o[2] == pytest.approx(0.3)  # no games: its prior
    prior = R._centred(o, rows, 0.5)
    assert prior[2] == 0.0  # it didn't play: next season starts at 0
    assert prior[:2].mean() == pytest.approx(0.0)


def test_targets_are_epa_per_play_over_the_window_relative_to_each_week():
    frames = _frames()
    tg = frames[("team_game", "schedule")].join(
        frames[("team_game", "efficiency")].rename({"known_at": "efficiency_known_at"}),
        on=[*F.KEYS, "season"],
    )
    off = F.targets(tg, "off", "next3")
    de = F.targets(tg, "def", "next3")
    rest = F.targets(tg, "off", "rest")
    # the last regular week has no 3 games left, but its window is complete; the Super Bowl isn't
    assert off.height == rest.height == tg.filter(c("game_type") == "REG").height
    # a team's weekly offense and the defenses it faced sum to the league's mean of zero
    one = tg.filter((c("game_type") == "REG") & (c("week") == world.WEEKS))
    last = F.targets(tg, "off", "next3").join(one.select(F.KEYS), on=F.KEYS)
    assert last["y"].dot(one.sort(F.KEYS)["eff_plays"].cast(pl.Float64)) == pytest.approx(0.0)
    assert de.height == off.height
    week1 = tg.filter((c("season") == 2023) & (c("week") == 1)).select(F.KEYS)
    k = rest.join(week1, on=F.KEYS)["known_at"]
    assert (k == k.max()).all()  # rest of season: known when the season's last week is


def _mse(bt) -> float:
    return float(((bt.scored["y"] - bt.scored["mean"]) ** 2).mean())


@pytest.mark.parametrize("side", ["off", "def"])
def test_the_ratings_beat_the_league_level(side):
    gw = _gateway()
    combo = backtest.run(VARIANTS[f"{side}_next3_combo"](), gateway=gw, seasons=SEASONS)
    league = backtest.run(VARIANTS[f"{side}_next3_league"](), gateway=gw, seasons=SEASONS)
    assert _mse(combo) < 0.9 * _mse(league)
    assert (combo.scored["q10"] <= combo.scored["q90"]).all()
    assert set(F.PUBLISHED) <= set(combo.features.columns)


def test_no_signal_when_teams_are_alike():
    gw = _gateway(noise_only=True)
    combo = backtest.run(VARIANTS["off_next3_ridge"](), gateway=gw, seasons=SEASONS)
    league = backtest.run(VARIANTS["off_next3_league"](), gateway=gw, seasons=SEASONS)
    assert _mse(combo) > 0.9 * _mse(league)


def _season_changes() -> pl.DataFrame:
    gw = _gateway()
    view = gw.view(END_OF_TIME, "in_season", F.INPUTS)
    return X.season_changes(view.table("team_game"), view.table("player_game"))


def test_season_changes_flag_a_new_qb_and_a_new_coach():
    ch = _season_changes()
    flagged = ch.filter((c("new_qb") > 0) | (c("new_coach") > 0)).select(
        "team", "season", "new_qb", "new_coach"
    )
    assert flagged.rows() == [("BBB", 2022, 0.0, 1.0), ("AAA", 2023, 1.0, 0.0)]
    assert ch["known_at"].null_count() == 0


def test_the_weaker_pull_cuts_the_prior_only_once_the_change_is_known():
    tg = _gateway().view(END_OF_TIME, "in_season", F.INPUTS).table("team_game")
    names = R.teams(tg)
    x = R.prepare(tg, names)
    ch = _season_changes()
    known = ch.filter((c("team") == NEW_QB[0]) & (c("season") == NEW_QB[1]))["known_at"].item()
    before, after = known - timedelta(hours=1), known + timedelta(hours=1)
    req = pl.DataFrame({"season": [2023, 2023], "week": [1, 1], "moment": [before, after]}).cast(
        {"season": pl.Int32, "week": pl.Int32, "moment": UTC_T}
    )
    rat = R.ratings(x, req, ["ridge", "change"], names, R.change_arrays(ch, names))
    i = names.index(NEW_QB[0])
    early, late = (rat.filter(c("moment") == m) for m in req["moment"].cast(UTC_T))
    # week 1 has no games yet, so the rating is the prior. Once AAA's new QB is known its prior
    # keeps 75% (a = 0.25); before, nothing changes. (BBB's 2022 coach already moved 2022's fit,
    # so `change` and `ridge` differ a little for everyone.)
    assert late["change_o"][i] == pytest.approx(0.75 * early["change_o"][i])
    assert early["change_o"][i] != pytest.approx(late["change_o"][i])
    other = names.index("CCC")
    assert late["change_o"][other] == pytest.approx(early["change_o"][other])
    assert np.allclose(late["change_d"], late["ridge_d"])  # defense keeps its pull
