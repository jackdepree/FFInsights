"""context-live: the play table, the outcomes, the rungs, the nulls and the output (synthetic)."""

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from pcf.core.contract import check_output
from pcf.experts.context_live import models, plays, run
from pcf.experts.context_live.outcomes import OUTCOMES, get

c = pl.col
T0 = datetime(2023, 9, 10, 17, tzinfo=UTC)


def _pbp(n: int = 8, **over) -> pl.DataFrame:
    base = {
        "game_id": ["2023_01_A_B"] * n,
        "play_id": list(range(1, n + 1)),
        "season": [2023] * n,
        "season_type": ["REG"] * n,
        "week": [1] * n,
        "posteam": ["KC"] * n,
        "defteam": ["BUF"] * n,
        "home_team": ["KC"] * n,
        "play_type": ["run", "pass", "pass", "pass", "no_play", "run", "pass", "run"][:n],
        "two_point_attempt": [0, 0, 0, 0, 0, 0, 0, 1][:n],
        "down": [1, 2, 3, 3, 1, 2, 1, 1][:n],
        "ydstogo": [10, 7, 3, 8, 10, 4, 10, 2][:n],
        "yardline_100": [75, 70, 60, 50, 40, 30, 20, 2][:n],
        "goal_to_go": [0] * n,
        "qtr": [1] * n,
        "half_seconds_remaining": [1700.0] * n,
        "game_seconds_remaining": [3500.0] * n,
        "score_differential": [0.0] * n,
        "posteam_timeouts_remaining": [3] * n,
        "defteam_timeouts_remaining": [3] * n,
        "shotgun": [0, 1, 1, 1, 0, 0, 1, 0][:n],
        "no_huddle": [0] * n,
        "rush_attempt": [1, 0, 1, 0, 0, 1, 0, 1][:n],
        "pass_attempt": [0, 1, 0, 1, 0, 0, 1, 0][:n],
        "qb_dropback": [0, 1, 1, 1, 0, 0, 1, 0][:n],
        "qb_scramble": [0, 0, 1, 0, 0, 0, 0, 0][:n],
        "sack": [0, 0, 0, 1, 0, 0, 0, 0][:n],
        "complete_pass": [0, 1, 0, 0, 0, 0, 0, 0][:n],
        "first_down": [0, 1, 1, 0, 0, 1, 0, 0][:n],
        "pass_touchdown": [0, 0, 0, 0, 0, 0, 0, 0][:n],
        "rush_touchdown": [0, 0, 0, 0, 0, 1, 0, 0][:n],
        "penalty": [0, 0, 0, 0, 1, 0, 0, 0][:n],
        "success": [0, 1, 1, 0, 0, 1, 0, 1][:n],
        "yards_gained": [-1, 12, 5, -7, 0, 25, 0, 2][:n],
        "air_yards": [None, 8.0, None, None, None, None, 15.0, None][:n],
        "known_at": [T0 + timedelta(hours=16)] * n,
        "qb_location": ["0", "S", "S", "U", "0", "U", "S", "U"][:n],
        "starting_hash": ["L", "M", "R", "L", "0", "R", "L", "M"][:n],
        "n_offense_backfield": [2, 1, 1, 1, 0, 2, 1, 2][:n],
        "is_motion": [True, False, True, False, False, False, True, False][:n],
        "is_play_action": [False, True, False, False, False, False, False, False][:n],
        "is_screen_pass": [False, False, False, False, False, False, True, False][:n],
        "is_rpo": [False] * n,
        "is_trick_play": [False] * n,
        "is_qb_sneak": [False] * n,
        "n_defense_box": [8, 6, 6, 6, 7, 7, 5, 9][:n],
        "n_blitzers": [0, 1, 0, 2, 0, 0, 0, 0][:n],
        "n_pass_rushers": [0, 5, 4, 6, 0, 0, 4, 0][:n],
        "ftn_known_at": [T0 + timedelta(days=13, hours=16)] * n,
    }
    base.update(over)
    return pl.DataFrame(base)


