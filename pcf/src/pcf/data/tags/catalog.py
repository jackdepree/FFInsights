"""The tag catalog: football's shared vocabulary, one written rule per tag (tag-tables brief).

Half the tags are statistical (successful, explosive), half are what commentators point out
(hero ball, answer drive, trap game). Each is defined once here, with:

- **level:** the table it labels (play, drive, team_game, player_game);
- **family:** measured, situation or lore;
- **timing:** its football timing, whether it describes the moment before the event or its
  result (tag-tables#F10). Only `before_*` tags may describe the row being predicted;
- **band:** the share of applicable rows it should fire on each season (rule h). A season
  outside it fails the build's checks;
- **applies:** the rows it's defined for. Elsewhere the tag is empty, never False.

A changed rule is a new version (`tag_<name>_v2`), never a silent edit (CEO decision 2A).
`docs/TAGS.md` is generated from this file (`python -m pcf.data.tags.page`).
"""

from dataclasses import dataclass

import polars as pl

LEVELS = ("play", "drive", "team_game", "player_game")
FAMILIES = ("measured", "situation", "lore")
# Football timing, earliest first. "before_*" tags can describe the row being predicted.
TIMINGS = ("before_snap", "before_game", "after_play", "after_drive", "after_game", "after_season")
BEFORE = ("before_snap", "before_game")


@dataclass(frozen=True)
class Tag:
    name: str
    level: str
    family: str
    timing: str
    meaning: str  # the everyday football meaning
    rule_text: str  # the rule, in words, for docs/TAGS.md
    rule: pl.Expr  # evaluated on the level's prepared frame (tags.build)
    band: tuple[float, float] | None  # expected share of applicable rows per season
    applies: pl.Expr | None = None  # rows the tag is defined for (default: every row)
    first_season: int = 1999
    part: str = "tags"  # the table part it's saved in
    values: tuple[str, ...] | None = None  # for category tags
    version: int = 1
    added_by: str = "tag-tables"

    @property
    def column(self) -> str:
        return f"tag_{self.name}" if self.version == 1 else f"tag_{self.name}_v{self.version}"


@dataclass(frozen=True)
class Reference:
    """A catalog entry for a column nflverse already has: listed, not copied."""

    name: str
    table: str
    part: str
    column: str
    meaning: str
    years: str


c = pl.col
lead = c("score_differential")  # the offense's lead before the snap
run = c("play_type") == "run"
passing = c("play_type") == "pass"
scrimmage = run | passing
has_down = c("down").is_not_null()
yards = c("yards_gained")
score_types = ["Touchdown", "Field goal"]

