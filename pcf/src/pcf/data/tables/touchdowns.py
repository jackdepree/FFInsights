"""The touchdown parts (td-expert project, decision 0043): `play.xtd`, `drive.td_chance`,
`player_game.touchdowns` and `team_game.touchdowns`.

- **A chance** is a target (a pass with a receiver, not a sack) or a carry (a run with a rusher) by
  anyone; two-point tries are left out. A player's chances are counted for his position (QB, RB,
  WR, TE); a target's thrower is its passer.
- **Expected touchdowns (xtd)** come from where the chance happened, fit on earlier seasons only:
  - RB, WR and TE chances take opportunity-quality's value (`play.xfp`'s `oq_td_exp`), so the two
    experts never disagree about the same chance;
  - QB carries (scrambles included) have their own model (`QB_INPUTS`: the situation and whether
    it was a scramble), fit like opportunity-quality's (boosted trees on
    the situation, up to 10 earlier regular seasons, never fewer than 3, from 2009): scrambles and
    sneaks are a different mix from a back's carries;
  - any other chance (a target to a lineman, a carry by a returner) uses opportunity-quality's own
    fitted models, passed in by the builder.
  - A throw's expected touchdowns are its target's.
- **The drive model:** each snap's chance that its drive ends in a touchdown, from the situation
  before the snap (`DRIVE`), fit on earlier regular seasons from 2006 the same way. Per drive: the
  chance at its first snap, at its first snap inside the 20, and its highest (the near miss on a
  drive that ended in a field-goal try; a description only, never a forecasting input: brief).
- **The drive-aware hindsight** (the team's ceiling, brief "Tests"): for a drive that reached the
  20, its chance at that first snap inside the 20; for one that didn't, what it did (a long
  touchdown, or none). It is a fair hindsight because the drive model's chance is an average over
  what can still happen, read at a moment fixed before the outcome; summing the chances' expected
  touchdowns isn't, because a failed goal-line series makes more chances (EXPLORATION F20, F21).
- **The luck measure** (looking back): touchdowns minus expected, in units of the dice's spread on
  those chances (the square root of the sum of p × (1 − p)), and the chance of scoring at least
  that many from those chances (`at_least`, exact).

Builders are pure: rows in, rows out. Every column carries the `tdx_` prefix, so it never clashes
with the play-by-play's (`td_team`, `td_player_id`) or opportunity-quality's (`oq_`).
"""

from __future__ import annotations

import pickle
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from pcf.data.tables.opportunity import KIND_INPUTS, SIDES, GAPS, SITUATION, TREES
from pcf.data.tables.pace import training_seasons

c = pl.col
POSITIONS = ("QB", "RB", "WR", "TE")
SKILL = ("RB", "WR", "TE")  # opportunity-quality's positions
FIRST_FIT = 2009  # QB carries' model: the first season it learns from (td-expert F1)
FIRST_DRIVE_FIT = 2006  # the drive model's first training season (VALIDATION.md §1)
FIRST_SEASON = 2012  # the first season with expected touchdowns (opportunity-quality's)
MODEL_VERSION = 2  # bump when the chances, the inputs or the fit settings change
RED_ZONE, INSIDE_10, GOAL_LINE = 20, 10, 5
# A QB's carries include his scrambles, which nflverse marks `rush` 0 and `pass` 1 (a 2023 check:
# 32 of 496 rushing touchdowns); every run play with a rusher counts. Opportunity-quality's
# carries need `rush` 1, which only matters for QBs, whom it doesn't score.
QB_INPUTS = [*KIND_INPUTS["carry"], "scramble"]
PBP_COLUMNS = [
    "game_id", "play_id", "season", "season_type", "play_type", "two_point_attempt", "sack",
    "rush", "qb_scramble", "receiver_player_id", "rusher_player_id", "passer_player_id", "td_player_id",
    "touchdown", "posteam", "home_team", "away_team", "fixed_drive", "fixed_drive_result",
    "air_yards", "pass_location", "run_location", "run_gap", "yardline_100", "down", "ydstogo",
    "goal_to_go", "shotgun", "no_huddle", "qtr", "half_seconds_remaining", "score_differential",
]  # fmt: skip
DRIVE = ["yardline_100", "down", "ydstogo", "goal_to_go", "qtr", "half_seconds_remaining",
         "score_differential"]  # fmt: skip
