"""The expert contract (docs/ARCHITECTURE.md): one interface for every expert, composite and
product, and the standard output schema every one of them writes.

    class Elo(Expert):
        id = "elo"
        cadence = "in_season"
        grain = "team_game"
        inputs = {"team_game": ("result",), "game": ("schedule",)}
        quantity = "elo_win_prob"
        kind = "probability"
        run = "tuesday"

        def features(self, view, games): ...   # rows predicted at view.at, from the view only
        def target(self, view): ...            # keys + y + known_at
        def fit(self, train): ...              # train: features, y, weight
        def predict(self, model, rows): ...    # keys + mean, q10, q50, q90

`pcf.validation.backtest` runs it walk-forward and `pcf.validation.leakage` checks it. Features
are defined per moment (`features(view, games)`). A model may add `features_history` as a faster
bulk version; it's used only if it matches the per-moment one at the leakage cutoffs.
"""

from __future__ import annotations

import importlib
import pkgutil
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, ClassVar

import polars as pl

from pcf.core import registry

if TYPE_CHECKING:
    from pcf.data.gateway import View

CADENCES = ("in_season", "retrospective", "offseason_events")
KINDS = ("amount", "probability")
UTC_TIME = pl.Datetime("us", "UTC")
OUTPUT_SCHEMA: dict[str, pl.DataType] = {
    "as_of": UTC_TIME,
    "quantity": pl.String(),
    "mean": pl.Float64(),
    "q10": pl.Float64(),
    "q50": pl.Float64(),
    "q90": pl.Float64(),
    "model": pl.String(),
    "model_version": pl.String(),
    "run_id": pl.String(),
    "train_end": UTC_TIME,
    "cadence": pl.String(),
}
QUANTILES = ("q10", "q50", "q90")
PREDICTION = ("mean", *QUANTILES)
# What a spike forecast adds (`Expert.spike`): the chance the result is above 0, and the forecast
# if it is. Higher layers read these, and the harness judges each part (VALIDATION.md §7).
SPIKE_PARTS: dict[str, pl.DataType] = {
    "p_nonzero": pl.Float64(),
    "if_nonzero_mean": pl.Float64(),
    "if_nonzero_q10": pl.Float64(),
    "if_nonzero_q50": pl.Float64(),
    "if_nonzero_q90": pl.Float64(),
}
# Model layers in the registry (phase 1-3) must be named in a consumer's inputs.
MODEL_PHASES = (1, 2, 3)
# Packages searched by `find`, in order. The harness's own toy expert lives in validation.
MODEL_PACKAGES = (
    "pcf.baselines",
    "pcf.experts",
    "pcf.composites",
    "pcf.products",
    "pcf.validation",
)
TAG_PARTS = ("tags", "tags_result")


