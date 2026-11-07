"""Team Elo (`pcf.experts.elo`): the rating walk, the same-team measures, per-moment features
equal to the bulk ones, and a backtest on the synthetic league with real team strengths."""

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest
from polars.testing import assert_frame_equal

from pcf.core.contract import check_expert, find_all
from pcf.data.gateway import END_OF_TIME, FrameSource, Gateway
from pcf.experts.elo.horizons import EloNext3, EloRest, window_wins
from pcf.experts.elo.model import EloMargin, EloTotal, EloWin
from pcf.experts.elo.ratings import Settings, Walk, season_priors
from pcf.experts.elo.same_team import same_team
from pcf.validation import backtest
from pcf.validation.splits import steps

from ..validation import world

c = pl.col
UTC_T = pl.Datetime("us", "UTC")
# the synthetic schedule pairs AAA-BBB, CCC-DDD and EEE-FFF every week with the first at home,
# so the gaps are within pairs, and home teams are a mix of strong and weak (home field stays small)
STRENGTH = dict(zip(world.TEAMS, [7.0, -7.0, -5.0, 5.0, 1.0, -1.0], strict=True))


# ------------------------------------------------------------------------------ the walk
def _result(season, home, away, hp, ap, neutral=False):
    return {"season": season, "home_team": home, "away_team": away, "home_pts": hp,
            "away_pts": ap, "neutral": neutral}  # fmt: skip


def test_one_result_moves_both_teams_by_k_times_the_miss():
    res = pl.DataFrame([_result(2020, "A", "B", 20.0, 20.0)]).with_columns(
        margin=pl.lit(0.0), total=pl.lit(40.0)
    )
    walk = Walk(season_priors(res), Settings())
    walk.add(_result(2021, "A", "B", 24.0, 14.0))  # hfa 0 (2020 home margin): miss 10
    assert walk.r["A"] == pytest.approx(0.6)
    assert walk.r["B"] == pytest.approx(-0.6)
    # the offense/defense ratings: 20 points per team expected, home scored 4 more, away 6 fewer
    assert walk.o["A"] == pytest.approx(0.05 * 4)
    assert walk.d["A"] == pytest.approx(0.05 * 6)


def test_a_new_season_pulls_ratings_halfway_once():
    empty = {"season": pl.Int32, "neutral": pl.Boolean, "margin": pl.Float64, "total": pl.Float64}
    walk = Walk(season_priors(pl.DataFrame(schema=empty)))
    walk.add(_result(2020, "A", "B", 30.0, 0.0))
    before = walk.r["A"]
    walk.edges(2021, "A", "B", False)
    walk.edges(2021, "A", "B", False)
    assert walk.r["A"] == pytest.approx(before * 0.5)


def test_home_field_is_the_previous_three_seasons_mean_home_margin():
    res = pl.DataFrame(
        {
            "season": [2017, 2018, 2019, 2019, 2020],
            "neutral": [False, False, False, True, False],
            "margin": [3.0, 1.0, 2.0, 30.0, 9.0],
            "total": [40.0] * 5,
        }  # fmt: skip
    )
    pri = season_priors(res)
    assert pri.hfa[2020] == pytest.approx(2.0)  # neutral game left out
    assert pri.hfa[2021] == pytest.approx(4.0)


# -------------------------------------------------------------------------- same team
def _pg(rows):
    return pl.DataFrame(
        rows,
        schema=[
            "gsis_id",
            "game_id",
            "season",
            "week",
            "team",
            "position",
            "known_at",
            "offense_pct",
            "defense_pct",
            "snaps_known_at",
            "report_status",
            "injury_known_at",
        ],  # fmt: skip
        orient="row",
    )