def test_the_play_table_sorts_plays_into_populations_with_their_outcomes():
    d = plays.frame(_pbp())
    assert d.height == 7  # the two-point try is left out
    pop = dict(zip(d["play_id"], d["population"], strict=True))
    assert pop == {1: "run", 2: "attempt", 3: "dropback", 4: "dropback", 5: "snap", 6: "run",
                   7: "attempt"}  # fmt: skip
    row = d.filter(c("play_id") == 1).row(0, named=True)
    assert row["stuffed"] == 1.0 and row["qb_location"] is None  # FTN's "0" is not charted
    assert d.filter(c("play_id") == 6)["explosive_run"].item() == 1.0
    assert d.filter(c("play_id") == 6)["td"].item() == 1.0
    assert (d["known_at"] == T0 + timedelta(days=13, hours=16)).all()  # FTN's known_at, the later


def test_a_play_with_no_ftn_row_keeps_the_play_by_plays_known_at():
    p = _pbp(ftn_known_at=[None] * 8)
    assert (plays.frame(p)["known_at"] == T0 + timedelta(hours=16)).all()


def test_the_play_table_refuses_a_play_by_play_without_its_columns():
    with pytest.raises(ValueError, match="missing"):
        plays.frame(_pbp().drop("yardline_100"))


def test_traits_join_the_offense_and_the_defense_and_refuse_duplicates():
    charted = pl.DataFrame(
        {
            "team": ["KC", "BUF"],
            "season": [2022, 2022],
            "prior_for": [2023, 2023],
            **{t: [1.0, 2.0] for t in plays.TRAITS},
        }  # fmt: skip
    )
    d = plays.with_traits(plays.frame(_pbp()), plays.traits(charted))
    assert (d["off_11_rate_oe"] == 1.0).all() and (d["def_box_oe"] == 2.0).all()
    with pytest.raises(ValueError, match="two trait rows"):
        plays.with_traits(plays.frame(_pbp()), plays.traits(pl.concat([charted, charted])))


def test_outcomes_pick_their_population_and_first_season():
    d = plays.frame(_pbp())
    assert get("rush_yards_exp").rows(d)["play_id"].to_list() == [1, 6]
    assert get("sack_prob").rows(d)["play_id"].to_list() == [2, 3, 4, 7]
    assert get("air_yards_exp").rows(d)["play_id"].to_list() == [2, 7]
    assert get("penalty_prob").rows(d).height == 7
    assert get("pressure_prob").first_season == plays.FIRST_PARTICIPATION
    names = {o.name for o in OUTCOMES}
    assert not names & {"interception_prob", "fumble_prob", "scramble_prob"}  # the CEO's call 2


