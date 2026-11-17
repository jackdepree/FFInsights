"""The yardstick (crude-forecaster brief): what an expert, a hunch's input or an idea's input adds
to the crude forecast of yards, in one unit across all of them.

- **Added alone** (method A): the share of the crude forecast's held-out squared error removed
  when it's the only thing added.
- **Fair share** (method C): its average held-out gain over every order the members could have
  been added in (a Shapley share). The shares add up to the gain from all of them together.
- Intervals are 90%, resampling whole weeks (VALIDATION.md §4), on the same rows for both sides.

    board = load_board("receiving")              # the crude forecast's walk-forward, cached
    table = yardstick(board)                     # every finished expert, both methods
    row = score_input(board, frame, "my_idea")   # one new input: minutes, not hours

Every forecast here is a walk-forward refit by `pcf.validation.backtest.walk`, so an added input
is judged only on seasons its model never saw.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import polars as pl

from pcf.baselines.crude import features as F
from pcf.baselines.crude.model import Crude, variant, with_experts
from pcf.config import get_config
from pcf.core.log import get_logger
from pcf.data.gateway import END_OF_TIME, Gateway
from pcf.validation import backtest
from pcf.validation.scores import mean_pinball

log = get_logger(__name__)
c = pl.col
DRAWS = 2000
LEVEL = 0.90
REFIT = "season"  # one fit per season, before week 1, as in the exploration (decision 0037)
# The member that must get nothing: a copy of one expert's columns shuffled within each week.
SHUFFLED = "shuffled"
FIRST_HALF = (2019, 2020, 2021)  # the halves of the scored seasons (the brief's failure test)


@dataclass
class Board:
    """One target and horizon: the crude forecaster's features (with every expert's columns) and
    outcomes for every step, and the forecasts made so far, by what was added."""

    base: type[Crude]
    features: pl.DataFrame
    outcomes: pl.DataFrame
    steps: list
    test: list[int]
    preds: dict[tuple, pl.DataFrame] = field(default_factory=dict)

    @property
    def keys(self) -> list[str]:
        return self.base.keys()

    def members(self) -> dict[str, tuple[tuple[str, ...], tuple[str, ...]]]:
        """Each finished expert as (groups added, extra columns), plus the shuffled copy."""
        out = {g: ((g,), ()) for g in self.base.expert_groups()}
        return out | {SHUFFLED: ((), tuple(shuffled_columns(self.base)))}

    def forecast(
        self,
        added: Sequence[str] = (),
        extra: Sequence[str] = (),
        seed: int | None = None,
        drop_season: int | None = None,
        feats: pl.DataFrame | None = None,
    ) -> pl.DataFrame:
        """The walk-forward forecasts with these groups and columns added (cached): keys, step,
        mean, q10, q50, q90 and y. `drop_season` leaves one training season out (fitting noise)."""
        key = (tuple(sorted(added)), tuple(extra), seed, drop_season, feats is not None)
        if feats is None and key in self.preds:
            return self.preds[key]
        expert = with_experts(self.base, tuple(sorted(added)), seed, tuple(extra))()
        transform = None
        if drop_season is not None:
            transform = _dropper(drop_season)
        out = backtest.walk(
            expert, self.features if feats is None else feats, self.outcomes, self.steps,
            self.test, REFIT, train_transform=transform,
        ).join(self.outcomes.select(*self.keys, "y"), on=self.keys, how="inner")  # fmt: skip
        out = out.with_columns(season=c("step").replace_strict(self._seasons()))
        if feats is None:
            self.preds[key] = out
        return out

    def _seasons(self) -> dict[int, int]:
        return {s.index: s.season for s in self.steps}


def _dropper(season: int) -> Callable[[pl.DataFrame], pl.DataFrame]:
    return lambda pool: pool.filter(c("step_season") != season)


def shuffled_columns(base: type[Crude]) -> list[str]:
    """The shuffled copy's columns: participation's for players, Elo's for teams."""
    groups = base.expert_groups()
    source = "participation" if "participation" in groups else "elo"
    return [f"shuffled_{col}" for col in groups[source]]


