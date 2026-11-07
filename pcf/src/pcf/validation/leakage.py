"""The leakage suite (docs/ARCHITECTURE.md, "Leakage defense in depth"; VALIDATION.md §9).

| # | Check | Here |
|---|---|---|
| 1 | Gateway only | `scan_code`: no loaders, file reads or table imports in model code |
| 2 | known_at sanity | `known_at_sanity`: UTC, no gaps, result parts never known before kickoff |
| 3 | Future perturbation | `future_check(mode="scramble")`: same features, future scrambled |
| 4 | Future deletion | `future_check(mode="delete")`: identical with the future deleted |
| 5 | Cadence | `cadence_check`: the registry's cadence; no unfinished season's post-season data |
| 6 | Model vintage | `vintage_check`: no upstream row made by a model trained after it |
| 7 | Walk-forward only | `walk_forward_check`: no random splitters; trained before made |
| 8 | Test-label perturbation | `test_label_check`: test results scrambled, same predictions |
| 9 | Shuffled-target null | `pcf.validation.nulls.signal_test` |
| 10 | Too good to be true | `too_good`: flags for review, never blocks |

Checks 3 and 4 compare a model's features with and without the data after a cutoff. Per-moment
features read views that already end at their moment, so for them the checks prove the gateway
and catch code that reaches around it. A bulk `features_history` gets the full test.
"""

from __future__ import annotations

import ast
import inspect
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl

from pcf.core.contract import Expert
from pcf.core.registry import project
from pcf.data.gateway import Gateway, Source
from pcf.data.schemas import table
from pcf.data.timeline import Calendar
from pcf.data.timeline.moments import season_ends
from pcf.validation.backtest import Backtest, feature_history, targets, walk

c = pl.col
UTC_TIME = pl.Datetime("us", "UTC")
CUTOFFS = 25
LAST_MOMENTS = 3  # per-moment checks compare the rows of the last 3 moments before each cutoff
LABEL_STEPS = 5
TOO_GOOD_CORRELATION = 0.9
SCRAMBLE_OFFSET = 7  # added to scrambled numbers, so even a constant column changes
FLOAT_TOLERANCE = 1e-9

FORBIDDEN_IMPORTS = ("pcf.data.tables", "pcf.data.sources", "pcf.data.tags.build", "duckdb")
FORBIDDEN_CALLS = {
    "open", "read_parquet", "scan_parquet", "read_csv", "scan_csv", "read_ipc", "scan_ipc",
    "read_json", "read_ndjson", "scan_ndjson", "read_database", "read_excel", "read_text",
    "read_bytes", "load", "snapshot",
}  # fmt: skip
SPLITTER_MODULES = ("sklearn.model_selection",)
SPLITTERS = {
    "KFold", "StratifiedKFold", "GroupKFold", "ShuffleSplit", "train_test_split",
    "cross_val_score", "cross_validate", "cross_val_predict", "GridSearchCV",
    "RandomizedSearchCV", "TimeSeriesSplit",
}  # fmt: skip


@dataclass(frozen=True)
class Check:
    number: int
    name: str
    passed: bool
    detail: str
    blocking: bool = True


# --- 1 and 7, in the code -------------------------------------------------------------------


