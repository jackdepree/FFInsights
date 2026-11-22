"""context-retro's walk-forward backtest by season: the ladder per outcome and mode, the
given-pressure test, the nulls, calibration, the history and the champion (decision 0040).

Like context-live (decision 0036) it describes plays that happened, so it has its own runner and
reuses the harness's pieces (the paired comparison by weeks, calibration, the vault rule) and
context-live's models (`context_live.models.fit`: the base rate, linear, the trees).

- **Refits:** one fit per test season and rung, on the earlier seasons (recency-weighted, half-life
  4). `train_window` is the provider rule (the brief's call 2, decision 0038's): participation's
  outcomes (pressure, time to throw) and every model given the pressure train on 2016 on through
  2023 and on 2023 on after it; the play-by-play's outcomes before the snap train on every
  earlier season from 2016.
- **The ladder** (call 5), per outcome and mode: E0 the training mean → linear → trees; E1 the
  pressure alone → linear → trees (both on the fields plus the pressure). A rung is kept only if
  it beats the one kept below it (the whole 90% interval of the paired difference by week).
- **Recalibration** (a rule set before the run): a shipped chance that fails the calibration bar
  (error over 3 points or slope outside 0.9-1.1) on the development seasons is refit with Platt
  scaling inside each training window; the recalibrated one ships if it passes and its log loss
  isn't clearly worse.
- **Nulls:** E0's shipped rung refit 20 times on outcomes shuffled within each week (VALIDATION.md
  §5, the 20-shuffle version); scored on its mean (log loss for a chance, squared error for an
  amount: the brief's "in log loss or squared error").

    python -m pcf.experts.context_retro.run backtest                    # 2017-2024
    python -m pcf.experts.context_retro.run backtest --seasons 2025 --open-vault --tag vault
        --fixed-from backtest                                           # the vault, once
    python -m pcf.experts.context_retro.run pit --seasons 2024          # point in time
    python -m pcf.experts.context_retro.run final --seasons 2025 --checks checks.json  # champion
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingRegressor

from pcf.config import get_config
from pcf.core.log import get_logger
from pcf.experts.context_live import models
from pcf.experts.context_live import run as live_run
from pcf.experts.context_live.outcomes import Outcome
from pcf.experts.context_retro import plays
from pcf.experts.context_retro.outcomes import OUTCOMES, PARTICIPATION, quantity
from pcf.validation import calibration
from pcf.validation.backtest import check_seasons
from pcf.validation.compare import Comparison, compare

log = get_logger(__name__)
c = pl.col
ID = "context-retro"
TEST_SEASONS = tuple(range(2017, 2025))  # the 2025 vault stays closed until validation
NEW_PROVIDER = 2023  # participation's pressure and time to throw (context-live#R12)
UTC_TIME = pl.Datetime("us", "UTC")
PARTICIPATION_FIELDS = (
    "was_pressure",
    "time_to_throw",
    "number_of_pass_rushers",
    "defenders_in_box",
    "defense_coverage_type",
    "defense_man_zone_type",
)
CADENCE = "retrospective"


@dataclass(frozen=True)
class Rung:
    name: str
    mode: str  # e0 or e1
    fields: str  # "none" (the mean), "calls" (the outcome's fields), "calls+pressure", "pressure"
    method: str
    calibrate: bool = False

    def field_list(self, o: Outcome) -> list[str]:
        calls = plays.fields_for(o.population)
        return {"none": [], "calls": calls, "pressure": [plays.CONDITION],
                "calls+pressure": [*calls, plays.CONDITION]}[self.fields]  # fmt: skip


RUNGS: tuple[Rung, ...] = (
    Rung("e0-0-base", "e0", "none", "base"),
    Rung("e0-1-linear", "e0", "calls", "linear"),
    Rung("e0-2-trees", "e0", "calls", "trees"),
    Rung("e1-0-pressure", "e1", "pressure", "linear"),
    Rung("e1-1-linear", "e1", "calls+pressure", "linear"),
    Rung("e1-2-trees", "e1", "calls+pressure", "trees"),
)
BY_RUNG = {r.name: r for r in RUNGS}
LADDERS = {"e0": ("e0-0-base", "e0-1-linear", "e0-2-trees"),
           "e1": ("e1-0-pressure", "e1-1-linear", "e1-2-trees")}  # fmt: skip


def platt(rung: Rung) -> Rung:
    return replace(rung, name=f"{rung.name}+platt", calibrate=True)


def rung_named(name: str) -> Rung:
    if name.endswith("+platt"):
        return platt(BY_RUNG[name.removesuffix("+platt")])
    return BY_RUNG[name]


def rungs_for(o: Outcome) -> list[Rung]:
    return [r for r in RUNGS if r.mode == "e0" or o.name != "pressure"]


def cache_dir() -> Path:
    return plays.cache_dir()


def report_dir() -> Path:
    """Small text reports, kept with the project's notes (no data rows)."""
    return Path(__file__).resolve().parents[4] / "projects" / ID / "build"