PLAY = [
    # Measured: after the play, on run and pass plays.
    Tag(
        "successful",
        "play",
        "measured",
        "after_play",
        "the play gained positive expected points",
        "EPA above 0 (nflverse `success`)",
        c("success") == 1,
        (0.37, 0.50),
        scrimmage,
    ),
    Tag(
        "explosive",
        "play",
        "measured",
        "after_play",
        "a big play",
        "run of 10+ yards or pass of 20+ yards",
        (run & (yards >= 10)) | (passing & (yards >= 20)),
        (0.07, 0.13),
        scrimmage,
    ),
    Tag(
        "chunk",
        "play",
        "measured",
        "after_play",
        "a chunk of yards in one play",
        "any gain of 15+ yards",
        yards >= 15,
        (0.07, 0.13),
        scrimmage,
    ),
    Tag(
        "stuffed_run",
        "play",
        "measured",
        "after_play",
        "the run went nowhere",
        "run for 0 or fewer yards",
        yards <= 0,
        (0.15, 0.25),
        run,
    ),
    Tag(
        "negative_play",
        "play",
        "measured",
        "after_play",
        "lost yards",
        "loss of yards, sacks included",
        yards < 0,
        (0.06, 0.12),
        scrimmage,
    ),
    Tag(
        "first_down_gained",
        "play",
        "measured",
        "after_play",
        "moved the chains",
        "the play earned a first down",
        c("first_down") == 1,
        (0.24, 0.33),
        scrimmage,
    ),
    Tag(
        "added_win_probability",
        "play",
        "measured",
        "after_play",
        "the play helped the offense win",
        "WPA above 0",
        c("wpa") > 0,
        (0.38, 0.50),
        scrimmage,
    ),
    Tag(
        "high_leverage",
        "play",
        "measured",
        "after_play",
        "a play that mattered",
        "WPA of 5 points or more either way",
        c("wpa").abs() >= 0.05,
        (0.09, 0.17),
        scrimmage,
    ),
    Tag(
        "turnover",
        "play",
        "measured",
        "after_play",
        "gave the ball away",
        "interception or lost fumble",
        (c("interception") == 1) | (c("fumble_lost") == 1),
        (0.012, 0.035),
        scrimmage,
    ),
    Tag(
        "low_percentage_throw",
        "play",
        "measured",
        "after_play",
        "a risky throw",
        "pass with under 40% completion probability",
        c("cp") < 0.40,
        (0.07, 0.16),
        passing & c("cp").is_not_null(),
        first_season=2006,
    ),
    # Situation: the game state before the snap, on plays with a down.
    Tag(
        "garbage_time",
        "play",
        "situation",
        "before_snap",
        "the game is decided",
        "4th quarter with a 17+ point margin, or 3rd quarter with 28+ (CEO decision 1A)",
        ((c("qtr") == 4) & (lead.abs() >= 17)) | ((c("qtr") == 3) & (lead.abs() >= 28)),
        (0.04, 0.10),
        has_down,
    ),
    Tag(
        "game_script",
        "play",
        "situation",
        "before_snap",
        "who's ahead, from the offense's view",
        "leading by 9+, trailing by 9+, or neutral (within one score)",
        pl.when(lead >= 9)
        .then(pl.lit("leading"))
        .when(lead <= -9)
        .then(pl.lit("trailing"))
        .otherwise(pl.lit("neutral")),
        None,
        has_down & lead.is_not_null(),
        values=("leading", "trailing", "neutral"),
    ),
    Tag(
        "neutral_script",
        "play",
        "situation",
        "before_snap",
        "teams play their normal game",
        "within one score (8 points), outside the last 2 "
        "minutes of a half, regulation only (CEO decision 1A)",
        (lead.abs() <= 8) & (c("half_seconds_remaining") > 120) & (c("qtr") <= 4),
        (0.50, 0.68),
        has_down,
    ),
    Tag(
        "red_zone",
        "play",
        "situation",
        "before_snap",
        "inside the 20",
        "inside the opponent's 20",
        c("yardline_100") <= 20,
        (0.11, 0.19),
        has_down,
    ),
    Tag(
        "goal_to_go",
        "play",
        "situation",
        "before_snap",
        "goal to go",
        "goal-to-go down",
        c("goal_to_go") == 1,
        (0.04, 0.09),
        has_down,
    ),
    Tag(
        "backed_up",
        "play",
        "situation",
        "before_snap",
        "backed up against its own goal line",
        "inside its own 10",
        c("yardline_100") >= 90,
        (0.015, 0.045),
        has_down,
    ),
    Tag(
        "money_down",
        "play",
        "situation",
        "before_snap",
        "3rd down",
        "3rd down",
        c("down") == 3,
        (0.17, 0.25),
        has_down,
    ),
    Tag(
        "obvious_pass_down",
        "play",
        "situation",
        "before_snap",
        "everyone knows a pass is coming",
        "2nd and 8+, or 3rd or 4th and 5+",
        ((c("down") == 2) & (c("ydstogo") >= 8))
        | (c("down").is_in([3.0, 4.0]) & (c("ydstogo") >= 5)),
        (0.28, 0.40),
        has_down,
    ),
    Tag(
        "short_yardage",
        "play",
        "situation",
        "before_snap",
        "a yard or two to go on a money down",
        "3rd or 4th and 2 or less",
        c("down").is_in([3.0, 4.0]) & (c("ydstogo") <= 2),
        (0.05, 0.10),
        has_down,
    ),
    Tag(
        "two_minute_drill",
        "play",
        "situation",
        "before_snap",
        "hurrying to score before the half",
        "last 2 minutes of a half, offense not leading by more than 8",
        c("qtr").is_in([2.0, 4.0]) & (c("half_seconds_remaining") <= 120) & (lead <= 8),
        (0.07, 0.14),
        has_down,
    ),
    Tag(
        "four_minute_offense",
        "play",
        "situation",
        "before_snap",
        "running out the clock",
        "last 4 minutes of the game, offense leading by 1 to 16",
        (c("qtr") == 4) & (c("game_seconds_remaining") <= 240) & lead.is_between(1, 16),
        (0.01, 0.04),
        has_down,
    ),
    Tag(
        "middle_eight",
        "play",
        "situation",
        "before_snap",
        "the stretch around halftime where a team can score twice",
        "last 4 minutes of the 1st half or first 4 minutes of the 2nd",
        ((c("qtr") == 2) & (c("half_seconds_remaining") <= 240))
        | ((c("qtr") == 3) & (c("half_seconds_remaining") >= 1560)),
        (0.13, 0.20),
        has_down,
    ),
    Tag(
        "opening_script",
        "play",
        "lore",
        "before_snap",
        "the coach's scripted opening plays",
        "fewer than 15 earlier run or pass plays by this offense in the game",
        c("earlier_snaps") < 15,
        (0.20, 0.30),
        has_down & c("posteam").is_not_null(),
    ),
    # Lore and decisions: after the play.
    Tag(
        "fourth_down_attempt",
        "play",
        "situation",
        "after_play",
        "went for it on 4th down",
        "a run or pass on 4th down (the decision is only known at the snap)",
        scrimmage,
        (0.10, 0.45),
        c("down") == 4,
    ),
    Tag(
        "hero_ball",
        "play",
        "lore",
        "after_play",
        "the QB forced a difficult throw downfield",
        "throw 15+ yards downfield with under 35% completion probability",
        (c("cp") < 0.35) & (c("air_yards") >= 15),
        (0.03, 0.10),
        passing & c("cp").is_not_null(),
        first_season=2006,
    ),
    Tag(
        "check_down",
        "play",
        "lore",
        "after_play",
        "took the short, safe throw",
        "pass thrown under 2 yards downfield, not a scramble",
        (c("air_yards") < 2) & (c("qb_scramble") != 1),
        (0.15, 0.35),
        passing & c("air_yards").is_not_null(),
        first_season=2006,
    ),
    Tag(
        "scramble_drill",
        "play",
        "lore",
        "after_play",
        "the play broke down and the QB ran",
        "QB scramble (nflverse `qb_scramble`)",
        c("qb_scramble") == 1,
        (0.01, 0.05),
        scrimmage,
    ),
    Tag(
        "momentum_swing",
        "play",
        "lore",
        "after_play",
        "a play that swung the game",
        "WPA of 10 points or more either way, or a turnover",
        (c("wpa").abs() >= 0.10) | (c("interception") == 1) | (c("fumble_lost") == 1),
        (0.03, 0.07),
        scrimmage,
    ),
    Tag(
        "stat_padding",
        "play",
        "lore",
        "after_play",
        "yards that came when the game was decided",
        "trailing team gains yards in garbage time",
        c("tag_garbage_time").fill_null(False) & (lead < 0) & (yards > 0),
        (0.01, 0.05),
        scrimmage,
    ),
]