def test_same_team_share_and_the_usual_qb():
    t = [datetime(2023, 9, d, tzinfo=UTC) for d in (1, 8, 15)]
    rows = []
    for n, gid in enumerate(["g1", "g2", "g3"]):
        for pid, pos, off in (("qb1", "QB", 1.0), ("qb2", "QB", 0.0), ("wr", "WR", 0.8)):
            snaps = t[n] if n < 2 else None
            status = "Out" if (gid == "g3" and pid == "qb1") else None
            week = t[n] - timedelta(days=3)  # the roster is known at the start of the week
            rows.append((pid, gid, 2023, n + 1, "AAA", pos, week, off, 0.0, snaps, status, t[2]))
    pg = _pg(rows)
    kick = pl.DataFrame({"game_id": ["g1", "g2", "g3"], "kickoff": t})
    target = pl.DataFrame({"game_id": ["g3", "g1"], "moment": [t[2], t[0]]})
    out = same_team(pg, kick, target).rows_by_key("game_id", named=True, unique=True)
    assert out["g3"]["qb_out"] == 1.0
    assert out["g3"]["share"] == pytest.approx((0.8 / 1.8 + 1.0) / 2)  # defense: no usual snaps
    assert out["g1"]["share"] == 1.0 and out["g1"]["qb_out"] == 0.0  # week 1: no history
    # a report known only after the moment doesn't count (the roster is known by then)
    late = same_team(
        pg, kick, target.with_columns(moment=pl.lit(t[2]).cast(UTC_T) - pl.duration(seconds=1))
    )
    assert late.filter(c("game_id") == "g3")["qb_out"][0] == 0.0


# --------------------------------------------------------------------- a league with strengths
def _frames(seed: int = 3, noise_only: bool = False) -> dict:
    parts = world.frames()
    sched = parts[("game", "schedule")].with_columns(location=pl.lit("Home"))
    rng = np.random.default_rng(seed)
    rows = []
    for g in sched.iter_rows(named=True):
        gap = 0 if noise_only else STRENGTH[g["home_team"]] - STRENGTH[g["away_team"]]
        hp = max(0.0, round(21 + 1.5 + gap / 2 + rng.normal(0, 5)))
        ap = max(0.0, round(21 - 1.5 - gap / 2 + rng.normal(0, 5)))
        if hp == ap:
            hp += 1
        rows.append({"game_id": g["game_id"], "season": g["season"], "home_score": hp,
                     "away_score": ap})  # fmt: skip
    result = pl.DataFrame(rows).with_columns(
        c("season").cast(pl.Int32),
        known_at=(sched["kickoff"] + pl.duration(hours=4)).cast(UTC_T),
    )
    roster = parts[("player_game", "roster")]
    kick = sched.select("game_id", "kickoff")
    snaps = roster.join(kick, on="game_id").select(
        "gsis_id", "game_id", "season", offense_pct=pl.lit(0.9), defense_pct=pl.lit(0.0),
        known_at=(c("kickoff") + pl.duration(hours=24)).cast(UTC_T),
    )  # fmt: skip
    injury = roster.join(kick, on="game_id").filter(c("position") == "QB").select(
        "gsis_id", "game_id", "season",
        report_status=pl.when((c("week") % 4 == 0) & c("team").is_in(["AAA", "DDD"]))
        .then(pl.lit("Out")).otherwise(pl.lit(None, pl.String)),
        known_at=(c("kickoff") - pl.duration(days=1)).cast(UTC_T),
    )  # fmt: skip
    return {
        ("game", "schedule"): sched,
        ("game", "result"): result,
        ("player_game", "roster"): roster,
        ("player_game", "snaps"): snaps,
        ("player_game", "injury"): injury,
    }


def _gateway(**kw) -> Gateway:
    return Gateway(FrameSource(_frames(**kw)), world.cal())


def test_every_variant_meets_the_contract():
    assert {x.variant for x in find_all("elo")} == {
        "margin",
        "total",
        "win",
        "margin_simple",
        "total_simple",
        "win_simple",
        "wins_next3",
        "wins_next3_yardstick",
        "wins_rest",
        "wins_rest_yardstick",
    }
    for cls in find_all("elo"):
        check_expert(cls)


