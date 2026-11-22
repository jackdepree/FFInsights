"""The forecast's checks after the harness (decision 0041), all walked on the saved feature history
of a validated run, so nothing is recomputed and every row is predicted by a model fit only on
earlier rows (`pcf.validation.backtest.walk`).

- `no_noise`: the brief's no-noise target, next game's PPR points on targets and carries, from a
  lasso on past points, targets, carries and snaps (and position), with and without the expert's
  forecast (its walk-forward history: rule e). Scored 2019-2024, trained from 2016.
- `kinds`: the kinds of chance beyond the counts (exploration F4, rechecked on the 2009-start
  model): goal-line carries, red-zone, end-zone and deep targets, air yards, expected touchdowns,
  on next game's points and on next game's expected points (H56's "pays?").
- `ladder`: the trees rung on `eff`'s inputs, and the expected-yards variants for the yardstick,
  each with a 20-shuffle signal test.
- `yardstick`: the forecasts scored on the crude forecaster's receiving and rushing boards.
- `fitting_noise`: the main gains again with one training season left out (2016, 2017, 2018) and,
  for trees, other seeds: how much a gain moves when nothing real changed.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np
import polars as pl

from pcf.baselines.crude import yardstick as Y
from pcf.config import get_config
from pcf.data.gateway import END_OF_TIME, Gateway
from pcf.experts.opportunity_quality import features as F
from pcf.experts.opportunity_quality import model as M
from pcf.experts.opportunity_quality.common import known_games
from pcf.experts.opportunity_quality.horizons import HORIZONS, REST, _Horizon
from pcf.validation import backtest
from pcf.validation.nulls import no_noise as no_noise_verdict
from pcf.validation.scores import row_losses

c = pl.col
KEYS = ["gsis_id", "game_id"]
SCORED = list(range(2019, 2025))  # the brief's scored seasons, and the yardstick's
TRAIN_FROM = 2016  # the first season with the expert's walk-forward history
DROPS = (2016, 2017, 2018)
SEEDS = (1, 2)
SHUFFLES = 20
BASE = [*F.lagged("fp", "targets", "carries", "snaps"), "is_wr", "is_te", "games_played"]
KINDS = F.lagged("gl", "rz", "ez", "deep", "air", "xtd")
FORECAST = ["oq_mean", "oq_p"]


# ---------------------------------------------------------------- saved inputs
def cache_dir() -> Path:
    path = get_config().zone("interim") / "opportunity_quality"
    path.mkdir(parents=True, exist_ok=True)
    return path


def saved_dir(variant: str = "eff", tag: str = "") -> Path:
    """Where `run forecast` saves a validated run's feature history and outcomes."""
    return cache_dir() / f"saved_{variant}{'_' + tag if tag else ''}"


def outcomes(column: str, scoring: str = "ppr") -> pl.DataFrame:
    """Every known player-game's `column` of `known_games` as an outcome (keys, y, known_at)."""
    view = Gateway().view(END_OF_TIME, "in_season", F.INPUTS)
    pg = view.table("player_game")
    return known_games(pg, scoring).select(*KEYS, y=column, known_at="known_at")


# ---------------------------------------------------------------- the walk
def walk_saved(
    expert,
    feats: pl.DataFrame,
    outs: pl.DataFrame,
    seasons: Sequence[int],
    first: int,
    transform: Callable[[pl.DataFrame], pl.DataFrame] | None = None,
) -> pl.DataFrame:
    """`expert` walked on saved features, testing `seasons`. `first` is the season the saved run's
    steps start at (its step numbers count from there). Returns the scored rows."""
    every = backtest.steps(Gateway().calendar, expert.cadence, range(first, max(seasons) + 1),
                           expert.run)  # fmt: skip
    test = [s.index for s in every if s.season in set(seasons)]
    pred = backtest.walk(expert, feats, outs, every, test, "season", backtest.HALF_LIFE,
                         train_transform=transform)  # fmt: skip
    season = {s.index: s.season for s in every}
    pred = pred.join(outs.select(*KEYS, "y"), on=KEYS, how="inner")
    return row_losses(pred, expert.kind).with_columns(season=c("step").replace_strict(season))


def plain(name: str, columns: list[str]) -> _Horizon:
    """A lasso with ranges from its latest misses by position and size (the horizons' model), on
    `columns`: the downstream models here."""
    attrs = {"variant": f"downstream_{name}", "horizon": 1, "columns": columns,
             "__module__": __name__}  # fmt: skip
    return type(f"Downstream_{name}", (_Horizon,), attrs)()


