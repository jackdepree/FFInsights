"""context-live's walk-forward backtest by season, nulls, history and MLflow (decision 0036).

This expert describes plays that happened, so like the participation maps (decisions 0030, 0031)
it has its own runner instead of the forecast harness, and reuses the harness's pieces (scores,
the paired comparison, calibration, the vault rule).

- **Point in time.** A play's `as_of` is the first weekly run at least 14 days after kickoff, when
  FTN's charting for the game is out (participation-late's moments). Inputs come from an in-season
  view; pressure and time to throw (after-the-season data) come from a retrospective view for
  training and scoring only. `check_point_in_time` rebuilds sample games from a view at each one's
  `as_of` and compares them with the season build.
- **Refits.** One fit per test season, on every earlier season from the outcome's first
  (recency-weighted, half-life 4 seasons). `train_end` is the latest `known_at` it saw.
- **Rungs** (`RUNGS`): the base rate; the situation alone, linear then trees; the situation and the
  live call fields, linear then trees; plus schemes-v2's traits. For the CEO's H65, each side's
  call fields alone.
- **What ships per outcome** (`choose`): the live model if it beats the situation-only model
  (90% interval of the paired difference below 0, by whole weeks) by more than the fitting noise;
  else the situation-only model if it beats the base rate; else the base rate (rule k).
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.core.log import get_logger
from pcf.data.gateway import END_OF_TIME, Gateway, TableSource
from pcf.experts.context_live import models, plays
from pcf.experts.context_live.outcomes import OUTCOMES, Outcome
from pcf.validation.backtest import HALF_LIFE, check_seasons
from pcf.validation.compare import Comparison, compare

log = get_logger(__name__)
c = pl.col
ID = "context-live"
TEST_SEASONS = (2023, 2024)  # FTN starts in 2022; the 2025 vault stays closed until validation
UTC_TIME = pl.Datetime("us", "UTC")


@dataclass(frozen=True)
class Rung:
    name: str
    fields: str | None  # a key of plays.FIELD_SETS (None for the base rate)
    method: str


RUNGS: tuple[Rung, ...] = (
    Rung("0-base", None, "base"),
    Rung("1-situation-linear", "situation", "linear"),
    Rung("2-situation-trees", "situation", "trees"),
    Rung("3-live-linear", "live", "linear"),
    Rung("4-live-trees", "live", "trees"),
    Rung("5-traits-trees", "traits", "trees"),
)
SIDES: tuple[Rung, ...] = (
    Rung("offense-trees", "offense", "trees"),
    Rung("defense-trees", "defense", "trees"),
)
BY_RUNG = {r.name: r for r in (*RUNGS, *SIDES)}
SITUATION_ONLY = ("0-base", "1-situation-linear", "2-situation-trees")


def cache_dir() -> Path:
    return get_config().zone("interim") / "context_live_build"


def report_dir() -> Path:
    """Small text reports, kept with the project's notes (no data rows)."""
    return Path(__file__).resolve().parents[4] / "projects" / ID / "build"


def moments(gw: Gateway) -> pl.DataFrame:
    """Each game's `as_of`: the first weekly run at least 14 days after kickoff."""
    from pcf.experts.participation_late.reconstruct import moments as late_moments

    return late_moments(gw)


def prepare(seasons: Sequence[int], rebuild: bool = False) -> None:
    """Each season's play table, with each game's `as_of`, cached (`cache_dir`). One season at a
    time: the play-by-play is too big to hold whole."""
    cache_dir().mkdir(parents=True, exist_ok=True)
    as_of = None
    for s in seasons:
        path = cache_dir() / f"plays_{s}.parquet"
        if path.exists() and not rebuild:
            continue
        gw = Gateway(TableSource(seasons=[s - 1, s]))
        if as_of is None:
            # every season's calendar: a season's last games wait for the next season's first run
            as_of = moments(Gateway())
        view = gw.view(END_OF_TIME, "in_season", plays.INPUTS)
        target_view = gw.view(END_OF_TIME, "retrospective", plays.TARGETS)
        frame = plays.build(view, s, target_view).join(as_of, on="game_id", how="left")
        if frame["as_of"].null_count():
            raise ValueError(f"{s}: {frame['as_of'].null_count()} plays have no as_of")
        frame.write_parquet(path)
        log.info("context-live: %d plays in %d", frame.height, s)


