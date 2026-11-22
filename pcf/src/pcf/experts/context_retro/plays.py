"""context-retro's play table: every dropback from 2016 with the situation, the calls charted since
2016, coverage (2018 on), FTN's calls (2022 on) and the six outcomes (decision 0041; the brief is
`projects/context-v2/BRIEF.md`, "The brief, after the exploration").

Retrospective (rule m): participation's coverage, pass rushers and box are after-the-season data,
so a play's `as_of` is the later of its game's (context-live's: the first weekly run 14 days after
kickoff) and participation's `known_at`. A season without a field has it as missing (the brief's
call 1), not a separate edition per era.

**A sack counts as a pressure in every season** (call 3): before 2023 participation leaves
`was_pressure` empty on every sack (context-v2's fourth look). `pressure_y` is that corrected flag;
a dropback with the flag missing and no sack has `pressure_y` missing: it is left out of every
model given the pressure and scored before the snap only.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import polars as pl

from pcf.config import get_config
from pcf.core.log import get_logger
from pcf.data.gateway import END_OF_TIME, Gateway, TableSource
from pcf.experts.context_live import plays as live_plays

log = get_logger(__name__)
c = pl.col
KEYS = live_plays.KEYS
FIRST = 2016  # participation's first season
COVERAGE_FIRST = 2018  # participation's coverage starts here
FTN_FIRST = 2022

INPUTS = {"play": ("pbp", "ftn")}
RETRO_INPUTS = {"play": ("participation",)}
SITUATION = live_plays.SITUATION
CALLS16 = ["shotgun", "no_huddle", "rushers_p", "box_p"]  # charted since 2016 (decision 0038)
# Participation's coverage codes (the 2023 provider adds Cover 9 and combo); one column each, so
# both the linear rung and the trees read them the same way. Missing before 2018.
COVERAGES = ["COVER_0", "COVER_1", "COVER_2", "2_MAN", "COVER_3", "COVER_4", "COVER_6", "COVER_9",
             "COMBO", "PREVENT", "BLOWN"]  # fmt: skip
COVERAGE = [f"cov_{k}" for k in COVERAGES] + ["man"]
# Before 2023 participation leaves coverage empty on every sack (as it does the pressure flag), so
# for an outcome whose plays include sacks, a missing coverage would mark the sack: those outcomes
# read coverage only from the provider that charts it on sacks too (decision 0041, call 7).
NEW_PROVIDER = 2023
DROPBACK_COVERAGE = [f"d{x}" for x in COVERAGE]
FTN = [x for x in live_plays.CALLS if x not in ("shotgun", "no_huddle")]
FIELDS_ATTEMPT = SITUATION + CALLS16 + COVERAGE + FTN  # depth and completion: no sacks in them
FIELDS_DROPBACK = SITUATION + CALLS16 + DROPBACK_COVERAGE + FTN
FIELDS = SITUATION + CALLS16 + COVERAGE + DROPBACK_COVERAGE + FTN
# In 2016-2017 participation has no rusher count on 1,447 dropbacks, almost none of them sacks
# (0.1% against 6.1%): a gap that marks the play. Filled with the league's usual count (4 rushers,
# 6 in the box; the modes of 2016-2022), so the gap carries nothing (call 8).
RUSHERS_FILL, BOX_FILL = 4.0, 6.0
CONDITION = "pressure_y"  # the given-pressure mode's extra field

COLUMNS = [*KEYS, "season", "season_type", "week", "posteam", "defteam", "passer_id", "known_at",
           "known_at_targets", "as_of", "is_dropback", "is_attempt", *FIELDS, "pressure_y",
           "time_to_throw_y", "sack_y", "air_yards_y", "complete_y", "yards"]  # fmt: skip


def cache_dir() -> Path:
    return get_config().zone("interim") / "context_retro_build"


def participation_fields(part: pl.DataFrame) -> pl.DataFrame:
    """Per play: participation's raw pressure flag, time to throw, pass rushers, box count,
    coverage (one column per code, missing before it is charted) and man (1) or zone (0)."""
    known = "participation_known_at" if "participation_known_at" in part.columns else "known_at"
    cov = c("defense_coverage_type")
    charted = cov.is_not_null() & (cov != "")
    return part.select(
        c("game_id"),
        c("play_id").cast(pl.Int64),
        was_pressure=c("was_pressure").cast(pl.Float64),
        time_to_throw_y=c("time_to_throw").cast(pl.Float64),
        rushers_p=c("number_of_pass_rushers").cast(pl.Float64),
        box_p=c("defenders_in_box").cast(pl.Float64),
        **{
            f"cov_{k}": pl.when(charted).then((cov == k).cast(pl.Float64)).otherwise(None)
            for k in COVERAGES
        },
        man=pl.when(c("defense_man_zone_type") == "MAN_COVERAGE").then(1.0)
        .when(c("defense_man_zone_type") == "ZONE_COVERAGE").then(0.0).otherwise(None),
        known_at_targets=c(known),
    )  # fmt: skip


def with_pressure(d: pl.DataFrame) -> pl.DataFrame:
    """`pressure_y`: participation's flag, with a sack counted as a pressure (call 3)."""
    return d.with_columns(
        pressure_y=pl.when(c("sack_y") == 1).then(1.0).otherwise(c("was_pressure"))
    )