FG_RESULTS = ("Field goal", "Missed field goal")


# ---------------------------------------------------------------- chances
def chance_rows(pbp: pl.DataFrame, roster: pl.DataFrame) -> pl.DataFrame:
    """Play-by-play (`PBP_COLUMNS`) and the roster part (gsis_id, game_id, position) → one row per
    chance by anyone: keys, season, season type, the player and his position ("" when he isn't
    on the roster part), kind, passer, team, drive, yard line, the situation inputs as floats, and
    whether it scored for him."""
    p = pbp.filter(c("two_point_attempt").fill_null(0) == 0)
    common = dict(
        tdx_team=c("posteam"),
        tdx_drive=c("fixed_drive").cast(pl.Int32),
        tdx_yardline=c("yardline_100").cast(pl.Float64),
    )
    target = p.filter(
        c("receiver_player_id").is_not_null() & (c("play_type") == "pass")
        & (c("sack").fill_null(0) != 1)
    ).select(
        "game_id", "play_id", "season", "season_type", *SITUATION,
        tdx_gsis_id=c("receiver_player_id"), tdx_kind=pl.lit("target"),
        tdx_passer_id=c("passer_player_id"),
        air=c("air_yards").cast(pl.Float64),
        loc=c("pass_location").replace_strict(SIDES, default=None, return_dtype=pl.Float64),
        gap=pl.lit(None, dtype=pl.Float64),
        scramble=pl.lit(0.0),
        tdx_td=((c("touchdown") == 1) & (c("td_player_id") == c("receiver_player_id")))
        .fill_null(False).cast(pl.Float64),
        **common,
    )  # fmt: skip
    carry = p.filter(
        c("rusher_player_id").is_not_null() & (c("play_type") == "run")
    ).select(
        "game_id", "play_id", "season", "season_type", *SITUATION,
        tdx_gsis_id=c("rusher_player_id"), tdx_kind=pl.lit("carry"),
        tdx_passer_id=pl.lit(None, dtype=pl.String),
        air=pl.lit(None, dtype=pl.Float64),
        loc=c("run_location").replace_strict(SIDES, default=None, return_dtype=pl.Float64),
        gap=c("run_gap").replace_strict(GAPS, default=None, return_dtype=pl.Float64),
        scramble=c("qb_scramble").fill_null(0).cast(pl.Float64),
        tdx_td=((c("touchdown") == 1) & (c("td_player_id") == c("rusher_player_id")))
        .fill_null(False).cast(pl.Float64),
        **common,
    )  # fmt: skip
    pos = roster.select(tdx_gsis_id="gsis_id", game_id="game_id", tdx_position="position")
    out = pl.concat([target, carry]).join(pos, on=["tdx_gsis_id", "game_id"], how="left")
    return (
        out.with_columns(
            c(SITUATION).cast(pl.Float64),
            c("play_id").cast(pl.Int64),
            c("season").cast(pl.Int32),
            c("tdx_position").fill_null(""),
        )
        .unique(["game_id", "play_id"], keep="first", maintain_order=True)
        .sort("game_id", "play_id")
    )


def _qb_carries(chances: pl.DataFrame) -> pl.DataFrame:
    return chances.filter((c("tdx_kind") == "carry") & (c("tdx_position") == "QB"))


def fit_qb_carry(chances: pl.DataFrame, seasons: list[int]) -> dict[str, Any]:
    """The QB carries' touchdown model, from the training seasons' regular-season QB carries."""
    from sklearn.ensemble import HistGradientBoostingClassifier

    d = _qb_carries(chances.filter(c("season_type") == "REG"))
    x = d.select(QB_INPUTS).to_numpy().astype(float)
    model = HistGradientBoostingClassifier(**TREES).fit(x, d["tdx_td"].to_numpy().astype(int))
    return {"model": model, "seasons": list(seasons), "rows": d.height}


def fit_drive(plays: pl.DataFrame, seasons: list[int]) -> dict[str, Any]:
    """The drive model, from the training seasons' regular-season snaps (`drive_snaps`)."""
    from sklearn.ensemble import HistGradientBoostingClassifier

    d = plays.filter(c("season_type") == "REG")
    x = d.select(DRIVE).to_numpy().astype(float)
    model = HistGradientBoostingClassifier(**TREES).fit(x, d["drive_td"].to_numpy().astype(int))
    return {"model": model, "seasons": list(seasons), "rows": d.height}