def _imported(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [a.name for a in node.names]
    if isinstance(node, ast.ImportFrom) and node.module:
        return [node.module, *(f"{node.module}.{a.name}" for a in node.names)]
    return []


def _under(name: str, prefixes: Sequence[str]) -> bool:
    return any(name == p or name.startswith(p + ".") for p in prefixes)


def scan_code(text: str) -> tuple[list[str], list[str]]:
    """Model code's problems: (reads around the gateway [check 1], random splitters [check 7])."""
    gateway, splitters = [], []
    for node in ast.walk(ast.parse(text)):
        for name in _imported(node):
            if _under(name, FORBIDDEN_IMPORTS):
                gateway.append(f"line {node.lineno}: imports {name}")
            if _under(name, SPLITTER_MODULES) or name.rsplit(".", 1)[-1] in SPLITTERS:
                splitters.append(f"line {node.lineno}: imports {name}")
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if name in FORBIDDEN_CALLS:
                gateway.append(f"line {node.lineno}: calls {name}()")
            if name in SPLITTERS:
                splitters.append(f"line {node.lineno}: calls {name}()")
    return sorted(set(gateway)), sorted(set(splitters))


def model_files(expert: Expert | type[Expert]) -> list[Path]:
    """The files of a model's code: its module, or its whole package folder under experts/,
    composites/ or products/."""
    cls = expert if isinstance(expert, type) else type(expert)
    path = Path(inspect.getsourcefile(cls) or "")
    if path.parent.parent.name in ("experts", "composites", "products"):
        return sorted(path.parent.glob("*.py"))
    return [path]


def code_checks(expert: Expert | type[Expert]) -> tuple[list[str], list[str]]:
    gateway, splitters = [], []
    for path in model_files(expert):
        g, s = scan_code(path.read_text(encoding="utf-8"))
        gateway += [f"{path.name} {x}" for x in g]
        splitters += [f"{path.name} {x}" for x in s]
    return gateway, splitters


def gateway_only_check(expert: Expert) -> Check:
    problems, _ = code_checks(expert)
    return Check(1, "gateway_only", not problems, "; ".join(problems) or "reads only its view")


# --- 2 ----------------------------------------------------------------------------------------


def known_at_sanity(expert: Expert, gateway: Gateway) -> Check:
    """Every declared part has a UTC `known_at` on every row, and parts about a game's result are
    never known before its kickoff."""
    kickoffs = gateway.calendar.games.select("game_id", "kickoff")
    problems = []
    for name, parts in expert.tables().items():
        t = table(name)
        for part in {t.spine, *parts}:
            df = gateway.source.part(name, part)
            dtype = df.schema.get("known_at")
            if not isinstance(dtype, pl.Datetime) or dtype.time_zone != "UTC":
                problems.append(f"{name}.{part}: known_at is {dtype}")
                continue
            if df["known_at"].null_count():
                problems.append(f"{name}.{part}: {df['known_at'].null_count()} rows lack known_at")
            if part in t.after:
                early = (
                    df.select("game_id", "known_at")
                    .join(kickoffs, on="game_id")
                    .filter(c("known_at") < c("kickoff"))
                    .height
                )
                if early:
                    problems.append(f"{name}.{part}: {early} rows known before kickoff")
    return Check(2, "known_at_sanity", not problems, "; ".join(problems) or "all parts sound")


# --- perturbed worlds -------------------------------------------------------------------------


def scramble(frame: pl.DataFrame, keep: Sequence[str], seed: int) -> pl.DataFrame:
    """Every column but `keep`, shuffled; numbers also shifted and booleans flipped, so each
    changes."""
    out = []
    for i, (col, dtype) in enumerate(frame.schema.items()):
        if col in keep:
            out.append(c(col))
            continue
        shuffled = c(col).shuffle(seed=seed + i)
        if dtype == pl.Boolean:
            shuffled = ~shuffled
        elif dtype.is_numeric():
            shuffled = shuffled + SCRAMBLE_OFFSET
        out.append(shuffled.alias(col))
    return frame.select(out)


class Perturbed:
    """A source whose rows chosen by `rows(name, part)` (an expression, or None for none) are
    deleted or scrambled. Keys, `season` and `known_at` are kept."""

    def __init__(
        self,
        source: Source,
        rows: Callable[[str, str], pl.Expr | None],
        mode: str,
        seed: int = 0,
    ):
        if mode not in ("delete", "scramble"):
            raise ValueError("mode is delete or scramble")
        self.source, self.rows, self.mode, self.seed = source, rows, mode, seed
        self._cache: dict[tuple[str, str], pl.DataFrame] = {}

    def part(self, name: str, part: str) -> pl.DataFrame:
        key = (name, part)
        if key not in self._cache:
            frame = self.source.part(name, part)
            pick = self.rows(name, part)
            if pick is not None:
                hit = frame.filter(pick)
                rest = frame.filter(~pick | pick.is_null())
                if self.mode == "scramble" and hit.height:
                    keep = [*table(name).key_names, "season", "known_at"]
                    rest = pl.concat([rest, scramble(hit, keep, self.seed)], how="vertical")
                frame = rest
            self._cache[key] = frame
        return self._cache[key]


def _after(cutoff: datetime) -> pl.Expr:
    return c("known_at") > pl.lit(cutoff).cast(UTC_TIME)


def future_world(gateway: Gateway, cutoff: datetime, mode: str, seed: int = 0) -> Gateway:
    """The world with everything known after `cutoff` deleted or scrambled, outputs included."""
    source = Perturbed(gateway.source, lambda _n, _p: _after(cutoff), mode, seed)

    def outputs(project_id: str, version: int) -> pl.DataFrame:
        df = gateway.output(project_id, version)
        late = c("as_of") > pl.lit(cutoff).cast(UTC_TIME)
        if mode == "delete":
            return df.filter(~late)
        keys = [x for x in df.columns if x not in ("mean", "q10", "q50", "q90")]
        return pl.concat([df.filter(~late), scramble(df.filter(late), keys, seed)])

    return Gateway(source, gateway.calendar, outputs)


def cutoffs(cal: Calendar, seasons: Sequence[int], n: int = CUTOFFS, seed: int = 0):
    """`n` cutoffs (label, moment): week 1, mid-season (week 9, near the trade deadline), the
    playoffs, the combine, free agency and the draft of the last season, then random moments
    across `seasons`."""
    last = max(seasons)
    weeks = cal.weeks.filter(c("season") == last)
    fixed: list[tuple[str, datetime]] = []

    def week_start(cond: pl.Expr, label: str) -> None:
        hit = weeks.filter(cond).sort("start")
        if hit.height:
            fixed.append((label, hit["start"][0] + timedelta(hours=14)))

    week_start(c("week") == 1, f"{last} week 1")
    regular = weeks.filter(c("phase") == "regular_season")["week"]
    mid = 9 if 9 in regular else int(regular.median() or 1)  # week 9: near the trade deadline
    week_start(c("week") == mid, f"{last} mid-season (week {mid})")
    week_start(c("phase") == "postseason", f"{last} playoffs")
    phases = cal.phases.filter(c("season") == last)
    for phase in ("free_agency", "draft"):
        hit = phases.filter(c("phase") == phase)
        if hit.height:
            fixed.append((f"{last} {phase.replace('_', ' ')}", hit["start"][0]))
    combine = cal.offseason.filter(c("season") == last)["combine_start"]
    if combine.len() and combine[0] is not None:
        day = datetime.combine(combine[0], datetime.min.time(), tzinfo=UTC)
        fixed.append((f"{last} combine", day + timedelta(hours=14)))
    span = cal.weeks.filter(c("season").is_in(list(seasons)))
    lo, hi = span["start"].min(), span["end"].max()
    rng = np.random.default_rng(seed)
    extra = max(0, n - len(fixed))
    random_at = [lo + (hi - lo) * float(u) for u in sorted(rng.random(extra))]
    return fixed[:n] + [(f"random {at:%Y-%m-%d}", at) for at in random_at]


def _differing(a: pl.DataFrame, b: pl.DataFrame, keys: Sequence[str]) -> int:
    """Rows that differ between two frames keyed alike: in one only, or with any other column
    different. Numbers count as equal within 1e-9 (relative): the same numbers summed in another
    order differ in the last digit, and no real leak is that small (validation-harness#F13)."""
    keys = list(keys)
    paired = a.join(b.select(a.columns), on=keys, how="full", suffix="__b", nulls_equal=True)
    differs = []
    for col, dtype in a.schema.items():
        if col in keys:
            continue
        x, y = c(col), c(f"{col}__b")
        if dtype.is_float():
            close = (x - y).abs() <= FLOAT_TOLERANCE * pl.max_horizontal(x.abs(), y.abs(), 1.0)
            same = (x.is_null() & y.is_null()) | close.fill_null(False)
        else:
            same = x.eq_missing(y)
        differs.append(~same)
    missing = pl.any_horizontal(c(k).is_null() | c(f"{k}__b").is_null() for k in keys)
    return paired.filter(missing | pl.any_horizontal(differs) if differs else missing).height


def future_check(
    bt: Backtest,
    gateway: Gateway,
    cuts: Sequence[tuple[str, datetime]],
    mode: str,
    seed: int = 0,
) -> Check:
    """Checks 3 (scramble) and 4 (delete). Per-moment features: the rows of the last few moments
    before each cutoff, rebuilt in the perturbed world. A bulk `features_history`: every row
    predicted by the cutoff, and it must also match the per-moment features."""
    number, name = (3, "future_perturbation") if mode == "scramble" else (4, "future_deletion")
    expert = bt.expert
    bulk = hasattr(expert, "features_history")
    base = bt.features
    failed = []
    rows = 0
    if bulk:
        whole = feature_history(expert, gateway, bt.steps, bulk=True)
    for label, cut in cuts:
        world = future_world(gateway, cut, mode, seed)
        moment = pl.lit(cut).cast(UTC_TIME)
        if bulk:
            mine = feature_history(expert, world, bt.steps, bulk=True).filter(c("as_of") <= moment)
            ref = whole.filter(c("as_of") <= moment)
            keys = [*expert.keys(), "as_of"]
            early = base.filter(c("as_of") <= moment)
            diff = _differing(ref, mine, keys) + _differing(early, ref.select(early.columns), keys)
        else:
            moments = base.filter(c("as_of") <= moment)["as_of"].unique().sort().tail(LAST_MOMENTS)
            if moments.is_empty():
                continue
            chosen = [s for s in bt.steps if s.games["moment"].is_in(moments.implode()).any()]
            mine = feature_history(expert, world, chosen).filter(
                c("as_of").is_in(moments.implode())
            )
            ref = base.filter(c("as_of").is_in(moments.implode()))
            diff = _differing(ref, mine, [*expert.keys(), "as_of"])
        rows += mine.height
        if diff:
            failed.append(f"{label}: {diff} rows differ")
    detail = "; ".join(failed) or f"identical at {len(cuts)} cutoffs ({rows:,} rows compared)"
    return Check(number, name, not failed, detail)


# --- 5, 6, 7 ------------------------------------------------------------------------------------


def cadence_check(expert: Expert, gateway: Gateway, cuts: Sequence[tuple[str, datetime]]) -> Check:
    """The expert's cadence is the registry's, and an in-season view never shows a post-season
    part's rows for a season that hasn't finished."""
    problems = []
    entry = project(expert.id)
    allowed = entry.get("cadence")
    if allowed and expert.cadence not in allowed:
        problems.append(f"cadence {expert.cadence} isn't the registry's {allowed}")
    if expert.cadence == "in_season":
        # Finished seasons from the calendar itself, not the gateway: the gateway is under test.
        ends = season_ends(gateway.calendar)
        for name, parts in expert.tables().items():
            post = [p for p in parts if p in table(name).post_season]
            for label, cut in cuts if post else []:
                view = gateway.view(cut, expert.cadence, expert.inputs)
                df = view.table(name)
                spine = table(name).spine
                shown = pl.any_horizontal(
                    c("known_at" if p == spine else f"{p}_known_at").is_not_null() for p in post
                )
                done = [s for s, end in ends.items() if end <= cut]
                early = df.filter(shown & ~c("season").is_in(done)).height
                if early:
                    problems.append(f"{label}: {early} {name} rows of an unfinished season")
    return Check(
        5, "cadence", not problems, "; ".join(problems) or f"{expert.cadence}, as registered"
    )


def vintage_check(bt: Backtest, gateway: Gateway) -> Check:
    """No upstream output row, and none of this backtest's, was made by a model trained after
    it (`train_end` > `as_of`)."""
    problems = []
    for project_id, version in bt.expert.upstream().items():
        df = gateway.output(project_id, version)
        bad = df.filter(c("train_end").is_null() | (c("train_end") > c("as_of"))).height
        if bad:
            problems.append(f"{project_id} v{version}: {bad} rows")
    own = bt.history.filter(c("train_end") > c("as_of")).height
    if own:
        problems.append(f"this backtest: {own} rows")
    inputs = ", ".join(bt.expert.upstream()) or "no model inputs"
    return Check(6, "vintage", not problems, "; ".join(problems) or f"sound ({inputs})")


def walk_forward_check(bt: Backtest) -> Check:
    """No random splitter in the model's code, and every prediction came from a model fit on
    rows known before it."""
    _, splitters = code_checks(bt.expert)
    late = bt.history.filter(c("train_end") > c("as_of")).height
    problems = splitters + ([f"{late} predictions trained after they were made"] if late else [])
    detail = "; ".join(problems) or f"{len(bt.test)} time-ordered steps"
    return Check(7, "walk_forward", not problems, detail)


# --- 8 ------------------------------------------------------------------------------------------


def test_label_check(
    bt: Backtest, gateway: Gateway, n_steps: int = LABEL_STEPS, seed: int = 0
) -> Check:
    """Scramble the results of every game from a test step on (the parts known after kickoff),
    rebuild that step's features and the outcomes, refit and predict it: the predictions must not
    change. Catches anything fit on the whole dataset."""
    expert = bt.expert
    keys = expert.keys()
    # Steps with predictions: a model can have none in some weeks (ECR has no week 18)
    tested = [i for i in bt.test if i in set(bt.history["step"].to_list())]
    picks = [tested[int(i)] for i in np.linspace(0, len(tested) - 1, min(n_steps, len(tested)))]
    by_index = {s.index: s for s in bt.steps}
    failed = []
    for index in picks:
        step = by_index[index]
        later = pl.concat([s.games["game_id"] for s in bt.steps if s.index >= index])
        # A result known before the step's last moment (Thursday's game, by the Saturday run) is
        # a fair input to that moment's features (decision 0020), so it stays as it is.
        last = pl.lit(step.games["moment"].max()).cast(UTC_TIME)

        def rows(name: str, part: str, later=later, last=last) -> pl.Expr | None:
            if part not in table(name).after:
                return None
            return c("game_id").is_in(later.implode()) & (c("known_at") > last)

        world = Gateway(Perturbed(gateway.source, rows, "scramble", seed), gateway.calendar,
                        gateway.output)  # fmt: skip
        mine = feature_history(expert, world, [step])
        feats = pl.concat([bt.features.filter(c("step") != index), mine], how="diagonal_relaxed")
        before = walk(expert, bt.features, bt.targets, bt.steps, [index], bt.refit, bt.half_life)
        after = walk(expert, feats, targets(expert, world), bt.steps, [index], bt.refit,
                     bt.half_life)  # fmt: skip
        cols = [
            k for k in ("mean", "q10", "q50", "q90") if k in before.columns
        ]  # probability: mean
        diff = _differing(before.select(*keys, *cols), after.select(*keys, *cols), keys)
        if diff:
            failed.append(f"step {index} ({step.season} wk {step.week}): {diff} rows differ")
    targets(expert, gateway)  # leave the expert as it was, in case it keeps state
    detail = "; ".join(failed) or f"identical at {len(picks)} test steps"
    return Check(8, "test_labels", not failed, detail)


# --- 10 -----------------------------------------------------------------------------------------


def too_good(bt: Backtest) -> Check:
    """A flag, not a block: any single feature correlated above 0.9 with the outcome."""
    keys = set(bt.expert.keys()) | {"step", "step_season", "step_week", "as_of", "y", "known_at"}
    pool = bt.features.join(bt.targets, on=bt.expert.keys(), how="inner")
    flagged = []
    for col, dtype in pool.schema.items():
        if col in keys or not dtype.is_numeric():
            continue
        r = pool.select(pl.corr(c(col).cast(pl.Float64), c("y").cast(pl.Float64))).item()
        if r is not None and abs(r) > TOO_GOOD_CORRELATION:
            flagged.append(f"{col} (r = {r:.2f})")
    detail = "; ".join(flagged) or f"no feature above |r| {TOO_GOOD_CORRELATION}"
    return Check(10, "too_good", not flagged, detail, blocking=False)


def run_checks(
    bt: Backtest,
    gateway: Gateway,
    signal=None,
    n_cutoffs: int = CUTOFFS,
    seed: int = 0,
) -> list[Check]:
    """Checks 1-8 and 10, plus 9 from a signal test if given."""
    seasons = sorted({s.season for s in bt.steps if s.index in bt.test})
    cuts = cutoffs(gateway.calendar, seasons, n_cutoffs, seed)
    out = [
        gateway_only_check(bt.expert),
        known_at_sanity(bt.expert, gateway),
        future_check(bt, gateway, cuts, "scramble", seed),
        future_check(bt, gateway, cuts, "delete", seed),
        cadence_check(bt.expert, gateway, cuts),
        vintage_check(bt, gateway),
        walk_forward_check(bt),
        test_label_check(bt, gateway, seed=seed),
    ]
    if signal is not None:
        detail = f"beat {signal.beaten} of {signal.n} shuffled refits (needs {signal.needed})"
        out.append(Check(9, "shuffled_null", signal.passed, detail))
    elif bt.expert.benchmark:
        out.append(Check(9, "shuffled_null", True, "not applicable: a benchmark from outside PCF"))
    out.append(too_good(bt))
    return out


def results(checks: Sequence[Check]) -> dict[str, bool]:
    """The blocking checks as {name: passed}, for `tracking.log_checks`."""
    return {ch.name: ch.passed for ch in checks if ch.blocking}