def with_shuffled(feats: pl.DataFrame, base: type[Crude], seed: int) -> pl.DataFrame:
    """The features plus the shuffled copy: one expert's columns, shuffled together within each
    week, so they keep their spread and lose their link to the rows."""
    cols = [col.removeprefix("shuffled_") for col in shuffled_columns(base)]
    order = feats.select("step").with_columns(
        row=pl.int_range(pl.len()), r=pl.int_range(pl.len()).shuffle(seed=seed).over("step")
    )
    # the row at each position takes the values of another row of the same week
    perm = order.sort("step", "row")["row"].to_numpy()
    shuffled_rows = order.sort("step", "r")["row"].to_numpy()
    source = feats.select(cols).to_numpy()
    values = np.empty_like(source)
    values[perm] = source[shuffled_rows]
    return feats.with_columns(
        pl.Series(f"shuffled_{col}", values[:, i]) for i, col in enumerate(cols)
    )


# ---------------------------------------------------------------- building and caching a board
def board_path(target: str, horizon: str) -> Path:
    return get_config().zone("outputs") / "crude-forecaster" / "boards" / f"{target}_{horizon}"


def build_board(
    target: str,
    horizon: str = "next",
    method: str = "lasso",
    gateway: Gateway | None = None,
    seasons: Sequence[int] = range(2019, 2025),
    save: bool = True,
) -> Board:
    """The crude forecast's feature history through the gateway (every expert's columns
    included), its outcomes and the shuffled copy; saved so later scorers start in seconds."""
    base = variant(target, horizon, method)
    gateway = gateway or Gateway()
    first = base.first_train or get_config().seasons.first_train
    every = backtest.steps(gateway.calendar, base.cadence, range(first, max(seasons) + 1), base.run)
    test = [s.index for s in every if s.season in set(seasons)]
    feats = backtest.feature_history(base(), gateway, every)
    outcomes = backtest.targets(base(), gateway)
    feats = with_shuffled(feats, base, get_config().seed)
    if save:
        path = board_path(target, horizon)
        path.mkdir(parents=True, exist_ok=True)
        feats.write_parquet(path / "features.parquet")
        outcomes.write_parquet(path / "outcomes.parquet")
    return Board(base, feats, outcomes, every, test)


def load_board(
    target: str, horizon: str = "next", method: str = "lasso", gateway: Gateway | None = None
) -> Board:
    """A saved board (built by `build_board`), with its steps rebuilt from the calendar."""
    base = variant(target, horizon, method)
    path = board_path(target, horizon)
    feats = pl.read_parquet(path / "features.parquet")
    outcomes = pl.read_parquet(path / "outcomes.parquet")
    gateway = gateway or Gateway()
    seasons = sorted(feats["step_season"].unique().to_list())
    every = backtest.steps(gateway.calendar, base.cadence, range(seasons[0], seasons[-1] + 1),
                           base.run)  # fmt: skip
    test = [s.index for s in every if s.season >= 2019 and s.season <= 2024]
    return Board(base, feats, outcomes, every, test)


# ---------------------------------------------------------------- scoring
def _weekly(new: pl.DataFrame, base: pl.DataFrame, keys: list[str], rows: pl.DataFrame | None):
    """Per week: the squared errors and range scores of both forecasts on the rows both have."""
    a = new.select(*keys, "step", "season", "y", mean_a="mean", q10="q10", q50="q50", q90="q90")
    a = a.with_columns(range_a=mean_pinball())
    b = base.select(*keys, mean_b="mean", q10="q10", q50="q50", q90="q90", y="y")
    b = b.with_columns(range_b=mean_pinball()).drop("q10", "q50", "q90", "y")
    d = a.join(b, on=keys, how="inner")
    if rows is not None:
        d = d.join(rows, on=keys, how="semi")
    return (
        d.group_by("step", "season")
        .agg(
            se_a=((c("mean_a") - c("y")) ** 2).sum(),
            se_b=((c("mean_b") - c("y")) ** 2).sum(),
            rs_a=c("range_a").sum(),
            rs_b=c("range_b").sum(),
            n=pl.len(),
        )
        .sort("step")
    )