def check_fit(fitted: dict[str, Any], season: int, what: str) -> None:
    """A fit saw only seasons before `season` (the vintage rule)."""
    late = [s for s in fitted["seasons"] if s >= season]
    if late:
        raise ValueError(f"{what} for {season} was fit on {late}")


def cached_fit(
    season: int,
    have: list[int],
    first: int,
    rows_of: Callable[[int], pl.DataFrame],
    fit: Callable[[pl.DataFrame, list[int]], dict[str, Any]],
    path: Path,
    what: str,
) -> dict[str, Any] | None:
    """The fit for `season` from `path`, or fit on its training seasons' rows and cached there.
    None when fewer than 3 seasons from `first` come before it."""
    train = training_seasons(season, [s for s in have if s >= first])
    if not train:
        return None
    key = f"v{MODEL_VERSION}:{what}:{season}:{','.join(map(str, train))}"
    if path.exists():
        with path.open("rb") as f:
            cached = pickle.load(f)  # PCF's own interim files
        if cached.get("key") == key:
            check_fit(cached["fitted"], season, what)
            return cached["fitted"]
    fitted = fit(pl.concat([rows_of(s) for s in train], how="diagonal_relaxed"), train)
    check_fit(fitted, season, what)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("wb") as f:
        pickle.dump({"key": key, "fitted": fitted}, f)
    tmp.replace(path)
    return fitted


def expected(
    chances: pl.DataFrame,
    xfp: pl.DataFrame,
    qb_fit: dict[str, Any],
    oq_fit: dict[str, Any],
) -> pl.DataFrame:
    """Every chance's expected touchdowns (`tdx_xtd`) and where it came from (`tdx_source`):
    `oq` (the `play.xfp` part's value for the same player and play), `qb` (the QB carries'
    model) or `oq_model` (opportunity-quality's fitted model, for anyone else)."""
    oq = xfp.select(
        "game_id", c("play_id").cast(pl.Int64), tdx_gsis_id="oq_gsis_id", oq_xtd="oq_td_exp"
    )
    out = chances.join(oq, on=["game_id", "play_id", "tdx_gsis_id"], how="left")
    is_qb = (c("tdx_kind") == "carry") & (c("tdx_position") == "QB")
    parts = [out.filter(c("oq_xtd").is_not_null()).with_columns(
        tdx_xtd=c("oq_xtd"), tdx_source=pl.lit("oq"))]  # fmt: skip
    rest = out.filter(c("oq_xtd").is_null())
    qb = rest.filter(is_qb)
    if qb.height:
        x = qb.select(QB_INPUTS).to_numpy().astype(float)
        parts.append(qb.with_columns(
            tdx_xtd=pl.Series(qb_fit["model"].predict_proba(x)[:, 1]), tdx_source=pl.lit("qb")))  # fmt: skip
    other = rest.filter(~is_qb)
    for kind in ("target", "carry"):
        d = other.filter(c("tdx_kind") == kind)
        if d.height:
            x = d.select(KIND_INPUTS[kind]).to_numpy().astype(float)
            m = oq_fit["models"][(kind, "td")]
            parts.append(d.with_columns(
                tdx_xtd=pl.Series(m.predict_proba(x)[:, 1]), tdx_source=pl.lit("oq_model")))  # fmt: skip
    return (
        pl.concat(parts, how="diagonal_relaxed")
        .select(
            "game_id", "play_id", "season", "tdx_gsis_id", "tdx_kind", "tdx_position",
            "tdx_passer_id", "tdx_team", "tdx_drive", "tdx_yardline",
            c("air").alias("tdx_air"),
            c("tdx_xtd").cast(pl.Float64), "tdx_td", "tdx_source",
        )  # fmt: skip
        .sort("game_id", "play_id")
    )


