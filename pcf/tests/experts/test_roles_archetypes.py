"""roles-archetypes: counts, features, pooled spaces, named roles and tests, on synthetic rows."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import polars as pl
import pytest

from pcf.experts.roles_archetypes import counts as C
from pcf.experts.roles_archetypes import embed as E
from pcf.experts.roles_archetypes import evaluate as V
from pcf.experts.roles_archetypes import features as F
from pcf.experts.roles_archetypes import named as N
from pcf.experts.roles_archetypes import space as S

c = pl.col
KNOWN = datetime(2020, 2, 3, tzinfo=UTC)


def _pbp(plays: list[dict]) -> pl.DataFrame:
    base = {k: None for k in C.PBP}
    base |= {"season": 2019, "season_type": "REG", "posteam": "AAA", "defteam": "BBB",
             "two_point_attempt": 0, "game_id": "g1", "epa": 0.0, "yards_gained": 0}  # fmt: skip
    rows = [base | p for p in plays]
    return pl.DataFrame(rows, schema_overrides={k: pl.String for k in C.PBP if k.endswith("_id")}
                        | {"play_id": pl.Int64, "week": pl.Int64, "down": pl.Int64,
                           "yardline_100": pl.Int64, "qb_dropback": pl.Int64,
                           "air_yards": pl.Float64, "complete_pass": pl.Int64,
                           "epa": pl.Float64, "yards_gained": pl.Int64,
                           "two_point_attempt": pl.Int64})  # fmt: skip


def _world() -> tuple[pl.DataFrame, pl.DataFrame]:
    """Four plays in week 1, AAA on offense: a WR on every play (targeted on the passes), a TE on
    runs only, a RB on every play (carrying the runs), a DE rushing. Personnel 11 throughout."""
    plays = [
        {"play_id": 1, "week": 1, "play_type": "pass", "qb_dropback": 1, "down": 1,
         "yardline_100": 50, "air_yards": 25.0, "pass_location": "left", "receiver_player_id": "wr",
         "complete_pass": 1, "solo_tackle_1_player_id": "cb"},
        {"play_id": 2, "week": 1, "play_type": "run", "qb_dropback": 0, "down": 2,
         "yardline_100": 45, "run_location": "middle", "rusher_player_id": "rb",
         "solo_tackle_1_player_id": "de"},
        {"play_id": 3, "week": 1, "play_type": "pass", "qb_dropback": 1, "down": 3,
         "yardline_100": 15, "air_yards": 5.0, "pass_location": "middle",
         "receiver_player_id": "wr", "complete_pass": 0, "sack_player_id": "de"},
        {"play_id": 4, "week": 1, "play_type": "run", "qb_dropback": 0, "down": 1,
         "yardline_100": 10, "run_location": "left", "rusher_player_id": "rb"},
    ]  # fmt: skip
    rows = []
    for pid in (1, 2, 3, 4):
        players = [("offense", "AAA", "wr", "WR"), ("offense", "AAA", "rb", "RB"),
                   ("offense", "AAA", "te2", "TE"), ("defense", "BBB", "de", "DE"),
                   ("defense", "BBB", "cb", "CB")]  # fmt: skip
        players.append(("offense", "AAA", "te", "TE") if pid in (2, 4) else
                       ("offense", "AAA", "wr2", "WR"))  # fmt: skip
        rows += [{"game_id": "g1", "play_id": pid, "side": s, "team": t, "gsis_id": g,
                  "position": p, "known_at": KNOWN} for s, t, g, p in players]  # fmt: skip
    of = pl.DataFrame(rows)
    return _pbp(plays), of


def test_counts_read_who_was_on_and_what_he_did():
    pbp, of = _world()
    cnt, games = C.season_counts(pbp, of)
    a = cnt.filter(c("half") == "all")
    row = {r["gsis_id"]: r for r in a.iter_rows(named=True)}
    assert row["wr"]["snaps"] == 4 and row["wr"]["targets"] == 2 and row["wr"]["deep"] == 1
    assert row["te"]["snaps"] == 2 and row["te"]["run_snaps"] == 2 and row["te"]["targets"] == 0
    assert row["rb"]["carries"] == 2 and row["rb"]["outside"] == 1
    assert row["de"]["rush"] == 1 and row["de"]["tackles"] == 1 and row["de"]["solo"] == 1
    assert row["cb"]["tackle_yds"] == 0 and row["cb"]["group"] == "CB"
    # plays 2 and 4 are 12 personnel (te and te2 on), 1 and 3 are 11
    assert row["te"]["n_run_early_12_of"] == 1 and row["te"]["n_run_early_12_rz"] == 1
    assert row["wr"]["tn_pass_late_11_rz"] == 1
    assert set(a["known_at"].to_list()) == {KNOWN}
    assert games.filter(c("gsis_id") == "te")["snaps"].to_list() == [2]


def test_a_defenders_offensive_snaps_never_put_him_in_the_offenses_space():
    pbp, of = _world()
    extra = of.filter(c("gsis_id") == "wr").with_columns(
        gsis_id=pl.lit("cb"), position=pl.lit("CB")
    )
    cnt, _ = C.season_counts(pbp, pl.concat([of, extra]))
    cb = cnt.filter((c("half") == "all") & (c("gsis_id") == "cb"))
    assert cb.filter(c("side") == "offense").is_empty()  # no offensive group, no offensive row
    assert cb.filter(c("side") == "defense")["group"].to_list() == ["CB"]


def test_features_adjust_for_the_team_and_shrink_to_the_group():
    pbp, of = _world()
    cnt, _ = C.season_counts(pbp, of)
    fe = F.features(cnt, F.priors(cnt))
    te = fe.filter((c("half") == "all") & (c("gsis_id") == "te")).row(0, named=True)
    wr = fe.filter((c("half") == "all") & (c("gsis_id") == "wr")).row(0, named=True)
    assert te["adj_run"] == pytest.approx(1.0 - 0.5)  # all his snaps runs, the team's half
    assert wr["adj_run"] == pytest.approx(0.0)
    assert te["oo_run"] > 0 > F._logit(np.array([0.4]))[0]
    # 2 targets on 2 pass snaps, pulled toward the WR pool's rate by 100 snaps of prior
    pool = (2 + 0) / (2 + 2)  # wr and wr2 together
    assert wr["tgt_per_pass"] == pytest.approx((2 + 100 * pool) / (2 + 100))


def _synthetic_feats(n: int = 400, seed: int = 0, seasons=(2016, 2017, 2018)) -> pl.DataFrame:
    """Rows on a known 2-D structure in 5 features, with halves that share it plus noise."""
    rng = np.random.default_rng(seed)
    rows = []
    for s in seasons:
        lat = rng.normal(size=(n, 2)) * [3.0, 1.5]
        mix = np.array([[1, 0.5, 0, 0.2, -1], [0, 1, 1, -0.5, 0.3]])
        for half, scale in (("all", 0.2), ("odd", 0.5), ("even", 0.5)):
            x = lat @ mix + rng.normal(scale=scale, size=(n, 5))
            snaps = np.full(n, 600 if half == "all" else 300)
            for i in range(n):
                rows.append({"gsis_id": f"p{i}", "team": "T", "season": s, "side": "offense",
                             "group": "WR" if i % 2 else "TE", "half": half, "snaps": snaps[i],
                             **{f"f{j}": float(x[i, j]) for j in range(5)}})  # fmt: skip
    return pl.DataFrame(rows)


FEATS = [f"f{j}" for j in range(5)]


def test_procrustes_recovers_a_rotation():
    rng = np.random.default_rng(1)
    q, _ = np.linalg.qr(rng.normal(size=(6, 6)))
    load = np.linalg.qr(rng.normal(size=(20, 6)))[0].T
    assert np.allclose(S.align(q @ load, load), load, atol=1e-8)


def test_the_space_finds_the_structure_keeps_axes_across_refits_and_sizes_its_noise():
    fe = _synthetic_feats()
    sp1 = S.fit_space(fe, "offense", FEATS, [2016], k=2)
    sp2 = S.fit_space(fe, "offense", FEATS, [2016, 2017], ref=sp1, k=2)
    assert sp1.explained.sum() > 0.95
    assert np.all(np.abs((sp1.loadings * sp2.loadings).sum(1)) > 0.99)  # rotated to the last
    placed = S.place(sp2, fe.filter(c("season") == 2017))
    # halves are noisier than the season: their placed intervals are wider
    width = (placed["oz0_hi"] - placed["oz0_lo"]).to_numpy()
    halves = placed["half"].to_numpy() != "all"
    assert width[halves].mean() > width[~halves].mean()
    hist, fits = S.walk(fe, "offense", FEATS, [2016, 2017, 2018], k=2)
    assert sorted(fits) == [2016, 2017, 2018]
    assert hist.group_by("season").agg(c("version").first()).sort("season")[
        "version"
    ].to_list() == [2016, 2017, 2018]


def test_players_under_200_snaps_are_shrunk_toward_their_group():
    fe = _synthetic_feats(seasons=(2016,))
    sp = S.fit_space(fe, "offense", FEATS, [2016], k=2)
    one = fe.filter(c("half") == "all").head(1).with_columns(snaps=pl.lit(100))
    placed = S.place(sp, one)
    w = placed["shrink_w"][0]
    assert w == pytest.approx(100 / 300)
    raw, shrunk = placed["oz0_raw"][0], placed["oz0"][0]
    mean = sp.group_means[one["group"][0]][0]
    assert shrunk == pytest.approx(w * raw + (1 - w) * mean)


def test_the_autoencoder_codes_read_like_the_pca_axes():
    fe = _synthetic_feats(n=200, seasons=(2016,))
    sp = S.fit_space(fe, "offense", FEATS, [2016], k=2)
    emb = E.fit_embedding(fe, sp, seed=0)
    rows = fe.filter(c("half") == "all")
    z, e = sp.project(rows), emb.project(rows)
    assert abs(np.corrcoef(z[:, 0], e[:, 0])[0, 1]) > 0.9
    assert E.explained(emb) > 0.9


def test_a_valley_cut_lands_between_two_modes():
    rng = np.random.default_rng(0)
    x = np.concatenate([rng.normal(0, 1, 500), rng.normal(6, 1, 500)])
    assert 2 < N._valley(x, 0.2, 0.8) < 4


def test_named_roles_follow_the_rules_and_how_sure_falls_near_a_cut():
    cuts = {k: N.Cut(k, f, v, "test") for k, (f, v) in {
        "carrier": ("car_per_run", 0.5), "in_tight": ("adj_p11", -0.1),
        "run_tilt": ("adj_run", 0.0),
        "blocker": ("adj_run", 0.1), "slot": ("adj_p11", 0.15), "deep": ("adot", 15.0),
        "downfield": ("tkl_depth", 7.0), "rusher": ("rush_per_pass", 0.04),
        "tackler": ("tkl_per_snap", 0.09), "nickel": ("adj_p11", 0.2)}.items()}  # fmt: skip
    noise = {f: 1.0 for f in ("car_per_run", "adj_p11", "adj_run", "adot", "tkl_depth",
                              "rush_per_pass", "tkl_per_snap")}  # fmt: skip
    base = {"team": "T", "season": 2019, "half": "all", "snaps": 600, "car_per_run": 0.0,
            "adj_p11": 0.0, "adj_run": 0.0, "adot": 8.0, "tkl_depth": 3.0, "rush_per_pass": 0.0,
            "tkl_per_snap": 0.0}  # fmt: skip
    rows = pl.DataFrame([
        base | {"gsis_id": "back", "side": "offense", "group": "RB", "car_per_run": 0.8,
                "adj_run": 0.05},
        base | {"gsis_id": "slot", "side": "offense", "group": "WR", "adj_p11": 0.3},
        base | {"gsis_id": "rush", "side": "defense", "group": "OLB", "rush_per_pass": 0.06},
        base | {"gsis_id": "nick", "side": "defense", "group": "CB", "tkl_depth": 9.0,
                "adj_p11": 0.3},
        base | {"gsis_id": "edge", "side": "defense", "group": "DL", "rush_per_pass": 0.0401},
    ])  # fmt: skip
    out = {r["gsis_id"]: r for r in N.name_roles(rows, cuts, noise).iter_rows(named=True)}
    assert out["back"]["role"] == "early-down back" and out["back"]["coarse"] == "back"
    assert out["slot"]["role"] == "slot receiver"
    assert out["rush"]["role"] == "pass rusher" and out["nick"]["role"] == "slot defender"
    assert 0.5 <= out["edge"]["sure"] < out["rush"]["sure"] <= 1.0


def test_the_walk_never_reads_a_later_target_season():
    rng = np.random.default_rng(0)
    n = 600
    rows = pl.DataFrame({"x": rng.normal(size=n),
                         "target_season": np.repeat([2018, 2019, 2020], 200),
                         "gsis_id": [f"p{i}" for i in range(n)], "group": ["WR"] * n})  # fmt: skip
    rows = rows.with_columns(y=2 * c("x") + pl.Series(rng.normal(scale=0.1, size=n)))
    p1 = V.walk(rows, ["x"], "y", V.LASSO, [2019, 2020])
    later = rows.with_columns(y=pl.when(c("target_season") == 2020).then(-99.0).otherwise(c("y")))
    p2 = V.walk(later, ["x"], "y", V.LASSO, [2019, 2020])
    is19 = (rows["target_season"] == 2019).to_numpy()
    assert np.allclose(p1[is19], p2[is19])  # 2019's forecast saw no 2020 target
    assert np.isnan(p1[(rows["target_season"] == 2018).to_numpy()]).all()
    g = V.gain(rows["y"].to_numpy(), np.zeros(n), p1, rows["gsis_id"].to_numpy())
    assert g.share > 0.9 and g.verdict == "better"


def test_shuffled_targets_stay_within_season_and_position():
    rows = pl.DataFrame({"y": np.arange(8.0), "target_season": [1, 1, 1, 1, 2, 2, 2, 2],
                         "group": ["a", "a", "b", "b"] * 2})  # fmt: skip
    y = V.shuffled_target(rows, "y", seed=3)
    for k in range(4):
        assert sorted(y[2 * k : 2 * k + 2]) == [2 * k, 2 * k + 1]