def _draws(n_blocks: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.multinomial(n_blocks, np.full(n_blocks, 1 / n_blocks), size=DRAWS)


def _interval(num: np.ndarray, den: np.ndarray, draws: np.ndarray) -> tuple[float, float, float]:
    """num.sum() / den.sum() with a 90% interval from resampled weeks."""
    boot = (draws @ num) / (draws @ den)
    lo, hi = np.quantile(boot, [(1 - LEVEL) / 2, (1 + LEVEL) / 2])
    return float(num.sum() / den.sum()), float(lo), float(hi)


@dataclass(frozen=True)
class Gain:
    """Share of the base forecast's squared error removed (positive is better), and the change
    in range score as a share of the base's (positive is better), each with its 90% interval."""

    share: float
    lo: float
    hi: float
    range_share: float
    range_lo: float
    range_hi: float
    rows: int
    weeks: int

    @property
    def verdict(self) -> str:
        """VALIDATION.md §5 on the range score: adds value, neutral, or adds noise."""
        if self.range_lo > 0:
            return "adds value"
        if self.range_hi < 0:
            return "adds noise"
        return "neutral"


def gain(
    new: pl.DataFrame,
    base: pl.DataFrame,
    keys: list[str],
    rows: pl.DataFrame | None = None,
    seed: int | None = None,
) -> Gain:
    """What `new` adds over `base`, paired on the same rows and resampled by whole weeks."""
    w = _weekly(new, base, keys, rows)
    draws = _draws(w.height, get_config().seed if seed is None else seed)
    se_a, se_b = w["se_a"].to_numpy(), w["se_b"].to_numpy()
    rs_a, rs_b = w["rs_a"].to_numpy(), w["rs_b"].to_numpy()
    share = _interval(se_b - se_a, se_b, draws)
    rng = _interval(rs_b - rs_a, rs_b, draws)
    return Gain(*share, *rng, int(w["n"].sum()), w.height)


def removed(pred: pl.DataFrame, rows: pl.DataFrame | None = None, keys=None) -> float:
    """Share of squared error around the scored rows' average that a forecast removes (the
    exploration's headline unit)."""
    d = pred if rows is None else pred.join(rows, on=keys, how="semi")
    y, m = d["y"].to_numpy(), d["mean"].to_numpy()
    return float(1 - ((m - y) ** 2).sum() / ((y - y.mean()) ** 2).sum())


def shapley(
    board: Board,
    members: Mapping[str, tuple[tuple[str, ...], tuple[str, ...]]] | None = None,
    rows: pl.DataFrame | None = None,
    steps: Sequence[int] | None = None,
    seed: int | None = None,
) -> pl.DataFrame:
    """Methods A and C for every member: added alone, and its fair share over every order, both
    as shares of the crude forecast's squared error, with 90% intervals. Also the all-members
    gain (the shares add up to it). `steps` limits the scoring to some weeks (the halves)."""
    members = dict(members or board.members())
    names = list(members)
    n = len(names)

    def pred(subset: frozenset) -> pl.DataFrame:
        added = tuple(g for m in sorted(subset) for g in members[m][0])
        extra = tuple(col for m in sorted(subset) for col in members[m][1])
        p = board.forecast(added, extra)
        return p if steps is None else p.filter(c("step").is_in(list(steps)))

    keys = board.keys
    crude = pred(frozenset())
    # squared error per week of every subset, on the same rows
    weekly = {}
    for r in range(n + 1):
        for combo in itertools.combinations(names, r):
            s = frozenset(combo)
            weekly[s] = _weekly(pred(s), crude, keys, rows)
        log.info("%s: subsets of size %d done", board.base.variant, r)
    base_se = weekly[frozenset()]["se_b"].to_numpy()
    draws = _draws(len(base_se), get_config().seed if seed is None else seed)
    out = []
    every = frozenset(names)
    total = _interval(base_se - weekly[every]["se_a"].to_numpy(), base_se, draws)
    for i in names:
        diff = np.zeros_like(base_se)
        for r in range(n):
            for combo in itertools.combinations([x for x in names if x != i], r):
                w = math.factorial(r) * math.factorial(n - r - 1) / math.factorial(n)
                s = frozenset(combo)
                diff += w * (weekly[s]["se_a"].to_numpy() - weekly[s | {i}]["se_a"].to_numpy())
        alone = gain(pred(frozenset({i})), crude, keys, rows, seed)
        share = _interval(diff, base_se, draws)
        out.append({
            "member": i, "alone": alone.share, "alone_lo": alone.lo, "alone_hi": alone.hi,
            "share": share[0], "share_lo": share[1], "share_hi": share[2],
            "range_alone": alone.range_share, "range_lo": alone.range_lo,
            "range_hi": alone.range_hi, "verdict": alone.verdict,
        })  # fmt: skip
    table = pl.DataFrame(out).with_columns(
        all_members=pl.lit(total[0]), all_lo=pl.lit(total[1]), all_hi=pl.lit(total[2]),
        rows=pl.lit(int(weekly[every]["n"].sum())),
    )  # fmt: skip
    return table


def noise(board: Board, members: Sequence[str] | None = None, seeds: Sequence[int] = (1, 2, 3),
          ) -> pl.DataFrame:  # fmt: skip
    """The yardstick's own fitting noise: each member's added-alone gain (and all of them) when
    the trees' seed changes and when one early training season is left out. Returns one row per
    member and refit."""
    mem = board.members()
    names = list(members or mem)
    refits: list[dict] = [{"seed": None, "drop": None}]
    if board.base.method in ("trees", "mix"):
        refits += [{"seed": s, "drop": None} for s in seeds]
    refits += [{"seed": None, "drop": s} for s in FIRST_HALF[:0] or (2016, 2017, 2018)]
    out = []
    for rf in refits:
        crude = board.forecast(seed=rf["seed"], drop_season=rf["drop"])
        for name in [*names, "all"]:
            sel = names if name == "all" else [name]
            added = tuple(g for m in sel for g in mem[m][0])
            extra = tuple(col for m in sel for col in mem[m][1])
            p = board.forecast(added, extra, seed=rf["seed"], drop_season=rf["drop"])
            g = gain(p, crude, board.keys)
            out.append({"member": name, "seed": rf["seed"], "drop_season": rf["drop"],
                        "alone": g.share, "range_alone": g.range_share,
                        "crude_removes": removed(crude)})  # fmt: skip
    return pl.DataFrame(out)


# ---------------------------------------------------------------- one call for a new input
def history_columns(
    board: Board, key: str, version: int, columns: Mapping[str, str], gateway: Gateway | None = None
) -> pl.DataFrame:
    """A saved walk-forward history's columns lined up to the board's rows (rule e): each row
    takes the latest output made by its own moment (`as_of` ≤ the row's), and none made by a
    model trained after it (check 6). `columns`: history column → new name. `key` is a registry
    id or `<id>/<variant>`, pinned like any input (decision 0037)."""
    gateway = gateway or Gateway()
    view = gateway.view(END_OF_TIME, board.base.cadence, {key: version})
    hist = view.output(key)
    on = [k for k in board.keys if k in hist.columns]
    if "game_id" not in on:
        raise ValueError(f"{key}: a history needs game_id to line up with the board's rows")
    rows = board.features.select(*board.keys, "as_of", "team")
    if "team" in hist.columns and "team" not in on:
        on = [*on, "team"]
    h = hist.select(*on, "as_of", *columns).rename({"as_of": "h_as_of", **columns})
    joined = rows.join(h, on=on, how="left").filter(
        c("h_as_of").is_null() | (c("h_as_of") <= c("as_of"))
    )
    joined = joined.sort("h_as_of").unique(board.keys, keep="last")
    return joined.select(*board.keys, *columns.values())


def score_input(
    board: Board,
    frame: pl.DataFrame,
    name: str,
    fill: float | None = None,
    rows: pl.DataFrame | None = None,
) -> dict:
    """The one-call scorer: what the new columns in `frame` (the board's keys plus the columns,
    made before each row's moment, e.g. by `history_columns`) add to the crude forecast, alone.
    Missing values get the column's median, or `fill`. Returns the added-alone gain, its range
    score change, both 90% intervals and the no-noise verdict."""
    new_cols = [col for col in frame.columns if col not in board.keys]
    if not new_cols:
        raise ValueError("score_input: the frame has no columns besides the board's keys")
    clash = set(new_cols) & set(board.features.columns)
    if clash:
        raise ValueError(f"score_input: columns {sorted(clash)} are already on the board")
    feats = board.features.join(frame, on=board.keys, how="left").with_columns(
        c(col).fill_null(c(col).median() if fill is None else fill) for col in new_cols
    )
    crude = board.forecast()
    new = board.forecast(extra=new_cols, feats=feats)
    g = gain(new, crude, board.keys, rows)
    return {
        "input": name, "target": board.base.target_spec.name, "horizon": board.base.horizon,
        "method": board.base.method, "alone": g.share, "alone_lo": g.lo, "alone_hi": g.hi,
        "range_alone": g.range_share, "range_lo": g.range_lo, "range_hi": g.range_hi,
        "verdict": g.verdict, "rows": g.rows, "weeks": g.weeks,
        "made": datetime.now(UTC).date().isoformat(),
    }  # fmt: skip


# ---------------------------------------------------------------- SHAP, the explanation
def shap_values(board: Board, added: Sequence[str], extra: Sequence[str] = ()) -> pl.DataFrame:
    """SHAP values on held-out rows (the explanation of where an input helps, never its test):
    each test season's model, fit only on earlier rows, explains that season's forecasts. One
    row per forecast row and input: keys, season, column, shap."""
    from pcf.baselines.crude import fitting

    expert = with_experts(board.base, tuple(sorted(added)), None, tuple(extra))()
    pool = board.features.join(board.outcomes, on=board.keys, how="inner")
    by_index = {s.index: s for s in board.steps}
    seasons = sorted({by_index[i].season for i in board.test})
    out = []
    for season in seasons:
        first = min(i for i in board.test if by_index[i].season == season)
        model, _ = backtest.fit_at(expert, pool, by_index[first].at, season)
        rows = board.features.filter(c("step_season") == season)
        x = rows.select(expert.columns).to_numpy().astype(float)
        contrib = fitting.contributions(model, x, expert.columns)
        frame = pl.DataFrame(contrib, schema=expert.columns).with_columns(rows.select(*board.keys))
        out.append(
            frame.unpivot(index=board.keys, variable_name="column", value_name="shap").with_columns(
                season=pl.lit(season)
            )
        )
    return pl.concat(out)


def group_of(board: Board) -> dict[str, str]:
    """Each input column's group: an expert's name, or `crude`."""
    out = {col: "crude" for col in board.base.crude_columns()}
    for g, cols in board.base.expert_groups().items():
        out |= dict.fromkeys(cols, g)
    return out | dict.fromkeys(shuffled_columns(board.base), SHUFFLED)


def played_rows(gateway: Gateway | None = None) -> pl.DataFrame:
    """The check row set (never the headline: a filter on the outcome): player-games where he took
    an offensive snap or recorded a stat. Keys gsis_id, game_id."""
    gateway = gateway or Gateway()
    pg = gateway.view(END_OF_TIME, "in_season", {"player_game": ("stats", "snaps")}).table(
        "player_game"
    )
    took = c("stats_known_at").is_not_null() | (c("offense_snaps").fill_null(0) > 0)
    return pg.filter(took).select("gsis_id", "game_id")


def allowed(history: pl.DataFrame, gateway: Gateway | None = None) -> pl.DataFrame:
    """Team yards allowed: the yards-gained forecast filed under the defense (the same number,
    seen from the other side; the exploration's F2). Keys game_id, team (the defense)."""
    gateway = gateway or Gateway()
    sched = gateway.view(END_OF_TIME, "in_season", {"team_game": ("schedule",)}).table("team_game")
    return (
        history.join(sched.select("game_id", "team", "opponent"), on=["game_id", "team"])
        .with_columns(team=c("opponent"), quantity=c("quantity").str.replace("gained", "allowed"))
        .drop("opponent")
    )


__all__ = [
    "F", "Board", "Gain", "allowed", "build_board", "gain", "group_of", "history_columns",
    "load_board", "noise", "played_rows", "removed", "score_input", "shap_values", "shapley",
]  # fmt: skip
