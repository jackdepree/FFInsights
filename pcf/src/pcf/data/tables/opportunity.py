"""The `play` part `xfp` and the `player_game` part `opportunity` (opportunity-quality project,
decision 0041): what each target and carry was worth from where it happened, fit on earlier seasons
only, and each player-game's chances summed.

- **A chance** is a target (a pass with a receiver, not a sack) or a carry (a designed run or a
  scramble with a rusher) by a running back, wide receiver or tight end; two-point tries are left
  out. Every season type is scored; the models learn from regular-season chances only.
- **The expected models** (boosted trees, the exploration's settings) score each chance from its
  situation alone (`SITUATION`: yard line, down, distance, goal to go, formation, tempo, quarter,
  clock, score, throw depth and side for targets, side and gap for carries). Each piece of a
  fantasy score has its own model: for a target the chance of a catch, the receiving yards (0 if
  incomplete) and the chance of a touchdown; for a carry the rushing yards and the chance of a
  touchdown. Any scoring's expected points are then a sum (`pcf.baselines.common.CHANCE_SCORING`).
- **Fit on earlier seasons only:** up to 10 regular seasons before, never fewer than 3, from
  `FIRST_FIT` (2009: before it the play-by-play lists mostly completed targets, td-expert's F1), so
  expected values start in 2012. Fits are cached per season, keyed by `MODEL_VERSION`.
- **Yards after the catch over expected:** on a completion, `yards_after_catch - xyac_mean_yardage`
  (nflverse's own expectation).

Builders are pure: rows in, rows out. Column names carry the `oq_` prefix, so they never clash
with the play-by-play's or the player stats' own.
"""

from __future__ import annotations

import pickle
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from pcf.data.tables.pace import training_seasons

c = pl.col
POSITIONS = ("RB", "WR", "TE")
FIRST_FIT = 2009  # the first season the expected models learn from (td-expert F1)
PBP_COLUMNS = [
    "game_id", "play_id", "season", "season_type", "play_type", "two_point_attempt", "sack",
    "rush", "receiver_player_id", "rusher_player_id", "td_player_id", "touchdown",
    "complete_pass", "yards_gained", "air_yards", "pass_location", "run_location", "run_gap",
    "yards_after_catch", "xyac_mean_yardage", "yardline_100", "down", "ydstogo", "goal_to_go",
    "shotgun", "no_huddle", "qtr", "half_seconds_remaining", "score_differential",
]  # fmt: skip
SITUATION = [
    "yardline_100", "down", "ydstogo", "goal_to_go", "shotgun", "no_huddle", "qtr",
    "half_seconds_remaining", "score_differential",
]  # fmt: skip
KIND_INPUTS = {"target": [*SITUATION, "air", "loc"], "carry": [*SITUATION, "loc", "gap"]}
# I100 (the CEO's spot-check, 2026-11-22): the same models with his position as one more input, so
# "expected" means expected for his position; built apart (`variant="position"`), never the table's
POSITION_CODE = {"RB": 0.0, "WR": 1.0, "TE": 2.0}
VARIANT_INPUTS = {
    "situation": KIND_INPUTS,
    "position": {k: [*v, "pos"] for k, v in KIND_INPUTS.items()},
}
# (kind, piece, classifier?): each fantasy piece a chance can earn
PIECES = (
    ("target", "catch", True),
    ("target", "yards", False),
    ("target", "td", True),
    ("carry", "yards", False),
    ("carry", "td", True),
)
TREES = {"max_iter": 200, "learning_rate": 0.06, "max_leaf_nodes": 31, "min_samples_leaf": 100,
         "random_state": 0}  # fmt: skip
MODEL_VERSION = 1  # bump when the chances, the inputs or the fit settings change
CACHE_FILE = "xfp.pkl"
SIDES = {"left": 0.0, "middle": 1.0, "right": 2.0}
GAPS = {"guard": 0.0, "tackle": 1.0, "end": 2.0}
GOAL_LINE = 5  # a carry from the 5 or closer
RED_ZONE = 10  # a target from the 10 or closer
DEEP = 20  # a target thrown 20+ yards downfield


