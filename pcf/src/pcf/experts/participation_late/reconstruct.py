"""The second edition of a season's map, walk-forward, scored against the morning-after map and
saved (participation-late).

For a test season S: participation-live's grid and history, plus FTN's counts per play
(`ftn`). The model is participation-live's sequence rung with the FTN columns as extra inputs,
fitted on the `TRAIN_SEASONS` before S (FTN marked missing before 2022, participation-late#F3).
For comparison, the same season gets the morning-after map (the same rung without FTN, same
training) and the late model fitted on FTN's seasons only.

Point in time: a game's late edition has `as_of` = the first weekly run at least `LAG` (14 days)
after kickoff, when FTN's charting for it is out in history (DATA_SOURCES.md).
`check_point_in_time` rebuilds sample games from an inputs view at that moment and also checks
that a view at the morning after doesn't yet hold the game's FTN rows.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta

import polars as pl

from pcf.config import get_config
from pcf.data.gateway import END_OF_TIME, Gateway, TableSource
from pcf.data.timeline.moments import runs
from pcf.experts.participation_late import ftn
from pcf.experts.participation_live import chain, grid, model
from pcf.experts.participation_live import reconstruct as live

c = pl.col
ID = "participation-late"
LAG = timedelta(days=14)
INPUTS = {**live.INPUTS, "play": ("pbp", "ftn")}
TEST_SEASONS = (2023, 2024)  # FTN starts in 2022; the 2025 vault stays closed


def ftn_features(seasons: Sequence[int], at=END_OF_TIME) -> pl.DataFrame:
    """FTN's input columns per play for the seasons, from an inputs view at `at`."""
    out = []
    for s in seasons:
        if s < ftn.FIRST_SEASON:
            continue
        view = Gateway(TableSource(seasons=[s])).view(at, "in_season", {"play": ("ftn",)})
        out.append(ftn.features(view.table("play", seasons=[s])))
    if not out:
        return ftn.features(pl.DataFrame(schema={"game_id": pl.String, "play_id": pl.Int64,
                                                 **{x: pl.Float64 for x in ftn.RAW}}))  # fmt: skip
    return pl.concat(out)


def load(season: int, feats: pl.DataFrame) -> pl.DataFrame:
    return ftn.join(live.load(season), feats)


def train_frame(season: int, feats: pl.DataFrame) -> pl.DataFrame:
    return ftn.join(live.train_frame(season), feats)


def moments(gw: Gateway) -> pl.DataFrame:
    """Each game's late `as_of`: the first weekly run at least `LAG` after kickoff."""
    r = runs(gw.calendar).select("at").sort("at")
    games = (
        gw.calendar.games.select("game_id", "kickoff")
        .with_columns(known=c("kickoff") + LAG)
        .sort("known")
    )
    out = games.join_asof(r, left_on="known", right_on="at", strategy="forward")
    return out.select("game_id", as_of="at")


def _lineups(test: pl.DataFrame, k: str, best: bool = True) -> pl.DataFrame:
    top = chain.likeliest(test.with_columns(p=c(f"p_{k}")))
    test = test.join(
        top.select(*grid.CELL_KEYS, c("likeliest").alias(f"top_{k}")), on=grid.CELL_KEYS, how="left"
    )
    if best:
        b = chain.best_guess(test.with_columns(p=c(f"p_{k}")))
        test = test.join(
            b.select(*grid.CELL_KEYS, c("best").alias(f"best_{k}")), on=grid.CELL_KEYS, how="left"
        )
    return test


def run_season(season: int, feats: pl.DataFrame) -> tuple[pl.DataFrame, dict]:
    """One test season: `p_live` (the morning-after map, refitted), `p_late` (with FTN, the
    champion) and `p_late_ftn_seasons` (with FTN, trained on FTN's seasons only), each with its
    likeliest lineup (`top_*`); the champion also with its snap-matched lineup."""
    train = train_frame(season, feats)
    test = load(season, feats)
    fits = {
        "live": model.fit(train, "sequence", seed=season),
        "late": model.fit(train, "sequence", seed=season, extra=ftn.COLUMNS),
        "late_ftn_seasons": model.fit(
            train.filter(c("season") >= ftn.FIRST_SEASON), "sequence", seed=season,
            extra=ftn.COLUMNS,
        ),
    }  # fmt: skip
    for k, m in fits.items():
        inf = chain.infer(test, m)
        test = test.join(
            inf.select(*grid.CELL_KEYS, c("p").alias(f"p_{k}")), on=grid.CELL_KEYS, how="left"
        )
        test = _lineups(test, k, best=k in ("live", "late"))
    return test, fits


