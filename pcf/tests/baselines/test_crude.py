"""The crude forecaster and its yardstick (crude-forecaster): the crude inputs, the windows, the
rungs and their ranges, the point-in-time features on a small synthetic league, and the
yardstick's arithmetic (paired gains, Shapley shares that add up, the shuffled copy)."""

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from pcf.baselines.crude import features as F
from pcf.baselines.crude import fitting
from pcf.baselines.crude import yardstick as Y
from pcf.baselines.crude.model import (
    VARIANTS,
    Crude,
    played_games,
    team_windows,
    variant,
    with_experts,
)
from pcf.core.contract import check_expert, find_all, project_of
from pcf.data.gateway import FrameSource, Gateway, history_run

c = pl.col
TS = pl.Datetime("us", "UTC")


# ---------------------------------------------------------------- crude inputs
def _games(rows):
    return pl.DataFrame(rows, schema=["gsis_id", "season", "week", "y", "vol", "fd", "td"],
                        orient="row")  # fmt: skip


def test_crude_inputs_average_this_season_the_last_four_and_last_season():
    g = _games([
        ("a", 2017, 1, 10.0, 2, 1, 0), ("a", 2017, 2, 30.0, 4, 1, 1),
        ("a", 2018, 1, 50.0, 5, 2, 0), ("a", 2018, 2, 70.0, 7, 3, 1), ("a", 2018, 3, 90.0, 9, 4, 0),
    ])  # fmt: skip
    out = F.crude_inputs(g, "gsis_id", 2018).row(0, named=True)
    assert out["y_s"] == pytest.approx(70.0)
    assert out["y_l4"] == pytest.approx((30 + 50 + 70 + 90) / 4)
    assert out["y_ls"] == pytest.approx(20.0)
    assert out["y_cum"] == 210.0
    assert out["y_trend"] == pytest.approx(out["y_l4"] - 70.0)
    assert out["y_sd"] == pytest.approx(20.0)
    assert out["ypa_s"] == pytest.approx(210 / 21)
    assert out["n_games"] == 3 and out["has_ls"] == 1.0 and out["no_history"] == 0.0


def test_week_one_takes_last_season_for_the_season_so_far():
    g = _games([("a", 2017, 1, 10.0, 2, 1, 0), ("a", 2017, 2, 30.0, 4, 1, 1)])
    out = F.crude_inputs(g, "gsis_id", 2018).row(0, named=True)
    assert out["y_s"] == pytest.approx(20.0) and out["vol_s"] == pytest.approx(3.0)
    assert out["y_sd"] == pytest.approx(out["y_ls_sd"]) and out["n_games"] == 0
    assert out["ypa_s"] == pytest.approx(40 / 6)


def test_a_unit_with_no_games_gets_zeros_and_says_so():
    g = _games([("a", 2017, 1, 10.0, 2, 1, 0)])
    rows = pl.DataFrame({"gsis_id": ["a", "rookie"]})
    out = F.with_crude(rows, F.crude_inputs(g, "gsis_id", 2018), "gsis_id", "gsis_id")
    rookie = out.filter(c("gsis_id") == "rookie").row(0, named=True)
    assert rookie["no_history"] == 1.0 and rookie["y_s"] == F.NO_HISTORY
    assert out.filter(c("gsis_id") == "a")["no_history"].item() == 0.0
    assert out.select(F.CRUDE).null_count().sum_horizontal().item() == 0


def test_a_game_counts_as_played_with_a_stat_or_an_offensive_snap():
    pg = pl.DataFrame({
        "stats_known_at": [datetime(2018, 1, 1, tzinfo=UTC), None, None],
        "snaps_known_at": [None, *[datetime(2018, 1, 1, tzinfo=UTC)] * 2],
        "offense_snaps": [None, 12, 0],
    })  # fmt: skip
    assert played_games(pg).height == 2


# ---------------------------------------------------------------- windows
def _sched():
    return pl.DataFrame({
        "game_id": [f"g{w}" for w in range(1, 6)], "team": ["A"] * 5,
        "season": [2018] * 5, "week": [1, 2, 4, 5, 6],
    })  # fmt: skip


def test_the_next_three_windows_are_complete_and_skip_the_bye():
    w = team_windows(_sched(), 3)
    assert w["game_id"].unique().sort().to_list() == ["g1", "g2", "g3"]  # g4, g5 lack 3 games
    g2 = w.filter(c("game_id") == "g2").sort("w_week")
    assert g2["w_week"].to_list() == [2, 4, 5] and g2["n"].unique().to_list() == [3]


