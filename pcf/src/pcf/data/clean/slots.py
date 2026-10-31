"""Each player on each play → a slot label (`WR2`, `CB1`, ...), with a fallback for players
missing from that week's depth chart (CEO decision 2A, cleaning-port brief).

Fallback, in order, recorded in `label_source`:
1. `week`: that team's chart for that week.
2. `earlier_week`: the player's label on that team's most recent earlier chart that season,
   unless someone listed this week already holds it. Then the next free number at that position.
3. `roster`: their roster position that week, ranked just past the deepest label in use there
   (WR4 if WR1-3 are taken).
4. `none`: none of the above. Labelled `unknown`, and counted in the log.
"""

import re
from collections.abc import Iterable

import polars as pl

from pcf.core.log import get_logger
from pcf.data.clean.depth_charts import SPECIAL

log = get_logger(__name__)

TEAM_WEEK = ["season", "week", "team"]
UNKNOWN = "unknown"

# Roster positions → chart positions. A roster says "T" or "OL" where a chart says LT or RT, so
# those keep a generic name and rank past the whole group they could be (RANK_PAST).
ROSTER_POSITIONS = {
    **{p: p for p in ["QB", "RB", "FB", "WR", "TE", "C", "T", "G", "OL"]},
    **{p: p for p in ["DE", "DT", "NT", "DL", "ILB", "OLB", "MLB", "CB", "FS", "SS", "S"]},
    "OT": "T",
    "OG": "G",
    "SAF": "S",
    "LB": "MLB",  # as the old chart clean-up did
    "DB": "CB",  # as the old chart clean-up did
    "K": SPECIAL,
    "P": SPECIAL,
    "LS": SPECIAL,
    # Return specialists listed only as such (rare on run and pass plays).
    "PR": SPECIAL,
    "KR": SPECIAL,
}
RANK_PAST = {
    "T": ["LT", "RT"],
    "G": ["LG", "RG"],
    "OL": ["LT", "LG", "C", "RG", "RT"],
    "DL": ["DE", "DT", "NT"],
    "S": ["SS", "FS"],
}

# Position → group, for summing slots by group (replaces the old hardcoded label list).
POSITION_GROUPS = {
    "qbs": ["QB"],
    "rbs": ["RB", "FB"],
    "tes": ["TE"],
    "wrs": ["WR"],
    "ol": ["LT", "LG", "C", "RG", "RT", "T", "G", "OL"],
    "dl": ["DE", "DT", "NT", "DL"],
    "lbs": ["OLB", "ILB", "MLB"],
    "cbs": ["CB"],
    "ss": ["SS", "FS", "S"],
    "special": [SPECIAL],
}
OFFENSE_GROUPS = ["qbs", "rbs", "tes", "wrs", "ol"]
DEFENSE_GROUPS = ["dl", "lbs", "cbs", "ss"]


def slot_labels(players: pl.DataFrame, labels: pl.DataFrame, rosters: pl.DataFrame) -> pl.DataFrame:
    """`players_on_play` rows + `depth_labels` + weekly rosters → the same rows with position,
    position_label and label_source.

    Rosters must be in PCF's team codes (`standard.weekly_rosters`). A player missing from the
    chart gets one label for the whole game, and it never repeats a label someone listed that
    week already holds, so no two players on one side of a play share a label.
    """
    keyed = players.with_columns(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32))
    chart = labels.select(*TEAM_WEEK, "gsis_id", "position", "position_label")
    listed = keyed.join(chart, on=[*TEAM_WEEK, "gsis_id"], how="left")

    found = listed.filter(pl.col("position_label").is_not_null()).with_columns(
        label_source=pl.lit("week")
    )
    unlisted = listed.filter(pl.col("position_label").is_null()).drop("position", "position_label")
    fallback = _fallback_labels(
        unlisted.select(*TEAM_WEEK, "gsis_id").unique(), chart, _roster_positions(rosters)
    )
    out = pl.concat(
        [found, unlisted.join(fallback, on=[*TEAM_WEEK, "gsis_id"], how="left")],
        how="diagonal_relaxed",
    )
    none = out.filter(pl.col("label_source") == "none").height
    if none:
        log.warning("slot labels: %d player-plays with no chart or roster row", none)
    return out.select(*players.columns, "position", "position_label", "label_source").sort(
        "game_id", "play_id", "side", "slot"
    )


def _roster_positions(rosters: pl.DataFrame) -> pl.DataFrame:
    """season, week, team, gsis_id → roster_position, in chart position names."""
    # The finer depth_chart_position first; the plain position when that's missing or not a
    # position PCF labels.
    known = list(ROSTER_POSITIONS)
    roster = rosters.select(
        pl.col("season").cast(pl.Int32),
        pl.col("week").cast(pl.Int32),
        "team",
        "gsis_id",
        "depth_chart_position",
        "position",
        roster_position=pl.when(pl.col("depth_chart_position").is_in(known))
        .then("depth_chart_position")
        .otherwise("position"),
    ).unique([*TEAM_WEEK, "gsis_id"], keep="first", maintain_order=True)
    unknown = roster.filter(
        pl.col("roster_position").is_not_null() & ~pl.col("roster_position").is_in(known)
    )
    if unknown.height:
        pairs = unknown.select("depth_chart_position", "position").unique().rows()
        raise ValueError(f"rosters have positions PCF doesn't map: {sorted(pairs, key=str)}")
    return roster.select(
        *TEAM_WEEK,
        "gsis_id",
        pl.col("roster_position").replace_strict(ROSTER_POSITIONS, default=None),
    )


