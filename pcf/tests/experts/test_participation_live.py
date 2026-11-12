"""participation-live: the grid, history, the on-field model, the balanced chain and the best
guess, on small synthetic games."""

import numpy as np
import polars as pl
import pytest

from pcf.experts.participation_live import chain, grid, history, model, score
from pcf.experts.participation_live.reconstruct import _empty_sums

c = pl.col
T = 24  # snaps
PART = 8  # part-timers on offense, 5 of them on each snap
FULL = 6  # on every snap


def _truth_lineups(seed: int = 0) -> np.ndarray:
    """(T, PART) on/off: 5 of 8 on each snap, sticky from snap to snap (a rotation)."""
    rng = np.random.default_rng(seed)
    on = np.zeros((T, PART), bool)
    cur = rng.choice(PART, 5, replace=False)
    for t in range(T):
        if t and rng.random() < 0.4:  # one change
            out_ = rng.choice(cur)
            new = rng.choice([j for j in range(PART) if j not in cur])
            cur = np.array([j if j != out_ else new for j in cur])
        on[t, cur] = True
    return on


def _world(seed: int = 0, game: str = "2020_01_KC_BUF", season: int = 2020):
    """A synthetic game's play-by-play and snap counts (offense KC only), and its answer key."""
    on = _truth_lineups(seed)
    players = [f"F{i}" for i in range(FULL)] + [f"P{j}" for j in range(PART)]
    pos = ["T", "G", "C", "G", "T", "QB"] + ["WR", "WR", "WR", "TE", "TE", "RB", "RB", "WR"]
    rows = []
    for t in range(T):
        rows.append(
            {
                "game_id": game, "play_id": 100 + t, "season": season, "special_teams_play": 0,
                "posteam": "KC", "defteam": "BUF", "season_type": "REG", "week": 1,
                "fixed_drive": 1 + t // 6, "qtr": 1 + t // 7, "down": 1 + t % 3, "ydstogo": 10,
                "yardline_100": 60 - t, "score_differential": 0, "half_seconds_remaining": 1800,
                "no_huddle": 0, "shotgun": t % 2, "play_type": "pass", "pass": 1,
                "order_sequence": t,
                # the receiver: the first part-timer on (named, so on for certain)
                "receiver_player_id": players[FULL + int(np.where(on[t])[0][0])] if t % 2 else None,
                "passer_player_id": "F5",
            }
        )  # fmt: skip
    pbp = pl.DataFrame(rows).with_columns(c("season").cast(pl.Int32))
    snaps = [T] * FULL + on.sum(0).tolist()
    pg = pl.DataFrame(
        {
            "gsis_id": players,
            "game_id": game,
            "team": "KC",
            "position": pos,
            "offense_snaps": [float(x) for x in snaps],
            "defense_snaps": 0.0,
        }
    )
    key = [(game, 100 + t, "offense", p) for t in range(T) for p in players[:FULL]]
    key += [
        (game, 100 + t, "offense", players[FULL + j])
        for t in range(T)
        for j in range(PART)
        if on[t, j]
    ]
    pp = pl.DataFrame(key, schema=["game_id", "play_id", "side", "gsis_id"], orient="row")
    return pbp, pg, pp, on


def _featured(seed=0, game="2020_01_KC_BUF", season=2020):
    pbp, pg, pp, on = _world(seed, game, season)
    g = grid.grid(pbp, pg).filter(c("side") == "offense")
    ps, ts = _empty_sums()
    coaches = pl.DataFrame({"game_id": [game], "team": ["KC"], "coach": ["X"], "season": [season]})
    f = model.cell_columns(
        history.features(g, ps, ts, coaches.with_columns(c("season").cast(pl.Int32)))
    )
    return grid.with_truth(f, grid.truth(pp)), on