def test_the_rest_of_season_window_runs_to_the_last_game():
    w = team_windows(_sched(), None)
    assert w.filter(c("game_id") == "g1").height == 5
    assert w.filter(c("game_id") == "g5").height == 1
    assert team_windows(_sched(), 1).height == 5


# ---------------------------------------------------------------- the rungs
def _train(n=2000, seed=0):
    rng = np.random.default_rng(seed)
    a = rng.uniform(0, 100, n)
    pos = rng.choice(["WR", "TE"], n)
    y = 0.8 * a + rng.normal(0, 10 + 0.2 * a, n)
    return pl.DataFrame({"y_s": a, "noise": rng.normal(size=n), "position": pos, "y": y,
                         "weight": np.ones(n)})  # fmt: skip


@pytest.mark.parametrize("method", fitting.METHODS)
def test_every_rung_gives_ordered_ranges_that_cover_about_80(method):
    train, test = _train(seed=1), _train(seed=2)
    model = fitting.fit(method, train, ["y_s", "noise"], ["position"], 0, "y_s")
    out = fitting.predict(model, test, ["y_s", "noise"], ["position"])
    assert (out["q10"] <= out["q50"]).all() and (out["q50"] <= out["q90"]).all()
    cover = ((out["y"] >= out["q10"]) & (out["y"] <= out["q90"])).mean()
    assert 0.74 < cover < 0.86
    if method == "season":
        assert np.allclose(out["mean"], test["y_s"])
    else:
        err = ((out["mean"] - out["y"]) ** 2).mean()
        assert err < ((test["y_s"] - test["y"]) ** 2).mean()  # it learns the 0.8


def test_ranges_widen_with_the_forecast():
    model = fitting.fit("lasso", _train(seed=1), ["y_s"], [], 0, "y_s")
    out = fitting.predict(model, _train(seed=2), ["y_s"], []).sort("mean")
    width = (out["q90"] - out["q10"]).to_numpy()
    assert width[-100:].mean() > width[:100].mean()


def test_lasso_shap_values_add_up_to_the_forecast():
    train = _train(seed=1)
    model = fitting.fit("lasso", train, ["y_s", "noise"], [], 0, "y_s")
    x = train.select("y_s", "noise").to_numpy()
    contrib = fitting.contributions(model, x, ["y_s", "noise"])
    pred = fitting.predict_core(model, x, x[:, 0])
    assert np.allclose(contrib.sum(axis=1) + model["lasso"]["y_mu"], pred)


# ---------------------------------------------------------------- the variants
def test_every_variant_meets_the_contract_and_is_found():
    found = find_all("crude-forecaster")
    assert len(found) == len(VARIANTS) == 4 * 3 * 4
    for cls in found:
        check_expert(cls)
    assert Crude not in found


def test_a_rung_names_the_rungs_below_it_as_baselines():
    names = [b.variant for b in variant("receiving", "next", "mix").baselines()]
    assert names == ["receiving_next_season", "receiving_next_lasso", "receiving_next_trees"]
    assert variant("team", "rest", "season").baselines() == []


def test_adding_an_expert_adds_only_its_columns():
    base = variant("rushing", "next3", "lasso")
    plus = with_experts(base, ("participation", "elo"))()
    extra = set(plus.columns) - set(base().columns)
    assert extra == {*F.PLAYER_EXPERTS, "part_h3", *F.TEAM_EXPERTS["elo"]}
    with pytest.raises(ValueError, match="no expert group"):
        _ = with_experts(variant("team"), ("participation",))().columns


# ---------------------------------------------------------------- the variant pins (0037)
def test_a_variant_input_reads_the_run_the_registry_pins_for_it(tmp_path):
    reg = tmp_path / "registry.yaml"
    reg.write_text(
        "projects:\n  - id: elo\n    history_runs:\n      margin: {1: abc}\n", encoding="utf-8"
    )
    assert history_run("elo/margin", 1, reg) == "abc"
    with pytest.raises(KeyError):
        history_run("elo/total", 1, reg)
    with pytest.raises(KeyError):
        history_run("elo/margin", 2, reg)
    assert project_of("elo/margin") == "elo" and project_of("elo") == "elo"


# ---------------------------------------------------------------- a small league
SEASONS = (2017, 2018)
WEEKS = 4
TEAMS = ("A", "B", "C", "D")