def uses_participation(o: Outcome, mode: str) -> bool:
    return o.name in PARTICIPATION or mode == "e1"


def train_window(o: Outcome, mode: str, season: int) -> tuple[int, int]:
    """The first and last training season (the provider rule)."""
    if uses_participation(o, mode) and season > NEW_PROVIDER:
        return NEW_PROVIDER, season - 1
    return plays.FIRST, season - 1


def rows_for(data: pl.DataFrame, o: Outcome, mode: str) -> pl.DataFrame:
    """The outcome's scored rows; given the pressure, only where the pressure is known."""
    rows = o.rows(data)
    return rows.filter(c(plays.CONDITION).is_not_null()) if mode == "e1" else rows


def training(data: pl.DataFrame, o: Outcome, mode: str, season: int) -> pl.DataFrame:
    """The training rows for a test season, inside its window, checked to be known before the
    season's first `as_of` (context-live's `training_rows`)."""
    lo, hi = train_window(o, mode, season)
    rows = live_run.training_rows(data.filter(c("season") >= lo), o, season)
    rows = rows.filter(c("season") <= hi)
    if mode == "e1":
        rows = rows.filter(c(plays.CONDITION).is_not_null())
    return rows


def fit_rung(data: pl.DataFrame, o: Outcome, rung: Rung, season: int, seed: int = 0,
             transform: Callable[[pl.DataFrame], pl.DataFrame] | None = None):  # fmt: skip
    train = training(data, o, rung.mode, season)
    if transform is not None:
        train = transform(train)
    m = models.fit(live_run.with_weights(train, season), o, rung.field_list(o), rung.method,
                   seed=seed, calibrate=rung.calibrate)  # fmt: skip
    return m, live_run.train_end(train)


def walk(data: pl.DataFrame, o: Outcome, seasons: Sequence[int], rungs: Sequence[Rung],
         seed: int = 0, transform=None) -> tuple[pl.DataFrame, dict]:  # fmt: skip
    """Every rung's held-out predictions: one frame per outcome (keys, season, week, block, as_of,
    y, pressure_y, then per rung `<rung>:mean`, ranges, `:loss`, `:se`; an E1 rung is empty where
    the pressure isn't known), and the fitted models and train_ends by (season, rung)."""
    out, fitted = [], {}
    for s in seasons:
        test = o.rows(data.filter(c("season") == s))
        frame = test.select(*plays.KEYS, "season", "week", "as_of", "y", plays.CONDITION,
                            block=pl.format("{}-{}", c("season"), c("week")))  # fmt: skip
        for r in rungs:
            m, end = fit_rung(data, o, r, s, seed, transform)
            fitted[(s, r.name)] = (m, end)
            sub = test if r.mode == "e0" else test.filter(c(plays.CONDITION).is_not_null())
            pred = live_run.losses(m.predict(sub).with_columns(y=sub["y"]), o.kind)
            pred = pred.drop("y").with_columns(sub.select(plays.KEYS))
            pred = pred.rename({x: f"{r.name}:{x}" for x in pred.columns if x not in plays.KEYS})
            frame = frame.join(pred, on=plays.KEYS, how="left")
        out.append(frame)
    return pl.concat(out, how="diagonal_relaxed"), fitted


def with_rung(frame: pl.DataFrame, extra: pl.DataFrame, name: str) -> pl.DataFrame:
    """`frame` with one more rung's columns from another walk on the same rows."""
    cols = [x for x in extra.columns if x.startswith(f"{name}:")]
    return frame.join(extra.select(*plays.KEYS, *cols), on=plays.KEYS, how="left")


