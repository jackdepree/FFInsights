"""The as_of gateway: what a view at a moment shows, hides and refuses."""

from datetime import UTC, datetime

import polars as pl
import pytest

from pcf.data.gateway import FrameSource, Gateway, UndeclaredInput, VintageError

from ..validation import world

c = pl.col
INPUTS = {"player_game": ("stats",), "player_play": ("on_field",)}
# Tuesday of 2022 week 3 (10:00 ET)
MOMENT = datetime(2022, 9, 20, 14, tzinfo=UTC)


@pytest.fixture(scope="module")
def gw():
    return world.gateway()


def test_a_view_shows_only_rows_known_at_its_moment(gw):
    pg = gw.view(MOMENT, "in_season", INPUTS).table("player_game")
    assert pg.filter(c("known_at") > MOMENT).is_empty()
    known = pg.filter(c("stats_known_at").is_not_null())
    assert known.height and known["stats_known_at"].max() <= MOMENT
    # Rows of this week's games are listed (the roster is known), their stats aren't yet.
    week3 = pg.filter((c("season") == 2022) & (c("week") == 3))
    assert week3.height and week3["fantasy_points_ppr"].null_count() == week3.height


def test_a_view_matches_load_semantics_on_the_spine_and_parts(gw):
    source = gw.source.part("player_game", "stats")
    view = gw.view(MOMENT, "in_season", INPUTS).table("player_game")
    expected = source.filter(c("known_at") <= MOMENT).height
    assert view["stats_known_at"].is_not_null().sum() == expected


def test_undeclared_tables_and_outputs_are_refused(gw):
    view = gw.view(MOMENT, "in_season", {"player_game": ("stats",)})
    with pytest.raises(UndeclaredInput):
        view.table("game")
    with pytest.raises(UndeclaredInput):
        view.output("elo")


def test_undeclared_parts_aren_t_shown(gw):
    pg = gw.view(MOMENT, "in_season", {"player_game": ()}).table("player_game")
    assert "fantasy_points_ppr" not in pg.columns


def test_post_season_parts_wait_for_the_season_to_finish_in_season_only():
    f = world.frames()
    sched = f[("game", "schedule")].select("game_id", "kickoff")
    early = (
        f[("player_play", "on_field")]
        .join(sched, on="game_id")
        .with_columns(known_at=c("kickoff") + pl.duration(days=1))
        .drop("kickoff")
    )
    gw = world.gateway(**{"player_play.on_field": early})
    in_season = gw.view(MOMENT, "in_season", INPUTS).table("player_play")
    retro = gw.view(MOMENT, "retrospective", INPUTS).table("player_play")
    assert set(in_season["season"]) == {2020, 2021}
    assert 2022 in set(retro["season"])  # a retrospective model may see it once known


def test_views_need_a_timezone(gw):
    with pytest.raises(ValueError):
        gw.view(datetime(2022, 9, 20), "in_season", INPUTS)


def _outputs(rows):
    def read(project_id, version):
        return pl.DataFrame(
            rows, schema=["team", "season", "as_of", "train_end", "mean", "cadence"], orient="row"
        ).with_columns(c("as_of", "train_end").cast(pl.Datetime("us", "UTC")))

    return read


def test_outputs_made_after_the_moment_are_hidden():
    rows = [
        ("AAA", 2022, datetime(2022, 9, 13, 14, tzinfo=UTC), datetime(2022, 9, 13, tzinfo=UTC),
         0.6, "in_season"),
        ("AAA", 2022, datetime(2022, 9, 27, 14, tzinfo=UTC), datetime(2022, 9, 27, tzinfo=UTC),
         0.7, "in_season"),
    ]  # fmt: skip
    gw = Gateway(FrameSource(world.frames()), world.cal(), _outputs(rows))
    out = gw.view(MOMENT, "in_season", {"elo": 1}).output("elo")
    assert out["mean"].to_list() == [0.6]


def test_outputs_from_a_model_trained_after_them_are_refused():
    rows = [("AAA", 2022, datetime(2022, 9, 13, 14, tzinfo=UTC),
             datetime(2023, 3, 1, tzinfo=UTC), 0.6, "in_season")]  # fmt: skip
    gw = Gateway(FrameSource(world.frames()), world.cal(), _outputs(rows))
    with pytest.raises(VintageError):
        gw.view(MOMENT, "in_season", {"elo": 1}).output("elo")


def test_retrospective_outputs_reach_in_season_views_only_for_finished_seasons():
    made = datetime(2022, 9, 13, 14, tzinfo=UTC)
    rows = [
        ("AAA", 2021, made, datetime(2022, 3, 1, tzinfo=UTC), 0.6, "retrospective"),
        ("AAA", 2022, made, datetime(2022, 9, 13, tzinfo=UTC), 0.7, "retrospective"),
    ]
    gw = Gateway(FrameSource(world.frames()), world.cal(), _outputs(rows))
    assert gw.view(MOMENT, "in_season", {"elo": 1}).output("elo")["season"].to_list() == [2021]
    assert gw.view(MOMENT, "retrospective", {"elo": 1}).output("elo").height == 2