def _kick(season: int, week: int) -> datetime:
    return datetime(season, 9, 10, 17, tzinfo=UTC) + timedelta(weeks=week - 1)


def _league():
    rng = np.random.default_rng(5)
    sched, team_stats, roster, stats, snaps = [], [], [], [], []
    for s in SEASONS:
        for w in range(1, WEEKS + 1):
            pairs = [("A", "B"), ("C", "D")] if w % 2 else [("A", "C"), ("B", "D")]
            for home, away in pairs:
                gid = f"{s}_{w:02d}_{away}_{home}"
                kick = _kick(s, w)
                for team, opp in ((home, away), (away, home)):
                    sched.append({"game_id": gid, "season": s, "week": w, "game_type": "REG",
                                  "team": team, "opponent": opp, "home": team == home,
                                  "known_at": kick - timedelta(days=90)})  # fmt: skip
                    known = kick + timedelta(days=1)
                    team_stats.append({"game_id": gid, "team": team, "season": s,
                                       "passing_yards": 200 + 10 * w,
                                       "rushing_yards": 100.0, "attempts": 30, "carries": 25,
                                       "sacks_suffered": 2, "passing_first_downs": 12,
                                       "rushing_first_downs": 6, "passing_tds": 1, "rushing_tds": 1,
                                       "known_at": known})  # fmt: skip
                    for p in ("WR", "TE"):
                        pid = f"{team}_{p}"
                        roster.append({"gsis_id": pid, "game_id": gid, "season": s, "week": w,
                                       "team": team, "opponent": opp, "position": p,
                                       "known_at": kick - timedelta(days=5)})  # fmt: skip
                        stats.append({"gsis_id": pid, "game_id": gid, "season": s,
                                      "receiving_yards": float(rng.integers(0, 120)),
                                      "targets": 6, "receiving_first_downs": 3,
                                      "receiving_tds": 0, "known_at": known})  # fmt: skip
                        snaps.append({"gsis_id": pid, "game_id": gid, "season": s,
                                      "offense_snaps": 40,
                                      "known_at": known})  # fmt: skip
    frames = {
        ("team_game", "schedule"): pl.DataFrame(sched),
        ("team_game", "stats"): pl.DataFrame(team_stats),
        ("player_game", "roster"): pl.DataFrame(roster),
        ("player_game", "stats"): pl.DataFrame(stats),
        ("player_game", "snaps"): pl.DataFrame(snaps),
    }
    for k, f in frames.items():
        frames[k] = f.with_columns(c("known_at").cast(TS), *(
            [c("season").cast(pl.Int32)]
            + ([c("week").cast(pl.Int32)] if "week" in f.columns else [])
        ))  # fmt: skip
    return frames


def _outputs(frames):
    """Every pinned expert input, made just before the moment, by a model trained before that."""
    sched = frames[("team_game", "schedule")]
    games = (
        sched.select("game_id", "season", "week")
        .unique()
        .with_columns(
            as_of=pl.struct("season", "week").map_elements(
                lambda r: _kick(r["season"], r["week"]) - timedelta(hours=30), return_dtype=TS
            )
        )
    )
    meta = {"quantity": "x", "q10": 0.0, "q50": 0.0, "q90": 0.0, "model": "m",
            "model_version": "1", "run_id": "r", "cadence": "in_season"}  # fmt: skip
    teams = sched.select("game_id", "team").join(games, on="game_id")
    players = (
        frames[("player_game", "roster")].select("gsis_id", "game_id").join(games, on="game_id")
    )
    home = sched.filter(c("home")).select("game_id")
    out = {}
    for key in F.EXPERT_INPUTS:
        if key.startswith("participation"):
            df = players.with_columns(mean=pl.lit(0.8), p_nonzero=pl.lit(0.9),
                                      if_nonzero_mean=pl.lit(0.85))  # fmt: skip
        elif key.startswith("elo"):
            df = home.join(games, on="game_id").with_columns(
                mean=pl.lit(2.0), home_rating=pl.lit(1.0), away_rating=pl.lit(-1.0),
                home_offense=pl.lit(0.5), away_offense=pl.lit(0.2), home_defense=pl.lit(0.1),
                away_defense=pl.lit(-0.3),
            )  # fmt: skip
        elif key.startswith("team-efficiency"):
            df = teams.with_columns(
                **{
                    k: pl.lit(0.05)
                    for k in (
                        "mean",
                        "off_rating",
                        "def_rating",
                        "off_pass",
                        "def_pass",
                        "off_run",
                        "def_run",
                    )
                }
            )
        else:
            df = teams.with_columns(mean=pl.lit(60.0))
        out[key] = df.with_columns(train_end=c("as_of") - pl.duration(days=1), **{
            k: pl.lit(v) for k, v in meta.items()})  # fmt: skip
    return lambda project_id, version: out[project_id]


