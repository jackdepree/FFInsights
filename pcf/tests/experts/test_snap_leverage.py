"""snap-leverage on a tiny synthetic season: team A's offense against team B's defense, four weeks,
four snaps a game (the last one high-stakes). A2 plays only the ordinary snaps and sits out week
2; B2 comes on only for the high-stakes snap."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from pcf.core.contract import PREDICTION, check_expert, find_all
from pcf.data.gateway import END_OF_TIME, FrameSource, Gateway
from pcf.data.timeline import calendar
from pcf.experts.snap_leverage import features as F
from pcf.experts.snap_leverage import usage as U
from pcf.experts.snap_leverage.model import VARIANTS

c = pl.col
T = pl.Datetime("us", "UTC")
SEASON = 2021
WEEKS = (1, 2, 3, 4)
LI = [0.5, 0.5, 1.0, 2.0]
HS = [False, False, False, True]
PLAYERS = {"A1": ("A", "WR"), "A2": ("A", "WR"), "B1": ("B", "DB"), "B2": ("B", "DB")}
ON = {"A1": [1, 2, 3, 4], "A2": [1, 2], "B1": [1, 2, 3, 4], "B2": [4]}
SEASON_END = datetime(2022, 2, 20, tzinfo=UTC)


def _kickoff(week: int) -> datetime:
    return datetime(2021, 9, 12, 17, tzinfo=UTC) + timedelta(days=7 * (week - 1))


def _gid(week: int) -> str:
    return f"{SEASON}_{week:02d}_A_B"


def _on(week: int, player: str) -> list[int]:
    return [] if (player == "A2" and week == 2) else ON[player]


def _world() -> dict:
    sched = pl.DataFrame(
        {
            "game_id": [_gid(w) for w in WEEKS],
            "season": SEASON,
            "week": list(WEEKS),
            "game_type": "REG",
            "kickoff": [_kickoff(w) for w in WEEKS],
            "gameday": [_kickoff(w).strftime("%Y-%m-%d") for w in WEEKS],
            "gametime": "13:00",  # US Eastern: 17:00 UTC in September
            "home_team": "B",
            "away_team": "A",
            "known_at": datetime(2021, 5, 1, tzinfo=UTC),
        }
    )
    # the Super Bowl, so the season can finish (true participation shows only then, in season)
    final = sched.head(1).with_columns(
        game_id=pl.lit(f"{SEASON}_22_C_D"), week=pl.lit(22, pl.Int64), game_type=pl.lit("SB"),
        home_team=pl.lit("C"), away_team=pl.lit("D"),
        kickoff=datetime(2022, 2, 13, 23, 30, tzinfo=UTC),
        gameday=pl.lit("2022-02-13"), gametime=pl.lit("18:30"),
    )  # fmt: skip
    sched = pl.concat([sched, final]).with_columns(
        c("season", "week").cast(pl.Int32), c("kickoff", "known_at").cast(T)
    )
    after = {w: _kickoff(w) + timedelta(hours=15) for w in WEEKS}  # the morning after
    roster, snaps, plays, on_field, mp = [], [], [], [], []
    for w in WEEKS:
        for p, (team, pos) in PLAYERS.items():
            roster.append(
                {"gsis_id": p, "game_id": _gid(w), "season": SEASON, "week": w, "team": team,
                 "position": pos, "rookie_year": 2018, "known_at": _kickoff(w) - timedelta(days=3)}
            )  # fmt: skip
            n = len(_on(w, p))
            if n:
                pct = n / 4
                snaps.append(
                    {"gsis_id": p, "game_id": _gid(w), "season": SEASON,
                     "offense_pct": pct if team == "A" else None,
                     "defense_pct": pct if team == "B" else None, "known_at": after[w]}
                )  # fmt: skip
            for play in _on(w, p):
                side = "offense" if team == "A" else "defense"
                on_field.append(
                    {"game_id": _gid(w), "play_id": play, "season": SEASON, "side": side,
                     "team": team, "gsis_id": p, "known_at": SEASON_END}
                )  # fmt: skip
                mp.append(
                    {"game_id": _gid(w), "play_id": play, "gsis_id": p, "side": side,
                     "team": team, "season": SEASON, "week": w, "as_of": after[w],
                     "mean": 1.0, "train_end": datetime(2021, 2, 1, tzinfo=UTC),
                     "cadence": "in_season"}
                )  # fmt: skip
        for i in range(4):
            plays.append(
                {"game_id": _gid(w), "play_id": i + 1, "season": SEASON, "leverage": LI[i],
                 "high_stakes": HS[i], "pcf_xpass": 0.5, "known_at": after[w]}
            )  # fmt: skip
    roster = pl.DataFrame(roster).with_columns(c("season", "week", "rookie_year").cast(pl.Int32))
    play = pl.DataFrame(plays).with_columns(c("season").cast(pl.Int32), c("known_at").cast(T))
    frames = {
        ("game", "schedule"): sched,
        ("player_game", "roster"): roster.with_columns(c("known_at").cast(T)),
        ("player_game", "snaps"): pl.DataFrame(snaps).with_columns(
            c("season").cast(pl.Int32), c("known_at").cast(T)
        ),
        ("play", "pbp"): play.select("game_id", "play_id", "season", "known_at"),
        ("play", "leverage"): play.select(
            "game_id", "play_id", "season", "leverage", "high_stakes", "known_at"
        ),
        ("play", "pace"): play.select("game_id", "play_id", "season", "pcf_xpass", "known_at"),
        ("player_play", "on_field"): pl.DataFrame(on_field).with_columns(
            c("season").cast(pl.Int32), c("known_at").cast(T)
        ),
    }
    the_map = pl.DataFrame(mp).with_columns(
        c("season", "week").cast(pl.Int32), c("as_of", "train_end").cast(T)
    )
    return {"frames": frames, "map": the_map}


@pytest.fixture(scope="module")
def world() -> dict:
    return _world()


def _gateway(world, the_map=None) -> Gateway:
    m = world["map"] if the_map is None else the_map
    return Gateway(
        FrameSource(world["frames"]),
        calendar(world["frames"][("game", "schedule")]),
        outputs=lambda _p, _v: m,
    )


def _features(gateway: Gateway, week: int) -> pl.DataFrame:
    games = pl.DataFrame(
        {"game_id": [_gid(week)], "season": [SEASON], "week": [week], "kickoff": [_kickoff(week)]}
    ).with_columns(c("kickoff").cast(T))
    view = gateway.view(_kickoff(week) - timedelta(hours=30), "in_season", F.INPUTS)
    return F.at_moment(view, games)


def test_the_nine_variants_meet_the_contract():
    assert {x.variant for x in find_all("snap-leverage")} == set(VARIANTS)
    assert len(VARIANTS) == 9
    for cls in VARIANTS.values():
        check_expert(cls)
    assert VARIANTS["snap_next3_full"].publishes == F.PUBLISHED
    below = [b.variant for b in VARIANTS["lev_rest_full"].baselines()]
    assert below == ["lev_rest_lev", "lev_rest_plain"]


def test_usage_weights_snaps_by_leverage_and_takes_out_the_situation():
    on = pl.DataFrame(
        [
            {
                "game_id": "g",
                "play_id": play,
                "gsis_id": p,
                "side": "offense",
                "team": "A",
                "p": 1.0,
            }  # fmt: skip
            for p in ("A1", "A2")
            for play in ON[p]
        ]
    )
    snaps = U.plays(
        pl.DataFrame(
            {
                "game_id": "g",
                "play_id": [1, 2, 3, 4],
                "leverage": LI,
                "high_stakes": HS,
                "pcf_xpass": [0.5, 0.5, 0.5, 0.5],
            }
        )  # fmt: skip
    )
    u = {r["gsis_id"]: r for r in U.usage(on, snaps).to_dicts()}
    a2 = u["A2"]
    assert a2["snap_share"] == pytest.approx(0.5)
    assert a2["lev_share"] == pytest.approx(1.0 / 4.0)  # 0.5 + 0.5 of 4.0
    assert a2["hs_share"] == 0.0
    assert a2["role_gap"] == pytest.approx(-0.5)
    # on half the snaps in this kind of situation, so half a high-stakes snap expected
    assert a2["trust_oe"] == pytest.approx(-0.5)
    assert u["A1"]["trust_oe"] == pytest.approx(0.0)
    # a chance below 1 counts the snap partly
    half = U.usage(on.with_columns(p=pl.lit(0.5)), snaps)
    assert half.filter(c("gsis_id") == "A1")["snap_share"].item() == pytest.approx(0.5)


def test_features_see_only_games_known_by_the_moment(world):
    gw = _gateway(world)
    f = {r["gsis_id"]: r for r in _features(gw, 3).to_dicts()}
    assert set(f) == set(PLAYERS)
    a2, b2 = f["A2"], f["B2"]
    assert a2["n_games"] == 2  # weeks 1 and 2
    assert a2["snap_last"] == 0.0 and a2["lev_last"] == 0.0  # rostered, didn't play week 2
    assert a2["snap_std"] == pytest.approx(0.25)
    assert a2["role_std"] == pytest.approx(-0.5)  # only the game he played
    assert b2["lev_std"] == pytest.approx(0.5) and b2["trust_std"] == pytest.approx(0.75)
    assert b2["snap_prev"] is None  # no earlier season
    first = _features(gw, 1)
    assert (first["n_games"] == 0).all() and first["snap_l3"].null_count() == first.height
    # changing week 3 on (the game predicted) leaves the features alone
    later = world["map"].with_columns(
        mean=pl.when(c("game_id") == _gid(3)).then(0.0).otherwise(c("mean"))
    )
    assert _features(_gateway(world, later), 3).equals(_features(gw, 3))
    # a map row made after the moment is not seen
    late = world["map"].with_columns(
        as_of=pl.when(c("game_id") == _gid(2)).then(pl.lit(datetime(2021, 12, 1, tzinfo=UTC)))
        .otherwise(c("as_of")).cast(T)
    )  # fmt: skip
    g = {r["gsis_id"]: r for r in _features(_gateway(world, late), 3).to_dicts()}
    assert g["A2"]["lev_last"] is None and g["A2"]["snap_last"] == 0.0


def test_targets_are_window_means_known_when_the_window_is(world):
    view = _gateway(world).view(END_OF_TIME, "in_season", F.INPUTS)
    snap = F.targets(view, "snap", "next3")
    assert set(snap["game_id"]) == {_gid(1), _gid(2)}  # 3 games left only in weeks 1 and 2
    a2 = snap.filter((c("gsis_id") == "A2") & (c("game_id") == _gid(1))).row(0, named=True)
    assert a2["y"] == pytest.approx((0.5 + 0.0 + 0.5) / 3)
    assert a2["known_at"] == _kickoff(3) + timedelta(hours=15)
    lev = F.targets(view, "lev", "rest")
    b2 = lev.filter((c("gsis_id") == "B2") & (c("game_id") == _gid(2))).row(0, named=True)
    assert b2["y"] == pytest.approx(0.5) and b2["known_at"] == SEASON_END
    assert lev.height == 4 * len(PLAYERS)
    # true participation is post-season only: an in-season view can't see this season's
    live = _gateway(world).view(_kickoff(4), "in_season", F.INPUTS)
    assert F.targets(live, "lev", "rest").is_empty()


def test_a_variant_fits_and_predicts_shares_with_ranges(world):
    rows = pl.concat([_features(_gateway(world), w) for w in WEEKS])
    # the synthetic season is too small to fit trees on: its rows, repeated, with noisy outcomes
    rng = np.random.default_rng(0)
    big = pl.concat([rows] * 200).with_columns(
        y=(c("lev_std").fill_null(0.3) + pl.Series(rng.normal(0, 0.1, rows.height * 200))).clip(
            0, 1
        ),
        weight=pl.lit(1.0),
    )
    e = VARIANTS["lev_rest_full"]()
    out = e.predict(e.fit(big), rows)
    assert out.height == rows.height
    ordered = pl.all_horizontal(c("q10") <= c("q50"), c("q50") <= c("q90"))
    assert out.select(ordered).to_series().all()
    inside = pl.all_horizontal(c(q).is_between(0, 1) for q in PREDICTION)
    assert out.select(inside).to_series().all()
    # snap_prev is empty in this world: left out of the fit, not a crash
    assert "snap_prev" not in e.explain(e.fit(big))["features"]


def test_usage_is_the_same_to_the_last_digit_whatever_the_row_order():
    """Sums in another order differ in the last digit, enough to flip a tree's split (check 8)."""
    rng = np.random.default_rng(1)
    n = 5000
    on = pl.DataFrame(
        {
            "game_id": rng.choice(["g1", "g2"], n),
            "play_id": rng.integers(1, 200, n),
            "gsis_id": rng.choice([f"P{i}" for i in range(40)], n),
            "side": "offense",
            "team": "A",
            "p": rng.random(n),
        }
    ).unique(["game_id", "play_id", "gsis_id"])
    snaps = U.plays(
        pl.DataFrame(
            {
                "game_id": ["g1"] * 199 + ["g2"] * 199,
                "play_id": list(range(1, 200)) * 2,
                "leverage": rng.random(398) * 3,
                "high_stakes": rng.random(398) > 0.8,
                "pcf_xpass": rng.random(398),
            }
        )
    )
    first = U.usage(on, snaps)
    for seed in range(3):
        again = U.usage(on.sample(fraction=1.0, shuffle=True, seed=seed), snaps.sample(
            fraction=1.0, shuffle=True, seed=seed))  # fmt: skip
        assert again.equals(first)