DRIVE = [
    Tag(
        "scoring_drive",
        "drive",
        "measured",
        "after_drive",
        "the drive scored",
        "ends in a touchdown or field goal",
        c("result").is_in(score_types),
        (0.27, 0.45),
    ),
    Tag(
        "three_and_out",
        "drive",
        "lore",
        "after_drive",
        "three plays and a punt",
        "ends in a punt without a first down",
        (c("result") == "Punt") & (c("first_downs") == 0),
        (0.15, 0.28),
    ),
    Tag(
        "methodical_drive",
        "drive",
        "lore",
        "after_drive",
        "a long, grinding drive",
        "10 or more run or pass plays",
        c("plays") >= 10,
        (0.07, 0.20),
    ),
    Tag(
        "quick_strike",
        "drive",
        "lore",
        "after_drive",
        "scored in a hurry",
        "touchdown in 4 or fewer plays, or 90 seconds or less",
        (c("result") == "Touchdown") & ((c("plays") <= 4) | (c("seconds") <= 90)),
        (0.03, 0.08),
    ),
    Tag(
        "answer_drive",
        "drive",
        "lore",
        "after_drive",
        "answered a touchdown with a touchdown",
        "touchdown right after the opponent's touchdown",
        (c("result") == "Touchdown")
        & (c("prev_result") == "Touchdown")
        & (c("prev_team") != c("posteam")),
        (0.02, 0.07),
    ),
    Tag(
        "goal_line_stand",
        "drive",
        "lore",
        "after_drive",
        "the defense held at the goal line",
        "had 1st and goal inside the 5 and didn't score a touchdown",
        c("goal_inside_5") & (c("result") != "Touchdown"),
        (0.005, 0.025),
    ),
    Tag(
        "backbreaker",
        "drive",
        "lore",
        "after_drive",
        "a score right before halftime",
        "touchdown or field goal ending in the last 2 minutes of the 1st half",
        c("result").is_in(score_types) & (c("end_qtr") == 2) & (c("end_half_seconds") <= 120),
        (0.025, 0.06),
    ),
    Tag(
        "sudden_change",
        "drive",
        "situation",
        "before_snap",
        "taking over after a turnover",
        "the drive starts right after the opponent turned the ball over",
        (c("prev_result") == "Turnover") & (c("prev_team") != c("posteam")),
        (0.06, 0.14),
        c("prev_result").is_not_null(),
    ),
]