def _gateway(frames, outputs=None):
    g = Gateway(FrameSource(frames), outputs=outputs or _outputs(frames))
    g.finished = lambda at: []  # no post-season parts are read; the league has no calendar
    return g


def _games_at(season, week):
    return pl.DataFrame({"game_id": [f"{season}_{week:02d}_B_A", f"{season}_{week:02d}_D_C"]
                         if week % 2 else [f"{season}_{week:02d}_C_A", f"{season}_{week:02d}_D_B"],
                         "season": [season] * 2, "week": [week] * 2})  # fmt: skip


@pytest.mark.parametrize("target", ["receiving", "team"])
def test_features_at_a_moment_use_only_games_known_by_then(target):
    """Deleting everything known after the moment changes nothing (leakage check 4, small)."""
    frames = _league()
    moment = _kick(2018, 3) - timedelta(hours=29)  # Saturday noon-ish before week 3
    e = variant(target, "next", "lasso")()
    full = e.features(_gateway(frames).view(moment, "in_season", e.inputs), _games_at(2018, 3))
    cut = {k: f.filter(c("known_at") <= moment) for k, f in frames.items()}
    past = e.features(_gateway(cut).view(moment, "in_season", e.inputs), _games_at(2018, 3))
    keys = e.keys()
    assert full.height > 0
    assert full.sort(keys).select(e.columns).equals(past.sort(keys).select(e.columns))
    if target == "receiving":
        row = full.filter(c("gsis_id") == "A_WR").row(0, named=True)
        a = frames[("player_game", "stats")].filter(
            (c("gsis_id") == "A_WR") & c("game_id").str.starts_with("2018")
            & (c("game_id").str.slice(5, 2).cast(pl.Int32) < 3)
        )["receiving_yards"]  # fmt: skip
        assert row["y_s"] == pytest.approx(a.mean()) and row["n_games"] == 2
        assert row["part_play"] == pytest.approx(0.9) and row["elo_margin"] in (2.0, -2.0)
    else:
        row = full.filter(c("team") == "A").row(0, named=True)
        assert row["off_y_s"] == pytest.approx(np.mean([310.0, 320.0]))
        assert row["elo_own"] == 1.0 and row["pace_opp_plays"] == 60.0


def test_a_player_below_the_row_rule_isnt_forecast():
    frames = _league()
    out = _outputs(frames)

    def low(project_id, version):
        df = out(project_id, version)
        if project_id == "participation/trees_week":
            df = df.with_columns(p_nonzero=pl.when(c("gsis_id") == "A_TE").then(0.3).otherwise(0.9))
        return df

    g = _gateway(frames, low)
    e = variant("receiving", "next", "lasso")()
    moment = _kick(2018, 3) - timedelta(hours=29)
    f = e.features(g.view(moment, "in_season", e.inputs), _games_at(2018, 3))
    assert "A_TE" not in f["gsis_id"].to_list() and "A_WR" in f["gsis_id"].to_list()


# ---------------------------------------------------------------- the yardstick's arithmetic
def _board(members_effect: dict[str, float], seed=0, weeks=40, per=50):
    """A board with forecasts filled in by hand: each member removes its share of the noise,
    and members add up (no overlap)."""
    rng = np.random.default_rng(seed)
    n = weeks * per
    keys = pl.DataFrame({"gsis_id": [f"p{i}" for i in range(n)],
                         "game_id": [f"g{i // per}" for i in range(n)]})  # fmt: skip
    y = rng.normal(50, 20, n)
    parts = {m: rng.normal(0, 10 * np.sqrt(e), n) for m, e in members_effect.items()}
    step = np.arange(n) // per
    floor = rng.normal(0, 3, n)  # what no member removes
    base = Y.Board(variant("receiving"), pl.DataFrame(), pl.DataFrame(), [], [])
    names = list(members_effect)
    import itertools as it

    for r in range(len(names) + 1):
        for combo in it.combinations(names, r):
            mean = y + sum(parts[m] for m in names if m not in combo) + floor
            df = keys.with_columns(step=pl.Series(step), season=pl.lit(2020), y=pl.Series(y),
                                   mean=pl.Series(mean), q10=pl.Series(mean - 20),
                                   q50=pl.Series(mean), q90=pl.Series(mean + 20))  # fmt: skip
            base.preds[(base.base.variant, tuple(sorted(combo)), (), None, None, False, None)] = df
    return base, {m: ((m,), ()) for m in names}