class Expert(ABC):
    """One model. Subclasses set the class attributes and the four methods.

    - `inputs`: a table name → the parts it reads, or a registry id → the pinned version of that
      model's outputs. The gateway refuses anything else.
    - `run` (in-season): the prediction moment, one of `pcf.data.timeline.moments.RUNS`, or
      `KICKOFF` for a benchmark.
    - `benchmark`: a yardstick from outside PCF (ECR, the closing line). Scored like a model, but
      it needs no signal test, and only a benchmark may run at kickoff (baselines brief, D5).
    - `variant`: one of several models under one project id (the baselines: `ecr`, `rolling4`).
    - `first_train`: the first season it can be trained on, if later than config's (ECR: 2021).
    - `event` (offseason events): one of `moments.EVENTS`.
    - `groups`: feature columns the range coverage is also judged in (VALIDATION.md §7), besides
      the season; e.g. position, rookie, starter.
    - `spike`: an amount whose results pile up at exactly 0. `predict` also returns `SPIKE_PARTS`,
      they're saved with the history, and the harness judges the two parts (decision 0014).
    """

    id: ClassVar[str]
    cadence: ClassVar[str]
    grain: ClassVar[str]
    inputs: ClassVar[Mapping[str, tuple[str, ...] | int]]
    quantity: ClassVar[str]
    kind: ClassVar[str] = "amount"
    run: ClassVar[str] = "tuesday"
    event: ClassVar[str | None] = None
    groups: ClassVar[tuple[str, ...]] = ()
    benchmark: ClassVar[bool] = False
    variant: ClassVar[str] = ""
    first_train: ClassVar[int | None] = None
    spike: ClassVar[bool] = False

    @abstractmethod
    def features(self, view: View, games: pl.DataFrame) -> pl.DataFrame:
        """The rows predicted at `view.at`, keyed by the grain's keys, with their features.
        `games` are the games predicted at this moment: game_id, season, week, kickoff."""

    @abstractmethod
    def target(self, view: View) -> pl.DataFrame:
        """The outcome per row: the grain's keys, `y`, and `known_at` (when it became known)."""

    @abstractmethod
    def fit(self, train: pl.DataFrame) -> Any:
        """A model from training rows: features, `y` and `weight` (recency, VALIDATION.md §1)."""

    @abstractmethod
    def predict(self, model: Any, rows: pl.DataFrame) -> pl.DataFrame:
        """The grain's keys plus `mean`, `q10`, `q50`, `q90` (probabilities: `mean` only)."""

    def explain(self, model: Any) -> dict[str, Any]:
        """Coefficients, importances or SHAP values. Empty by default."""
        return {}

    @classmethod
    def label(cls) -> str:
        """The model's name in outputs and scorecards: its id, and its variant if it has one."""
        return f"{cls.id}/{cls.variant}" if cls.variant else cls.id

    @classmethod
    def keys(cls) -> list[str]:
        from pcf.data.schemas import table

        return table(cls.grain).key_names

    @classmethod
    def tables(cls) -> dict[str, tuple[str, ...]]:
        """The table inputs: name → parts."""
        return {k: v for k, v in cls.inputs.items() if not isinstance(v, int)}

    @classmethod
    def upstream(cls) -> dict[str, int]:
        """The model inputs: registry id → pinned version."""
        return {k: v for k, v in cls.inputs.items() if isinstance(v, int)}


def check_expert(expert: type[Expert] | Expert, path=None) -> None:
    """The contract, checked against the registry: a known id and cadence, a real grain, real
    tables and parts, and `inputs` that match `depends_on` (the graph on paper is the graph in the
    code). Raises ValueError listing every problem."""
    from pcf.data.schemas import TABLES
    from pcf.data.timeline.moments import EVENTS, KICKOFF, RUNS

    cls = expert if isinstance(expert, type) else type(expert)
    problems = []
    entries = registry.projects(path)
    entry = entries.get(cls.id)
    if entry is None:
        raise ValueError(f"{cls.__name__}: no project {cls.id!r} in the registry")
    is_model = entry.get("phase") in MODEL_PHASES
    if cls.cadence not in CADENCES:
        problems.append(f"cadence {cls.cadence!r} isn't one of {CADENCES}")
    elif is_model and cls.cadence not in (entry.get("cadence") or []):
        problems.append(f"cadence {cls.cadence!r} isn't the registry's {entry.get('cadence')}")
    if cls.kind not in KINDS:
        problems.append(f"kind {cls.kind!r} isn't one of {KINDS}")
    if cls.grain not in TABLES:
        problems.append(f"grain {cls.grain!r} isn't a table")
    if cls.cadence == "in_season" and cls.run == KICKOFF and not cls.benchmark:
        problems.append("only a benchmark may run at kickoff")
    elif cls.cadence == "in_season" and cls.run not in (*RUNS, KICKOFF):
        problems.append(f"run {cls.run!r} isn't one of {list(RUNS)}")
    if cls.cadence == "offseason_events" and cls.event not in EVENTS:
        problems.append(f"event {cls.event!r} isn't one of {EVENTS}")
    needs = set()
    for name, value in cls.inputs.items():
        if isinstance(value, int):
            if name not in entries:
                problems.append(f"input {name!r} isn't a registry project")
            needs.add(name)
            continue
        if name not in TABLES:
            problems.append(f"input {name!r} is neither a table nor a project")
            continue
        missing = set(value) - set(TABLES[name].parts)
        if missing:
            problems.append(f"{name} has no parts {sorted(missing)}")
        needs.add("grain-tables")
        if name == "drive" or set(value) & set(TAG_PARTS):
            needs.add("tag-tables")
    if is_model:
        depends = set(entry.get("depends_on") or [])
        for project in sorted(needs - depends):
            problems.append(f"reads {project} but the registry's depends_on doesn't list it")
        unread = {p for p in depends if entries.get(p, {}).get("phase") in MODEL_PHASES} - needs
        for project in sorted(unread):
            problems.append(f"depends_on lists model {project} but inputs don't read it")
    if problems:
        raise ValueError(f"{cls.__name__} ({cls.id}): " + "; ".join(problems))