def two_part(name: str, columns: list[str], method: str = "lasso", outcome: str = "xfp"):
    attrs = {"variant": f"downstream_{name}", "columns": columns, "method": method,
             "outcome": outcome, "__module__": __name__}  # fmt: skip
    return type(f"Downstream_{name}", (M._TwoPart,), attrs)()


def _drop(season: int) -> Callable[[pl.DataFrame], pl.DataFrame]:
    return lambda pool: pool.filter(c("step_season") != season)


def _shuffled(seed: int) -> Callable[[pl.DataFrame], pl.DataFrame]:
    return lambda pool: backtest.shuffle_within_steps(pool, seed)


def gain_line(label: str, new: pl.DataFrame, base: pl.DataFrame) -> tuple[str, Y.Gain]:
    g = Y.gain(new, base, KEYS)
    return (
        f"  {label:<46} {100 * g.share:+6.2f}% of squared error ({100 * g.lo:+.2f} to "
        f"{100 * g.hi:+.2f}); range score {100 * g.range_share:+.2f}% ({100 * g.range_lo:+.2f} "
        f"to {100 * g.range_hi:+.2f}): {g.verdict}; {g.rows} rows",
        g,
    )


def _with_forecast(feats: pl.DataFrame, hist: pl.DataFrame) -> pl.DataFrame:
    """The saved features with the expert's walk-forward forecast for the same row (made at the
    same moment, by a model fit before it), from `TRAIN_FROM` on."""
    h = hist.select(*KEYS, oq_mean="mean", oq_p="p_nonzero", h_as_of="as_of")
    out = feats.filter(c("step_season") >= TRAIN_FROM).join(h, on=KEYS, how="inner")
    bad = out.filter(c("h_as_of") > c("as_of")).height
    if bad:
        raise ValueError(f"{bad} rows have a forecast made after their own moment")
    return out.drop("h_as_of")


# ---------------------------------------------------------------- the checks
def no_noise(feats: pl.DataFrame, hist: pl.DataFrame, first: int) -> tuple[list[str], dict]:
    """Next game's points on targets and carries, with and without the expert's forecast."""
    pts = outcomes("fp")
    rows = _with_forecast(feats, hist)
    without = walk_saved(plain("base", BASE), rows, pts, SCORED, first)
    with_ = walk_saved(plain("with", [*BASE, *FORECAST]), rows, pts, SCORED, first)
    with_xfp = walk_saved(plain("xfp", [*BASE, *F.lagged("xfp")]), rows, pts, SCORED, first)
    # The brief's baseline has no playing-time inputs; this pair gives both sides participation's
    playing = walk_saved(plain("playing", [*BASE, *F.PLAYING]), rows, pts, SCORED, first)
    with_playing = walk_saved(plain("with_playing", [*BASE, *F.PLAYING, *FORECAST]), rows, pts,
                              SCORED, first)  # fmt: skip
    verdict, comp = no_noise_verdict(with_, without, KEYS)
    out = ["No-noise target: next game's PPR points on targets and carries, 2019-2024 (trained "
           "from 2016)"]  # fmt: skip
    added = {"+ the forecast (mean, chance of a chance)": with_,
             "+ past expected points only (the exploration's -0.19%)": with_xfp}  # fmt: skip
    for label, new in added.items():
        out.append(gain_line(label, new, without)[0])
    out.append(gain_line("+ playing time (participation's inputs) only", playing, without)[0])
    out.append(gain_line("+ the forecast, beside playing time", with_playing, playing)[0])
    out.append(f"  verdict (VALIDATION §5, range score per row): {verdict}; {comp}")
    by_pos = []
    for pos in ("RB", "WR", "TE"):
        keep = rows.filter(c("position") == pos).select(KEYS)
        g = Y.gain(with_, without, KEYS, keep)
        by_pos.append(f"{pos} {100 * g.share:+.2f}% ({100 * g.lo:+.2f} to {100 * g.hi:+.2f})")
    out.append("  by position: " + "; ".join(by_pos))
    fair, _ = no_noise_verdict(with_playing, playing, KEYS)
    out.append(f"  verdict beside playing time: {fair}")
    return out, {"with": with_, "without": without, "rows": rows, "pts": pts}