def paired(frame: pl.DataFrame, a: str, b: str, seed: int = 0) -> Comparison:
    def scored(rung: str) -> pl.DataFrame:
        return frame.select(*plays.KEYS, "block", loss=c(f"{rung}:loss"))

    return compare(scored(a), scored(b), plays.KEYS, "block", (a, b), seed=seed)


def shared(frame: pl.DataFrame, *rungs: str) -> pl.DataFrame:
    return frame.filter(pl.all_horizontal([c(f"{r}:loss").is_not_null() for r in rungs]))


def share_removed(frame: pl.DataFrame, rung: str, base: str = "e0-0-base") -> float:
    """Percent of the training mean's squared error the rung removes, on rows both have."""
    f = shared(frame, rung, base)
    return float(100 * (1 - f[f"{rung}:se"].sum() / f[f"{base}:se"].sum()))


def loss_gain(frame: pl.DataFrame, a: str, b: str) -> float:
    """Percent of b's main loss that a removes, on rows both have."""
    f = shared(frame, a, b)
    return float(100 * (1 - f[f"{a}:loss"].sum() / f[f"{b}:loss"].sum()))


def log_loss_gain(frame: pl.DataFrame, a: str, b: str) -> float:
    """For a chance: percent of b's log loss that a removes (the main loss)."""
    return loss_gain(frame, a, b)


def level_share(frame: pl.DataFrame, rung: str) -> float:
    """The share with each season's level taken out (decision 0038's unit, for comparing seasons
    across the provider change): the rung's mean around its season mean, against y's."""
    f = frame.filter(c(f"{rung}:mean").is_not_null())
    f = f.with_columns(yc=c("y") - c("y").mean().over("season"),
                       ec=c(f"{rung}:mean") - c(f"{rung}:mean").mean().over("season"))  # fmt: skip
    return float(100 * (1 - ((f["yc"] - f["ec"]) ** 2).sum() / (f["yc"] ** 2).sum()))


def ladder(frame: pl.DataFrame, mode: str) -> tuple[str, list[dict]]:
    """The ladder for a mode: each rung against the one kept below it; the last kept ships."""
    names = LADDERS[mode]
    kept, steps = names[0], []
    for nxt in names[1:]:
        comp = paired(frame, nxt, kept)
        steps.append({"rung": nxt, "against": kept, **comp.__dict__, "beats": comp.beats})
        if comp.beats:
            kept = nxt
    return kept, steps


def calibration_check(frame: pl.DataFrame, rung: str) -> dict:
    """A chance's calibration on the scored rows: overall and by season (error, slope, passed)."""
    f = frame.filter(c(f"{rung}:mean").is_not_null()).select("season", "y", mean=c(f"{rung}:mean"))
    rep = calibration.probability_report(f)
    out = {"error": rep["error"], "slope": rep["slope"], "passed": rep["passed"],
           "table": rep["table"].to_dicts(), "by_season": {}}  # fmt: skip
    for s in sorted(f["season"].unique().to_list()):
        r = calibration.probability_report(f.filter(c("season") == s))
        out["by_season"][s] = {"error": r["error"], "slope": r["slope"], "passed": r["passed"]}
    return out


def range_check(frame: pl.DataFrame, rung: str) -> dict:
    """An amount's range coverage (q10-q90), overall and by season and down."""
    f = frame.filter(c(f"{rung}:mean").is_not_null()).select(
        "season", "y", *[c(f"{rung}:{q}").alias(q) for q in models.LEVELS]
    )
    rep = calibration.coverage(f.with_columns(c("season").cast(pl.String)), ["season"])
    return {k: (v.to_dicts() if isinstance(v, pl.DataFrame) else v) for k, v in rep.items()}


def spread(frame: pl.DataFrame, rung: str) -> list[float]:
    """The chances' (or expected values') 10th and 90th percentiles."""
    m = frame[f"{rung}:mean"].drop_nulls()
    return [float(m.quantile(0.1)), float(m.quantile(0.9))]


def shuffle_outcomes(seed: int) -> Callable[[pl.DataFrame], pl.DataFrame]:
    """The signal test's null: outcomes shuffled within each week (VALIDATION.md §5)."""
    return lambda rows: rows.with_columns(y=c("y").shuffle(seed=seed).over("season", "week"))


