"""A season's reconstruction through the gateway, walk-forward, scored and saved.

Two kinds of view, so the answer key can't reach an estimate:
- **inputs** (`INPUTS`, in season): the play-by-play, rosters, snap counts and head coaches. The
  answer key isn't declared, so the gateway refuses it. Each game's grid uses that game's rows
  only; `check_point_in_time` rebuilds sample games from a view at each one's own moment.
- **the answer key** (`ANSWER_KEY`, retrospective): `player_play.on_field` of completed seasons,
  for history, training and scoring.

For a season S: history from every season before S, the model fitted on the `TRAIN_SEASONS`
seasons before S, then each game rebuilt. A row's `as_of` is the first weekly run at least a day
after kickoff (when the snap counts are in); `train_end` is the end of season S − 1.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl

from pcf.config import get_config
from pcf.data.clean import standard
from pcf.data.gateway import END_OF_TIME, Gateway, TableSource
from pcf.data.timeline.moments import runs, season_ends
from pcf.experts.participation_live import chain, grid, history, model

c = pl.col
ID = "participation-live"
INPUTS = {
    "play": ("pbp",),
    "player_game": ("roster", "snaps"),
    "team_game": ("pregame",),
}
ANSWER_KEY = {"player_play": ("on_field",)}
FIRST_KEY = 2016  # the answer key's first season
TRAIN_SEASONS = 3
KEEP = [
    "game_id", "play_id", "side", "team", "gsis_id", "season", "season_type", "week", "n",
    "n_plays", "group", "position", "share", "full", "named", "pinned", "sd", "sd2", "start",
    "start2", "drive_n", "fixed_drive", "f_no_huddle", "ls", "stay", "ret", "dn",
    *model.LEAGUE, *model.HISTORY, "same_coach",
]  # fmt: skip
KEEP = list(dict.fromkeys(KEEP))


def cache_dir() -> Path:
    return get_config().zone("interim") / "participation_live_build"


def _coaches(view, seasons: Sequence[int]) -> pl.DataFrame:
    tg = view.table("team_game", seasons=list(seasons)).select("game_id", "team", "season", "coach")
    return standard.standard_teams(tg, "team")


def season_grid(view, season: int) -> pl.DataFrame:
    """A season's grid from an inputs view (no answer key)."""
    pbp = view.table("play", seasons=[season])
    pg = view.table("player_game", seasons=[season]).select(
        "gsis_id", "game_id", "team", "position", "offense_snaps", "defense_snaps"
    )
    return grid.grid(pbp, pg)


def season_truth(key_view, season: int) -> pl.DataFrame:
    return grid.truth(key_view.table("player_play", seasons=[season]))


Sums = dict[int, tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]]