def load(seasons: Sequence[int]) -> pl.DataFrame:
    return pl.concat(
        [pl.read_parquet(cache_dir() / f"plays_{s}.parquet") for s in seasons], how="vertical"
    )


def with_weights(train: pl.DataFrame, season: int, half_life: float | None = HALF_LIFE):
    if not half_life:
        return train.with_columns(weight=pl.lit(1.0))
    return train.with_columns(weight=0.5 ** ((season - c("season")) / half_life))


def known(rows: pl.DataFrame) -> pl.Expr:
    """When a training row's inputs and outcome were both known."""
    if "known_at_targets" in rows.columns:
        return pl.max_horizontal("known_at", "known_at_targets")
    return c("known_at")


def training_rows(data: pl.DataFrame, outcome: Outcome, season: int) -> pl.DataFrame:
    """The outcome's rows from the seasons before `season`, checked to be known before the season's
    first `as_of`."""
    rows = outcome.rows(data.filter(c("season") < season))
    if rows.is_empty():
        raise ValueError(f"{outcome.name}: no training rows before {season}")
    first = data.filter(c("season") == season)["as_of"].min()
    late = rows.filter(known(rows) > first).height
    if late:
        raise ValueError(f"{outcome.name}: {late} training rows weren't known by {first}")
    return rows


def train_end(rows: pl.DataFrame) -> datetime:
    return rows.select(known(rows).max()).item()


def fit_rung(
    data: pl.DataFrame, outcome: Outcome, rung: Rung, season: int, seed: int = 0,
    transform: Callable[[pl.DataFrame], pl.DataFrame] | None = None,
) -> tuple[models.Fitted, datetime]:  # fmt: skip
    train = training_rows(data, outcome, season)
    if transform is not None:
        train = transform(train)
    fields = plays.FIELD_SETS[rung.fields] if rung.fields else []
    model = models.fit(with_weights(train, season), outcome, fields, rung.method, seed=seed)
    return model, train_end(train)


def losses(pred: pl.DataFrame, kind: str) -> pl.DataFrame:
    """Each row's main loss (log loss for a chance, the mean pinball of q10-q90 for an amount) and
    squared error of the mean (the exploration's readable share)."""
    y = c("y")
    if kind == "probability":
        p = c("mean").clip(1e-15, 1 - 1e-15)
        loss = -(y * p.log() + (1 - y) * (1 - p).log())
    else:
        parts = [
            pl.max_horizontal(level * (y - c(q)), (level - 1) * (y - c(q)))
            for q, level in models.LEVELS.items()
        ]
        loss = pl.sum_horizontal(parts) / len(parts)
    return pred.with_columns(loss=loss, se=(y - c("mean")) ** 2)


def rungs_for(outcome: Outcome, sides: bool = True) -> list[Rung]:
    if outcome.situation_only:
        return [BY_RUNG[r] for r in SITUATION_ONLY]
    return [*RUNGS, *(SIDES if sides else ())]


def test_seasons_for(outcome: Outcome, seasons: Sequence[int]) -> list[int]:
    """Test seasons with at least one earlier season of the outcome to train on."""
    return [s for s in seasons if s > outcome.first_season]