def _mean_only(train: pl.DataFrame, o: Outcome, rung: Rung, seed: int):
    """A rung's mean alone (no ranges): what the null is scored on."""
    w = train["weight"].to_numpy()
    if rung.method == "trees" and o.kind == "amount":
        fields = rung.field_list(o)
        x = models.matrix(train, fields)
        # a field with no values in the window is left out, as models.fit does
        fields = [f for i, f in enumerate(fields) if not np.isnan(x[:, i]).all()]
        x = models.matrix(train, fields)
        cats = np.array([f in models.CATEGORIES for f in fields], dtype=bool)
        est = HistGradientBoostingRegressor(
            **models.TREES, random_state=seed, categorical_features=cats if cats.any() else None
        )
        est.fit(x, train["y"].to_numpy().astype(float), sample_weight=w)
        return lambda rows: est.predict(models.matrix(rows, fields))
    m = models.fit(train, o, rung.field_list(o), rung.method, seed=seed)
    return lambda rows: m.predict(rows)["mean"].to_numpy()


def mean_loss(y: np.ndarray, p: np.ndarray, kind: str) -> np.ndarray:
    if kind == "probability":
        p = np.clip(p, 1e-15, 1 - 1e-15)
        return -(y * np.log(p) + (1 - y) * np.log(1 - p))
    return (y - p) ** 2


def null_test(data: pl.DataFrame, o: Outcome, seasons: Sequence[int], rung: str,
              real: float, n: int = 20) -> dict:  # fmt: skip
    """Refit `rung` (E0) `n` times on outcomes shuffled within each week and score its mean on the
    same held-out rows: the real model must beat all `n`. `real` is its mean loss (log loss or
    squared error) on those rows."""
    r = rung_named(rung)
    out = []
    for i in range(n):
        losses = []
        for s in seasons:
            train = shuffle_outcomes(1000 + i)(training(data, o, r.mode, s))
            f = _mean_only(live_run.with_weights(train, s), o, r, seed=0)
            test = rows_for(data.filter(c("season") == s), o, r.mode)
            losses.append(mean_loss(test["y"].to_numpy().astype(float), f(test), o.kind))
        out.append(float(np.concatenate(losses).mean()))
    beaten = sum(real < x for x in out)
    return {"n": n, "beaten": beaten, "passed": beaten == n, "null_best": min(out),
            "null_mean": float(np.mean(out)), "real": real}  # fmt: skip


def real_mean_loss(frame: pl.DataFrame, rung: str, kind: str) -> float:
    f = frame.filter(c(f"{rung}:mean").is_not_null())
    return float(mean_loss(f["y"].to_numpy().astype(float), f[f"{rung}:mean"].to_numpy(),
                           kind).mean())  # fmt: skip


def history_rows(frame: pl.DataFrame, o: Outcome, mode: str, rung: str, fitted: dict,
                 run_id: str) -> pl.DataFrame:  # fmt: skip
    """The shipped rung's predictions in the standard schema (keys game_id, play_id). A chance's
    q10-q90 are the chance itself."""
    ends = pl.DataFrame(
        {"season": [s for (s, r) in fitted if r == rung],
         "train_end": [e for (s, r), (_, e) in fitted.items() if r == rung]},
        schema={"season": pl.Int32, "train_end": UTC_TIME},
    )  # fmt: skip
    mean = c(f"{rung}:mean")
    q = {x: (c(f"{rung}:{x}") if o.kind == "amount" else mean) for x in models.LEVELS}
    out = frame.filter(mean.is_not_null()).join(ends, on="season", how="left")
    return out.select(
        *plays.KEYS, "season", "week", as_of=c("as_of").cast(UTC_TIME),
        quantity=pl.lit(quantity(o.name, mode)), mean=mean, **q, model=pl.lit(ID),
        model_version=pl.lit(rung), run_id=pl.lit(run_id), train_end=c("train_end"),
        cadence=pl.lit(CADENCE),
    )  # fmt: skip


def split_rows(history: pl.DataFrame, data: pl.DataFrame) -> pl.DataFrame:
    """The blame split per dropback (the brief's terms), in the standard schema: the pressure part
    (sack E1 - E0) and the after-pressure part (sack - E1), on dropbacks with both chances. The
    two add up to the sack over expected (sack - E0)."""
    keys = plays.KEYS
    e0 = history.filter(c("quantity") == "sack_e0").select(*keys, e0="mean")
    e1 = history.filter(c("quantity") == "sack_e1").drop("quantity", "q10", "q50", "q90")
    d = e1.rename({"mean": "e1"}).join(e0, on=keys).join(data.select(*keys, "sack_y"), on=keys)
    parts = []
    for name, value in (("sack_pressure_part", c("e1") - c("e0")),
                        ("sack_after_part", c("sack_y") - c("e1"))):  # fmt: skip
        parts.append(d.with_columns(quantity=pl.lit(name), mean=value).with_columns(
            q10=c("mean"), q50=c("mean"), q90=c("mean")))  # fmt: skip
    cols = history.columns
    return pl.concat([p.select(cols) for p in parts])