def season_sums(gt: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """A season's player, team and pair sums (`history`)."""
    return (*history.season_sums(gt), history.pair_sums(gt))


def featured(g: pl.DataFrame, sums: Sums, coaches: pl.DataFrame) -> pl.DataFrame:
    """The grid with history (from the sums of earlier seasons) and the model's cell columns."""
    season = g["season"].max()
    earlier = [s for s in sums if s < season]
    if earlier:
        ps = pl.concat([sums[s][0] for s in earlier])
        ts = pl.concat([sums[s][1] for s in earlier])
        pairs = pl.concat([sums[s][2] for s in earlier])
    else:
        (ps, ts), pairs = _empty_sums(), None
    out = model.cell_columns(history.features(g, ps, ts, coaches, pairs))
    floats = [x for x in out.columns if out.schema[x] == pl.Float64 and x not in ("share",)]
    return out.select([x for x in KEEP if x in out.columns]).with_columns(
        [c(x).cast(pl.Float32) for x in floats if x in KEEP]
    )


def _empty_sums() -> tuple[pl.DataFrame, pl.DataFrame]:
    p = {"gsis_id": pl.String, "season": pl.Int32, "cells": pl.UInt32}
    for k in grid.FLAGS:
        p[f"res_{k}"], p[f"n_{k}"] = pl.Float64, pl.UInt32
    p.update(stay_res=pl.Float64, stay_n=pl.UInt32, ret_res=pl.Float64, ret_n=pl.UInt32)
    t = {"team": pl.String, "side": pl.String, "group": pl.String, "season": pl.Int32}
    for k in grid.FLAGS:
        t[f"tres_{k}"], t[f"tn_{k}"] = pl.Float64, pl.UInt32
    return pl.DataFrame(schema=p), pl.DataFrame(schema=t)


def prepare(seasons: Sequence[int], gateway: Gateway | None = None, rebuild: bool = False) -> None:
    """Each season's featured grid with its answer key, cached (`cache_dir`). A season's
    features use only earlier seasons' answer keys, so they're the same for every test season."""
    cache_dir().mkdir(parents=True, exist_ok=True)
    sums: Sums = {}
    for s in range(FIRST_KEY, max(seasons) + 1):
        path = cache_dir() / f"grid_{s}.parquet"
        if path.exists() and not rebuild:
            gt = pl.read_parquet(path)
        else:
            # a season at a time: the play-by-play is too big to hold whole
            gw = gateway or Gateway(TableSource(seasons=[s - 1, s]))
            view = gw.view(END_OF_TIME, "in_season", INPUTS)
            key_view = gw.view(END_OF_TIME, "retrospective", ANSWER_KEY)
            g = season_grid(view, s)
            gt = grid.with_truth(
                featured(g, sums, _coaches(view, [s - 1, s])), season_truth(key_view, s)
            )
            gt.write_parquet(path)
        sums[s] = season_sums(gt)


def load(season: int) -> pl.DataFrame:
    return pl.read_parquet(cache_dir() / f"grid_{season}.parquet")


def train_frame(season: int) -> pl.DataFrame:
    """The part-timer cells of the `TRAIN_SEASONS` before `season`."""
    seasons = [s for s in range(season - TRAIN_SEASONS, season) if s >= FIRST_KEY]
    return pl.concat([load(s).filter(~c("full")) for s in seasons])


def moments(gw: Gateway) -> tuple[pl.DataFrame, dict[int, datetime]]:
    """Each game's `as_of` (the first weekly run at least a day after kickoff) and each season's
    end (`train_end` of the next season's rows)."""
    cal = gw.calendar
    r = runs(cal).select("at").sort("at")
    games = (
        cal.games.select("game_id", "kickoff")
        .with_columns(known=c("kickoff") + pl.duration(days=1))
        .sort("known")
    )
    as_of = games.join_asof(r, left_on="known", right_on="at", strategy="forward")
    return as_of.select("game_id", as_of="at"), season_ends(cal)


def _guess(test: pl.DataFrame, k: str, name: str, totals: bool, mix: bool) -> pl.DataFrame:
    g = chain.best_guess(test.with_columns(p=c(f"p_{k}")), totals=totals, mix=mix)
    return test.join(
        g.select(*grid.CELL_KEYS, c("best").alias(name)), on=grid.CELL_KEYS, how="left"
    )


def run_season(
    season: int,
    kinds: Sequence[str] = model.KINDS,
    guess: Sequence[str] = ("history", "sequence"),
    nomix: Sequence[str] = ("sequence",),
) -> tuple[pl.DataFrame, dict[str, model.OnFieldModel]]:
    """One test season: every rung fitted on the seasons before, every game rebuilt. Returns the
    grid and the models. Per rung: `p_<kind>` (the chances) and `top_<kind>` (each play's
    likeliest 11); for the rungs in `guess`, `best_<kind>` (the snap-matched best guess); for
    those in `nomix`, both again without the position mix (`top_<kind>_nomix`,
    `best_<kind>_nomix`), for the record of what the mix adds."""
    train = train_frame(season)
    test = load(season)
    models = {}
    for k in kinds:
        m = model.fit(train, k, seed=season)
        models[k] = m
        inf = chain.infer(test, m)
        test = test.join(
            inf.select(*grid.CELL_KEYS, c("p").alias(f"p_{k}")), on=grid.CELL_KEYS, how="left"
        )
        test = _guess(test, k, f"top_{k}", totals=False, mix=True)
        if k in guess:
            test = _guess(test, k, f"best_{k}", totals=True, mix=True)
        if k in nomix:
            test = _guess(test, k, f"top_{k}_nomix", totals=False, mix=False)
            test = _guess(test, k, f"best_{k}_nomix", totals=True, mix=False)
    return test, models


def check_point_in_time(
    season: int, m: model.OnFieldModel, n_games: int = 4, seed: int = 0
) -> float:
    """Rebuild sample games from an inputs view at each game's own `as_of` (only what was known
    then) and return the largest gap to the season run's chances. 0 means the season run used
    nothing a game's morning didn't know."""
    gw = Gateway(TableSource(seasons=[season - 1, season]))
    as_of, _ = moments(gw)
    full = load(season)
    ids = full["game_id"].unique().sort().sample(n_games, seed=seed).to_list()
    sums = {s: season_sums(load(s)) for s in range(FIRST_KEY, season)}
    worst = 0.0
    for gid in ids:
        at = as_of.filter(c("game_id") == gid)["as_of"].item()
        view = gw.view(at, "in_season", INPUTS)
        g = season_grid(view, season).filter(c("game_id") == gid)
        f = featured(g, sums, _coaches(view, [season - 1, season]))
        a = chain.infer(f, m).select(*grid.CELL_KEYS, "p")
        b = chain.infer(full.filter(c("game_id") == gid), m).select(
            *grid.CELL_KEYS, c("p").alias("q")
        )
        j = a.join(b, on=grid.CELL_KEYS, how="full", coalesce=True)
        if j["p"].null_count() or j["q"].null_count():
            return float("inf")
        worst = max(worst, float((j["p"] - j["q"]).abs().max()))
    return worst


def output_rows(
    test: pl.DataFrame, kind: str, as_of: pl.DataFrame, train_end: datetime, run_id: str
) -> pl.DataFrame:
    """The standard schema: per cell its chance (`quantity` on_field_chance), the two lineups,
    the play's `certainty` (the likeliest lineup's expected share right), the side and team.
    Probabilities: q10-q90 are the chance itself (no range on a chance)."""
    p = c(f"p_{kind}")
    test = chain.lineup_certainty(test.with_columns(p=p), f"top_{kind}")
    out = test.join(as_of, on="game_id", how="left").select(
        "game_id", "play_id", "gsis_id", "side", "team", "season", "week", "n",
        best=c(f"best_{kind}"),
        likeliest=c(f"top_{kind}"),
        certainty=c("certainty").cast(pl.Float64),
        as_of="as_of",
        quantity=pl.lit("on_field_chance"),
        mean=p.cast(pl.Float64),
        q10=p.cast(pl.Float64),
        q50=p.cast(pl.Float64),
        q90=p.cast(pl.Float64),
        model=pl.lit(ID),
        model_version=pl.lit(kind),
        run_id=pl.lit(run_id),
        train_end=pl.lit(train_end).cast(pl.Datetime("us", "UTC")),
        cadence=pl.lit("in_season"),
    )  # fmt: skip
    return out


def train_end_of(season: int, ends: dict[int, datetime]) -> datetime:
    return ends.get(season - 1, datetime(season, 3, 1, tzinfo=UTC) - timedelta(days=1))


SCORE_COLUMNS = ["game_id", "play_id", "side", "team", "gsis_id", "season", "n", "group", "share",
                 "n_plays", "sd", "pinned", "on", "full_truth"]  # fmt: skip


def _likeliest_scores(test: pl.DataFrame, k: str, b: str | None = None) -> dict[str, float]:
    from pcf.experts.participation_live import score

    b = b or f"top_{k}"
    pp = {
        m: v
        for m, v in score.per_play(test, k, b).items()
        if "log_loss" not in m and "calib" not in m
    }
    return pp | score.sanity(test, k, b) | score.substitution(test, k, b)


def backtest(
    seasons: Sequence[int] = range(2019, 2025),
    kinds: Sequence[str] = model.KINDS,
    guess: Sequence[str] = ("share", "history", "sequence"),
    champion: str = "sequence",
    nomix: Sequence[str] = ("sequence",),
) -> dict:
    """Walk-forward by season: each season rebuilt by every rung trained on the seasons before.
    Logged as one MLflow attempt; the champion's rows saved as the walk-forward history
    (outputs/participation-live/<run_id>/history.parquet). Returns the per-season and pooled
    scores and the champion's models."""
    import mlflow

    from pcf.core import tracking
    from pcf.data.gateway import HISTORY
    from pcf.experts.participation_live import score
    from pcf.validation.backtest import check_seasons

    seasons = list(seasons)
    check_seasons(seasons, open_vault=False)
    prepare(seasons)
    as_of, ends = moments(Gateway())
    out: dict = {"seasons": {}, "models": {}}
    pooled, rows = [], []
    with tracking.attempt(
        ID,
        train_end=train_end_of(max(seasons), ends),
        name=f"backtest {seasons[0]}-{seasons[-1]}",
        params={"kinds": ",".join(kinds), "champion": champion, "train_seasons": TRAIN_SEASONS},
    ) as run:
        for s in seasons:
            test, models = run_season(s, kinds, guess, nomix)
            out["models"][s] = models[champion]
            res = {k: score.per_play(test, k) for k in kinds}
            for k in guess:
                res[k] |= score.sanity(test, k) | score.substitution(test, k)
            for k in kinds:
                res[f"{k}_likeliest"] = _likeliest_scores(test, k)
            for k in nomix:
                res[f"{k}_nomix"] = _likeliest_scores(test, k, f"best_{k}_nomix")
                res[f"{k}_likeliest_nomix"] = _likeliest_scores(test, k, f"top_{k}_nomix")
            out["seasons"][s] = res
            for k, d in res.items():
                mlflow.log_metrics({f"{s}.{k}.{m}": v for m, v in d.items() if v == v})
            keep = [*SCORE_COLUMNS, *(f"p_{k}" for k in kinds), *(f"top_{k}" for k in kinds),
                    *(f"best_{k}" for k in guess), *(f"best_{k}_nomix" for k in nomix),
                    *(f"top_{k}_nomix" for k in nomix)]  # fmt: skip
            pooled.append(test.select(keep))
            rows.append(output_rows(test, champion, as_of, train_end_of(s, ends), run.info.run_id))
        allt = pl.concat(pooled)
        out["pooled"] = {k: score.per_play(allt, k) for k in kinds}
        for k in guess:
            out["pooled"][k] |= score.sanity(allt, k) | score.substitution(allt, k)
        for k in kinds:
            out["pooled"][f"{k}_likeliest"] = _likeliest_scores(allt, k)
        for k in nomix:
            out["pooled"][f"{k}_nomix"] = _likeliest_scores(allt, k, f"best_{k}_nomix")
            out["pooled"][f"{k}_likeliest_nomix"] = _likeliest_scores(allt, k, f"top_{k}_nomix")
        out["by_group"] = {k: score.by_group(allt, k) for k in ("share", "history", champion)}
        out["by_group"]["likeliest"] = score.by_group(allt, champion, f"top_{champion}")
        out["by_group"]["history_likeliest"] = score.by_group(allt, "history", "top_history")
        for k, d in out["pooled"].items():
            mlflow.log_metrics({f"all.{k}.{m}": v for m, v in d.items() if v == v})
        out["point_in_time_gap"] = check_point_in_time(seasons[-1], out["models"][seasons[-1]])
        mlflow.log_metric("point_in_time_gap", out["point_in_time_gap"])
        path = get_config().zone("outputs") / ID / run.info.run_id / HISTORY
        path.parent.mkdir(parents=True, exist_ok=True)
        pl.concat(rows).write_parquet(path)
        out["history_path"] = str(path)
        out["run_id"] = run.info.run_id
        out["scored"] = allt
    return out