def chance_rows(pbp: pl.DataFrame, roster: pl.DataFrame) -> pl.DataFrame:
    """Play-by-play (`PBP_COLUMNS`) and the roster part (gsis_id, game_id, position) → one row per
    chance by a RB, WR or TE: keys, the player, kind, position (and its code `pos`), the situation
    inputs as floats, and what the chance earned (catch, yards, td; yac_oe on completions)."""
    p = pbp.filter(c("two_point_attempt").fill_null(0) == 0)
    target = p.filter(
        c("receiver_player_id").is_not_null() & (c("play_type") == "pass")
        & (c("sack").fill_null(0) != 1)
    ).select(
        "game_id", "play_id", "season", "season_type", *SITUATION,
        oq_gsis_id=c("receiver_player_id"), oq_kind=pl.lit("target"),
        air=c("air_yards").cast(pl.Float64),
        loc=c("pass_location").replace_strict(SIDES, default=None, return_dtype=pl.Float64),
        gap=pl.lit(None, dtype=pl.Float64),
        oq_catch=c("complete_pass").fill_null(0).cast(pl.Float64),
        oq_yards=pl.when(c("complete_pass") == 1).then(c("yards_gained")).otherwise(0)
        .cast(pl.Float64),
        oq_td=((c("touchdown") == 1) & (c("td_player_id") == c("receiver_player_id")))
        .fill_null(False).cast(pl.Float64),
        oq_yac_oe=pl.when(c("complete_pass") == 1)
        .then(c("yards_after_catch") - c("xyac_mean_yardage")).cast(pl.Float64),
    )  # fmt: skip
    carry = p.filter(
        c("rusher_player_id").is_not_null() & (c("play_type") == "run") & (c("rush") == 1)
    ).select(
        "game_id", "play_id", "season", "season_type", *SITUATION,
        oq_gsis_id=c("rusher_player_id"), oq_kind=pl.lit("carry"),
        air=pl.lit(None, dtype=pl.Float64),
        loc=c("run_location").replace_strict(SIDES, default=None, return_dtype=pl.Float64),
        gap=c("run_gap").replace_strict(GAPS, default=None, return_dtype=pl.Float64),
        oq_catch=pl.lit(0.0), oq_yards=c("yards_gained").cast(pl.Float64),
        oq_td=((c("touchdown") == 1) & (c("td_player_id") == c("rusher_player_id")))
        .fill_null(False).cast(pl.Float64),
        oq_yac_oe=pl.lit(None, dtype=pl.Float64),
    )  # fmt: skip
    pos = roster.select(oq_gsis_id="gsis_id", game_id="game_id", oq_position="position")
    out = pl.concat([target, carry]).join(pos, on=["oq_gsis_id", "game_id"], how="inner")
    return (
        out.filter(c("oq_position").is_in(POSITIONS))
        .with_columns(
            c(SITUATION).cast(pl.Float64),
            c("play_id").cast(pl.Int64),
            c("season").cast(pl.Int32),
            pos=c("oq_position").replace_strict(POSITION_CODE, return_dtype=pl.Float64),
        )  # fmt: skip
        .sort("game_id", "play_id")
    )


def _fit_piece(x: np.ndarray, y: np.ndarray, classifier: bool):
    from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

    if classifier:
        return HistGradientBoostingClassifier(**TREES).fit(x, y.astype(int))
    return HistGradientBoostingRegressor(**TREES).fit(x, y)


def fit(chances: pl.DataFrame, seasons: list[int], variant: str = "situation") -> dict[str, Any]:
    """One model per piece, from the training seasons' regular-season chances; `variant` picks
    the inputs (`VARIANT_INPUTS`)."""
    t = chances.filter(c("season_type") == "REG")
    inputs = VARIANT_INPUTS[variant]
    models = {}
    for kind, piece, classifier in PIECES:
        d = t.filter(c("oq_kind") == kind)
        x = d.select(inputs[kind]).to_numpy().astype(float)
        models[(kind, piece)] = _fit_piece(x, d[f"oq_{piece}"].to_numpy(), classifier)
    return {"models": models, "seasons": list(seasons), "rows": t.height, "variant": variant}


def check_fit(fitted: dict[str, Any], season: int) -> None:
    """A fit saw only seasons before `season` (the vintage rule) and has every piece."""
    late = [s for s in fitted["seasons"] if s >= season]
    if late:
        raise ValueError(f"expected points for {season} were fit on {late}")
    missing = {(k, p) for k, p, _ in PIECES} - set(fitted["models"])
    if missing:
        raise ValueError(f"expected points for {season}: no model for {sorted(missing)}")


def apply(chances: pl.DataFrame, fitted: dict[str, Any]) -> pl.DataFrame:
    """Chances → the `play.xfp` part: keys, season, the player, kind, position, the expected
    pieces (`oq_catch_exp`, `oq_yards_exp`, `oq_td_exp`; a carry's catch chance is 0) and what it
    earned."""
    out = []
    inputs = VARIANT_INPUTS[fitted.get("variant", "situation")]
    for kind in ("target", "carry"):
        d = chances.filter(c("oq_kind") == kind)
        x = d.select(inputs[kind]).to_numpy().astype(float)
        exp = {}
        for k, piece, classifier in PIECES:
            if k != kind:
                continue
            m = fitted["models"][(k, piece)]
            exp[f"oq_{piece}_exp"] = m.predict_proba(x)[:, 1] if classifier else m.predict(x)
        if "oq_catch_exp" not in exp:
            exp["oq_catch_exp"] = np.zeros(d.height)
        out.append(d.with_columns(**{k: pl.Series(v, dtype=pl.Float64) for k, v in exp.items()}))
    return (
        pl.concat(out, how="diagonal")
        .select(
            "game_id",
            "play_id",
            "season",
            "oq_gsis_id",
            "oq_kind",
            "oq_position",
            "oq_catch_exp",
            "oq_yards_exp",
            "oq_td_exp",
            "oq_catch",
            "oq_yards",
            "oq_td",
            "oq_yac_oe",
        )  # fmt: skip
        .sort("game_id", "play_id")
    )