def _world(n: int = 4000, seed: int = 0, seasons=(2022, 2023, 2024)) -> pl.DataFrame:
    """Synthetic plays: a blitz raises pressure, the down sets the base, the hash means nothing."""
    rng = np.random.default_rng(seed)
    rows = []
    for s in seasons:
        down = rng.integers(1, 5, n).astype(float)
        blitz = rng.integers(0, 3, n).astype(float)
        p = 1 / (1 + np.exp(-(-1.5 + 0.3 * (down - 2) + 0.8 * blitz)))
        frame = {x: rng.normal(size=n) for x in plays.SITUATION}
        frame.update({x: rng.integers(0, 2, n).astype(float) for x in plays.CALLS})
        frame.update({x: rng.normal(size=n) for x in plays.TRAITS})
        frame.update(
            down=down, n_blitzers=blitz,
            qb_location=rng.choice(["U", "S", "P"], n),
            starting_hash=rng.choice(["L", "M", "R"], n),
            pressure_y=(rng.random(n) < p).astype(float),
            yards=4 + 2 * blitz + rng.normal(scale=3, size=n),
        )  # fmt: skip
        f = pl.DataFrame(frame).with_columns(
            game_id=pl.format("{}_{}", pl.lit(s), (pl.int_range(n) // 120)),
            play_id=pl.int_range(n, dtype=pl.Int64),
            season=pl.lit(s, pl.Int32),
            week=(pl.int_range(n) // (n // 4) + 1).cast(pl.Int32),
            known_at=pl.lit(datetime(s, 9, 1, tzinfo=UTC)),
            as_of=pl.lit(datetime(s, 10, 1, tzinfo=UTC)),
            is_run=pl.lit(True), is_dropback=pl.lit(True), is_attempt=pl.lit(True),
        )  # fmt: skip
        rows.append(f)
    return pl.concat(rows, how="diagonal_relaxed")


def test_models_give_chances_and_ordered_ranges():
    d = _world().with_columns(y=c("pressure_y"), weight=pl.lit(1.0))
    o = get("pressure_prob")
    for method in models.METHODS:
        m = models.fit(d, o, plays.FIELD_SETS["live"], method)
        p = m.predict(d.head(200))["mean"]
        assert p.is_between(0, 1).all()
    base = models.fit(d, o, [], "base")
    assert base.predict(d.head(3))["mean"][0] == pytest.approx(d["y"].mean())
    a = get("rush_yards_exp")
    amounts = d.with_columns(y=c("yards"))
    for method in models.METHODS:
        pred = models.fit(amounts, a, plays.FIELD_SETS["live"], method).predict(amounts.head(500))
        assert (pred["q10"] <= pred["q50"]).all() and (pred["q50"] <= pred["q90"]).all()


def test_yards_forecasts_stay_on_the_field():
    d = _world().with_columns(y=c("yards"), weight=pl.lit(1.0), yardline_100=pl.lit(3.0))
    rows = d.head(300).with_columns(yardline_100=pl.Series(np.linspace(1, 99, 300)))
    for name, back in (("rush_yards_exp", 0), ("air_yards_exp", 10)):
        pred = models.fit(d, get(name), plays.FIELD_SETS["live"], "trees").predict(rows)
        to_goal = rows["yardline_100"]
        for q in ("mean", "q10", "q50", "q90"):
            assert (pred[q] <= to_goal + back).all() and (pred[q] >= to_goal - 100).all()
        if back == 0:  # a run from the 1 forecast to gain 4+ yards is clipped to the goal line
            assert (pred["q90"] == to_goal).any()


def test_platt_scaling_fixes_an_overconfident_chance():
    rng = np.random.default_rng(1)
    true = rng.uniform(0.05, 0.6, 20000)
    y = (rng.random(true.size) < true).astype(float)
    logit = np.log(true / (1 - true))
    loud = 1 / (1 + np.exp(-1.6 * logit))  # too sure in both directions
    a, b = models.platt_fit(loud, y, np.ones(y.size))
    assert b == pytest.approx(1 / 1.6, abs=0.05)
    fixed = models.platt_apply((a, b), loud)
    assert np.abs(fixed - true).mean() < np.abs(loud - true).mean() / 3
    d = _world().with_columns(y=c("pressure_y"), weight=pl.lit(1.0))
    m = models.fit(d, get("pressure_prob"), plays.FIELD_SETS["live"], "trees", calibrate=True)
    assert "platt" in m.parts and m.predict(d.head(50))["mean"].is_between(0, 1).all()


def test_the_runner_finds_the_blitz_and_ships_the_live_model():
    d = _world()
    o = get("pressure_prob")
    frame, fitted = run.walk(d, o, [2023, 2024], run.RUNGS)
    assert frame.height == 4000 and set(frame["season"]) == {2024}  # pressure starts in 2023
    choice = run.choose(frame, o)
    assert choice["shipped"] in ("3-live-linear", "4-live-trees")
    assert run.share_removed(frame, choice["shipped"]) > run.share_removed(
        frame, "2-situation-trees"
    )
    hist = run.history_rows(frame, o, choice["shipped"], fitted, "r1")
    check_output(hist, plays.KEYS, "probability")
    assert (hist["train_end"] < hist["as_of"]).all()


def test_training_rows_must_be_known_before_the_season():
    d = _world().with_columns(
        known_at=pl.when(c("season") == 2023).then(pl.lit(datetime(2025, 1, 1, tzinfo=UTC)))
        .otherwise(c("known_at"))
    )  # fmt: skip
    with pytest.raises(ValueError, match="weren't known"):
        run.training_rows(d, get("pressure_prob"), 2024)


def test_losses_are_log_loss_and_mean_pinball():
    p = pl.DataFrame({"y": [1.0, 0.0], "mean": [0.8, 0.2]})
    out = run.losses(p, "probability")
    assert out["loss"].to_list() == pytest.approx([-np.log(0.8)] * 2)
    a = pl.DataFrame({"y": [5.0], "mean": [4.0], "q10": [0.0], "q50": [4.0], "q90": [10.0]})
    # pinball at 0.1: 0.1*5; at 0.5: 0.5*1; at 0.9: 0.1*5
    assert run.losses(a, "amount")["loss"][0] == pytest.approx((0.5 + 0.5 + 0.5) / 3)


def test_the_nulls_keep_each_weeks_values_and_break_the_link():
    d = _world(n=400).with_columns(y=c("pressure_y"))
    s = run.shuffle_outcomes(1)(d)
    for (_, _), g in d.group_by("season", "week"):
        same = s.join(g.select("game_id", "play_id"), on=["game_id", "play_id"])
        assert sorted(same["y"]) == sorted(g["y"])
    m = run.shuffle_calls(1)(d)
    assert m.select(plays.SITUATION).equals(d.select(plays.SITUATION))
    assert not m["n_blitzers"].equals(d["n_blitzers"])
    # the call fields move together, as one play's calls
    cols = ["n_blitzers", "is_screen_pass", "season", "week"]
    assert sorted(m.select(cols).rows()) == sorted(d.select(cols).rows())


def _scored(name: str, ids: list[int], exp: list[float], sit: list[float], y: list[float]):
    return pl.DataFrame(
        {"game_id": ["g1"] * len(ids), "play_id": ids, "season": [2024] * len(ids),
         "week": [3] * len(ids), "y": y, "4-live-trees:mean": exp, "2-situation-trees:mean": sit}
    ).with_columns(c("season").cast(pl.Int32))  # fmt: skip


def test_a_plays_context_is_its_expected_success_over_the_league():
    from pcf.experts.context_live import context

    scored = {
        "run_success_prob": _scored("r", [1, 2], [0.5, 0.3], [0.4, 0.4], [1.0, 0.0]),
        "dropback_success_prob": _scored("d", [3], [0.6], [0.5], [1.0]),
    }
    shipped = {k: "4-live-trees" for k in scored} | {
        f"{k}:situation": "2-situation-trees" for k in scored
    }
    p = context.play_context(scored, shipped, {2024: 0.4}).sort("play_id")
    assert p["ctx_success"].to_list() == pytest.approx([0.1, -0.1, 0.2])
    assert p["ctx_calls"].to_list() == pytest.approx([0.1, -0.1, 0.1])
    with pytest.raises(ValueError, match="league"):
        context.play_context(scored, shipped, {2023: 0.4})


def test_a_players_context_weights_plays_by_his_chance_and_teams_count_each_play_once():
    from pcf.experts.context_live import context

    p = pl.DataFrame({"game_id": ["g1"] * 2, "play_id": [1, 2], "season": [2024] * 2,
                      "week": [3] * 2, "ctx_success": [0.2, -0.1], "ctx_success_sit": [0.0] * 2,
                      "ctx_calls": [0.2, -0.1], "actual": [0.6, -0.4]})  # fmt: skip
    field = pl.DataFrame({"game_id": ["g1"] * 3, "play_id": [1, 2, 1], "gsis_id": ["a", "a", "b"],
                          "side": ["offense"] * 3, "team": ["KC"] * 3, "season": [2024] * 3,
                          "week": [3] * 3, "chance": [1.0, 0.5, 0.25],
                          "position": ["RB", "RB", "WR"]})  # fmt: skip
    pg = context.player_game(p, field)
    a = pg.filter(c("gsis_id") == "a").row(0, named=True)
    assert a["plays"] == pytest.approx(1.5)
    assert a["ctx_success"] == pytest.approx((0.2 - 0.05) / 1.5)
    table = pl.DataFrame({"game_id": ["g1"] * 2, "play_id": [1, 2], "posteam": ["KC"] * 2,
                          "defteam": ["BUF"] * 2})  # fmt: skip
    tg = context.team_game(p, table)
    assert tg.filter(c("side") == "defense")["team"].item() == "BUF"
    assert tg.filter(c("side") == "offense")["ctx_success"].item() == pytest.approx(0.05)
    crew = context.personnel(field)
    assert crew.filter(c("play_id") == 1)["n_rb_map"].item() == 1.0
    assert crew.filter(c("play_id") == 1)["n_wr_map"].item() == 0.25
    assert crew.filter(c("play_id") == 2)["n_wr_map"].item() == 0.0
