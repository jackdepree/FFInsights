"""Where a model misses (miss-lenses): a planted pattern is found, noise isn't, and every report
is dated."""

import numpy as np
import polars as pl
import pytest

from pcf.data.gateway import FrameSource
from pcf.data.tags.catalog import BEFORE, TAGS
from pcf.validation import misses
from pcf.validation.misses import LENS_LIST, LENSES, METHOD, Lens, lens_frame, report

c = pl.col
POSITIONS = ["QB", "RB", "WR", "TE"]


def _world(seed: int = 1) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Player-games over 8 seasons with misses of pure noise, except +2 points for a planted
    group and for rookies."""
    rng = np.random.default_rng(seed)
    rows = [
        (f"P{p:03d}", f"{s}_{w:02d}_{p // 2:03d}", s, w, POSITIONS[p % 4])
        for s in range(2016, 2024) for w in range(1, 18) for p in range(80)
    ]  # fmt: skip
    frame = pl.DataFrame(
        rows, schema=["gsis_id", "game_id", "season", "week", "position"], orient="row"
    )
    n = frame.height
    frame = frame.with_columns(
        planted=pl.Series(rng.random(n) < 0.2),
        noise_id=pl.Series(rng.integers(0, 600, n)).cast(pl.String),
        tag_rookie=pl.Series(rng.random(n) < 0.1),
        tag_revenge_game=pl.Series(rng.random(n) < 0.1),
        offense_pct=pl.Series(rng.random(n)),
    )
    shift = (frame["planted"].cast(pl.Float64) + frame["tag_rookie"].cast(pl.Float64)) * 2
    scored = frame.select(
        "gsis_id", "game_id",
        mean=pl.lit(10.0),
        y=pl.Series(10 + shift + rng.normal(0, 5, n)),
    )  # fmt: skip
    return scored, frame


PLANTED = Lens("planted", "before", "a planted group", lambda d: c("planted").cast(pl.String),
               ("planted",))  # fmt: skip
NOISE = Lens("noise", "before", "600 groups of noise", lambda d: c("noise_id"), ("noise_id",))


@pytest.fixture(scope="module")
def m():
    scored, frame = _world()
    return report(scored, frame, lenses=[*LENSES, PLANTED, NOISE])


def _lens(m, name: str) -> dict:
    return m.lenses.filter(c("lens") == name).row(0, named=True)


def test_a_planted_lens_is_found(m):
    planted = _lens(m, "planted")
    assert planted["bias_share"] > 0.02
    assert planted["top_group"] == "true"
    # +2 planted, +0.2 from the rookies among them, give or take the noise
    assert planted["lo"] > 1.7 and planted["hi"] < 2.9


def test_noise_in_many_small_groups_is_not_rewarded(m):
    """Learned on the other half of the seasons, corrections for noise make misses worse."""
    assert _lens(m, "noise")["bias_share"] < 0.005
    assert _lens(m, "snap_share")["bias_share"] < 0.005


def test_a_tag_that_is_off_is_flagged_and_a_noise_tag_is_not(m):
    flagged = m.flagged["lens"].to_list()
    assert "tag_rookie" in flagged and "tag_revenge_game" not in flagged
    rookie = m.flagged.filter(c("lens") == "tag_rookie").row(0, named=True)
    assert rookie["top_group"] == "true" and rookie["avg_miss"] > 1.2  # vs the model's average


def test_lenses_without_their_inputs_are_listed_not_guessed(m):
    assert {"depth", "team_points", "margin", "qb_efficiency"} <= set(m.skipped)
    assert {"player_change", "team_change"} <= set(m.skipped)
    assert "snap_share" not in m.skipped


def test_after_game_lenses_are_labelled_diagnostic():
    fixed = {lens.name: lens.when for lens in LENSES}
    assert fixed == {"position": "before", "depth": "before", "week": "before",
                     "snap_share": "after", "team_points": "after", "margin": "after",
                     "qb_efficiency": "after", "player_change": "before",
                     "team_change": "before"}  # fmt: skip
    timing = {t.column: t.timing for t in TAGS} | {x.name: "before_game" for x in misses.EXTRA}
    for lens in misses._candidates():
        assert lens.when == ("before" if timing[lens.name] in BEFORE else "after"), lens.name


def test_every_report_is_dated(m, tmp_path):
    out = m.frame("run1")
    assert (out["lens_list"] == LENS_LIST).all() and (out["method"] == METHOD).all()
    assert (out["run_id"] == "run1").all() and out["measured_at"].null_count() == 0
    assert set(out["kind"]) == {"fixed", "flagged"}
    path = misses.save(m, tmp_path, "run1")
    assert pl.read_parquet(path).height == out.height


def test_the_lens_frame_reads_what_the_source_has():
    roster = pl.DataFrame({
        "gsis_id": ["A", "B"], "game_id": ["G1", "G1"], "season": [2023, 2023], "week": [1, 1],
        "team": ["KC", "BUF"], "position": ["WR", "QB"],
    })  # fmt: skip
    sched = pl.DataFrame({"game_id": ["G1"], "home_team": ["KC"]})
    result = pl.DataFrame({"game_id": ["G1"], "home_score": [31], "away_score": [10]})
    injury = pl.DataFrame({"gsis_id": ["C"], "game_id": ["G1"], "report_status": ["Out"]})
    roster = pl.concat([roster, roster.head(1).with_columns(gsis_id=pl.lit("C"))])
    frame = lens_frame(FrameSource({
        ("player_game", "roster"): roster, ("game", "schedule"): sched, ("game", "result"): result,
        ("player_game", "injury"): injury,
    })).sort("gsis_id")  # fmt: skip
    assert frame["team_points"].to_list() == [31, 10, 31]
    assert frame["margin"].to_list() == [21, -21, 21]
    assert frame["home"].to_list() == [True, False, True]
    # A's same-position teammate C is Out; the QB's isn't
    assert frame["teammate_out"].to_list() == [True, False, True]
    assert "depth" not in frame.columns


def _change_source() -> FrameSource:
    """Two seasons of one team, 6 games each. 2022: coach Old, QB Q1 all year. 2023: coach New,
    QB Q2 opens, Q3 takes over in week 4. Player A is on the team throughout and is back from
    injury in week 3 of 2023; B is a rookie in 2023."""
    games = [(f"{s}_{w:02d}", s, w) for s in (2022, 2023) for w in range(1, 7)]
    tg = pl.DataFrame(games, schema=["game_id", "season", "week"], orient="row").with_columns(
        team=pl.lit("KC"), game_type=pl.lit("REG")
    )
    pre = tg.select(
        "game_id", "team",
        qb_id=pl.when(c("season") == 2022).then(pl.lit("Q1"))
        .when(c("week") < 4).then(pl.lit("Q2")).otherwise(pl.lit("Q3")),
        coach=pl.when(c("season") == 2022).then(pl.lit("Old")).otherwise(pl.lit("New")),
    )  # fmt: skip
    cols = ["game_id", "season", "week", "team"]
    roster = pl.concat([
        tg.select(pl.lit("A").alias("gsis_id"), *cols, position=pl.lit("WR")),
        tg.filter(c("season") == 2023).select(
            pl.lit("B").alias("gsis_id"), *cols, position=pl.lit("RB")
        ),
    ])  # fmt: skip
    tags = roster.select(
        "gsis_id", "game_id",
        tag_rookie=c("gsis_id") == "B",
        tag_new_team=pl.lit(False),
        tag_first_game_back=(c("gsis_id") == "A") & (c("season") == 2023) & (c("week") == 3),
    )  # fmt: skip
    team_tags = tg.select("game_id", "team", tag_off_bye=(c("season") == 2023) & (c("week") == 6))
    return FrameSource({
        ("player_game", "roster"): roster, ("player_game", "tags"): tags,
        ("team_game", "schedule"): tg, ("team_game", "pregame"): pre,
        ("team_game", "tags"): team_tags, ("game", "schedule"): tg.select("game_id"),
    })  # fmt: skip


def test_the_change_lenses_count_games_since_each_change():
    frame = lens_frame(_change_source())
    by = {lens.name: lens for lens in LENSES}
    labelled = frame.with_columns(
        player=by["player_change"].build(frame), team=by["team_change"].build(frame)
    ).sort("gsis_id", "season", "week")
    a23 = labelled.filter((c("gsis_id") == "A") & (c("season") == 2023))
    assert a23["player"].to_list() == [
        "none", "none", "first game back from injury", "games 2-4 back from injury",
        "games 2-4 back from injury", "games 2-4 back from injury",
    ]  # fmt: skip
    # a new coach and a new opening QB; the QB changes again in week 4
    assert a23["team"].to_list() == [
        "new head coach, games 1-4", "new head coach, games 1-4", "new head coach, games 1-4",
        "QB changed in season, games 1-4", "QB changed in season, games 1-4",
        "QB changed in season, games 1-4",
    ]  # fmt: skip
    b = labelled.filter(c("gsis_id") == "B")
    assert b["player"].to_list() == ["rookie, weeks 1-4"] * 4 + ["rookie, weeks 5+"] * 2
    # 2022 has no season before it in the data: nothing is called new, and no QB changed
    a22 = labelled.filter((c("gsis_id") == "A") & (c("season") == 2022))
    assert set(a22["team"]) == {"none"} and set(a22["player"]) == {"none"}


def test_the_change_lenses_are_skipped_without_their_parts():
    roster = pl.DataFrame({
        "gsis_id": ["A"], "game_id": ["G1"], "season": [2023], "week": [1], "team": ["KC"],
        "position": ["WR"],
    })  # fmt: skip
    frame = lens_frame(FrameSource({
        ("player_game", "roster"): roster, ("game", "schedule"): pl.DataFrame({"game_id": ["G1"]}),
    }))  # fmt: skip
    assert "team_game_no" not in frame.columns and "since_back" not in frame.columns