def test_identical_forecasts_gain_nothing_and_a_better_one_gains():
    board, members = _board({"elo": 1.0})
    v = board.base.variant
    crude = board.preds[(v, (), (), None, None, False, None)]
    g0 = Y.gain(crude, crude, board.keys)
    assert g0.share == 0 and g0.verdict == "neutral"
    g = Y.gain(board.preds[(v, ("elo",), (), None, None, False, None)], crude, board.keys)
    assert g.lo > 0 and g.share > 0.3


def test_shapley_shares_add_up_to_the_all_member_gain():
    board, members = _board({"elo": 1.0, "pace": 0.5, "schemes": 0.0})
    t = Y.shapley(board, members)
    assert t["share"].sum() == pytest.approx(t["all_members"][0], rel=1e-9)
    by = {r["member"]: r for r in t.iter_rows(named=True)}
    assert by["elo"]["share"] > by["pace"]["share"] > 0
    assert by["schemes"]["share"] == pytest.approx(0, abs=1e-12)  # it removes nothing
    # no overlap between members: alone and fair share agree
    assert by["elo"]["alone"] == pytest.approx(by["elo"]["share"], rel=0.05)


def test_the_shuffled_copy_keeps_each_week_s_values():
    feats = pl.DataFrame(
        {"step": [1, 1, 1, 2, 2], **{col: [1.0, 2.0, 3.0, 4.0, 5.0] for col in F.PLAYER_EXPERTS}}
    )
    out = Y.with_shuffled(feats, variant("receiving"), seed=3)
    for col in F.PLAYER_EXPERTS:
        for s in (1, 2):
            week = out.filter(c("step") == s)
            assert sorted(week[f"shuffled_{col}"]) == sorted(week[col])
    # the columns move together: a row's shuffled values all come from one other row
    assert out.select((c("shuffled_part_share") == c("shuffled_part_play")).all()).item()


def test_a_missing_expert_value_gets_the_moment_s_median_and_never_drops_a_row():
    rows = pl.DataFrame(
        {"a": [1.0, None, 3.0], "b": [None, None, None]}, schema={"a": pl.Float64, "b": pl.Float64}
    )
    out = F.fill_missing(rows, ["a", "b"])
    assert out["a"].to_list() == [1.0, 2.0, 3.0] and out["b"].to_list() == [0.0, 0.0, 0.0]


def test_coefficients_read_in_yards_per_unit_with_intervals_from_resampled_weeks():
    rng = np.random.default_rng(1)
    base = variant("receiving", method="lasso")
    weeks, per = 60, 80
    n = weeks * per
    feats = pl.DataFrame(
        {col: rng.normal(size=n) for col in base.crude_columns()}
        | {"y_s": rng.uniform(0, 80, n)}
    ).with_columns(
        gsis_id=pl.Series([f"p{i % per}" for i in range(n)]),
        game_id=pl.Series([f"g{i // per}" for i in range(n)]),
        step=pl.Series([i // per for i in range(n)]),
        step_season=pl.Series([2016 + (i // per) // 17 for i in range(n)]),
        position=pl.lit("WR"),
        as_of=pl.Series([datetime(2016, 9, 1, tzinfo=UTC) + timedelta(days=7 * (i // per))
                         for i in range(n)]).cast(TS),
    )  # fmt: skip
    y = 2.0 * feats["y_s"].to_numpy() + rng.normal(0, 5, n)
    outcomes = feats.select("gsis_id", "game_id").with_columns(y=pl.Series(y))
    board = Y.Board(base, feats, outcomes, [], [])
    t = Y.coefficients(board, draws=40, seed=0)
    row = t.filter(c("input") == "y_s").row(0, named=True)
    assert row["lo"] <= row["per_unit"] <= row["hi"]
    assert 1.9 < row["per_unit"] < 2.05 and row["kept"] == 1.0
    assert t["input"][0] == "y_s"  # the biggest per standard deviation comes first
    noise = t.filter(c("input") != "y_s")
    assert noise["per_sd"].abs().max() < 0.5  # yards per sd: pure-noise inputs stay near zero