def uncharted_rushers(d: pl.DataFrame) -> pl.DataFrame:
    """FTN's "0 pass rushers" with a box of 2 or fewer is an uncharted play, not a play with
    nobody rushing (context-live#R17, idea I72): missing."""
    zero = (c("n_pass_rushers") == 0) & (c("n_defense_box") <= 2)
    return d.with_columns(n_pass_rushers=pl.when(zero).then(None).otherwise(c("n_pass_rushers")))


def frame(play: pl.DataFrame, part: pl.DataFrame, as_of: pl.DataFrame) -> pl.DataFrame:
    """One season's dropbacks from an in-season view's `play` (pbp and ftn parts), a retrospective
    view's participation part and each game's `as_of` (game_id, as_of)."""
    base = live_plays.frame(play).filter(c("is_dropback"))
    # a scramble names its QB as the rusher: it's still his dropback
    passer = play.select(c("game_id"), c("play_id").cast(pl.Int64),
                         passer_id=pl.coalesce("passer_player_id", "rusher_player_id"))  # fmt: skip
    d = base.join(passer, on=KEYS, how="left")
    d = d.join(participation_fields(part), on=KEYS, how="left")
    d = d.join(as_of, on="game_id", how="left")
    if d["as_of"].null_count():
        raise ValueError(f"{d['as_of'].null_count()} dropbacks have no as_of")
    d = uncharted_rushers(with_pressure(d))
    d = d.with_columns(
        # the retrospective row is known once participation is out (rule m)
        as_of=pl.max_horizontal("as_of", "known_at_targets"),
        known_at_targets=c("known_at_targets").fill_null(c("known_at")),
        rushers_p=c("rushers_p").fill_null(RUSHERS_FILL),
        box_p=c("box_p").fill_null(BOX_FILL),
        **{f"d{x}": pl.when(c("season") >= NEW_PROVIDER).then(c(x)).otherwise(None)
           for x in COVERAGE},
    )  # fmt: skip
    return d.select(COLUMNS)


def fields_for(population: str) -> list[str]:
    """The call fields an outcome reads, by its plays (attempts, or dropbacks with sacks)."""
    return FIELDS_ATTEMPT if population == "attempt" else FIELDS_DROPBACK


def season_table(season: int, as_of: pl.DataFrame, gw: Gateway | None = None,
                 at=END_OF_TIME) -> pl.DataFrame:  # fmt: skip
    """One season's play table from views at `at` (END_OF_TIME for the build; a game's own
    `as_of` for the point-in-time check)."""
    gw = gw or Gateway(TableSource(seasons=[season - 1, season]))
    play = gw.view(at, "in_season", INPUTS).table("play", seasons=[season])
    part = gw.view(at, "retrospective", RETRO_INPUTS).table("play", seasons=[season])
    return frame(play, part, as_of)


def prepare(seasons: Sequence[int], rebuild: bool = False) -> None:
    """Each season's table, cached in interim/context_retro_build/ (one season at a time: the
    play-by-play is too big to hold whole)."""
    from pcf.experts.context_live.run import moments

    cache_dir().mkdir(parents=True, exist_ok=True)
    as_of = None
    for s in seasons:
        path = cache_dir() / f"plays_{s}.parquet"
        if path.exists() and not rebuild:
            continue
        if as_of is None:
            as_of = moments(Gateway())
        t = season_table(s, as_of)
        t.write_parquet(path)
        log.info("context-retro: %d dropbacks in %d", t.height, s)


def load(seasons: Sequence[int]) -> pl.DataFrame:
    return pl.concat([pl.read_parquet(cache_dir() / f"plays_{s}.parquet") for s in seasons])