def check_output(df: pl.DataFrame, keys: list[str], kind: str = "amount") -> None:
    """The standard output schema: the keys and every column with its type, no missing keys,
    one row per key, quantity and moment, `train_end` no later than `as_of` (the vintage rule),
    and for amounts q10 ≤ q50 ≤ q90."""
    for col in keys:
        if col not in df.columns:
            raise ValueError(f"output has no key column {col}")
        if df[col].null_count():
            raise ValueError(f"output has {df[col].null_count()} rows with no {col}")
    for col, dtype in OUTPUT_SCHEMA.items():
        if col not in df.columns:
            raise ValueError(f"output has no {col} column")
        if df.schema[col] != dtype:
            raise ValueError(f"output {col} is {df.schema[col]}, not {dtype}")
    if df.select(*keys, "quantity", "as_of").is_duplicated().any():
        raise ValueError("output has two rows for one key, quantity and moment")
    if df["train_end"].null_count() or df.filter(pl.col("train_end") > pl.col("as_of")).height:
        raise ValueError("output train_end must be set and no later than as_of (check 6)")
    if df["mean"].null_count():
        raise ValueError(f"output has {df['mean'].null_count()} rows with no mean")
    if kind == "amount":
        bad = df.filter((pl.col("q10") > pl.col("q50")) | (pl.col("q50") > pl.col("q90"))).height
        if bad or df.select(pl.sum_horizontal(pl.col(*QUANTILES).null_count())).item():
            raise ValueError(f"output quantiles are missing or out of order on {bad} rows")
    if "p_nonzero" in df.columns:
        check_spike_parts(df)


def check_spike_parts(df: pl.DataFrame) -> None:
    """The two parts of a spike forecast: all present, a real chance, ranges in order, and a mean
    that is the chance times the share."""
    c = pl.col
    missing = [p for p in SPIKE_PARTS if p not in df.columns or df[p].null_count()]
    if missing:
        raise ValueError(f"output is missing spike parts {missing}")
    if not df["p_nonzero"].is_between(0, 1).all():
        raise ValueError("output p_nonzero must be between 0 and 1")
    bad = df.filter(
        (c("if_nonzero_q10") > c("if_nonzero_q50")) | (c("if_nonzero_q50") > c("if_nonzero_q90"))
    ).height
    if bad:
        raise ValueError(f"output if_nonzero ranges are out of order on {bad} rows")
    off = df.filter((c("p_nonzero") * c("if_nonzero_mean") - c("mean")).abs() > 1e-9).height
    if off:
        raise ValueError(f"output mean isn't p_nonzero × if_nonzero_mean on {off} rows")


def find(project_id: str, variant: str | None = None) -> type[Expert]:
    """The Expert subclass with this id (and variant), from the model packages."""
    for cls in find_all(project_id):
        if variant is None or cls.variant == variant:
            return cls
    raise KeyError(f"no Expert with id {project_id!r} and variant {variant!r}")


def find_all(project_id: str) -> list[type[Expert]]:
    """Every Expert subclass with this id (one per variant), from the model packages."""
    found = []
    for package_name in MODEL_PACKAGES:
        package = importlib.import_module(package_name)
        for info in pkgutil.walk_packages(package.__path__, f"{package_name}."):
            module = importlib.import_module(info.name)
            for value in vars(module).values():
                if (
                    isinstance(value, type)
                    and issubclass(value, Expert)
                    and value is not Expert
                    and getattr(value, "id", None) == project_id
                    and value.__module__ == module.__name__
                    and not getattr(value, "__abstractmethods__", None)
                    and not getattr(value, "baseline", False)
                    and hasattr(value, "quantity")  # not a shared base class
                    and value not in found
                ):
                    found.append(value)
    if not found:
        raise KeyError(f"no Expert with id {project_id!r} in {', '.join(MODEL_PACKAGES)}")
    return found