def test_grid_pins_and_sequence_flags():
    g, _ = _featured()
    assert g.select("play_id").n_unique() == T
    full = set(g.filter(c("full"))["gsis_id"].unique().to_list())
    every = g.group_by("gsis_id").agg(c("on").sum())
    assert full == set(every.filter(c("on") == T)["gsis_id"].to_list())
    assert {f"F{i}" for i in range(FULL)} <= full
    # the named receivers are pinned and truly on
    assert g.filter(c("named"))["on"].min() == 1
    first = g.filter(c("gsis_id") == "P0").sort("n")
    assert first["start"].to_list()[:2] == [True, False]
    assert first["start2"].to_list()[:2] == [False, True]
    # a new drive every 6 snaps: the snap after one isn't in the same drive
    assert first["sd"].to_list()[6] is False and first["sd"].to_list()[7] is True
    assert first["sd2"].to_list()[7] is False and first["sd2"].to_list()[8] is True
    # every part-timer's share is his snaps x 11 / the side's
    assert g.filter(c("gsis_id") == "P0")["share"][0] == pytest.approx(
        first["on"].sum() * 11 / (11 * T)
    )


def test_balanced_chain_meets_both_totals_and_pins():
    rng = np.random.default_rng(1)
    B, Tn, J = 3, 15, 7
    real = np.ones((B, Tn, J), bool)
    real[2, 10:] = False
    real[1, :, 6] = False
    p1 = rng.uniform(0.2, 0.8, (B, Tn, J, 2, 2))
    allow = np.ones((B, Tn, J), bool)
    allow[0, 4, 1] = False
    rows = np.where(real.any(2), 3.0, 0.0)
    cols = rows.sum(1, keepdims=True) * np.ones((B, J)) / real.any(1).sum(1, keepdims=True)
    cols = np.where(real.any(1), cols, 0)
    m = chain._solve(p1, allow, real, rows, cols)
    assert np.abs(m.sum(2) - rows).max() < 1e-3
    assert np.abs(m.sum(1) - cols).max() < 0.05
    assert m[0, 4, 1] == pytest.approx(1.0)
    assert m[~real].max() == 0


def test_memory_moves_chances_along_the_drive():
    """With stickiness, a named player's neighbours in the same drive become more likely on."""
    p1 = np.full((1, 5, 2, 2, 2), 0.5)
    p1[..., 1] = 0.9  # on the snap before → likely on
    p1[..., 0] = 0.1
    p1[:, 0] = 0.5
    real = np.ones((1, 5, 2), bool)
    allow = np.ones((1, 5, 2), bool)
    allow[0, 2, 0] = False  # player 0 named on snap 2
    m, _ = chain._forward_backward(p1, np.zeros((1, 5, 2)), allow, real)
    assert m[0, 2, 0] == pytest.approx(1.0)
    assert m[0, 1, 0] > 0.8 and m[0, 3, 0] > 0.8
    assert m[0, 1, 1] == pytest.approx(0.5, abs=1e-6)  # player 1 has no evidence


def _training(n_games=40):
    frames = [_featured(seed=s, game=f"2020_{s:02d}_KC_BUF")[0] for s in range(n_games)]
    return pl.concat(frames)


def test_sequence_model_learns_stickiness_and_beats_shuffled():
    train = _training()
    train = train.with_columns(group=pl.lit("WR"))  # one group, enough rows
    old = model.MIN_ROWS
    model.MIN_ROWS = 100
    try:
        seq = model.fit(train.filter(~c("full")), "sequence")
        shuf = model.fit(train.filter(~c("full")), "shuffled")
    finally:
        model.MIN_ROWS = old
    w = dict(zip(model.MEMORY, seq.groups["WR"].memory, strict=True))
    assert w["v_sd"] > 1.0  # on the snap before, same drive → on now
    test, _ = _featured(seed=99, game="2020_99_KC_BUF")
    test = test.with_columns(group=pl.lit("WR"))
    out = {}
    for k, m in (("sequence", seq), ("shuffled", shuf)):
        p = chain.infer(test, m).filter(~c("pinned"))
        out[k] = score.log_loss(p["p"].to_numpy(), p["on"].to_numpy().astype(float))
    assert out["sequence"] < out["shuffled"]


