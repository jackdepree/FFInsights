"""Player pace (`pcf.experts.player_pace`, `pcf.experts.player_pace_retro`; decision 0029): the
contract, the expected-starter rule, no later data in an in-season feature, and the
retrospective features use only earlier seasons."""

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from pcf.core.contract import check_expert, find_all
from pcf.experts.player_pace import features as F
from pcf.experts.player_pace.model import VARIANTS
from pcf.experts.player_pace_retro import model as R

c = pl.col
UTC_T = pl.Datetime("us", "UTC")
T0 = datetime(2022, 9, 11, 17, 0, tzinfo=UTC)  # week 1 kickoff
WEEK = timedelta(days=7)


def test_every_variant_of_both_meets_the_contract():
    assert {x.variant for x in find_all("player-pace")} == set(VARIANTS)
    assert set(VARIANTS) == {
        "proe_team", "proe_qb", "proe_lineup", "pace_oe_team", "pace_oe_qb",
        "plays_qb", "dropbacks_qb", "runs_qb",
    }  # fmt: skip
    for cls in VARIANTS.values():
        check_expert(cls)
        assert cls.cadence == "in_season"
    retro = {x.variant for x in find_all("player-pace-retro")}
    assert retro == {f"{m}_{v}" for m in R.MEASURES for v in ("group", "last", "shrunk")}
    for cls in find_all("player-pace-retro"):
        check_expert(cls)
        assert cls.cadence == "retrospective"
    assert [b.variant for b in VARIANTS["proe_qb"].baselines()] == ["proe_team", "proe_shrunk"]


# --- the in-season features: a small world of one team, A, over 4 weeks ---------------------


def _tg(starters=("qb1", "qb1", "qb1", "qb2")) -> pl.DataFrame:
    """Team A's games, weeks 1-4 of 2022, and two of 2021 so the QBs have a history. qb1 passes
    a lot (PROE +0.10), qb2 runs (-0.10); the rest of the league (team B) sits at 0."""
    rows = []
    for i, qb in enumerate(("qb1", "qb2")):  # 2021: one start each for A, one for B
        k = T0 - timedelta(days=300) + i * WEEK
        rows.append(("A", 2021, k, qb, 0.10 if qb == "qb1" else -0.10))
        rows.append(("B", 2021, k, "qbB", 0.0))
    for w, qb in enumerate(starters):
        k = T0 + w * WEEK
        rows.append(("A", 2022, k, qb, 0.10 if qb == "qb1" else -0.10))
        rows.append(("B", 2022, k, "qbB", 0.0))
    df = pl.DataFrame(rows, schema=["team", "season", "kickoff", "qb_id", "proe"], orient="row")
    return df.with_columns(
        game_id=pl.concat_str(
            c("season").cast(pl.Utf8), pl.lit("_"), c("kickoff").dt.ordinal_day().cast(pl.Utf8),
            pl.lit("_"), c("team"),
        ),
        season=c("season").cast(pl.Int32),
        kickoff=c("kickoff").cast(UTC_T),
        plays=pl.lit(60, pl.Int32),
        pace_oe=pl.lit(0.0),
        pace_snaps=pl.lit(40, pl.Int32),
        pace_known_at=(c("kickoff") + timedelta(hours=24)).cast(UTC_T),
        pregame_known_at=c("kickoff").cast(UTC_T),
    )  # fmt: skip


def _pg(tg: pl.DataFrame, out: dict[str, str] | None = None, cut: set[str] = frozenset()):
    """Both QBs on A's roster every game (unless in `cut`), qb2 a rookie; `out` maps a game_id
    to the QB its report rules out. Snaps: qb1 played all of 2022's earlier games."""
    out = out or {}
    rows = []
    for r in tg.filter(c("team") == "A").iter_rows(named=True):
        for qb in ("qb1", "qb2"):
            if qb in cut and r["season"] == 2022:
                continue
            status = "Out" if out.get(r["game_id"]) == qb else None
            rows.append({
                "gsis_id": qb, "game_id": r["game_id"], "team": "A", "season": r["season"],
                "position": "QB", "years_exp": 0 if qb == "qb2" else 5,
                "known_at": r["kickoff"] - timedelta(days=5),
                "report_status": status, "injury_known_at": r["kickoff"] - timedelta(hours=50),
                "offense_snaps": 60 if qb == r["qb_id"] else 0,
                "offense_pct": 1.0 if qb == r["qb_id"] else 0.0,
                "snaps_known_at": r["kickoff"] + timedelta(hours=14),
            })  # fmt: skip
    return pl.DataFrame(rows).with_columns(
        c("season").cast(pl.Int32),
        *(c(x).cast(UTC_T) for x in ("known_at", "injury_known_at", "snaps_known_at")),
    )


