"""The `team_game` part `pace` and the `play` part `pace` (pace project, decision 0028): each
team's volume and habits in a game, measured on every play against PCF's own expected pass chance
and expected pace, each fit only on earlier seasons.

From play-by-play, regular season and playoffs, quarters and overtime:
- **Snaps:** run and pass plays and no-plays (penalties), kneels and spikes, with a down. Scrimmage
  plays are runs and passes without kneels or spikes. A dropback (`pass`) counts sacks and
  scrambles.
- **The gap:** game seconds from the previous snap of the same drive and quarter (0-60 s; nflverse
  has no play clock), with what stopped or slowed the clock since (the previous snap an
  incompletion, out of bounds, a penalty or no-play, a spike, a sack; timeouts called).
- **Expected pass chance** (`X_PASS`) and **expected gap** (`X_PACE`): gradient-boosted trees fit
  on the `TRAIN_SEASONS` seasons before (`fit_expected`), from the situation alone, never a team's
  own choices. nflverse's `xpass` was fit through 2019 and now expects 1-2 points more passing
  than teams throw (pace exploration F13), so levels come from our own.
- **Per team-game** (`OFFENSE`, `DEFENSE`): plays, dropbacks, runs, drives and plays per drive;
  pass rate over expected on every play and on each of 1st, 2nd and 3rd down (separate habits:
  F1, F15); pace over expected (seconds; negative is fast) on every snap with a gap; the no-huddle
  rate; EPA per play. The defense's columns describe what offenses did against it.

The builders are pure: rows in, rows out. Fitting is deterministic (fixed seed); the build step
caches each season's fitted pair.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl

from pcf.data.clean import standard

c = pl.col
TRAIN_SEASONS = 10  # an expected model is fit on the seasons before, at most this many
MIN_TRAIN_SEASONS = 3
GAP_SECONDS = (0, 60)
SNAP_TYPES = ("pass", "run", "no_play", "qb_kneel", "qb_spike")
PBP_COLUMNS = [
    "game_id", "play_id", "season", "posteam", "defteam", "down", "ydstogo", "yardline_100",
    "qtr", "half_seconds_remaining", "game_seconds_remaining", "score_differential", "wp",
    "vegas_wp", "ep", "epa", "pass", "rush", "qb_kneel", "qb_spike", "sack", "no_huddle",
    "incomplete_pass", "out_of_bounds", "penalty", "timeout", "play_type", "fixed_drive",
]  # fmt: skip
X_PASS = [
    "down", "ydstogo", "yardline_100", "qtr", "half_seconds_remaining", "game_seconds_remaining",
    "score_differential", "wp", "vegas_wp",
]  # fmt: skip
X_PACE = [
    "wp", "ep", "qtr", "half_seconds_remaining", "prev_incomplete", "prev_oob", "prev_penalty",
    "prev_noplay", "prev_spike", "prev_sack", "timeouts_before",
]  # fmt: skip
OFFENSE = [
    "plays", "dropbacks", "runs", "drives", "plays_per_drive", "proe", "proe_1st", "proe_2nd",
    "proe_3rd", "downs_1st", "downs_2nd", "downs_3rd", "exp_pass_rate", "pace_oe", "pace_snaps",
    "no_huddle", "epa_per_play",
]  # fmt: skip
DEFENSE = [
    "def_plays", "def_dropbacks_all", "def_runs", "def_drives", "def_plays_per_drive", "def_proe",
    "def_pace_oe", "def_pace_snaps", "def_epa_per_play",
]  # fmt: skip
# nflverse's play-by-play has its own `pass_oe` (against its `xpass`), so ours is named apart
PLAY = ["pcf_xpass", "pcf_pass_oe", "exp_gap", "pace_oe"]


def snap_rows(pbp: pl.DataFrame) -> pl.DataFrame:
    """Play-by-play (`PBP_COLUMNS`) → one row per snap with its gap and clock flags, teams
    standardized. `scrimmage` marks runs and passes without kneels or spikes."""
    d = pbp.select(PBP_COLUMNS).sort("game_id", "play_id")
    snap = c("play_type").is_in(SNAP_TYPES) & c("down").is_not_null() & c("posteam").is_not_null()
    # timeouts called since the previous snap: rows between snaps belong to the next snap
    d = d.with_columns(snap=snap.fill_null(False)).with_columns(
        grp=c("snap").cast(pl.Int32).cum_sum().over("game_id")
    )
    timeouts = (
        d.group_by("game_id", "grp")
        .agg(timeouts_before=(c("timeout") == 1).sum().cast(pl.Int32))
        .with_columns(c("grp") + 1)
    )
    s = d.filter(c("snap")).join(timeouts, on=["game_id", "grp"], how="left")

    def prev(x: str) -> pl.Expr:
        return c(x).shift(1).over("game_id")

    same = (
        (prev("fixed_drive") == c("fixed_drive"))
        & (prev("qtr") == c("qtr"))
        & (prev("posteam") == c("posteam"))
    )
    lo, hi = GAP_SECONDS
    gap = prev("game_seconds_remaining") - c("game_seconds_remaining")
    s = s.sort("game_id", "play_id").with_columns(
        gap=pl.when(same.fill_null(False) & gap.is_between(lo, hi)).then(gap).cast(pl.Float64),
        prev_incomplete=prev("incomplete_pass").fill_null(0).cast(pl.Float64),
        prev_oob=prev("out_of_bounds").fill_null(0).cast(pl.Float64),
        prev_penalty=prev("penalty").fill_null(0).cast(pl.Float64),
        prev_noplay=(prev("play_type") == "no_play").fill_null(False).cast(pl.Float64),
        prev_spike=prev("qb_spike").fill_null(0).cast(pl.Float64),
        prev_sack=prev("sack").fill_null(0).cast(pl.Float64),
        timeouts_before=c("timeouts_before").fill_null(0).cast(pl.Float64),
        scrimmage=(
            ((c("pass") == 1) | (c("rush") == 1)) & (c("qb_kneel") == 0) & (c("qb_spike") == 0)
        ).fill_null(False),
        season=c("season").cast(pl.Int32),
    )
    s = standard.standard_teams(s, "posteam", "defteam")
    return s.drop("snap", "grp", "timeout", "incomplete_pass", "out_of_bounds", "penalty")


def _pass_rows(snaps: pl.DataFrame) -> pl.DataFrame:
    return snaps.filter(c("scrimmage"))


def _pace_rows(snaps: pl.DataFrame) -> pl.DataFrame:
    return snaps.filter(c("gap").is_not_null())


def _x(rows: pl.DataFrame, columns: list[str]) -> np.ndarray:
    """Model inputs as floats; a missing input (e.g. no Vegas win chance) is NaN, which the trees
    handle themselves, so no play is dropped."""
    return rows.select(c(x).cast(pl.Float64) for x in columns).to_numpy()


def fit_expected(snaps: pl.DataFrame) -> dict[str, Any]:
    """The expected pass chance and expected gap, fit on `snaps` (earlier seasons only)."""
    from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

    settings = {"max_iter": 300, "learning_rate": 0.1, "max_leaf_nodes": 63, "random_state": 0}
    p = _pass_rows(snaps)
    passing = HistGradientBoostingClassifier(**settings)
    passing.fit(_x(p, X_PASS), p["pass"].to_numpy().astype(int))
    g = _pace_rows(snaps)
    pace = HistGradientBoostingRegressor(**settings)
    pace.fit(_x(g, X_PACE), g["gap"].to_numpy().astype(float))
    seasons = sorted(snaps["season"].unique().to_list())
    return {"pass": passing, "pace": pace, "seasons": seasons}


def apply_expected(snaps: pl.DataFrame, models: dict[str, Any]) -> pl.DataFrame:
    """`snaps` with `exp_pass` and `pass_oe` on scrimmage plays, `exp_gap` and `pace_oe` on snaps
    with a gap (null elsewhere)."""
    s = snaps.with_row_index("_i")
    p = _pass_rows(s)
    g = _pace_rows(s)
    exp_pass = models["pass"].predict_proba(_x(p, X_PASS))[:, 1]
    exp_gap = models["pace"].predict(_x(g, X_PACE))
    s = s.join(p.select("_i").with_columns(exp_pass=pl.Series(exp_pass)), on="_i", how="left")
    s = s.join(g.select("_i").with_columns(exp_gap=pl.Series(exp_gap)), on="_i", how="left")
    return s.drop("_i").with_columns(
        pass_oe=c("pass") - c("exp_pass"), pace_oe=c("gap") - c("exp_gap")
    )


def _side(s: pl.DataFrame, team: str, prefix: str) -> pl.DataFrame:
    sc = s.filter(c("scrimmage"))
    out = sc.group_by("game_id", "season", team=c(team)).agg(
        plays=pl.len().cast(pl.Int32),
        dropbacks=(c("pass") == 1).sum().cast(pl.Int32),
        runs=(c("rush") == 1).sum().cast(pl.Int32),
        drives=c("fixed_drive").n_unique().cast(pl.Int32),
        proe=c("pass_oe").mean(),
        proe_1st=c("pass_oe").filter(c("down") == 1).mean(),
        proe_2nd=c("pass_oe").filter(c("down") == 2).mean(),
        proe_3rd=c("pass_oe").filter(c("down") == 3).mean(),
        downs_1st=(c("down") == 1).sum().cast(pl.Int32),
        downs_2nd=(c("down") == 2).sum().cast(pl.Int32),
        downs_3rd=(c("down") == 3).sum().cast(pl.Int32),
        exp_pass_rate=c("exp_pass").mean(),
        epa_per_play=c("epa").mean(),
    )
    paced = s.group_by("game_id", team=c(team)).agg(
        pace_oe=c("pace_oe").mean(),
        pace_snaps=c("pace_oe").is_not_null().sum().cast(pl.Int32),
        no_huddle=c("no_huddle").mean(),
    )
    out = out.join(paced, on=["game_id", "team"], how="left").with_columns(
        plays_per_drive=c("plays") / c("drives")
    )
    if prefix:
        keep = {
            "plays", "dropbacks", "runs", "drives", "plays_per_drive", "proe", "pace_oe",
            "pace_snaps", "epa_per_play",
        }  # fmt: skip
        # tendencies has `def_dropbacks` (neutral plays only), so the full count is named apart
        names = {"dropbacks": "def_dropbacks_all"}
        out = out.select(
            "game_id",
            "season",
            "team",
            *[c(x).alias(names.get(x, prefix + x)) for x in OFFENSE if x in keep],
        )
    return out


def pace_rows(snaps: pl.DataFrame) -> pl.DataFrame:
    """Snaps with their expected values (`apply_expected`) → one row per team and game:
    game_id, team, season, `OFFENSE` and `DEFENSE`."""
    keys = ["game_id", "team", "season"]
    off = _side(snaps, "posteam", "")
    de = _side(snaps, "defteam", "def_")
    return (
        off.join(de, on=keys, how="full", coalesce=True)
        .select(*keys, *OFFENSE, *DEFENSE)
        .with_columns(c(pl.Float64).fill_nan(None))
        .sort("game_id", "team")
    )


def play_rows(snaps: pl.DataFrame) -> pl.DataFrame:
    """Snaps with their expected values → the `play` part `pace`: game_id, play_id, season and
    `PLAY`, for every snap."""
    return snaps.select(
        "game_id",
        "play_id",
        "season",
        pcf_xpass="exp_pass",
        pcf_pass_oe="pass_oe",
        exp_gap="exp_gap",
        pace_oe="pace_oe",
    ).sort("game_id", "play_id")


def training_seasons(season: int, have: list[int]) -> list[int]:
    """The seasons an expected model for `season` is fit on: up to `TRAIN_SEASONS` before it.
    Empty when fewer than `MIN_TRAIN_SEASONS` exist."""
    before = sorted(s for s in have if s < season)[-TRAIN_SEASONS:]
    return before if len(before) >= MIN_TRAIN_SEASONS else []


def check_fit(models: dict[str, Any], season: int) -> None:
    """A fitted pair was fit only on seasons before `season` (the vintage rule)."""
    late = [s for s in models["seasons"] if s >= season]
    if late:
        raise ValueError(f"expected models for {season} were fit on {late}")
    if not np.isfinite(models["pace"].predict(np.zeros((1, len(X_PACE))))).all():
        raise ValueError("the expected pace model predicts a non-finite gap")


MODEL_VERSION = 1  # bump when the snaps, the inputs or the fit settings change
CACHE_FILE = "models.pkl"


def cache_key(season: int, train: list[int]) -> str:
    """What a cached pair must match to be reused: the code's version and the seasons fit on."""
    return f"v{MODEL_VERSION}:{season}:{','.join(map(str, train))}"


def expected_for(
    season: int,
    have: list[int],
    snaps_of: Any,
    cache_dir: Any,
) -> dict[str, Any] | None:
    """The expected pair for `season`, from `cache_dir/season=<season>` or fit on the training
    seasons' snaps (`snaps_of(season)`) and cached. None when too few earlier seasons exist."""
    import pickle

    train = training_seasons(season, have)
    if not train:
        return None
    key = cache_key(season, train)
    path = cache_dir / f"season={season}" / CACHE_FILE
    if path.exists():
        with path.open("rb") as f:
            cached = pickle.load(f)  # PCF's own interim files
        if cached.get("key") == key:
            check_fit(cached["models"], season)
            return cached["models"]
    models = fit_expected(pl.concat([snaps_of(s) for s in train], how="diagonal_relaxed"))
    check_fit(models, season)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("wb") as f:
        pickle.dump({"key": key, "models": models}, f)
    tmp.replace(path)
    return models