def progress(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {text}\n")


def judge(frame: pl.DataFrame, o: Outcome, fixed: dict | None) -> dict:
    """The ladder per mode, the recalibration rule, the given-pressure comparison and the
    scores, for one outcome on its scored frame (it may add `+platt` columns: see `backtest`)."""
    res: dict = {"label": o.label, "kind": o.kind, "rows": frame.height}
    for mode in ("e0", "e1") if o.name != "pressure" else ("e0",):
        top, steps = ladder(frame, mode)
        res[mode] = {"ladder": steps, "chosen": top}
        if fixed is not None:
            res[mode]["rule_on_these_seasons"] = top
            res[mode]["chosen"] = fixed[o.name][mode]
    return res


def scores(frame: pl.DataFrame, o: Outcome, res: dict) -> None:
    for mode in [m for m in ("e0", "e1") if m in res]:
        top = res[mode]["shipped"]
        r = res[mode]
        r["share"] = share_removed(frame, top)
        r["level_share"] = level_share(frame, top)
        r["share_by_season"] = {
            s: share_removed(frame.filter(c("season") == s), top)
            for s in sorted(frame["season"].unique().to_list())
        }
        r["vs_base"] = paired(frame, top, "e0-0-base").__dict__
        r["spread"] = spread(frame, top)
        if o.kind == "probability":
            r["log_loss_gain"] = log_loss_gain(frame, top, "e0-0-base")
            r["calibration"] = calibration_check(frame, top)
        else:
            r["range"] = range_check(frame, top)
    if "e1" in res:
        a, b = res["e1"]["shipped"], res["e0"]["shipped"]
        res["given_pressure"] = {
            "comparison": paired(frame, a, b).__dict__,
            "gain": loss_gain(frame, a, b),
            "by_season": {
                s: loss_gain(frame.filter(c("season") == s), a, b)
                for s in sorted(frame["season"].unique().to_list())
            },  # fmt: skip
        }


def backtest(seasons: Sequence[int] = TEST_SEASONS, names: Sequence[str] | None = None,
             open_vault: bool = False, nulls: int = 20, tag: str = "backtest",
             fixed: dict | None = None) -> dict:  # fmt: skip
    """Every outcome walk-forward over `seasons`: each rung, the ladder, the recalibration rule,
    the nulls and the scores. One MLflow attempt; the scored frames go to
    interim/context_retro_build/<tag>/, the shipped rungs' rows (and the split) to
    outputs/context-retro/<run_id>/history.parquet."""
    import mlflow

    from pcf.core import tracking

    seasons = list(seasons)
    check_seasons(seasons, open_vault)
    plays.prepare(range(plays.FIRST, max(seasons) + 1))
    data = plays.load(range(plays.FIRST, max(seasons) + 1))
    chosen = [o for o in OUTCOMES if names is None or o.name in names]
    work = cache_dir() / tag
    work.mkdir(parents=True, exist_ok=True)
    prog = get_config().zone("logs") / f"context_retro_{tag}.progress"
    results: dict = {}
    rows = []
    t0 = time.perf_counter()
    end = data.filter(c("season") < max(seasons)).select(live_run.known(data).max()).item()
    params = {"seasons": ",".join(map(str, seasons)), "nulls": nulls, "vault": open_vault,
              "fields": ",".join(plays.FIELDS_DROPBACK)}  # fmt: skip
    with tracking.attempt(ID, train_end=end, name=f"{tag} {seasons[0]}-{seasons[-1]}",
                          params=params) as run:  # fmt: skip
        if open_vault:
            tracking.mark_vault_opened(ID)
        for o in chosen:
            frame, fitted = walk(data, o, seasons, rungs_for(o))
            res = judge(frame, o, fixed)
            for mode in [m for m in ("e0", "e1") if m in res]:
                top = res[mode]["chosen"]
                res[mode]["shipped"] = top
                if o.kind != "probability":
                    continue
                if fixed is not None:
                    if top.endswith("+platt"):
                        extra, more = walk(data, o, seasons, [rung_named(top)])
                        frame = with_rung(frame, extra, top)
                        fitted.update(more)
                    continue
                cal = calibration_check(frame, top)
                res[mode]["raw_calibration"] = {k: cal[k] for k in ("error", "slope", "passed")}
                if not cal["passed"] and not top.endswith("base"):
                    p = platt(BY_RUNG[top])
                    extra, more = walk(data, o, seasons, [p])
                    frame = with_rung(frame, extra, p.name)
                    fitted.update(more)
                    pc = calibration_check(frame, p.name)
                    comp = paired(frame, p.name, top)
                    res[mode]["platt"] = {"error": pc["error"], "slope": pc["slope"],
                                          "passed": pc["passed"], **comp.__dict__}  # fmt: skip
                    if pc["passed"] and comp.verdict != "worse":
                        res[mode]["shipped"] = p.name
            scores(frame, o, res)
            frame.write_parquet(work / f"{o.name}.parquet")
            top0 = res["e0"]["shipped"]
            if nulls and top0 != "e0-0-base":
                real = real_mean_loss(frame, top0, o.kind)
                res["e0"]["signal"] = null_test(data, o, seasons, top0, real, nulls)
            last = max(seasons)
            m = fitted[(last, res["e0"]["shipped"])][0]
            res["e0"]["importance"] = models.importances(
                m, o.rows(data.filter(c("season") == last)).head(20000)
            )
            for mode in [m for m in ("e0", "e1") if m in res]:
                rows.append(history_rows(frame, o, mode, res[mode]["shipped"], fitted,
                                         run.info.run_id))  # fmt: skip
            results[o.name] = res
            mlflow.log_metrics({f"{o.name}.{m}.share": res[m]["share"]
                                for m in ("e0", "e1") if m in res})  # fmt: skip
            progress(prog, f"{o.name}: e0 {res['e0']['shipped']}"
                     f"{', e1 ' + res['e1']['shipped'] if 'e1' in res else ''},"
                     f" {time.perf_counter() - t0:.0f}s")  # fmt: skip
            log.info("context-retro %s done", o.name)
        history = pl.concat(rows, how="vertical")
        if "sack" in results:
            history = pl.concat([history, split_rows(history, data)])
        bad = history.filter(c("train_end") >= c("as_of")).height
        results["_vintage_violations"] = bad
        if bad:
            raise ValueError(f"{bad} rows have a train_end at or after their as_of (check 6)")
        path = get_config().zone("outputs") / ID / run.info.run_id / "history.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        history.write_parquet(path)
        (work / "results.json").write_text(json.dumps(results, indent=1, default=str))
        (work / "run.json").write_text(json.dumps({"run_id": run.info.run_id, "path": str(path)}))
        mlflow.log_text(json.dumps(results, indent=1, default=str), "results.json")
        results["_run_id"] = run.info.run_id
        results["_history"] = str(path)
        progress(prog, f"done run {run.info.run_id}")
    return results


def shipped(tag: str = "backtest") -> dict[str, dict[str, str]]:
    """Each outcome's shipped rung per mode, from a saved backtest."""
    res = json.loads((cache_dir() / tag / "results.json").read_text())
    return {k: {m: v[m]["shipped"] for m in ("e0", "e1") if m in v}
            for k, v in res.items() if not k.startswith("_")}  # fmt: skip


def final(tag: str, through: int, checks: dict[str, bool]) -> dict:
    """The champion: each outcome's shipped rungs (E0 and E1, from the backtest `tag`) fitted as
    for the season after `through` (so on every season through it, inside the provider rule),
    logged as one model keyed by quantity (`sack_e0`, ...) and registered if every check passed.
    A retrospective expert has no live output: next season's rows are scored after that season."""
    from pcf.core import tracking

    ship = shipped(tag)
    data = plays.load(range(plays.FIRST, through + 1))
    fitted, ends = {}, []
    end = data.select(live_run.known(data).max()).item()
    with tracking.attempt(ID, train_end=end, name=f"champion through {through}",
                          params={"from": tag, "through": through}) as run:  # fmt: skip
        for o in OUTCOMES:
            for mode, name in ship[o.name].items():
                m, e = fit_rung(data, o, rung_named(name), through + 1)
                fitted[quantity(o.name, mode)] = m
                ends.append(e)
        model = models.ContextModel(fitted, train_end=str(max(ends)))
        tracking.log_model(model, trusted_types=models.TRUSTED_TYPES)
        passed = tracking.log_checks(checks)
        version = tracking.register(ID) if passed else None
    return {"run_id": run.info.run_id, "version": version, "train_end": str(max(ends)),
            "quantities": sorted(fitted)}  # fmt: skip


def check_point_in_time(season: int, n_games: int = 4, seed: int = 0) -> dict:
    """Rebuild sample games' rows from views at each game's own `as_of` and compare every field
    and outcome with the season build: the largest difference must be 0. Also: a view the day
    before participation's release holds none of the season's participation fields."""
    from pcf.data.gateway import Gateway, TableSource
    from pcf.experts.context_live.run import moments

    gw = Gateway(TableSource(seasons=[season - 1, season]))
    full = plays.load([season])
    as_of = moments(Gateway())
    ids = full["game_id"].unique().sort().sample(n_games, seed=seed).to_list()
    cols = [x for x in plays.COLUMNS if x not in (*plays.KEYS, "season_type", "posteam",
                                                  "defteam", "passer_id")]  # fmt: skip
    worst = 0.0
    for gid in ids:
        at = full.filter(c("game_id") == gid)["as_of"].max()
        a = plays.season_table(season, as_of, gw, at).filter(c("game_id") == gid).sort(plays.KEYS)
        b = full.filter(c("game_id") == gid).sort(plays.KEYS)
        if not a.select(plays.KEYS).equals(b.select(plays.KEYS)):
            return {"gap": float("inf"), "games": ids}
        for f in cols:
            x, y = a[f], b[f]
            if x.dtype == pl.String or y.dtype == pl.String:
                worst = max(worst, float((x.fill_null("") != y.fill_null("")).any()) * 1e9)
                continue
            if x.dtype.is_temporal():
                worst = max(worst, float((x != y).fill_null(x.is_null() != y.is_null()).any()))
                continue
            d = (x.cast(pl.Float64).fill_null(-999) - y.cast(pl.Float64).fill_null(-999)).abs()
            worst = max(worst, float(d.max() or 0.0))
    release = full["known_at_targets"].max()  # participation's release (filled rows are earlier)
    before = gw.view(release - timedelta(seconds=1), "retrospective",
                     plays.RETRO_INPUTS).table("play", seasons=[season])  # fmt: skip
    # the play table's rows are the play-by-play's; what must be empty is participation's fields
    fields = [x for x in PARTICIPATION_FIELDS if x in before.columns]
    filled = before.select(pl.any_horizontal(c(x).is_not_null() for x in fields).sum()).item()
    return {"gap": worst, "games": ids, "participation_rows_before_release": int(filled or 0),
            "fields_checked": fields}  # fmt: skip


def main(argv: Sequence[str] | None = None) -> None:
    import argparse

    ap = argparse.ArgumentParser(prog="python -m pcf.experts.context_retro.run")
    ap.add_argument("what", choices=["prepare", "backtest", "pit", "final"])
    ap.add_argument("--checks", default="", help="final: a JSON file of named checks (true/false)")
    ap.add_argument("--seasons", default=",".join(map(str, TEST_SEASONS)))
    ap.add_argument("--outcomes", default="")
    ap.add_argument("--nulls", type=int, default=20)
    ap.add_argument("--tag", default="backtest")
    ap.add_argument("--open-vault", action="store_true")
    ap.add_argument("--fixed-from", default="", help="score the rungs this backtest shipped")
    a = ap.parse_args(argv)
    seasons = [int(x) for x in a.seasons.split(",")]
    if a.what == "prepare":
        plays.prepare(range(plays.FIRST, max(seasons) + 1))
    elif a.what == "pit":
        print(check_point_in_time(max(seasons)))
    elif a.what == "final":
        checks = json.loads(Path(a.checks).read_text()) if a.checks else {}
        print(final(a.tag, max(seasons), checks))
    else:
        names = [x for x in a.outcomes.split(",") if x] or None
        fixed = shipped(a.fixed_from) if a.fixed_from else None
        res = backtest(seasons, names, a.open_vault, a.nulls, a.tag, fixed)
        print(res["_run_id"], res["_history"])


if __name__ == "__main__":
    main()
