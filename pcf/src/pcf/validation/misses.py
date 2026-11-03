"""Where a model misses (`miss-lenses`): its errors split by a short, dated list of lenses, plus
the few tags that stand out, so every project reports them the same way.

A miss is actual minus projected (`y - mean`): positive means the model was too low. Per lens:
- **bias share:** how much of the squared miss a per-group correction removes, learned on the
  other half of the seasons (even on odd, odd on even) so noise can't flatter a lens;
- **spread share:** the same for the size of the miss;
- **top group:** the group (200+ rows) with the largest average miss, with a 90% interval
  resampled by week.

Lenses known only after the game (snap share, team points) are **diagnostic**: they say what went
differently, never what a model may use. Every report is dated: when it was measured, the lens
list and the scoring method (CEO, 2026-11-03).

    report(scored, lens_frame(gateway.source, seasons))
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

import numpy as np
import polars as pl

from pcf.data.gateway import Source
from pcf.data.tags.catalog import BEFORE, TAGS

c = pl.col
LENS_LIST = "2026-11-03"  # the dated lens list in use (miss-lenses D1, D5)
METHOD = "2026-11-03"  # the dated way lenses are scored (D2)
MIN_ROWS = 200  # the smallest group a top group or a flagged tag may be
MIN_FIT = 30  # the smallest group whose correction is learned for the bias share
MAX_FLAGGED = 5
DRAWS = 1000
LEVEL = 0.90  # the top group's interval
FLAG_LEVEL = 0.99  # a tag stands out only past this: ~20 tags are scanned, so 90% would
# flag about 2 by chance
FILE = "misses.parquet"
KEYS = ["gsis_id", "game_id"]


@dataclass(frozen=True)
class Lens:
    name: str
    when: str  # "before" or "after" the game
    meaning: str
    build: Callable[[pl.DataFrame], pl.Expr]
    needs: tuple[str, ...]  # columns of the lens frame
    positions: tuple[str, ...] | None = None  # only these positions (default: all)


def _bands(x: pl.Expr, cuts: Sequence[float], labels: Sequence[str]) -> pl.Expr:
    out = pl.when(x.is_null()).then(pl.lit(None, pl.String))
    for cut, label in zip(cuts, labels[:-1], strict=True):
        out = out.when(x < cut).then(pl.lit(label))
    return out.otherwise(pl.lit(labels[-1]))


# The fixed lenses for player-game models (miss-lenses D1, list of 2026-11-03)
LENSES: list[Lens] = [
    Lens("position", "before", "the player's position", lambda d: c("position"), ("position",)),
    Lens(
        "depth", "before", "depth-chart rank (1, 2, 3+, unlisted)",
        lambda d: c("depth").clip(1, 3).cast(pl.Int32).cast(pl.String)
        .str.replace("3", "3+").fill_null("unlisted"),
        ("depth",),
    ),
    Lens(
        "week", "before", "week of the season",
        lambda d: _bands(c("week"), [2, 5, 10, 15], ["1", "2-4", "5-9", "10-14", "15+"]),
        ("week",),
    ),
    Lens(
        "snap_share", "after", "share of the offense's snaps played",
        lambda d: _bands(c("offense_pct"), [0.25, 0.5, 0.75], ["<25%", "25-50%", "50-75%", "75%+"]),
        ("offense_pct",),
    ),
    Lens(
        "team_points", "after", "points the player's team scored",
        lambda d: _bands(c("team_points"), [17, 24, 31], ["<17", "17-23", "24-30", "31+"]),
        ("team_points",),
    ),
    Lens(
        "margin", "after", "the team's final margin",
        lambda d: _bands(c("margin"), [-13, 14], ["lost by 14+", "within 13", "won by 14+"]),
        ("margin",),
    ),
    Lens(
        "qb_efficiency", "after", "completed more than expected (QBs)",
        lambda d: c("tag_positive_cpoe_game").cast(pl.String),
        ("tag_positive_cpoe_game",), positions=("QB",),
    ),
]  # fmt: skip
FIXED = {lens.name for lens in LENSES}


def _tag_lenses() -> list[Lens]:
    """Every player-game and team-game tag not already a fixed lens: candidates to flag."""
    out = []
    for tag in TAGS:
        if tag.level not in ("player_game", "team_game") or tag.column in FIXED:
            continue
        if tag.column == "tag_positive_cpoe_game":
            continue
        when = "before" if tag.timing in BEFORE else "after"
        out.append(Lens(tag.column, when, tag.meaning, lambda d, col=tag.column: c(col).cast(
            pl.String), (tag.column,)))  # fmt: skip
    return out


def _part(source: Source, table: str, part: str) -> pl.DataFrame | None:
    try:
        return source.part(table, part)
    except FileNotFoundError:
        return None


def lens_frame(source: Source, seasons: Sequence[int] | None = None) -> pl.DataFrame:
    """One row per player-game with every lens's inputs that the source has. It's read after
    the fact, for diagnosis: never pass it to a model."""
    roster = source.part("player_game", "roster")
    if seasons is not None:
        roster = roster.filter(c("season").is_in(list(seasons)))
    df = roster.select(*KEYS, "season", "week", "team", "position")
    for part, cols in [
        ("depth", ["depth"]),
        ("snaps", ["offense_pct"]),
        ("tags", None),
        ("tags_result", None),
    ]:
        p = _part(source, "player_game", part)
        if p is None:
            continue
        keep = cols or [x for x in p.columns if x.startswith("tag_")]
        df = df.join(p.select(*KEYS, *[x for x in keep if x in p.columns]), on=KEYS, how="left")
    for part in ("tags", "tags_result"):
        p = _part(source, "team_game", part)
        if p is not None:
            tags = [x for x in p.columns if x.startswith("tag_")]
            df = df.join(p.select("game_id", "team", *tags), on=["game_id", "team"], how="left")
    result = _part(source, "game", "result")
    if result is not None and {"home_score", "away_score"} <= set(result.columns):
        sched = source.part("game", "schedule").select("game_id", "home_team")
        g = result.select("game_id", "home_score", "away_score").join(sched, on="game_id")
        df = df.join(g, on="game_id", how="left")
        home = c("team") == c("home_team")
        df = df.with_columns(
            team_points=pl.when(home).then(c("home_score")).otherwise(c("away_score")),
            margin=pl.when(home)
            .then(c("home_score") - c("away_score"))
            .otherwise(c("away_score") - c("home_score")),
        ).drop("home_team", "home_score", "away_score")
    return df


@dataclass
class Misses:
    """A miss report: the fixed lenses, the flagged tags, and when and how it was measured."""

    lenses: pl.DataFrame
    flagged: pl.DataFrame
    rows: int
    seasons: list[int]
    skipped: list[str]
    measured_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    lens_list: str = LENS_LIST
    method: str = METHOD

    def frame(self, run_id: str | None = None) -> pl.DataFrame:
        """Both tables in one, stamped with the dates and the run (saved as misses.parquet)."""
        both = pl.concat(
            [self.lenses.with_columns(kind=pl.lit("fixed")),
             self.flagged.with_columns(kind=pl.lit("flagged"))],
            how="vertical_relaxed",
        )  # fmt: skip
        return both.with_columns(
            measured_at=pl.lit(self.measured_at),
            lens_list=pl.lit(self.lens_list),
            method=pl.lit(self.method),
            run_id=pl.lit(run_id, pl.String),
        )


def _crossfit_share(d: pl.DataFrame, col: str) -> float | None:
    """The share of `col`'s squared deviation (from its position-and-half mean) that group means
    learned on the other half of the seasons remove. None with only one half."""
    d = d.with_columns(half=c("season") % 2)
    if d["half"].n_unique() < 2:
        return None
    base = d.with_columns(m0=c(col).mean().over("position", "half"))
    by = ["position", "group"]
    means = (
        base.group_by(*by, "half")
        .agg(g=(c(col) - c("m0")).mean(), n=pl.len())
        .filter(c("n") >= MIN_FIT)
        .with_columns(half=1 - c("half"))
        .drop("n")
    )
    j = base.join(means, on=[*by, "half"], how="left").with_columns(c("g").fill_null(0.0))
    before = ((j[col] - j["m0"]) ** 2).sum()
    if before == 0:
        return None
    return float(1 - ((j[col] - j["m0"] - j["g"]) ** 2).sum() / before)


def _interval(d: pl.DataFrame, rng: np.random.Generator, level: float) -> tuple[float, float]:
    """The interval of the average miss, resampling whole weeks."""
    w = d.group_by("season", "week").agg(s=c("miss").sum(), n=pl.len())
    s, n = w["s"].to_numpy(), w["n"].to_numpy()
    draws = rng.multinomial(len(s), np.full(len(s), 1 / len(s)), size=DRAWS)
    boot = (draws @ s) / (draws @ n)
    tail = (1 - level) / 2
    lo, hi = np.quantile(boot, [tail, 1 - tail])
    return float(lo), float(hi)


def _groups(d: pl.DataFrame, skip: Sequence[str] = ()) -> pl.DataFrame:
    return (
        d.filter(~c("group").is_in(list(skip)))
        .group_by("group")
        .agg(rows=pl.len(), avg_miss=c("miss").mean(), mae=c("miss").abs().mean())
        .filter(c("rows") >= MIN_ROWS)
        .sort(c("avg_miss").abs(), descending=True)
    )


def _score(
    d: pl.DataFrame, lens: Lens, rng: np.random.Generator, skip=(), level: float = LEVEL
) -> dict:
    groups = _groups(d, skip)
    row = {
        "lens": lens.name, "when": lens.when, "meaning": lens.meaning, "rows": d.height,
        "bias_share": _crossfit_share(d, "miss"), "spread_share": _crossfit_share(d, "size"),
        "top_group": None, "top_rows": None, "avg_miss": None, "lo": None, "hi": None,
    }  # fmt: skip
    if not groups.is_empty():
        top = groups.row(0, named=True)
        lo, hi = _interval(d.filter(c("group") == top["group"]), rng, level)
        row |= {"top_group": top["group"], "top_rows": top["rows"], "avg_miss": top["avg_miss"],
                "lo": lo, "hi": hi}  # fmt: skip
    return row


SCHEMA = {
    "lens": pl.String, "when": pl.String, "meaning": pl.String, "rows": pl.Int64,
    "bias_share": pl.Float64, "spread_share": pl.Float64, "top_group": pl.String,
    "top_rows": pl.Int64, "avg_miss": pl.Float64, "lo": pl.Float64, "hi": pl.Float64,
}  # fmt: skip


def report(
    scored: pl.DataFrame,
    frame: pl.DataFrame,
    lenses: Sequence[Lens] = LENSES,
    seed: int = 0,
) -> Misses:
    """`scored`: a player-game history with `y` and `mean`. `frame`: from `lens_frame`. The fixed
    lenses always; then every tag whose largest group (200+ rows) is clearly off on average (the
    99% interval excludes zero), at most 5, largest first. A flagged tag's `avg_miss` is
    measured against the model's average miss at the same positions."""
    rng = np.random.default_rng(seed)
    base = (
        scored.select(*KEYS, "y", "mean")
        .join(frame, on=KEYS, how="inner")
        .with_columns(miss=c("y") - c("mean"))
        .with_columns(size=c("miss").abs())
    )
    fixed, skipped = [], []
    for lens in lenses:
        if not set(lens.needs) <= set(base.columns):
            skipped.append(lens.name)
            continue
        d = base
        if lens.positions:
            d = d.filter(c("position").is_in(list(lens.positions)))
        d = d.with_columns(group=lens.build(d)).drop_nulls("group")
        if d.is_empty():
            skipped.append(lens.name)
            continue
        fixed.append(_score(d, lens, rng))
    # A tag is judged against the model's average miss at the same positions, on the rows it
    # fires on ("false" is everyone else, so it only repeats the model's overall bias).
    flagged = []
    for lens in _tag_lenses():
        if lens.name not in base.columns:
            continue
        d = (
            base.with_columns(group=lens.build(base))
            .drop_nulls("group")
            .with_columns(miss=c("miss") - c("miss").mean().over("position"))
        )
        if d.is_empty() or _groups(d, ["false"]).is_empty():
            continue
        row = _score(d, lens, rng, skip=["false"], level=FLAG_LEVEL)
        if row["lo"] is not None and (row["lo"] > 0 or row["hi"] < 0):
            flagged.append(row)
    flagged = sorted(flagged, key=lambda r: -abs(r["avg_miss"]))[:MAX_FLAGGED]
    return Misses(
        lenses=pl.DataFrame(fixed, schema=SCHEMA),
        flagged=pl.DataFrame(flagged, schema=SCHEMA),
        rows=base.height,
        seasons=sorted(base["season"].unique().to_list()),
        skipped=skipped,
    )  # fmt: skip


def from_history(history: pl.DataFrame, expert, gateway, seed: int = 0) -> Misses:
    """The report for a saved walk-forward history (`outputs/<id>/<variant>/<run_id>/`), with
    the outcomes read again through the expert's own `target`."""
    from pcf.validation.backtest import targets

    y = targets(expert, gateway).select(*expert.keys(), "y")
    return report(history.join(y, on=expert.keys()), lens_frame(gateway.source), seed=seed)


def save(m: Misses, folder, run_id: str | None = None):
    """misses.parquet next to the run's history, stamped with its dates."""
    path = folder / FILE
    m.frame(run_id).write_parquet(path)
    return path