def walk(
    data: pl.DataFrame, outcome: Outcome, seasons: Sequence[int], rungs: Sequence[Rung],
    seed: int = 0, transform: Callable[[pl.DataFrame], pl.DataFrame] | None = None,
    test_transform: Callable[[pl.DataFrame], pl.DataFrame] | None = None,
) -> tuple[pl.DataFrame, dict]:  # fmt: skip
    """Every rung's held-out predictions on the test seasons: one frame (keys, season, week,
    block, as_of, y, then per rung `<rung>:mean`, ranges and `<rung>:loss`, `<rung>:se`), and the
    fitted models and train_ends by season and rung."""
    out, fitted = [], {}
    for s in test_seasons_for(outcome, seasons):
        test = outcome.rows(data.filter(c("season") == s))
        if test_transform is not None:
            test = test_transform(test)
        frame = test.select(*plays.KEYS, "season", "week", "as_of", "y",
                            block=pl.format("{}-{}", c("season"), c("week")))  # fmt: skip
        for r in rungs:
            m, end = fit_rung(data, outcome, r, s, seed, transform)
            fitted[(s, r.name)] = (m, end)
            pred = losses(m.predict(test).with_columns(y=test["y"]), outcome.kind)
            frame = frame.with_columns(
                [pred[x].alias(f"{r.name}:{x}") for x in pred.columns if x != "y"]
            )
        out.append(frame)
    return pl.concat(out), fitted


def scored(frame: pl.DataFrame, rung: str) -> pl.DataFrame:
    """One rung's rows as the comparison expects (keys, block, loss)."""
    return frame.select(*plays.KEYS, "block", loss=c(f"{rung}:loss"))


def paired(frame: pl.DataFrame, a: str, b: str, seed: int = 0) -> Comparison:
    return compare(scored(frame, a), scored(frame, b), plays.KEYS, "block", (a, b), seed=seed)


def share_removed(frame: pl.DataFrame, rung: str, base: str = "0-base") -> float:
    """Percent of the base rate's squared error the rung removes (the exploration's unit)."""
    return float(100 * (1 - frame[f"{rung}:se"].sum() / frame[f"{base}:se"].sum()))


def loss_gain(frame: pl.DataFrame, a: str, b: str) -> float:
    """Percent of b's main loss that a removes."""
    return float(100 * (1 - frame[f"{a}:loss"].sum() / frame[f"{b}:loss"].sum()))


def better(frame: pl.DataFrame, simple: str, complex_: str) -> str:
    """The ladder: the more complex rung only if it beats the simpler one."""
    return complex_ if paired(frame, complex_, simple).beats else simple


def choose(frame: pl.DataFrame, outcome: Outcome, noise: float = 0.0) -> dict:
    """What ships for an outcome (rule k), with the comparisons behind it. `noise` is the fitting
    noise in percent of the situation model's loss: the live model's gain must exceed it."""
    sit = better(frame, "1-situation-linear", "2-situation-trees")
    out: dict = {"situation": sit}
    base_vs_sit = paired(frame, sit, "0-base")
    out["situation_vs_base"] = base_vs_sit
    if outcome.situation_only:
        out["shipped"] = sit if base_vs_sit.beats else "0-base"
        return out
    live = better(frame, "3-live-linear", "4-live-trees")
    out["live"] = live
    live_vs_sit = paired(frame, live, sit)
    gain = loss_gain(frame, live, sit)
    out["live_vs_situation"] = live_vs_sit
    out["live_gain"] = gain
    out["traits_vs_live"] = paired(frame, "5-traits-trees", live)
    if live_vs_sit.beats and gain > noise:
        shipped = live
        if out["traits_vs_live"].beats:
            shipped = "5-traits-trees"
    elif base_vs_sit.beats:
        shipped = sit
    else:
        shipped = "0-base"
    out["shipped"] = shipped
    return out


def shuffle_outcomes(seed: int) -> Callable[[pl.DataFrame], pl.DataFrame]:
    """The signal test's null: outcomes shuffled within each week (VALIDATION.md §5)."""
    return lambda rows: rows.with_columns(y=c("y").shuffle(seed=seed).over("season", "week"))