def test_infer_and_best_guess_keep_11_and_the_snap_totals():
    test, on = _featured(seed=3)
    m = model.fit(test.filter(~c("full")), "share")
    g = chain.best_guess(chain.infer(test, m))
    per = g.group_by("play_id").agg(sp=c("p").sum(), sb=c("best").sum())
    assert (per["sp"] - 11).abs().max() < 1e-3
    assert (per["sb"] == 11).all()
    assert g.filter(c("pinned"))["p"].min() == pytest.approx(1.0)
    assert g.filter(c("pinned"))["best"].all()
    tot = g.group_by("gsis_id").agg(sb=c("best").sum(), target=c("share").first() * T)
    assert (tot["sb"] - tot["target"]).abs().max() <= 1.0 + 1e-9


def test_history_uses_only_earlier_seasons():
    g, _ = _featured(season=2021, game="2021_01_KC_BUF")
    g20, _ = _featured(season=2020)
    ps, ts = history.season_sums(g20)
    ps_same, ts_same = history.season_sums(g)  # the season's own: must be ignored
    coaches = pl.DataFrame(
        {"game_id": ["2021_01_KC_BUF"], "team": ["KC"], "coach": ["X"], "season": [2021]}
    ).with_columns(c("season").cast(pl.Int32))
    base = g.select(
        grid.CELL_KEYS
        + list(grid.FLAG_COLUMNS)
        + [x for x in g.columns if x in ("season", "team", "group", "full", "share", "sd", "n")]
    )
    a = history.features(base, ps, ts, coaches)
    b = history.features(base, pl.concat([ps, ps_same]), pl.concat([ts, ts_same]), coaches)
    assert a.select(history.PLAYER_COLUMNS).equals(b.select(history.PLAYER_COLUMNS))
    assert a["ph_n"].max() > 0  # 2020 is used


def test_scores_on_a_perfect_guess():
    test, _ = _featured(seed=5)
    t = test.with_columns(p_x=c("on").cast(pl.Float64) * 0.98 + 0.01, best_x=c("on") == 1)
    s = score.per_play(t, "x")
    assert s["offense_open_right"] == 1.0 and s["offense_all_11"] == 1.0
    sub = score.substitution(t, "x")
    assert sub["subs_per_snap_best"] == pytest.approx(sub["subs_per_snap_true"])


def test_likeliest_takes_each_plays_top_chances():
    test, _ = _featured(seed=4)
    m = model.fit(test.filter(~c("full")), "share")
    g = chain.likeliest(chain.infer(test, m), mix=False)
    per = g.group_by("play_id").agg(c("likeliest").sum())
    assert (per["likeliest"] == 11).all()
    assert g.filter(c("pinned"))["likeliest"].all()
    # within a play, every open player picked has a chance at least as high as any left out
    open_ = g.filter(~c("pinned"))
    worst_in = open_.filter(c("likeliest")).group_by("play_id").agg(c("p").min())
    best_out = open_.filter(~c("likeliest")).group_by("play_id").agg(c("p").max().alias("q"))
    j = worst_in.join(best_out, on="play_id")
    assert (j["p"] >= j["q"] - 1e-9).all()


def test_position_mix_keeps_each_plays_expected_count():
    """With the mix, each play's count of each group is its chances' sum, rounded; every play
    still has 11."""
    test, _ = _featured(seed=6)
    m = model.fit(test.filter(~c("full")), "share")
    inf = chain.infer(test, m)
    for totals in (True, False):
        g = chain.best_guess(inf, totals=totals, mix=True)
        per = (
            g.filter(~c("pinned"))
            .group_by("play_id", "group")
            .agg(e=c("p").sum(), k=c("best").sum())
        )
        assert ((per["k"] - per["e"]).abs() < 1.0 + 1e-6).all()
        assert (g.group_by("play_id").agg(c("best").sum())["best"] == 11).all()


def test_apportion_adds_to_the_rows_and_stays_near():
    e = np.array([[1.4, 1.4, 2.2], [0.5, 0.5, 2.0]])
    k = chain._apportion(e, np.array([5.0, 3.0]), np.full((2, 3), 3.0))
    assert k.sum(1).tolist() == [5, 3]
    assert (np.abs(k - e) < 1).all()