def kinds(feats: pl.DataFrame, nn: dict, first: int) -> list[str]:
    """The kinds of chance beyond the counts, on next game's points and expected points."""
    rows, pts = nn["rows"], nn["pts"]
    base = walk_saved(plain("counts", BASE), rows, pts, SCORED, first)
    k = walk_saved(plain("kinds", [*BASE, *KINDS]), rows, pts, SCORED, first)
    with_k = walk_saved(plain("with_kinds", [*BASE, *FORECAST, *KINDS]), rows, pts, SCORED, first)
    xfp = outcomes("xfp")
    eff = walk_saved(M.Eff(), feats, xfp, SCORED, first)
    goal = walk_saved(two_part("goal", F.GOAL_LINE), feats, xfp, SCORED, first)
    out = ["Kinds of chance beyond the counts (goal-line carries, red-zone, end-zone and deep "
           "targets, air yards, expected TDs), 2019-2024"]  # fmt: skip
    out.append(gain_line("next game's points: counts + kinds vs counts", k, base)[0])
    out.append(gain_line("next game's points: + forecast + kinds vs + forecast", with_k,
                         nn["with"])[0])  # fmt: skip
    out.append(gain_line("next game's expected points: eff + kinds vs eff", goal, eff)[0])
    return out


def ladder(feats: pl.DataFrame, first: int) -> tuple[list[str], dict]:
    """Trees on `eff`'s inputs; the expected-yards variants; each with its signal test."""
    out = ["The ladder and the yards variants, 2016-2024 (the validated seasons)"]
    seasons = list(range(2016, 2025))
    walks = {}
    xfp = outcomes("xfp")
    eff = walk_saved(M.Eff(), feats, xfp, seasons, first)
    walks["eff"] = eff
    trees = walk_saved(M.EffTrees(), feats, xfp, seasons, first)
    walks["eff_trees"] = trees
    out.append(gain_line("trees on eff's inputs vs eff (lasso)", trees, eff)[0])
    for cls, column in ((M.EffRecYards, "xrec"), (M.EffRushYards, "xrush")):
        outs = outcomes(column)
        real = walk_saved(cls(), feats, outs, seasons, first)
        walks[cls.variant] = real
        mean = real["loss"].mean()
        nulls = [walk_saved(cls(), feats, outs, seasons, first, _shuffled(s))["loss"].mean()
                 for s in range(SHUFFLES)]  # fmt: skip
        beaten = int(np.sum(np.array(nulls) > mean))
        out.append(f"  {cls.variant:<16} range score {mean:.3f} expected yards; shuffled "
                   f"refits {min(nulls):.3f} to {max(nulls):.3f}: beats {beaten} of {SHUFFLES} "
                   f"(needs {SHUFFLES}); MAE {real['readable'].mean():.2f} yards")  # fmt: skip
    return out, walks


def _aligned(board: Y.Board, preds: dict[str, pl.DataFrame]) -> pl.DataFrame:
    """The board's rows with each forecast made by their own moment (rule e, check 6)."""
    rows = board.features.select(*KEYS, "as_of")
    for prefix, p in preds.items():
        cols = {"mean": f"{prefix}_mean"} | ({"p_nonzero": f"{prefix}_p"} if prefix == "oq" else {})
        h = p.select(*KEYS, *cols, h_as_of="as_of").rename(cols)
        rows = (
            rows.join(h, on=KEYS, how="left")
            .with_columns(
                pl.when(c("h_as_of") <= c("as_of")).then(c(v)).alias(v) for v in cols.values()
            )
            .drop("h_as_of")
        )
    return rows.drop("as_of")


def yardstick(hist: pl.DataFrame, walks: dict) -> list[str]:
    out = ["The yardstick (crude-forecaster): what each forecast adds to the crude forecast of "
           "next game's yards, alone, 2019-2024; missing (QBs, no forecast) = 0"]  # fmt: skip
    for target, yards in (("receiving", "eff_rec_yards"), ("rushing", "eff_rush_yards")):
        board = Y.load_board(target, "next")
        frame = _aligned(board, {"oq": hist, "oy": walks[yards]})
        for name, cols in (("expected points forecast", ["oq_mean", "oq_p"]),
                           (f"expected {target} yards forecast", ["oy_mean"]),
                           ("both", ["oq_mean", "oq_p", "oy_mean"])):  # fmt: skip
            r = Y.score_input(board, frame.select(*KEYS, *cols), name, fill=0.0)
            out.append(f"  {target:<9} {name:<32} {100 * r['alone']:+.2f}% "
                       f"({100 * r['alone_lo']:+.2f} to {100 * r['alone_hi']:+.2f}); range "
                       f"{100 * r['range_alone']:+.2f}%: {r['verdict']}; "
                       f"{r['rows']} rows")  # fmt: skip
    return out