def check_point_in_time(season: int, m: model.OnFieldModel, n_games: int = 4, seed: int = 0):
    """(gap, rows): rebuild sample games from an inputs view at each one's late `as_of` and
    return the largest gap to the season run's chances (0 = none), and the number of the games'
    FTN rows a view at their morning after already holds (0 = FTN can't reach the first
    edition)."""
    gw = Gateway(TableSource(seasons=[season - 1, season]))
    late_at = moments(gw)
    live_at, _ = live.moments(gw)
    feats = ftn_features([season])
    full = load(season, feats)
    ids = full["game_id"].unique().sort().sample(n_games, seed=seed).to_list()
    sums = {s: live.season_sums(live.load(s)) for s in range(live.FIRST_KEY, season)}
    worst, early = 0.0, 0
    for gid in ids:
        at = late_at.filter(c("game_id") == gid)["as_of"].item()
        view = gw.view(at, "in_season", INPUTS)
        g = live.season_grid(view, season).filter(c("game_id") == gid)
        f = live.featured(g, sums, live._coaches(view, [season - 1, season]))
        f = ftn.join(f, ftn.features(view.table("play", seasons=[season])))
        a = chain.infer(f, m).select(*grid.CELL_KEYS, "p")
        b = chain.infer(full.filter(c("game_id") == gid), m).select(
            *grid.CELL_KEYS, c("p").alias("q")
        )
        j = a.join(b, on=grid.CELL_KEYS, how="full", coalesce=True)
        if j["p"].null_count() or j["q"].null_count():
            return float("inf"), early
        worst = max(worst, float((j["p"] - j["q"]).abs().max()))
        morning = live_at.filter(c("game_id") == gid)["as_of"].item()
        mv = gw.view(morning, "in_season", {"play": ("ftn",)})
        early += ftn.features(mv.table("play", seasons=[season])).filter(c("game_id") == gid).height
    return worst, early


def output_rows(test: pl.DataFrame, as_of: pl.DataFrame, train_end, run_id: str) -> pl.DataFrame:
    """participation-live's schema for the late edition (`model` participation-late)."""
    out = live.output_rows(test, "late", as_of, train_end, run_id)
    return out.with_columns(model=pl.lit(ID), model_version=pl.lit("late"))


def moved(test: pl.DataFrame) -> dict[str, float]:
    """How far the late edition moved from the morning-after map: mean change in an open cell's
    chance, and the share of play-sides whose likeliest lineup changed."""
    t = test.filter(~c("pinned"))
    per = test.group_by("game_id", "play_id", "side").agg(
        changed=(c("top_late") != c("top_live")).any()
    )
    return {
        "mean_chance_change": float((t["p_late"] - t["p_live"]).abs().mean()),
        "plays_lineup_changed": float(per["changed"].mean()),
    }


SCORE_COLUMNS = [*live.SCORE_COLUMNS, "named", "full"]
KINDS = ("live", "late", "late_ftn_seasons")


def backtest(seasons: Sequence[int] = TEST_SEASONS) -> dict:
    """Walk-forward by season, logged as one MLflow attempt; the champion's (late) rows saved
    as the walk-forward history (outputs/participation-late/<run_id>/history.parquet)."""
    import mlflow

    from pcf.core import tracking
    from pcf.data.gateway import HISTORY
    from pcf.experts.participation_live import score
    from pcf.validation.backtest import check_seasons

    seasons = list(seasons)
    check_seasons(seasons, open_vault=False)
    live.prepare(seasons)
    gw = Gateway()
    as_of = moments(gw)
    _, ends = live.moments(gw)
    feats = ftn_features(range(ftn.FIRST_SEASON, max(seasons) + 1))
    out: dict = {"seasons": {}, "models": {}}
    pooled, rows = [], []
    with tracking.attempt(
        ID,
        train_end=live.train_end_of(max(seasons), ends),
        name=f"backtest {seasons[0]}-{seasons[-1]}",
        params={"champion": "late", "train_seasons": live.TRAIN_SEASONS, "lag_days": LAG.days},
    ) as run:
        for s in seasons:
            test, fits = run_season(s, feats)
            out["models"][s] = fits["late"]
            res = {k: score.per_play(test, k, f"top_{k}") for k in KINDS}
            for k in ("live", "late"):
                res[f"{k}_snap_matched"] = score.per_play(test, k) | score.sanity(test, k)
            res["moved"] = moved(test)
            out["seasons"][s] = res
            for k, d in res.items():
                mlflow.log_metrics({f"{s}.{k}.{m}": v for m, v in d.items() if v == v})
            keep = [*SCORE_COLUMNS, *(f"p_{k}" for k in KINDS), *(f"top_{k}" for k in KINDS),
                    "best_live", "best_late", *ftn.COLUMNS]  # fmt: skip
            pooled.append(test.select([x for x in keep if x in test.columns]))
            rows.append(output_rows(test, as_of, live.train_end_of(s, ends), run.info.run_id))
        allt = pl.concat(pooled)
        out["pooled"] = {k: score.per_play(allt, k, f"top_{k}") for k in KINDS}
        for k in ("live", "late"):
            out["pooled"][f"{k}_snap_matched"] = score.per_play(allt, k) | score.sanity(allt, k)
        out["pooled"]["moved"] = moved(allt)
        for k, d in out["pooled"].items():
            mlflow.log_metrics({f"all.{k}.{m}": v for m, v in d.items() if v == v})
        out["by_group"] = {k: score.by_group(allt, k, f"top_{k}") for k in ("live", "late")}
        out["certainty"] = {k: score.certainty(allt, k) for k in ("live", "late")}
        gap, early = check_point_in_time(seasons[-1], out["models"][seasons[-1]])
        out["point_in_time_gap"], out["ftn_rows_at_morning"] = gap, early
        mlflow.log_metrics({"point_in_time_gap": gap, "ftn_rows_at_morning": early})
        path = get_config().zone("outputs") / ID / run.info.run_id / HISTORY
        path.parent.mkdir(parents=True, exist_ok=True)
        pl.concat(rows).write_parquet(path)
        out["history_path"] = str(path)
        out["run_id"] = run.info.run_id
        out["scored"] = allt
    return out
