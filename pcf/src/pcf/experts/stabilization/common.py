"""Stabilization's constants (decision 0052): the measures, groups, seasons and folders.

Every measure is a rate `num / den` per player-game (or team-game), `den` its attempts. The kinds
follow the exploration (EXPLORATION.md, the noise ceiling): **usage** (how a player is used),
**mixed** and **efficiency** (how well it goes against expected). The in-season filter is built for
usage rates and team offensive tendencies; efficiency rates stay static unless I154's game-noise
factor makes the filter beat static (the agreed brief, rung 4).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pcf.config import get_config

PROJECT = "stabilization"
FIRST, LAST = 2006, 2024  # the 2025 vault stays closed (the CEO decides at the end)
TEST = tuple(range(2018, 2025))  # the brief's walk-forward test seasons
CHECKPOINTS = (4, 8, 12)  # forecasts after games 4, 8 and 12 of a season
HORIZON = 4  # the next 4 games
Z80 = 1.2815515655446004
Z90 = 1.6448536269514722
COPIES = 19  # shuffled-player copies: the real forecast must beat all of them (p < 0.05)
DRAWS = 2000  # bootstrap draws (players resampled; teams for team measures)
SWING_WEIGHT = 20.0  # I14: a player's swing is shrunk toward 1 with 20 games' weight

# Roster position -> the measure group (stabilization keeps its roster grouping of linebackers:
# the CEO, 2026-11-26: "No stabilization's build does not need to count off ball linebackers as
# inside linebackers for now"; skill-over-expected's off-ball rule stays there).
GROUP = {
    "WR": "receiver",
    "TE": "receiver",
    "RB": "back",
    "FB": "back",
    "QB": "qb",
    "DE": "rusher",
    "DT": "rusher",
    "NT": "rusher",
    "DL": "rusher",
    "OLB": "rusher",
    "CB": "coverage",
    "S": "coverage",
    "SS": "coverage",
    "FS": "coverage",
    "DB": "coverage",
    "LB": "coverage",
    "ILB": "coverage",
    "MLB": "coverage",
}
# Roster position -> the position each rate is centred by (its pull target's class)
POS = {
    "WR": "WR",
    "TE": "TE",
    "RB": "RB",
    "FB": "RB",
    "QB": "QB",
    "DE": "DL",
    "DT": "DL",
    "NT": "DL",
    "DL": "DL",
    "OLB": "OLB",
    "CB": "CB",
    "S": "S",
    "SS": "S",
    "FS": "S",
    "DB": "S",
    "LB": "LB",
    "ILB": "LB",
    "MLB": "LB",
}


@dataclass(frozen=True)
class Measure:
    name: str
    label: str
    group: str  # receiver measures are also read for backs (backs run routes)
    kind: str  # usage, mixed or efficiency
    attempts: str
    source: str  # pbp, pfr (at its lag) or standin (snap share times the team's plays)
    first: int


MEASURES = (
    Measure("tprr", "targets a route", "receiver", "usage", "routes (stand-in)", "standin", 2013),
    Measure("yprr", "yards a route", "receiver", "mixed", "routes (stand-in)", "standin", 2013),
    Measure("adot", "aDOT (air yards a target)", "receiver", "usage", "targets", "pbp", 2006),
    Measure("catch_oe", "catch over expected", "receiver", "efficiency", "targets", "pbp", 2006),
    Measure("yac_oe", "YAC over expected", "receiver", "efficiency", "catches", "pbp", 2006),
    Measure(
        "car_per_run",
        "carries a run snap",
        "back",
        "usage",
        "run snaps (stand-in)",
        "standin",
        2013,
    ),
    Measure("yaco", "yards after contact a carry", "back", "efficiency", "carries", "pfr", 2018),
    Measure(
        "broken_per_touch", "broken tackles a touch", "back", "efficiency", "touches", "pfr", 2018
    ),
    Measure("hitsack", "hit-or-sack rate faced", "qb", "mixed", "dropbacks", "pbp", 2006),
    Measure("sack", "sack rate", "qb", "mixed", "dropbacks", "pbp", 2006),
    Measure("scramble", "scramble rate", "qb", "usage", "dropbacks", "pbp", 2006),
    Measure("qb_adot", "QB aDOT", "qb", "usage", "attempts", "pbp", 2006),
    Measure("cpoe", "completion over expected", "qb", "mixed", "attempts", "pbp", 2006),
    Measure("pressured", "pressured rate (PFR)", "qb", "efficiency", "dropbacks", "pfr", 2018),
    Measure(
        "press_per_snap",
        "pressures a pass snap",
        "rusher",
        "efficiency",
        "pass snaps (stand-in)",
        "pfr",
        2018,
    ),
    Measure(
        "hits_per_snap",
        "QB hits a pass snap",
        "rusher",
        "mixed",
        "pass snaps (stand-in)",
        "standin",
        2013,
    ),
    Measure(
        "tgt_per_cov",
        "targets a coverage snap",
        "coverage",
        "usage",
        "pass snaps (stand-in)",
        "pfr",
        2018,
    ),
    Measure(
        "catch_allowed", "catch rate allowed", "coverage", "efficiency", "targets", "pfr", 2018
    ),
    Measure("adot_allowed", "aDOT allowed", "coverage", "usage", "targets", "pfr", 2018),
    Measure(
        "missed_tackle",
        "missed tackle rate",
        "coverage",
        "efficiency",
        "tackle chances",
        "pfr",
        2018,
    ),
)
BY_NAME = {m.name: m for m in MEASURES}
# The measures whose attempts are a stand-in for participation's exact count (the brief's live
# stand-ins): routes, run snaps and pass snaps on defense.
STANDIN = ("tprr", "yprr", "car_per_run", "hits_per_snap", "press_per_snap", "tgt_per_cov")
# PFR's charting is known the Tuesday after the following week: a forecast reads it at its lag.
LAGGED = tuple(m.name for m in MEASURES if m.source == "pfr")

TEAM_MEASURES = ("hitsack", "proe", "shotgun", "no_huddle", "explosive", "success", "adot")
TEAM_KIND = {
    "hitsack": "mixed",
    "proe": "usage",
    "shotgun": "usage",
    "no_huddle": "usage",
    "explosive": "efficiency",
    "success": "efficiency",
    "adot": "usage",
}
TEAM_LABEL = {
    "hitsack": "hit-or-sack rate",
    "proe": "pass rate over expected",
    "shotgun": "shotgun rate",
    "no_huddle": "no-huddle rate",
    "explosive": "explosive-play rate",
    "success": "success rate",
    "adot": "aDOT",
}

# H113's teammates' conditions, per measure (the exploration's pre-registered list)
COND = {
    "hs": "team hit-or-sack allowed",
    "oc": "passer's cpoe to others",
    "pr": "team pass rate over expected",
    "op": "rest of the defense's pressures a dropback",
    "ocat": "rest of the coverage's catch rate allowed",
}
COND_OF = {
    **{m: ("hs", "oc", "pr") for m in ("tprr", "yprr", "adot", "catch_oe", "yac_oe")},
    **{m: ("op",) for m in ("press_per_snap", "hits_per_snap")},
    **{m: ("ocat",) for m in ("tgt_per_cov", "catch_allowed", "adot_allowed", "missed_tackle")},
}
GROUP_MEASURES = {
    g: tuple(m.name for m in MEASURES if m.group == g)
    for g in ("receiver", "back", "qb", "rusher", "coverage")
}
# the other measures a back's rates may borrow (backs run routes: the receiver measures)
BORROW = {"back": ("car_per_run", "tprr", "yprr", "adot")}
CONSISTENT_R = 0.5  # H114's bar: a measure is "consistent" at a true-rate season r of 0.5+


def cache_dir() -> Path:
    d = get_config().zone("interim") / "stabilization_build"
    d.mkdir(parents=True, exist_ok=True)
    return d


def report_dir() -> Path:
    d = Path(__file__).resolve().parents[4] / "projects" / PROJECT / "build"
    d.mkdir(parents=True, exist_ok=True)
    return d