# ---------------------------------------------------------------- drives
def drive_snaps(pbp: pl.DataFrame) -> pl.DataFrame:
    """Every scrimmage snap on a drive (a down, a team with the ball), with its drive's result:
    keys, season, season type, team, drive, the situation (`DRIVE`) as floats, and `drive_td`
    (the drive ended in its offense's touchdown)."""
    return (
        pbp.filter(
            c("fixed_drive").is_not_null() & c("posteam").is_not_null() & c("down").is_not_null()
            & c("fixed_drive_result").is_not_null() & c("yardline_100").is_not_null()
        )
        .select(
            "game_id", c("play_id").cast(pl.Int64), c("season").cast(pl.Int32), "season_type",
            team="posteam", fixed_drive=c("fixed_drive").cast(pl.Int32),
            result="fixed_drive_result", **{x: c(x).cast(pl.Float64) for x in DRIVE},
        )  # fmt: skip
        .with_columns(drive_td=(c("result") == "Touchdown").cast(pl.Float64))
        .sort("game_id", "play_id")
    )


def drive_rows(snaps: pl.DataFrame, fitted: dict[str, Any]) -> pl.DataFrame:
    """The `drive.td_chance` part: per drive, its team, the drive model's chance at its first snap
    (`tdx_p_start`), at its first snap inside the 20 (`tdx_p_rz`, null if it never got there) and
    its highest (`tdx_p_peak`); whether it reached the 20, scored a touchdown or ended in a
    field-goal try; and its drive-aware hindsight (`tdx_hind`)."""
    x = snaps.select(DRIVE).to_numpy().astype(float)
    p = snaps.with_columns(p=pl.Series(fitted["model"].predict_proba(x)[:, 1]))
    rz = c("yardline_100") <= RED_ZONE
    out = p.group_by("game_id", "fixed_drive", maintain_order=True).agg(
        c("season").first(),
        tdx_team=c("team").first(),
        tdx_p_start=c("p").first(),
        tdx_p_rz=c("p").filter(rz).first(),
        tdx_p_peak=c("p").max(),
        tdx_snaps=pl.len().cast(pl.Float64),
        tdx_td=c("drive_td").first(),
        tdx_fg_try=c("result").first().is_in(FG_RESULTS).cast(pl.Float64),
    )
    return out.with_columns(
        tdx_reached_rz=c("tdx_p_rz").is_not_null().cast(pl.Float64),
        tdx_hind=pl.when(c("tdx_p_rz").is_not_null()).then(c("tdx_p_rz")).otherwise(c("tdx_td")),
    ).sort("game_id", "fixed_drive")


# ---------------------------------------------------------------- luck
def at_least(p: np.ndarray, group: np.ndarray, k: np.ndarray) -> np.ndarray:
    """The chance that each group's chances (probabilities `p`, group ids `group` 0..G-1) score at
    least `k[g]` touchdowns, exactly (Poisson-binomial), for every group g."""
    n_groups = len(k)
    if n_groups == 0:
        return np.zeros(0)
    top = int(max(k.max(), 0)) + 1
    order = np.argsort(group, kind="stable")
    g, pp = group[order], p[order]
    counts = np.bincount(g, minlength=n_groups)
    width = int(counts.max()) if len(counts) else 0
    start = np.concatenate([[0], np.cumsum(counts)[:-1]])
    slot = np.arange(len(g)) - start[g]
    mat = np.zeros((n_groups, max(width, 1)))
    mat[g, slot] = pp
    dist = np.zeros((n_groups, top))
    dist[:, 0] = 1.0
    for j in range(width):
        q = mat[:, j][:, None]
        shifted = np.zeros_like(dist)
        shifted[:, 1:] = dist[:, :-1]
        dist = dist * (1 - q) + shifted * q  # the last cell loses mass past `top`: not needed
    cum = np.cumsum(dist, axis=1)
    kk = np.clip(k.astype(int), 0, top)
    below = np.where(kk > 0, cum[np.arange(n_groups), np.maximum(kk - 1, 0)], 0.0)
    return np.clip(1.0 - below, 0.0, 1.0)


def luck(td: pl.Expr, xtd: pl.Expr, var: pl.Expr) -> pl.Expr:
    """Touchdowns over expected in dice spreads (0 when there was no dice)."""
    return pl.when(var > 0).then((td - xtd) / var.sqrt()).otherwise(0.0)