def shuffle_calls(seed: int) -> Callable[[pl.DataFrame], pl.DataFrame]:
    """The brief's second null: the call fields moved together to another play of the same week,
    so they keep their mix but carry nothing about this play."""

    def go(rows: pl.DataFrame) -> pl.DataFrame:
        rng = np.random.default_rng(seed)
        groups = rows.with_row_index("_i").group_by("season", "week").agg("_i")
        order = np.empty(rows.height, dtype=np.int64)
        for idx in groups["_i"].to_list():
            idx = np.asarray(idx)
            order[idx] = idx[rng.permutation(len(idx))]
        moved = rows.select(plays.CALLS)[order]
        return rows.with_columns([moved[x] for x in plays.CALLS])

    return go


def null_test(
    data: pl.DataFrame, outcome: Outcome, seasons: Sequence[int], rung: str, real: float,
    kind: str = "outcomes", n: int = 20,
) -> dict:  # fmt: skip
    """Refit `rung` `n` times on a null and score each on the test seasons: the real model must
    beat all `n` (VALIDATION.md §5, the 20-shuffle version). `real` is its pooled main loss."""
    r = BY_RUNG[rung]
    out = []
    for i in range(n):
        if kind == "outcomes":
            frame, _ = walk(data, outcome, seasons, [r], transform=shuffle_outcomes(1000 + i))
        else:
            f = shuffle_calls(2000 + i)
            frame, _ = walk(data, outcome, seasons, [r], transform=f, test_transform=f)
        out.append(float(frame[f"{rung}:loss"].mean()))
    beaten = sum(real < x for x in out)
    return {"kind": kind, "n": n, "beaten": beaten, "passed": beaten == n,
            "null_best": min(out), "null_mean": float(np.mean(out)), "real": real}  # fmt: skip


def fitting_noise(
    data: pl.DataFrame, outcome: Outcome, seasons: Sequence[int], a: str, b: str, n: int = 5
) -> dict:
    """The spread of a's gain over b (percent of b's main loss) across refits on training rows
    resampled by whole games, and of a's share removed."""
    gains, shares = [], []
    for i in range(n):
        rng = np.random.default_rng(3000 + i)

        def resample(rows: pl.DataFrame, rng=rng) -> pl.DataFrame:
            games = rows["game_id"].unique().sort().to_numpy()
            pick = pl.DataFrame({"game_id": games[rng.integers(0, len(games), len(games))]})
            return pick.join(rows, on="game_id", how="inner")

        frame, _ = walk(data, outcome, seasons, [BY_RUNG[a], BY_RUNG[b], BY_RUNG["0-base"]],
                        transform=resample)  # fmt: skip
        gains.append(loss_gain(frame, a, b))
        shares.append(share_removed(frame, a))
    return {"gain_sd": float(np.std(gains, ddof=1)), "share_sd": float(np.std(shares, ddof=1)),
            "gains": gains, "shares": shares}  # fmt: skip


def history_rows(frame: pl.DataFrame, outcome: Outcome, rung: str, fitted: dict,
                 run_id: str) -> pl.DataFrame:  # fmt: skip
    """The shipped rung's predictions in the standard schema (keys game_id, play_id). A chance's
    q10-q90 are the chance itself (no range on a chance)."""
    ends = pl.DataFrame(
        {"season": [s for (s, r) in fitted if r == rung],
         "train_end": [e for (s, r), (_, e) in fitted.items() if r == rung]},
        schema={"season": pl.Int32, "train_end": UTC_TIME},
    )  # fmt: skip
    mean = c(f"{rung}:mean")
    q = {x: (c(f"{rung}:{x}") if outcome.kind == "amount" else mean) for x in models.LEVELS}
    return frame.join(ends, on="season", how="left").select(
        *plays.KEYS, "season", "week",
        as_of=c("as_of").cast(UTC_TIME),
        quantity=pl.lit(outcome.name),
        mean=mean, **q,
        model=pl.lit(ID),
        model_version=pl.lit(rung),
        run_id=pl.lit(run_id),
        train_end=c("train_end"),
        cadence=pl.lit("in_season"),
    )  # fmt: skip


