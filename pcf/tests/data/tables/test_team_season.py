"""`team_season.charted`: each team's charted traits per season, raw and over expected, known
after the season and usable in season only from the next (decision 0026)."""

from datetime import timedelta

import polars as pl
import pytest

from pcf.data.gateway import FrameSource, Gateway
from pcf.data.schemas import check_parts, table
from pcf.data.tables.store import load, write_parts
from pcf.data.tables.team_season import COLUMNS, PARTICIPATION_COLUMNS, team_season_parts
from pcf.validation.leakage import known_at_sanity

from .toy import KICK, cal, utc

GAME, SUPER_BOWL = "2025_01_BUF_KC", "2025_22_BUF_KC"
SB_KICK = utc(2026, 2, 8, 23, 30)


def _play(play_id, offense="KC", dropback=True, game=GAME, **over):
    """A neutral first-and-10 shotgun play: a dropback, or a run."""
    row = {
        "game_id": game, "play_id": play_id, "season": 2025, "posteam": offense,
        "defteam": "BUF" if offense == "KC" else "KC", "down": 1, "ydstogo": 10, "qtr": 1,
        "wp": 0.5, "half_seconds_remaining": 1500, "pass": int(dropback), "rush": int(not dropback),
        "shotgun": 1, "qb_dropback": int(dropback), "qb_kneel": 0, "qb_spike": 0,
        "air_yards": 8.0 if dropback else None, "pass_attempt": int(dropback), "sack": 0,
        "epa": 0.0,
    }  # fmt: skip
    return {k: over.get(k, v) for k, v in row.items()}


def _chart(play_id, game=GAME, man=None, rushers=0, dbs="2 CB, 2 S", box=6, **over):
    row = {
        "nflverse_game_id": game, "play_id": float(play_id),
        "offense_personnel": "1 RB, 1 TE, 3 WR", "defense_personnel": f"{dbs}, 4 DL, 3 LB",
        "offense_formation": "SHOTGUN", "defenders_in_box": box, "number_of_pass_rushers": rushers,
        "defense_man_zone_type": {True: "MAN_COVERAGE", False: "ZONE_COVERAGE"}.get(man, ""),
        "defense_coverage_type": None if man is None else ("COVER_1" if man else "COVER_4"),
        "time_to_throw": 2.5 if man is not None else None,
    }  # fmt: skip
    return {k: over.get(k, v) for k, v in row.items()}


def _parts(plays, charts):
    pbp = pl.DataFrame(plays, schema_overrides={"season": pl.Int32})
    part = pl.DataFrame(charts, schema_overrides={"defenders_in_box": pl.Int32})
    return team_season_parts(pbp, part.select(PARTICIPATION_COLUMNS), cal())


def _row(rows, team):
    return rows.row(by_predicate=pl.col("team") == team, named=True)


def test_traits_raw_and_against_the_league_in_the_same_look():
    plays = [
        _play(1),  # KC throws: BUF in man, 6 rushers, nickel
        _play(2, dropback=False),  # KC runs into a 7-man box, from 12 personnel
        _play(3, "BUF"),  # BUF throws: KC in zone, 4 rushers, dime
        _play(4, wp=0.97),  # a blowout: not neutral
    ]
    charts = [
        _chart(1, man=True, rushers=6, dbs="3 CB, 2 S"),
        _chart(2, box=7, offense_personnel="1 RB, 2 TE, 2 WR"),
        _chart(3, man=False, rushers=4, dbs="4 CB, 2 S"),
        _chart(4, man=True),
    ]
    rows = _parts(plays, charts)["charted"]
    assert rows.columns == ["team", "season", "known_at", *COLUMNS]
    kc, buf = _row(rows, "KC"), _row(rows, "BUF")
    assert (kc["off_plays"], kc["off_dropbacks"], kc["def_plays"]) == (2, 1, 1)
    assert kc["off_11_rate"] == pytest.approx(0.5)
    assert kc["off_12_rate"] == pytest.approx(0.5)
    # down and distance are the same on every play: the league's 11 rate is 2 of 3
    assert kc["off_11_rate_oe"] == pytest.approx(((1 - 2 / 3) + (0 - 2 / 3)) / 2)
    assert kc["off_time_to_throw"] == pytest.approx(2.5)
    # the two dropbacks share a look (11, shotgun, first and 10): man 1 of 2
    assert buf["def_man_rate"] == 1.0 and buf["def_man_rate_oe"] == pytest.approx(0.5)
    assert kc["def_man_rate"] == 0.0 and kc["def_man_rate_oe"] == pytest.approx(-0.5)
    assert kc["off_faced_man_rate_oe"] == pytest.approx(0.5)
    assert buf["def_blitz_rate"] == 1.0 and buf["def_rushers"] == 6
    assert buf["def_nickel_rate"] == 0.5 and buf["def_dime_rate"] == 0.0  # the run: 4 DBs
    assert kc["def_dime_rate"] == 1.0
    assert kc["off_faced_box"] == pytest.approx(6.5)
    # the run's 12-personnel look is its own cell
    assert buf["def_box_oe"] == pytest.approx(0.0)


def test_timing_columns_and_the_regular_season_only():
    plays = [_play(1), _play(2, game=SUPER_BOWL)]
    charts = [_chart(1, man=True), _chart(2, game=SUPER_BOWL, man=False)]
    parts = _parts(plays, charts)
    check_parts(parts, "team_season")
    kc = _row(parts["charted"], "KC")
    assert kc["off_plays"] == 1 and kc["games"] == 1  # the Super Bowl isn't counted
    assert kc["first_kickoff"] == KICK and kc["last_kickoff"] == KICK
    # participation is published after the season: the day after the Super Bowl
    assert kc["known_at"] == SB_KICK + timedelta(days=1)
    assert kc["prior_for"] == 2026
    t = table("team_season")
    assert t.post_season == ("charted",) and t.after == ("charted",)


def test_saved_and_read_back_through_the_gateway(tmp_path):
    parts = _parts([_play(1)], [_chart(1, man=True)])
    write_parts(parts, "team_season", [2025], tmp_path)
    saved = load("team_season", root=tmp_path)
    assert saved.select("team", "season").rows() == [("BUF", 2025), ("KC", 2025)]
    known = parts["charted"]["known_at"][0]
    gw = Gateway(FrameSource({("team_season", "charted"): parts["charted"]}), cal())
    inputs = {"team_season": ("charted",)}
    before = gw.view(known - timedelta(seconds=1), "retrospective", inputs).table("team_season")
    assert before.is_empty()
    assert gw.view(known, "retrospective", inputs).table("team_season").height == 2
    # in season: only once the season is over (the next season's prior)
    later = known + timedelta(days=30)
    assert gw.view(later, "in_season", inputs).table("team_season").height == 2


class _Reads:
    """Just enough of an expert for leakage check 2: the tables it declares."""

    def tables(self):
        return {"team_season": ("charted",)}


def test_a_season_known_before_its_last_game_fails_leakage_check_2():
    rows = _parts([_play(1)], [_chart(1, man=True)])["charted"]
    honest = Gateway(FrameSource({("team_season", "charted"): rows}), cal())
    assert known_at_sanity(_Reads(), honest).passed
    early = rows.with_columns(known_at=pl.col("last_kickoff") - timedelta(days=1))
    planted = Gateway(FrameSource({("team_season", "charted"): early}), cal())
    check = known_at_sanity(_Reads(), planted)
    assert not check.passed and "before their last game" in check.detail


def test_a_play_listed_twice_raises():
    with pytest.raises(ValueError, match="twice"):
        _parts([_play(1)], [_chart(1), _chart(1)])