def with_luck(
    rows: pl.DataFrame, plays: pl.DataFrame, keys: list[str], td: str, prefix: str
) -> pl.DataFrame:
    """`rows` (one per key, with the touchdown count `td`) with `<prefix>_p_atleast`: the chance of
    at least that many from the group's chances in `plays` (keys, `tdx_xtd`)."""
    ids = rows.select(keys).with_row_index("gid")
    pl_ = plays.join(ids, on=keys, how="inner")
    k = rows[td].fill_null(0).to_numpy().astype(int)
    prob = at_least(
        pl_["tdx_xtd"].to_numpy().astype(float), pl_["gid"].to_numpy().astype(int), k
    )
    return rows.with_columns(pl.Series(f"{prefix}_p_atleast", prob, dtype=pl.Float64))


# ---------------------------------------------------------------- player-games and team-games
_T, _C = c("tdx_kind") == "target", c("tdx_kind") == "carry"
_VAR = c("tdx_xtd") * (1 - c("tdx_xtd"))
PLAYER_SUMS: dict[str, pl.Expr] = {
    "tdx_carries": _C.sum(),
    "tdx_rush_td": c("tdx_td").filter(_C).sum(),
    "tdx_rush_xtd": c("tdx_xtd").filter(_C).sum(),
    "tdx_rush_var": _VAR.filter(_C).sum(),
    "tdx_targets": _T.sum(),
    "tdx_rec_td": c("tdx_td").filter(_T).sum(),
    "tdx_rec_xtd": c("tdx_xtd").filter(_T).sum(),
    "tdx_rec_var": _VAR.filter(_T).sum(),
    "tdx_rz_carries": (_C & (c("tdx_yardline") <= RED_ZONE)).sum(),
    "tdx_i10_carries": (_C & (c("tdx_yardline") <= INSIDE_10)).sum(),
    "tdx_gl_carries": (_C & (c("tdx_yardline") <= GOAL_LINE)).sum(),
    "tdx_rz_targets": (_T & (c("tdx_yardline") <= RED_ZONE)).sum(),
    "tdx_i10_targets": (_T & (c("tdx_yardline") <= INSIDE_10)).sum(),
    "tdx_ez_targets": (_T & (c("tdx_air") >= c("tdx_yardline"))).sum(),
}
THROWN_SUMS: dict[str, pl.Expr] = {
    "tdx_throws": pl.len(),
    "tdx_thrown_td": c("tdx_td").sum(),
    "tdx_thrown_xtd": c("tdx_xtd").sum(),
    "tdx_thrown_var": _VAR.sum(),
    "tdx_rz_throws": (c("tdx_yardline") <= RED_ZONE).sum(),
}


def player_game_rows(plays: pl.DataFrame, roster: pl.DataFrame) -> pl.DataFrame:
    """The `player_game.touchdowns` part: every rostered QB, RB, WR and TE in a game with chances,
    his chances' touchdowns and expected touchdowns (rushing, receiving, thrown) with the dice's
    spread on them (`_var`: the sum of p × (1 − p)), his chances near the goal line, and the luck
    measure (`tdx_luck_z`, `tdx_p_atleast` for his rushing and receiving touchdowns;
    `tdx_thrown_luck_z`, `tdx_thrown_p_atleast` for his throws). 0 when he had none. Keys and
    season; the caller adds `known_at` (the play-by-play's)."""
    own = plays.group_by(gsis_id="tdx_gsis_id", game_id="game_id").agg(**PLAYER_SUMS)
    thrown = (
        plays.filter(_T & c("tdx_passer_id").is_not_null())
        .group_by(gsis_id="tdx_passer_id", game_id="game_id")
        .agg(**THROWN_SUMS)
    )
    games = plays.select("game_id").unique()
    rows = roster.filter(c("position").is_in(POSITIONS)).join(games, on="game_id", how="semi")
    out = (
        rows.select("gsis_id", "game_id", c("season").cast(pl.Int32))
        .join(own, on=["gsis_id", "game_id"], how="left")
        .join(thrown, on=["gsis_id", "game_id"], how="left")
    )
    cols = [*PLAYER_SUMS, *THROWN_SUMS]
    out = out.with_columns(c(cols).cast(pl.Float64).fill_null(0.0)).with_columns(
        tdx_td=c("tdx_rush_td") + c("tdx_rec_td"),
        tdx_xtd=c("tdx_rush_xtd") + c("tdx_rec_xtd"),
        tdx_var=c("tdx_rush_var") + c("tdx_rec_var"),
    )
    out = out.with_columns(
        tdx_luck_z=luck(c("tdx_td"), c("tdx_xtd"), c("tdx_var")),
        tdx_thrown_luck_z=luck(c("tdx_thrown_td"), c("tdx_thrown_xtd"), c("tdx_thrown_var")),
    )
    keys = ["gsis_id", "game_id"]
    own_plays = plays.select(gsis_id="tdx_gsis_id", game_id="game_id", tdx_xtd="tdx_xtd")
    thrown_plays = plays.filter(_T & c("tdx_passer_id").is_not_null()).select(
        gsis_id="tdx_passer_id", game_id="game_id", tdx_xtd="tdx_xtd"
    )
    out = with_luck(out, own_plays, keys, "tdx_td", "tdx")
    out = with_luck(out, thrown_plays, keys, "tdx_thrown_td", "tdx_thrown")
    return out.sort("gsis_id", "game_id")