def progress(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {text}\n")


def backtest(
    seasons: Sequence[int] = TEST_SEASONS, names: Sequence[str] | None = None,
    open_vault: bool = False, nulls: int = 20, noise_refits: int = 5, tag: str = "backtest",
) -> dict:  # fmt: skip
    """Every outcome walk-forward over `seasons`, each rung, the choice of what ships, the nulls
    and the fitting noise. Logged as one MLflow attempt; the scored frames go to
    interim/context_live_build/<tag>/ and the shipped rungs' rows to
    outputs/context-live/<run_id>/history.parquet."""
    import mlflow

    from pcf.core import tracking

    seasons = list(seasons)
    check_seasons(seasons, open_vault)
    first = min(o.first_season for o in OUTCOMES)
    prepare(range(first, max(seasons) + 1))
    data = load(range(first, max(seasons) + 1))
    chosen = [o for o in OUTCOMES if names is None or o.name in names]
    work = cache_dir() / tag
    work.mkdir(parents=True, exist_ok=True)
    prog = get_config().zone("logs") / f"context_live_{tag}.progress"
    results: dict = {}
    rows = []
    t0 = time.perf_counter()
    end = data.filter(c("season") < max(seasons)).select(known(data).max()).item()
    params = {"seasons": ",".join(map(str, seasons)), "nulls": nulls,
              "noise_refits": noise_refits, "vault": open_vault}  # fmt: skip
    name = f"{tag} {seasons[0]}-{seasons[-1]}"
    with tracking.attempt(ID, train_end=end, name=name, params=params) as run:
        if open_vault:
            tracking.mark_vault_opened(ID)
        for o in chosen:
            frame, fitted = walk(data, o, seasons, rungs_for(o))
            frame.write_parquet(work / f"{o.name}.parquet")
            res: dict = {"label": o.label, "kind": o.kind, "rows": frame.height,
                         "seasons": test_seasons_for(o, seasons)}  # fmt: skip
            res["share"] = {r.name: share_removed(frame, r.name) for r in rungs_for(o)}
            res["loss"] = {r.name: float(frame[f"{r.name}:loss"].mean()) for r in rungs_for(o)}
            sit = better(frame, "1-situation-linear", "2-situation-trees")
            live = sit if o.situation_only else better(frame, "3-live-linear", "4-live-trees")
            noise = {"gain_sd": 0.0}
            if noise_refits and not o.situation_only:
                noise = fitting_noise(data, o, seasons, live, sit, noise_refits)
            res["noise"] = noise
            choice = choose(frame, o, noise=noise["gain_sd"])
            res["choice"] = {k: (v.__dict__ if isinstance(v, Comparison) else v)
                             for k, v in choice.items()}  # fmt: skip
            if not o.situation_only:
                sit_trees = "2-situation-trees"
                res["sides"] = {
                    "offense_vs_situation": paired(frame, "offense-trees", sit_trees).__dict__,
                    "defense_vs_situation": paired(frame, "defense-trees", sit_trees).__dict__,
                    # H65: what both sides add together beyond the sum of each alone
                    "together_beyond_each": float(
                        res["share"]["4-live-trees"] - res["share"]["offense-trees"]
                        - res["share"]["defense-trees"] + res["share"]["2-situation-trees"]
                    ),
                }  # fmt: skip
            top = choice["shipped"]
            if nulls and top != "0-base":
                real = res["loss"][top]
                res["signal"] = null_test(data, o, seasons, top, real, "outcomes", nulls)
                if not o.situation_only and top not in SITUATION_ONLY:
                    res["calls_null"] = null_test(data, o, seasons, top, real, "calls", nulls)
            last = max(test_seasons_for(o, seasons))
            m = fitted[(last, top)][0]
            res["importance"] = models.importances(
                m, o.rows(data.filter(c("season") == last)).head(20000)
            )
            rows.append(history_rows(frame, o, top, fitted, run.info.run_id))
            results[o.name] = res
            mlflow.log_metrics({f"{o.name}.share.{k}": v for k, v in res["share"].items()})
            mlflow.log_metrics({f"{o.name}.loss.{k}": v for k, v in res["loss"].items()})
            progress(prog, f"{o.name}: shipped {top}, {time.perf_counter() - t0:.0f}s")
            log.info("context-live %s: shipped %s", o.name, top)
        history = pl.concat(rows, how="vertical")
        path = get_config().zone("outputs") / ID / run.info.run_id / "history.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        history.write_parquet(path)
        (work / "results.json").write_text(json.dumps(results, indent=1, default=str))
        mlflow.log_text(json.dumps(results, indent=1, default=str), "results.json")
        results["_run_id"] = run.info.run_id
        results["_history"] = str(path)
        progress(prog, f"done run {run.info.run_id}")
    return results


def check_point_in_time(season: int, n_games: int = 4, seed: int = 0) -> dict:
    """Rebuild sample games' play rows from an inputs view at each game's own `as_of` and compare
    them with the season build (the largest difference in any field must be 0), and check that a
    view a day before that `as_of` minus 13 days holds none of the game's FTN rows."""
    gw = Gateway(TableSource(seasons=[season - 1, season]))
    full = load([season])
    ids = full["game_id"].unique().sort().sample(n_games, seed=seed).to_list()
    fields = plays.SITUATION + plays.CALLS + plays.TRAITS
    worst, early = 0.0, 0
    for gid in ids:
        at = full.filter(c("game_id") == gid)["as_of"].max()
        view = gw.view(at, "in_season", plays.INPUTS)
        a = plays.build(view, season).filter(c("game_id") == gid).sort(plays.KEYS)
        b = full.filter(c("game_id") == gid).sort(plays.KEYS)
        if a.select(plays.KEYS).equals(b.select(plays.KEYS)) is False:
            return {"gap": float("inf"), "early_ftn": early, "games": ids}
        for f in fields:
            x, y = a[f], b[f]
            if f in models.CATEGORIES:
                if (x.fill_null("") != y.fill_null("")).any():
                    worst = float("inf")
                continue
            d = (x.cast(pl.Float64).fill_null(-999) - y.cast(pl.Float64).fill_null(-999)).abs()
            worst = max(worst, float(d.max() or 0.0))
        kickoff_after = full.filter(c("game_id") == gid)["known_at"].min()
        before = gw.view(kickoff_after, "in_season", plays.INPUTS).table("play", seasons=[season])
        early += before.filter(c("game_id") == gid, c("ftn_known_at").is_not_null()).height
    return {"gap": worst, "early_ftn": early, "games": ids}


def main(argv: Sequence[str] | None = None) -> None:
    import argparse

    ap = argparse.ArgumentParser(prog="python -m pcf.experts.context_live.run")
    ap.add_argument("what", choices=["prepare", "backtest", "pit"])
    ap.add_argument("--seasons", default=",".join(map(str, TEST_SEASONS)))
    ap.add_argument("--outcomes", default="")
    ap.add_argument("--nulls", type=int, default=20)
    ap.add_argument("--noise", type=int, default=5)
    ap.add_argument("--tag", default="backtest")
    ap.add_argument("--open-vault", action="store_true")
    a = ap.parse_args(argv)
    seasons = [int(x) for x in a.seasons.split(",")]
    if a.what == "prepare":
        prepare(range(plays.FIRST_SEASON, max(seasons) + 1))
    elif a.what == "pit":
        print(check_point_in_time(max(seasons)))
    else:
        names = [x for x in a.outcomes.split(",") if x] or None
        res = backtest(seasons, names, a.open_vault, a.nulls, a.noise, a.tag)
        print(res["_run_id"], res["_history"])


if __name__ == "__main__":
    main()
