"""The tag catalog and builders on toy rows: rules, empty-where-not-applicable, and timing.

The timing tests are the point-in-time check for tags (rule c): a `before_*` tag of a row may not
change when the results of that row, or anything later, are scrambled.
"""

import random
from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from pcf.data.tags import BEFORE, TAGS, tags_for
from pcf.data.tags.build import (
    OUTCOME_COLUMNS,
    apply_tags,
    drive_parts,
    play_tags,
    player_game_tags,
    team_game_tags,
)
from pcf.data.tags.catalog import Tag

c = pl.col
T0 = datetime(2024, 9, 8, 17, tzinfo=UTC)
TEAMS = ["KC", "BUF", "DEN", "LV"]
RESULTS = ["Touchdown", "Field goal", "Punt", "Turnover", "Turnover on downs", "End of half"]


def toy_plays(seed: int = 0, games: int = 3, drives: int = 22) -> pl.DataFrame:
    """Random but well-formed play-by-play: drives alternate teams, scores and clock move."""
    rng = random.Random(seed)
    rows = []
    for g in range(games):
        home, away = TEAMS[g % 4], TEAMS[(g + 1) % 4]
        play_id, clock, margin = 1, 3600, 0
        for d in range(1, drives + 1):
            off, de = (home, away) if d % 2 else (away, home)
            result = rng.choice(RESULTS)
            yardline = rng.randint(5, 95)
            for n in range(rng.randint(1, 12)):
                clock = max(clock - rng.randint(5, 45), 0)
                qtr = min(4, 4 - clock // 900) if clock else 4
                half = clock - 1800 if clock > 1800 else clock
                play_type = rng.choice(["run", "pass", "pass", "no_play"] if n else ["run", "pass"])
                ydstogo = rng.randint(1, 15)
                cp = rng.random() if play_type == "pass" else None
                air = rng.randint(-3, 40) if play_type == "pass" else None
                gained = rng.randint(-8, 40)
                lead = margin if off == home else -margin
                rows.append(
                    {
                        "game_id": f"2024_01_{away}_{home}_{g}",
                        "play_id": float(play_id),
                        "season": 2024,
                        "known_at": T0 + timedelta(days=g * 7 + 1),
                        "posteam": off,
                        "defteam": de,
                        "play_type": play_type,
                        "down": float(rng.randint(1, 4)),
                        "ydstogo": float(ydstogo),
                        "qtr": float(qtr),
                        "half_seconds_remaining": float(half),
                        "game_seconds_remaining": float(clock),
                        "score_differential": float(lead),
                        "yardline_100": float(yardline),
                        "goal_to_go": float(yardline <= ydstogo),
                        "fixed_drive": float(d),
                        "fixed_drive_result": result,
                        "yards_gained": float(gained),
                        "epa": rng.gauss(0, 1),
                        "wpa": rng.gauss(0, 0.05),
                        "success": float(rng.random() < 0.45),
                        "first_down": float(rng.random() < 0.3),
                        "touchdown": 0.0,
                        "interception": float(rng.random() < 0.02),
                        "fumble_lost": float(rng.random() < 0.01),
                        "sack": 0.0,
                        "cp": cp,
                        "cpoe": None,
                        "air_yards": None if air is None else float(air),
                        "yards_after_catch": None,
                        "complete_pass": 0.0,
                        "qb_scramble": float(rng.random() < 0.03),
                    }
                )
                play_id += 1
                yardline = min(max(yardline - gained // 3, 1), 99)
            margin += {"Touchdown": 7, "Field goal": 3}.get(result, 0) * (1 if off == home else -1)
    return pl.DataFrame(rows)


def scramble(frame: pl.DataFrame, rows: pl.Expr, columns: list[str], seed: int) -> pl.DataFrame:
    """Shuffle `columns` among the rows where `rows` is true; other rows are left alone."""
    picked = frame.with_row_index("_i").filter(rows)
    shuffled = picked.select(
        "_i", *(c(col).shuffle(seed=seed + k) for k, col in enumerate(columns))
    )
    return frame.with_row_index("_i").update(shuffled, on="_i").drop("_i")


def before_columns(level: str) -> list[str]:
    return [t.column for t in tags_for(level) if t.timing in BEFORE]


# The catalog


def test_the_catalog_is_well_formed():
    assert len(TAGS) == 52
    assert len({t.column for t in TAGS}) == len(TAGS)
    assert all(t.column.startswith("tag_") for t in TAGS)
    for t in TAGS:
        if t.band is not None:
            assert 0 <= t.band[0] < t.band[1] <= 1, t.name


def test_before_tags_read_no_result_columns():
    for t in TAGS:
        if t.timing not in BEFORE:
            continue
        exprs = [t.rule] + ([t.applies] if t.applies is not None else [])
        read = {name for e in exprs for name in e.meta.root_names()}
        assert not read & set(OUTCOME_COLUMNS), (t.name, read & set(OUTCOME_COLUMNS))


def test_a_tag_is_empty_where_it_does_not_apply_and_before_its_first_season():
    tag = Tag("big", "play", "measured", "after_play", "", "", c("x") > 1, (0, 1), c("ok"), 2010)
    frame = pl.DataFrame(
        {"season": [2009, 2010, 2010, 2010], "x": [5, 5, 0, 5], "ok": [True, True, True, False]}
    )
    assert apply_tags(frame, [tag])["tag_big"].to_list() == [None, True, False, None]


def test_a_new_version_gets_its_own_column():
    tag = Tag("big", "play", "measured", "after_play", "", "", c("x") > 1, (0, 1), version=2)
    assert tag.column == "tag_big_v2"


# Plays and drives


def test_play_tags_follow_their_rules():
    out = play_tags(toy_plays()).join(toy_plays(), on=["game_id", "play_id"])
    scrimmage = out.filter(c("play_type").is_in(["run", "pass"]))
    assert scrimmage["tag_successful"].to_list() == (scrimmage["success"] == 1).to_list()
    assert out.filter(c("play_type") == "no_play")["tag_successful"].null_count() > 0
    red = out["tag_red_zone"] == (out["yardline_100"] <= 20)
    assert red.all()
    # The first plays of each offense are its opening script.
    first = out.sort("play_id").group_by("game_id", "posteam", maintain_order=True).first()
    assert first["tag_opening_script"].all()


def test_garbage_time_is_never_neutral_script():
    out = play_tags(toy_plays(seed=3, drives=40))
    both = out.filter(c("tag_garbage_time") & c("tag_neutral_script"))
    assert both.height == 0


@pytest.mark.parametrize("seed", [0, 1])
def test_before_snap_play_tags_ignore_this_play_and_later_ones(seed):
    plays = toy_plays(seed)
    game = plays["game_id"][0]
    cut = plays.filter(c("game_id") == game)["play_id"].sort()[40]
    later = (c("game_id") == game) & (c("play_id") >= cut)
    scrambled = scramble(plays, later, OUTCOME_COLUMNS, seed)
    assert not scrambled.equals(plays)
    cols = ["game_id", "play_id", *before_columns("play")]
    keep = (c("game_id") != game) | (c("play_id") <= cut)
    assert (
        play_tags(plays)
        .filter(keep)
        .select(cols)
        .equals(play_tags(scrambled).filter(keep).select(cols))
    )
    # The scramble bites: result tags of the later plays do change.
    assert not play_tags(plays)["tag_explosive"].equals(play_tags(scrambled)["tag_explosive"])


def test_drives_add_up_and_sudden_change_follows_a_turnover():
    plays = toy_plays()
    parts = drive_parts(plays)
    summary, tags = parts["summary"], parts["tags"]
    assert summary.height == plays.select("game_id", "fixed_drive").n_unique()
    drives = summary.join(tags, on=["game_id", "fixed_drive"])
    assert drives.filter(c("tag_three_and_out"))["first_downs"].eq(0).all()
    prev = drives.sort("game_id", "fixed_drive").with_columns(
        prev=c("result").shift(1).over("game_id")
    )
    assert (prev.filter(c("tag_sudden_change"))["prev"] == "Turnover").all()


def test_sudden_change_ignores_this_drive_and_later_ones():
    plays = toy_plays(seed=2)
    game = plays["game_id"][0]
    later = (c("game_id") == game) & (c("fixed_drive") >= 8)
    scrambled = scramble(plays, later, OUTCOME_COLUMNS, 2)
    keep = (c("game_id") != game) | (c("fixed_drive") <= 8)
    cols = ["game_id", "fixed_drive", *before_columns("drive")]
    assert before_columns("drive") == ["tag_sudden_change"]
    before = drive_parts(plays)["tags"].filter(keep).select(cols)
    after = drive_parts(scrambled)["tags"].filter(keep).select(cols)
    assert before.equals(after)


# Team-games


def toy_team_games(seed: int = 0, weeks: int = 17) -> tuple[pl.DataFrame, pl.DataFrame]:
    """A season of KC and DEN, each playing the other in week 1 and 9, others elsewhere."""
    rng = random.Random(seed)
    team_rows, game_rows = [], []
    for week in range(1, weeks + 1):
        kick = T0 + timedelta(days=7 * (week - 1), hours=rng.choice([0, 3, 7]))
        game_id = f"2024_{week:02d}"
        for team, home in (("KC", True), ("DEN", False)):
            spread = rng.choice([-13.5, -7.5, -3.0, 2.5, 6.5])
            team_rows.append(
                {
                    "game_id": game_id,
                    "season": 2024,
                    "week": week,
                    "game_type": "REG",
                    "team": team,
                    "opponent": "DEN" if team == "KC" else "KC",
                    "home": home,
                    "kickoff": kick,
                    "rest": rng.choice([4, 7, 7, 7, 14]),
                    "div_game": rng.choice([0, 1]),
                    "known_at": T0 - timedelta(days=100),
                    "pregame_known_at": kick - timedelta(hours=2),
                    "qb_id": rng.choice(["A", "A", "A", "B"]) + team,
                    "spread": spread if home else -spread,
                }
            )
        game_rows.append(
            {
                "game_id": game_id,
                "roof": rng.choice(["outdoors", "dome"]),
                "temp": float(rng.randint(10, 90)),
                "wind": float(rng.randint(0, 25)),
                "result_known_at": kick + timedelta(hours=4),
            }
        )
    return pl.DataFrame(team_rows), pl.DataFrame(game_rows)


def test_backup_qb_start_compares_with_the_usual_starter_so_far():
    team_games, games = toy_team_games()
    kc = dict(enumerate("AABABBB", start=1))
    team_games = team_games.with_columns(
        qb_id=pl.when(c("team") == "KC")
        .then(c("week").replace_strict(kc, default="B", return_dtype=pl.String))
        .otherwise(c("qb_id"))
    )
    out = team_game_tags(team_games, games)["tags"].join(team_games, on=["game_id", "team"])
    kc = out.filter(c("team") == "KC").sort("week")["tag_backup_qb_start"].to_list()
    # Week 1 has no earlier games. By week 7, B ties A (3 each) and is more recent: usual.
    assert kc[:7] == [None, False, True, False, True, True, False]


@pytest.mark.parametrize("cut", [1, 6, 12])
def test_before_game_team_tags_ignore_this_game_and_later_results(cut):
    team_games, games = toy_team_games(seed=cut)
    later = c("week") > cut
    at_or_later = c("game_id") >= f"2024_{cut:02d}"
    # The schedule stays: it's known from week 1. Later starters and all results don't.
    team_scrambled = scramble(team_games, later, ["qb_id"], cut)
    games_scrambled = scramble(games, at_or_later, ["temp", "wind", "roof"], cut)
    keep = c("week") <= cut
    cols = ["game_id", "team", *before_columns("team_game")]
    before = team_game_tags(team_games, games)["tags"].join(
        team_games.select("game_id", "team", "week"), on=["game_id", "team"]
    )
    after = team_game_tags(team_scrambled, games_scrambled)["tags"].join(
        team_games.select("game_id", "team", "week"), on=["game_id", "team"]
    )
    assert before.filter(keep).select(cols).equals(after.filter(keep).select(cols))


def test_team_tags_are_known_no_earlier_than_their_inputs():
    team_games, games = toy_team_games()
    parts = team_game_tags(team_games, games)
    tags = parts["tags"].join(team_games, on=["game_id", "team"], suffix="_in")
    assert (tags["known_at"] >= tags["pregame_known_at"]).all()
    result = parts["tags_result"].join(games, on="game_id")
    assert (result["known_at"] == result["result_known_at"]).all()


# Player-games


def toy_player_games() -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """Two seasons of one player: KC in 2023, traded to DEN for 2024, hurt in week 4."""
    rows = []
    for season, team, opp in ((2023, "KC", "DEN"), (2024, "DEN", "KC")):
        for week in range(1, 9):
            if season == 2024 and week == 5:
                continue  # off the 53 after the injury
            report = {4: "Out", 6: "Questionable"}.get(week) if season == 2024 else None
            rows.append(
                {
                    "gsis_id": "P1",
                    "game_id": f"{season}_{week:02d}",
                    "season": season,
                    "week": week,
                    "team": team,
                    "opponent": opp,
                    "known_at": T0,
                    "status": "INA" if report == "Out" else "ACT",
                    "game_status_known_at": T0,
                    "report_status": report,
                    "injury_known_at": T0 if report else None,
                    "rookie_year": 2023,
                    "attempts": 20,
                    "passing_cpoe": 1.5,
                    "stats_known_at": T0 + timedelta(days=1),
                }
            )
    player_games = pl.DataFrame(rows, schema_overrides={"season": pl.Int32, "week": pl.Int32})
    history = player_games.select("gsis_id", "season", "week", "team")
    team_games = pl.DataFrame(
        [
            {
                "game_id": f"{s}_{w:02d}",
                "season": s,
                "team": t,
                "kickoff": T0 + timedelta(days=365 * (s - 2023) + 7 * w),
            }
            for s, t in ((2023, "KC"), (2024, "DEN"))
            for w in range(1, 9)
        ],
        schema_overrides={"season": pl.Int32},
    )
    return player_games, history, team_games


def test_player_tags_follow_their_rules():
    player_games, history, team_games = toy_player_games()
    out = (
        player_game_tags(player_games, history, team_games)["tags"]
        .join(player_games, on=["gsis_id", "game_id"])
        .sort("season", "week")
    )
    y24 = out.filter(c("season") == 2024)
    assert out.filter(c("season") == 2023)["tag_rookie"].all()
    assert y24["tag_new_team"].all() and y24["tag_revenge_game"].all()
    # Week 6 follows the week 4 Out and the week 5 absence; week 6 is also Questionable.
    by_week = dict(zip(y24["week"], y24["tag_first_game_back"], strict=True))
    assert by_week[3] is False and by_week[4] is None and by_week[6] is True
    questionable = dict(zip(y24["week"], y24["tag_active_while_questionable"], strict=True))
    assert questionable[6] is True and questionable[7] is False and questionable[4] is None


def test_before_game_player_tags_ignore_later_weeks():
    player_games, history, team_games = toy_player_games()
    full = player_game_tags(player_games, history, team_games)["tags"]
    for cut in (2, 4, 6):
        early = (c("season") < 2024) | (c("week") <= cut)
        cut_tags = player_game_tags(player_games.filter(early), history.filter(early), team_games)[
            "tags"
        ]
        cols = ["gsis_id", "game_id", *before_columns("player_game")]
        kept = full.join(cut_tags.select("game_id"), on="game_id").select(cols)
        assert kept.sort("game_id").equals(cut_tags.select(cols).sort("game_id")), cut


def test_the_tags_page_is_current():
    from pcf.data.tags.page import PAGE, render

    assert PAGE.read_text(encoding="utf-8") == render(), "run `python -m pcf.data.tags.page`"