TEAM_SUMS: dict[str, pl.Expr] = {
    "tdx_chances": pl.len(),
    "tdx_tds": c("tdx_td").sum(),
    "tdx_xtd": c("tdx_xtd").sum(),
    "tdx_var": _VAR.sum(),
    "tdx_rush_td": c("tdx_td").filter(_C).sum(),
    "tdx_rec_td": c("tdx_td").filter(_T).sum(),
    "tdx_rush_xtd": c("tdx_xtd").filter(_C).sum(),
    "tdx_rec_xtd": c("tdx_xtd").filter(_T).sum(),
    "tdx_rz_chances": (c("tdx_yardline") <= RED_ZONE).sum(),
    "tdx_i10_carries": (_C & (c("tdx_yardline") <= INSIDE_10)).sum(),
    "tdx_i10_targets": (_T & (c("tdx_yardline") <= INSIDE_10)).sum(),
}
_RZ = c("tdx_reached_rz") == 1
_FG = c("tdx_fg_try") == 1
DRIVE_SUMS: dict[str, pl.Expr] = {
    "tdx_drives": pl.len(),
    "tdx_drive_tds": c("tdx_td").sum(),
    "tdx_rz_trips": _RZ.sum(),
    "tdx_rz_tds": c("tdx_td").filter(_RZ).sum(),
    "tdx_hind": c("tdx_hind").sum(),
    "tdx_hind_var": (c("tdx_p_rz") * (1 - c("tdx_p_rz"))).filter(_RZ).sum(),
    "tdx_start_sum": c("tdx_p_start").sum(),
    "tdx_fg_drives": _FG.sum(),
    "tdx_rz_fg_drives": (_FG & _RZ).sum(),
    "tdx_near_miss": c("tdx_p_peak").filter(_FG).sum(),
    "tdx_rz_near_miss": c("tdx_p_peak").filter(_FG & _RZ).sum(),
}


def team_game_rows(plays: pl.DataFrame, drives: pl.DataFrame, pbp: pl.DataFrame) -> pl.DataFrame:
    """The `team_game.touchdowns` part: each team in a game with play-by-play, its chances'
    touchdowns and expected touchdowns (rushing and receiving, every player), its calling near
    the goal line (targets and carries inside the 10), its drives, red-zone trips, the
    drive-aware hindsight (`tdx_hind`, with the dice's spread on it) and near misses (the sum of
    the closest each field-goal drive came). 0 when it had none. Keys (game_id, team) and season."""
    teams = pl.concat(
        pbp.select("game_id", c("season").cast(pl.Int32), team=c(side)).unique()
        for side in ("home_team", "away_team")
    ).unique(["game_id", "team"])
    chance = plays.group_by(game_id="game_id", team="tdx_team").agg(**TEAM_SUMS)
    drive = drives.group_by(game_id="game_id", team="tdx_team").agg(**DRIVE_SUMS)
    out = teams.join(chance, on=["game_id", "team"], how="left").join(
        drive, on=["game_id", "team"], how="left"
    )
    cols = [*TEAM_SUMS, *DRIVE_SUMS]
    return out.with_columns(c(cols).cast(pl.Float64).fill_null(0.0)).sort("game_id", "team")