TEAM_GAME = [
    Tag(
        "primetime",
        "team_game",
        "situation",
        "before_game",
        "the night game",
        "kickoff at 7pm Eastern or later (1999 has no kickoff times)",
        c("et_hour") >= 19,
        (0.08, 0.30),
        first_season=2000,
    ),
    Tag(
        "short_week",
        "team_game",
        "situation",
        "before_game",
        "a short week (Thursday games)",
        "4 or fewer days of rest",
        c("rest") <= 4,
        (0.00, 0.10),
    ),
    Tag(
        "off_bye",
        "team_game",
        "situation",
        "before_game",
        "coming off a bye",
        "13 or more days of rest",
        c("rest") >= 13,
        (0.02, 0.13),  # 2001: 11% (the week postponed after 9/11)
    ),
    Tag(
        "divisional",
        "team_game",
        "situation",
        "before_game",
        "a division rival",
        "division game (half the schedule before the 2002 realignment)",
        c("div_game") == 1,
        (0.30, 0.55),
    ),
    Tag(
        "home_underdog",
        "team_game",
        "situation",
        "before_game",
        "the home team getting points",
        "home team that's the underdog",
        c("home") & (c("spread") > 0),
        (0.12, 0.25),
        c("spread").is_not_null(),
    ),
    Tag(
        "big_favorite",
        "team_game",
        "situation",
        "before_game",
        "a heavy favorite",
        "favored by 10 or more",
        c("spread") <= -10,
        (0.02, 0.13),
        c("spread").is_not_null(),
    ),
    Tag(
        "trap_game",
        "team_game",
        "lore",
        "before_game",
        "a big favorite looking ahead to a rival",
        "favored by 7+, with a division game next (regular season)",
        (c("spread") <= -7) & (c("next_reg_div") == 1).fill_null(False),
        (0.02, 0.11),
        (c("game_type") == "REG") & c("spread").is_not_null(),
    ),
    Tag(
        "backup_qb_start",
        "team_game",
        "lore",
        "before_game",
        "the backup is starting",
        "today's starting QB isn't the team's most common starter so far this season",
        c("qb_id") != c("usual_qb"),
        (0.05, 0.28),
        c("usual_qb").is_not_null() & c("qb_id").is_not_null(),
    ),
    Tag(
        "weather_game",
        "team_game",
        "situation",
        "after_game",
        "a cold or windy game",
        "outdoors, 32°F or colder or 15+ mph wind (game-time readings: no forecasts)",
        (c("temp") <= 32) | (c("wind") >= 15),
        (0.05, 0.30),  # 2022: 28% (readings for only half its outdoor games, tag-tables#F15)
        c("roof").is_in(["outdoors", "open"]) & (c("temp").is_not_null() | c("wind").is_not_null()),
        part="tags_result",
    ),
]