def fitting_noise(feats: pl.DataFrame, nn: dict, first: int) -> list[str]:
    """The main gains with one training season left out, and trees with other seeds."""
    xfp = outcomes("xfp")
    out = ["Fitting noise: each gain, 2019-2024, with one training season left out (nothing real "
           "changes)"]  # fmt: skip
    pairs = {
        "eff vs xfp (H61: efficiency earns work)": (M.Eff, M.Xfp),
        "eff vs counts": (M.Eff, M.Counts),
        "xfp vs counts": (M.Xfp, M.Counts),
    }
    for label, (a, b) in pairs.items():
        shares = []
        for d in (None, *DROPS):
            t = None if d is None else _drop(d)
            new = walk_saved(a(), feats, xfp, SCORED, first, t)
            old = walk_saved(b(), feats, xfp, SCORED, first, t)
            shares.append(100 * Y.gain(new, old, KEYS).share)
        out.append(f"  {label:<40} all {shares[0]:+.2f}%; without 2016/17/18 "
                   + ", ".join(f"{s:+.2f}" for s in shares[1:])
                   + f" (spread {max(shares) - min(shares):.2f})")  # fmt: skip
    shares = []
    rows, pts = nn["rows"], nn["pts"]
    for d in (None, *DROPS):
        t = None if d is None else _drop(d)
        new = walk_saved(plain("with", [*BASE, *FORECAST]), rows, pts, SCORED, first, t)
        old = walk_saved(plain("base", BASE), rows, pts, SCORED, first, t)
        shares.append(100 * Y.gain(new, old, KEYS).share)
    out.append(f"  {'no-noise: with vs without the forecast':<40} all {shares[0]:+.2f}%; without "
               + ", ".join(f"{s:+.2f}" for s in shares[1:])
               + f" (spread {max(shares) - min(shares):.2f})")  # fmt: skip
    eff = walk_saved(M.Eff(), feats, xfp, SCORED, first)
    seeds = []
    old = dict(M.TREES)
    try:
        for s in (0, *SEEDS):
            M.TREES["random_state"] = s
            seeds.append(100 * Y.gain(walk_saved(M.EffTrees(), feats, xfp, SCORED, first), eff,
                                      KEYS).share)  # fmt: skip
    finally:
        M.TREES.clear()
        M.TREES.update(old)
    out.append(f"  {'trees vs lasso, seeds 0/1/2':<40} " + ", ".join(f"{s:+.2f}" for s in seeds))
    return out


def horizon_points(horizon: int | None) -> pl.DataFrame:
    """A window's average PPR points per game on targets and carries, as outcomes."""
    attrs = {"variant": "downstream_points", "horizon": horizon, "outcome": "fp",
             "columns": BASE, "__module__": __name__}  # fmt: skip
    return backtest.targets(type("Downstream_points", (_Horizon,), attrs)(), Gateway())


def horizons_check() -> list[str]:
    """The kinds of chance beyond the counts at the longer horizons (the brief's plan, step 6), on
    each horizon's saved features: on expected points per game (goal_* against eff_*) and on actual
    points per game (counts against counts + kinds, and both beside playing time)."""
    out = ["Kinds of chance beyond the counts at the longer horizons, 2016-2024"]
    seasons = list(range(2016, 2025))
    for tag, h in (("h3", 3), ("rest", REST)):
        feats, outs = backtest.load_features(saved_dir(f"eff_{tag}"))
        first = int(feats["step_season"].min())
        eff = walk_saved(HORIZONS[f"eff_{tag}"](), feats, outs, seasons, first)
        goal = walk_saved(HORIZONS[f"goal_{tag}"](), feats, outs, seasons, first)
        out.append(gain_line(f"{tag}: expected points, goal_{tag} vs eff_{tag}", goal, eff)[0])
        pts = horizon_points(h)
        base = walk_saved(plain("h_counts", BASE), feats, pts, seasons, first)
        kinds_ = walk_saved(plain("h_kinds", [*BASE, *KINDS]), feats, pts, seasons, first)
        out.append(gain_line(f"{tag}: points, counts + kinds vs counts", kinds_, base)[0])
        both = [*BASE, *F.PLAYING]
        play = walk_saved(plain("h_play", both), feats, pts, seasons, first)
        play_k = walk_saved(plain("h_play_kinds", [*both, *KINDS]), feats, pts, seasons, first)
        out.append(gain_line(f"{tag}: points, beside playing time", play_k, play)[0])
    return out


def run_all(variant: str = "eff") -> tuple[list[str], dict]:
    feats, _ = backtest.load_features(saved_dir(variant))
    first = int(feats["step_season"].min())
    hist, run_id = backtest.latest_history(M._Base.id, variant)
    lines = [f"Downstream checks on {variant} run {run_id} (saved features: {feats.height} rows)",
             ""]  # fmt: skip
    nn_lines, nn = no_noise(feats, hist, first)
    lines += nn_lines + [""] + kinds(feats, nn, first) + [""]
    ladder_lines, walks = ladder(feats, first)
    lines += ladder_lines + [""] + yardstick(hist, walks) + [""] + fitting_noise(feats, nn, first)
    return lines, walks