@pytest.mark.parametrize("cls", [EloMargin, EloRest])
def test_per_moment_features_equal_the_bulk_ones(cls):
    gw = _gateway()
    ex = cls()
    every = steps(gw.calendar, ex.cadence, world.SEASONS, ex.run)
    bulk = ex.features_history(gw.view(END_OF_TIME, ex.cadence, ex.inputs),
                               pl.concat([s.games for s in every]))  # fmt: skip
    seen = 0
    for s in every:
        for (moment,), frame in s.games.group_by("moment", maintain_order=True):
            one = ex.features(gw.view(moment, ex.cadence, ex.inputs), frame.drop("moment"))
            keys = ex.keys()
            other = bulk.join(one.select(keys), on=keys)
            assert_frame_equal(one.sort(keys), other.sort(keys), rel_tol=1e-9)
            seen += one.height
    assert seen == bulk.height
    if cls is EloMargin:
        assert bulk["qb_diff"].abs().sum() > 0  # the injury reports reached the features


def test_ratings_find_the_strong_teams_and_forecasts_have_signal():
    bt = backtest.run(EloMargin(), gateway=_gateway(), seasons=[2022, 2023], bulk=True)
    true_gap = bt.features.select(
        "gap",
        s=c("home_team").replace_strict(STRENGTH) - c("away_team").replace_strict(STRENGTH),
    )
    assert np.corrcoef(true_gap["gap"], true_gap["s"])[0, 1] > 0.6
    y = bt.scored["y"]
    miss = float((y - bt.scored["mean"]).abs().mean())
    flat = float((y - y.mean()).abs().mean())  # the same number for every game, chosen in hindsight
    assert miss < flat - 1


@pytest.mark.parametrize("cls", [EloTotal, EloWin])
def test_the_other_variants_backtest(cls):
    bt = backtest.run(cls(), gateway=_gateway(), seasons=[2023], bulk=True)
    h = bt.scored
    assert h.height > 0
    if cls.kind == "probability":
        assert h["mean"].is_between(0, 1).all()
    else:
        assert (h["q10"] <= h["q90"]).all()


# ------------------------------------------------------------------------ the long horizon
def test_window_wins_count_from_this_game_on_and_wait_for_the_whole_window():
    t = [datetime(2023, 9, d, tzinfo=UTC) for d in (3, 10, 17, 24)]
    game = pl.DataFrame(
        {
            "game_id": ["g1", "g2", "g3", "g4"],
            "season": [2023] * 4,
            "week": [1, 2, 3, 4],
            "game_type": ["REG"] * 4,
            "kickoff": t,
            "home_team": ["A", "B", "A", "A"],
            "away_team": ["B", "A", "B", "B"],
            "location": ["Home"] * 4,
            "home_score": [20, 17, 10, None],
            "away_score": [10, 17, 13, None],
            "result_known_at": [t[0], t[1], t[2], None],
            "known_at": [t[0]] * 4,  # on the schedule from the start
        }
    )
    a = window_wins(game, 3).filter(c("team") == "A").rows_by_key("game_id", named=True)
    assert a["g1"][0]["y"] == 1.5  # won, tied, lost
    assert "g2" not in a  # g4 isn't played yet
    rest = window_wins(game, None)
    assert rest.is_empty()  # every window reaches g4


def test_long_horizon_forecasts_stay_inside_the_games_left():
    gw = _gateway()
    for cls in (EloNext3, EloRest):
        bt = backtest.run(cls(), gateway=gw, seasons=[2022, 2023], bulk=True)
        h = bt.scored
        assert h.height > 0
        assert (h["q10"] >= 0).all() and (h["q90"] <= bt.features["left"].max()).all()
        assert (bt.features["elo_wins"] <= bt.features["left"]).all()