def _ps() -> pl.DataFrame:
    return pl.DataFrame(
        schema={"gsis_id": pl.Utf8, "season": pl.Int32, "known_at": UTC_T,
                "onf_pm_proe": pl.Float64, "onf_w_proe": pl.Float64}
    )  # fmt: skip


def _targets(tg: pl.DataFrame, week: int) -> pl.DataFrame:
    """Week `week` of 2022 (1-based) at its Saturday run, a day before kickoff."""
    k = T0 + (week - 1) * WEEK
    return tg.filter(c("kickoff") == k).select(
        *F.KEYS, "season", moment=pl.lit(k - timedelta(days=1)).cast(F.MOMENT)
    )


def _qb(tg, pg, week) -> dict:
    t = _targets(tg, week)
    return F.expected_qb(t, F._starts(tg), pg).filter(c("team") == "A").row(0, named=True)


def test_the_expected_starter_is_the_last_one_unless_ruled_out_or_cut():
    tg = _tg()
    assert _qb(tg, _pg(tg), 3)["qb_id_expected"] == "qb1"
    # week 4's actual starter (qb2) isn't known before kickoff: still qb1
    assert _qb(tg, _pg(tg), 4)["qb_id_expected"] == "qb1"
    wk3 = _targets(tg, 3)["game_id"].filter(_targets(tg, 3)["team"] == "A")[0]
    # ruled out: the rostered QB with the most snaps who isn't out
    got = _qb(tg, _pg(tg, out={wk3: "qb1"}), 3)
    assert got["qb_last"] == "qb1" and got["qb_id_expected"] == "qb2"
    # cut (off the roster): the same
    assert _qb(tg, _pg(tg, cut={"qb1"}), 3)["qb_id_expected"] == "qb2"


def test_the_qb_columns_carry_his_history_and_flag_a_change_and_a_rookie():
    tg = _tg()
    wk3 = _targets(tg, 3)["game_id"].filter(_targets(tg, 3)["team"] == "A")[0]
    pg = _pg(tg, out={wk3: "qb1"})
    f = F.qb_features(_targets(tg, 3), tg, pg).filter(c("team") == "A").row(0, named=True)
    assert f["qb_id_expected"] == "qb2"
    assert f["qb_change"] == 1.0 and f["qb_rookie"] == 1.0
    assert f["qb_proe_gap"] < 0  # qb2 ran in his start
    assert f["qb_share"] == 0.0 and f["qb_proe_other"] == pytest.approx(f["qb_proe_gap"])
    same = F.qb_features(_targets(tg, 3), tg, _pg(tg)).filter(c("team") == "A").row(0, named=True)
    assert same["qb_change"] == 0.0 and same["qb_proe_gap"] > 0 and same["qb_share"] == 1.0


def test_an_in_season_feature_never_uses_the_game_itself_or_later_ones():
    """Change week 3 on (starters, rates, snaps, later reports): week 3's features stay."""
    tg = _tg()
    pg = _pg(tg)
    changed_tg = _tg(starters=("qb1", "qb1", "qb2", "qb2")).with_columns(
        proe=pl.when(c("kickoff") >= T0 + 2 * WEEK).then(0.9).otherwise(c("proe"))
    )
    later = (c("season") == 2022) & c("game_id").is_in(
        changed_tg.filter(c("kickoff") > T0 + 2 * WEEK)["game_id"].to_list()
    )
    changed_pg = _pg(changed_tg).with_columns(
        report_status=pl.when(later).then(pl.lit("Out")).otherwise(c("report_status"))
    )
    t = _targets(tg, 3)
    a = F.player_features(t, tg, pg, _ps())
    b = F.player_features(t, changed_tg, changed_pg, _ps())
    assert_frame_equal(a.sort(F.KEYS), b.sort(F.KEYS))