PLAYER_GAME = [
    Tag(
        "rookie",
        "player_game",
        "situation",
        "before_game",
        "a rookie",
        "first NFL season",
        c("season") == c("rookie_year"),
        (0.10, 0.22),
        c("rookie_year").is_not_null(),
        first_season=2002,
    ),
    Tag(
        "new_team",
        "player_game",
        "situation",
        "before_game",
        "new to the team this season",
        "on a different team than at the end of the player's previous season",
        c("team") != c("last_team"),
        (0.10, 0.30),
        c("last_team").is_not_null(),
        first_season=2003,
    ),
    Tag(
        "revenge_game",
        "player_game",
        "lore",
        "before_game",
        "facing a former team",
        "the opponent is a team the player was on in an earlier game",
        c("faced_former"),
        (0.003, 0.03),
        first_season=2003,
    ),
    Tag(
        "first_game_back",
        "player_game",
        "situation",
        "before_game",
        "back from injury",
        "active after being listed Out for the team's previous game, or after missing the "
        "team's previous game off the 53-man roster",
        ((c("prev_report") == "Out").fill_null(False) & (c("prev_game_no") == c("game_no") - 1))
        | (c("prev_game_no") < c("game_no") - 1),
        (0.01, 0.08),
        (c("status") == "ACT") & c("prev_game_no").is_not_null(),
        first_season=2019,
    ),
    Tag(
        "active_while_questionable",
        "player_game",
        "situation",
        "before_game",
        "playing through an injury",
        "listed Questionable, then active (not on the report counts as no: tag-tables#F7)",
        (c("report_status") == "Questionable").fill_null(False),
        (0.02, 0.08),
        c("status") == "ACT",
        first_season=2019,
    ),
    Tag(
        "positive_cpoe_game",
        "player_game",
        "measured",
        "after_game",
        "completed more than expected",
        "the passer's CPOE for the game is above 0 (10+ attempts)",
        c("passing_cpoe") > 0,
        (0.40, 0.62),
        (c("attempts") >= 10) & c("passing_cpoe").is_not_null(),
        first_season=2006,
        part="tags_result",
    ),
]

TAGS: list[Tag] = [*PLAY, *DRIVE, *TEAM_GAME, *PLAYER_GAME]

FTN = "FTN charting (2022→)"
REFERENCES = [
    Reference("play_action", "play", "ftn", "is_play_action", "play action", FTN),
    Reference("screen", "play", "ftn", "is_screen_pass", "screen pass", FTN),
    Reference("rpo", "play", "ftn", "is_rpo", "run-pass option", FTN),
    Reference("trick_play", "play", "ftn", "is_trick_play", "trick play", FTN),
    Reference("no_huddle", "play", "ftn", "is_no_huddle", "no huddle", FTN),
    Reference("motion", "play", "ftn", "is_motion", "pre-snap motion", FTN),
    Reference("blitz", "play", "ftn", "n_blitzers", "blitz (more than 0 blitzers)", FTN),
    Reference("out_of_pocket", "play", "ftn", "is_qb_out_of_pocket", "QB out of the pocket", FTN),
    Reference(
        "interception_worthy",
        "play",
        "ftn",
        "is_interception_worthy",
        "a throw that should have been intercepted",
        FTN,
    ),
    Reference(
        "held_the_ball",
        "play",
        "ftn",
        "is_qb_fault_sack",
        "sack on the QB: held the ball (stands in for coverage sack, tag-tables#F5)",
        FTN,
    ),
    Reference(
        "pressure",
        "play",
        "participation",
        "was_pressure",
        "QB pressured",
        "participation (2016–2025, after the season)",
    ),
]


def tags_for(level: str, part: str | None = None) -> list[Tag]:
    """The catalog's tags at a level (and part), in catalog order."""
    return [t for t in TAGS if t.level == level and (part is None or t.part == part)]


def _check_catalog() -> None:
    names = [t.column for t in TAGS] + [r.name for r in REFERENCES]
    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        raise ValueError(f"tag names used twice: {sorted(dupes)}")
    for t in TAGS:
        if t.level not in LEVELS or t.family not in FAMILIES or t.timing not in TIMINGS:
            raise ValueError(f"tag {t.name}: bad level, family or timing")
        if (t.values is None) == (t.band is None):
            raise ValueError(f"tag {t.name}: a yes/no tag needs a band, a category tag values")


_check_catalog()