def _number(label: pl.Expr) -> pl.Expr:
    return label.str.extract(r"(\d+)$").cast(pl.Int32)


def _fallback_labels(
    missing: pl.DataFrame, chart: pl.DataFrame, roster: pl.DataFrame
) -> pl.DataFrame:
    """One row per unlisted player and team-week: position, position_label, label_source."""
    earlier = missing.sort("week").join_asof(
        chart.sort("week").rename({"position": "earlier_position", "position_label": "earlier"}),
        on="week",
        by=["season", "team", "gsis_id"],
        strategy="backward",
        allow_exact_matches=False,
        check_sortedness=False,  # sorted by week above; polars can't check within groups
    )
    candidates = earlier.join(roster, on=[*TEAM_WEEK, "gsis_id"], how="left").with_columns(
        position=pl.coalesce("earlier_position", "roster_position"),
        label_source=pl.when(pl.col("earlier").is_not_null())
        .then(pl.lit("earlier_week"))
        .when(pl.col("roster_position").is_not_null())
        .then(pl.lit("roster"))
        .otherwise(pl.lit("none")),
    )

    # Step 2 keeps the earlier label only while nobody listed this week holds it.
    taken = chart.select(*TEAM_WEEK, earlier="position_label")
    keeps = (
        candidates.filter(pl.col("earlier").is_not_null())
        .join(taken, on=[*TEAM_WEEK, "earlier"], how="anti")
        .sort("gsis_id")
        .unique([*TEAM_WEEK, "earlier"], keep="first")
        .select(*TEAM_WEEK, "gsis_id", position_label="earlier")
    )
    labelled = candidates.join(keeps, on=[*TEAM_WEEK, "gsis_id"], how="left")

    # Everyone else with a position is ranked past the deepest label in use at that position (or
    # in the group a generic roster position could be): players from an earlier chart first,
    # then roster-only players, each in gsis_id order.
    in_use = pl.concat(
        [
            chart.select(*TEAM_WEEK, "position", "position_label"),
            labelled.filter(pl.col("position_label").is_not_null()).select(
                *TEAM_WEEK, "position", "position_label"
            ),
        ]
    ).select(*TEAM_WEEK, "position", number=_number(pl.col("position_label")))
    generic = pl.DataFrame(
        [(g, p) for g, members in RANK_PAST.items() for p in members],
        schema=["generic", "position"],
        orient="row",
    )
    deepest = (
        pl.concat(
            [
                in_use,
                in_use.join(generic, on="position")
                .drop("position")
                .rename({"generic": "position"}),
            ],
            how="diagonal",
        )
        .group_by(*TEAM_WEEK, "position")
        .agg(deepest=pl.col("number").max())
    )
    rest = (
        labelled.filter(pl.col("position_label").is_null() & pl.col("position").is_not_null())
        .sort(pl.col("label_source") != "earlier_week", "gsis_id")
        .with_columns(extra=pl.int_range(1, pl.len() + 1).over(*TEAM_WEEK, "position"))
        .join(deepest, on=[*TEAM_WEEK, "position"], how="left")
        .select(
            *TEAM_WEEK,
            "gsis_id",
            ranked=pl.col("position")
            + (pl.col("deepest").fill_null(0) + pl.col("extra")).cast(pl.String),
        )
    )
    return labelled.join(rest, on=[*TEAM_WEEK, "gsis_id"], how="left").select(
        *TEAM_WEEK,
        "gsis_id",
        "position",
        position_label=pl.coalesce("position_label", "ranked", pl.lit(UNKNOWN)),
        label_source="label_source",
    )


def position_of(position_label: str) -> str:
    """`WR2` → `WR`, `special1` → `special`."""
    return re.sub(r"\d+$", "", position_label)


def position_groups(position_labels: Iterable[str]) -> dict[str, list[str]]:
    """Group slot labels for summing by group (the old `get_position_groups`, from the labels
    actually present instead of a hardcoded list). Keys: offense, defense and each group."""
    labels = sorted(set(position_labels) - {UNKNOWN})
    by_position = {p: g for g, positions in POSITION_GROUPS.items() for p in positions}
    groups: dict[str, list[str]] = {g: [] for g in POSITION_GROUPS}
    for label in labels:
        group = by_position.get(position_of(label))
        if group is None:
            raise ValueError(f"slot label {label!r} has no position group")
        groups[group].append(label)
    groups["offense"] = [lbl for g in OFFENSE_GROUPS for lbl in groups[g]]
    groups["defense"] = [lbl for g in DEFENSE_GROUPS for lbl in groups[g]]
    return groups