# --- the retrospective features ----------------------------------------------------------------


def _season_rows() -> pl.DataFrame:
    rows = [
        ("te", 2019, "TE", 0.30, 100.0), ("te", 2020, "TE", 0.10, 50.0),
        ("te", 2021, "TE", 0.20, 80.0), ("te", 2022, "TE", 9.0, 80.0),
        ("rb", 2021, "RB", None, 0.0),
    ]  # fmt: skip
    df = pl.DataFrame(rows, schema=["gsis_id", "season", "onf_group", "onf_pm_proe", "onf_w_proe"],
                      orient="row")  # fmt: skip
    return df.with_columns(
        c("season").cast(pl.Int32),
        onf_pm_proe_pers=c("onf_pm_proe"),
        onf_pm_pace=pl.lit(None, pl.Float64),
        onf_w_pace=pl.lit(0.0),
    )


def test_retro_features_use_earlier_seasons_only_with_decay():
    f = R.season_features(_season_rows(), 2022)
    te = f.filter(c("gsis_id") == "te").row(0, named=True)
    assert te["season"] == 2022 and te["group"] == "TE" and te["seasons_seen"] == 3
    w = [100 * 0.7**2, 50 * 0.7, 80.0]
    assert te["proe_w"] == pytest.approx(sum(w))
    assert te["proe_wd"] == pytest.approx(0.30 * w[0] + 0.10 * w[1] + 0.20 * w[2])
    assert te["proe_last"] == pytest.approx(0.20) and te["proe_last_w"] == pytest.approx(80.0)
    # the season itself (9.0) never enters; nor a later one
    later = _season_rows().with_columns(
        onf_pm_proe=pl.when(c("season") >= 2022).then(-5.0).otherwise(c("onf_pm_proe"))
    )
    assert_frame_equal(f, R.season_features(later, 2022))
    rb = f.filter(c("gsis_id") == "rb").row(0, named=True)
    assert rb["proe_w"] == 0.0 and rb["proe_last"] is None


def test_who_is_out_reads_only_the_last_few_finished_seasons():
    """A per-moment view reads `PM_SEASONS` earlier seasons; the bulk history must read the same
    (leakage checks 3 and 4 compare them), so an older season never counts."""
    tg = _tg()
    t = _targets(tg, 3)
    game = t.filter(c("team") == "A")["game_id"][0]
    k = tg.filter(c("game_id") == game)["kickoff"][0]
    pg = pl.DataFrame(
        {"gsis_id": ["te"], "game_id": [game], "team": ["A"], "season": [2022],
         "position": ["TE"], "report_status": ["Out"],
         "injury_known_at": [k - timedelta(hours=50)], "offense_pct": [0.8],
         "snaps_known_at": [k - timedelta(days=6)]}
    ).with_columns(
        c("season").cast(pl.Int32), c("injury_known_at", "snaps_known_at").cast(UTC_T)
    )  # fmt: skip
    season = 2022 - F.PM_SEASONS - 1  # just outside the window
    ps = pl.DataFrame(
        {"gsis_id": ["te"], "season": [season], "known_at": [T0 - timedelta(days=900)],
         "onf_pm_proe": [0.5], "onf_w_proe": [500.0]}
    ).with_columns(c("season").cast(pl.Int32), c("known_at").cast(UTC_T))  # fmt: skip
    out = F.lineup_out(t, pg, ps).filter(c("team") == "A")["lineup_out"][0]
    assert out == 0.0
    inside = F.lineup_out(t, pg, ps.with_columns(season=pl.lit(2021, pl.Int32)))
    assert inside.filter(c("team") == "A")["lineup_out"][0] < 0