def cache_key(season: int, train: list[int], variant: str = "situation") -> str:
    tag = "" if variant == "situation" else f"-{variant}"
    return f"v{MODEL_VERSION}{tag}:{season}:{','.join(map(str, train))}"


def fitted_for(
    season: int,
    have: list[int],
    chances_of: Callable[[int], pl.DataFrame],
    cache_dir: Path,
    variant: str = "situation",
) -> dict[str, Any] | None:
    """The fit for `season`, from `cache_dir/season=<season>` or fit on the training seasons'
    chances and cached. None when fewer than 3 seasons from `FIRST_FIT` come before it."""
    train = training_seasons(season, [s for s in have if s >= FIRST_FIT])
    if not train:
        return None
    key = cache_key(season, train, variant)
    path = cache_dir / f"season={season}" / CACHE_FILE
    if path.exists():
        with path.open("rb") as f:
            cached = pickle.load(f)  # PCF's own interim files
        if cached.get("key") == key:
            check_fit(cached["fitted"], season)
            return cached["fitted"]
    fitted = fit(pl.concat([chances_of(s) for s in train], how="diagonal_relaxed"), train, variant)
    check_fit(fitted, season)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("wb") as f:
        pickle.dump({"key": key, "fitted": fitted}, f)
    tmp.replace(path)
    return fitted


# The player-game part's sums (column → expression on the play part, joined to the pbp's
# yard line and throw depth)
_T = c("oq_kind") == "target"
_C = c("oq_kind") == "carry"
SUMS: dict[str, pl.Expr] = {
    "oq_chances": pl.len(),
    "oq_targets": _T.sum(),
    "oq_carries": _C.sum(),
    "oq_catches": c("oq_catch").filter(_T).sum(),
    "oq_rec_yards": c("oq_yards").filter(_T).sum(),
    "oq_rush_yards": c("oq_yards").filter(_C).sum(),
    "oq_rec_tds": c("oq_td").filter(_T).sum(),
    "oq_rush_tds": c("oq_td").filter(_C).sum(),
    "oq_catch_exp": c("oq_catch_exp").filter(_T).sum(),
    "oq_rec_yards_exp": c("oq_yards_exp").filter(_T).sum(),
    "oq_rush_yards_exp": c("oq_yards_exp").filter(_C).sum(),
    "oq_rec_td_exp": c("oq_td_exp").filter(_T).sum(),
    "oq_rush_td_exp": c("oq_td_exp").filter(_C).sum(),
    "oq_gl_carries": (_C & (c("yardline_100") <= GOAL_LINE)).sum(),
    "oq_rz_targets": (_T & (c("yardline_100") <= RED_ZONE)).sum(),
    "oq_ez_targets": (_T & (c("air_yards") >= c("yardline_100"))).sum(),
    "oq_deep_targets": (_T & (c("air_yards") >= DEEP)).sum(),
    "oq_air_yards": c("air_yards").filter(_T).fill_null(0).sum(),
    "oq_yac_oe": c("oq_yac_oe").filter(_T).fill_null(0.0).sum(),
    "oq_yac_n": c("oq_yac_oe").filter(_T).is_not_null().sum(),
}
EXPECTED = ["oq_catch_exp", "oq_rec_yards_exp", "oq_rush_yards_exp", "oq_rec_td_exp",
            "oq_rush_td_exp"]  # fmt: skip


def player_game_rows(
    xfp: pl.DataFrame, pbp: pl.DataFrame, roster: pl.DataFrame, has_expected: bool
) -> pl.DataFrame:
    """The `player_game.opportunity` part: every rostered RB, WR and TE in a game with
    play-by-play, his chances summed (`SUMS`; 0 when he had none). The expected sums are empty in
    a season with no expected model (`has_expected` False: before 2012). Keys and season; the
    caller adds `known_at` (the play-by-play's)."""
    plays = xfp.join(
        pbp.select("game_id", c("play_id").cast(pl.Int64), "yardline_100", "air_yards"),
        on=["game_id", "play_id"],
        how="left",
    )
    sums = plays.group_by(gsis_id="oq_gsis_id", game_id="game_id").agg(**SUMS)
    games = pbp.select("game_id").unique()
    rows = roster.filter(c("position").is_in(POSITIONS)).join(games, on="game_id", how="semi")
    out = rows.select("gsis_id", "game_id", c("season").cast(pl.Int32)).join(
        sums, on=["gsis_id", "game_id"], how="left"
    )
    out = out.with_columns(c(list(SUMS)).cast(pl.Float64).fill_null(0.0))
    if not has_expected:
        out = out.with_columns(pl.lit(None, dtype=pl.Float64).alias(x) for x in EXPECTED)
    return out.sort("gsis_id", "game_id")
