"""H88's test: season priors from context-retro against context-live's, on the crude forecaster's
yards boards (pre-registered in projects/context-retro/BUILD.md; decision 0040).

A season prior is a passer's or an offense's rate over expected on five outcomes the two experts
share (pressure, sack and time to throw per dropback; depth and completion per attempt): the sum
of actual minus expected over the regular season, divided by the plays plus `SHRINK`, so a small
sample is pulled toward 0. Season s's priors go on season s+1's rows, and only once they were
known (their `as_of` at or before the row's).

    python -m pcf.experts.context_retro.priors --tag backtest
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import polars as pl

from pcf.config import get_config
from pcf.core.log import get_logger
from pcf.experts.context_retro import plays
from pcf.experts.context_retro.split import play_parts

log = get_logger(__name__)
c = pl.col
SHRINK = 100  # plays of its own denominator (context-v2's third look)
LIVE_RUN = "b68c042b087948f8b25fbb6a7903105d"  # context-live's back-history, calls16 (0038)
BOARDS = (("passing", "next"), ("passing", "rest"), ("team", "next"), ("team", "rest"))
# outcome: (actual column, plays it's on, context-live's quantity, context-retro's)
SHARED = {
    "pressure": ("pressure_y", "is_dropback", "pressure_prob", "pressure_e0"),
    "sack": ("sack_y", "is_dropback", "sack_prob", "sack_e0"),
    "time_to_throw": ("time_to_throw_y", "is_dropback", "time_to_throw_exp", "time_to_throw_e0"),
    "air_yards": ("air_yards_y", "is_attempt", "air_yards_exp", "air_yards_e0"),
    "completion": ("complete_y", "is_attempt", "completion_prob", "completion_e0"),
}
ARMS = ("plain", "live", "retro", "retro_plus")


def expectations(history: pl.DataFrame, column: dict[str, str]) -> pl.DataFrame:
    """One row per play with each shared outcome's expectation (`<outcome>_exp`) from a
    history (`column`: outcome → its quantity there), and the history's latest `as_of`."""
    want = {q: o for o, q in column.items()}
    h = history.filter(c("quantity").is_in(list(want)))
    wide = h.pivot(on="quantity", index=plays.KEYS, values="mean")
    wide = wide.rename({q: f"{o}_exp" for q, o in want.items() if q in wide.columns})
    when = h.group_by(plays.KEYS).agg(h_as_of=c("as_of").max())
    return wide.join(when, on=plays.KEYS, how="left")


def _shrunk(name: str) -> pl.Expr:
    """The sum over its plays plus SHRINK; missing when it had no plays."""
    n = c(f"{name}_n")
    return pl.when(n > 0).then(c(f"{name}_sum") / (n + SHRINK)).alias(f"{name}_oe")


def season_rates(data: pl.DataFrame, exp: pl.DataFrame | None, unit: str,
                 extra: pl.DataFrame | None = None) -> pl.DataFrame:  # fmt: skip
    """Per unit (`passer_id` or `posteam`) and regular season: each shared outcome's shrunk rate
    over expected (`<outcome>_oe`), with `exp` the expectations (None: the league's season average,
    the plain arm), and `known` (the latest as_of of its rows). `extra`: per-play columns to add
    as shrunk sums per dropback (the split's parts)."""
    d = data.filter(c("season_type") == "REG")
    if exp is None:
        d = d.with_columns(
            [c(y).mean().over("season", c(on)).alias(f"{o}_exp") for o, (y, on, _, _) in
             SHARED.items()], h_as_of=c("as_of"))  # fmt: skip
    else:
        d = d.join(exp, on=plays.KEYS, how="left")
        d = d.with_columns([pl.lit(None, pl.Float64).alias(f"{o}_exp") for o in SHARED
                            if f"{o}_exp" not in d.columns])  # fmt: skip
    aggs, outs = [], []
    for o, (y, on, _, _) in SHARED.items():
        ok = c(on) & c(y).is_not_null() & c(f"{o}_exp").is_not_null()
        aggs += [(c(y) - c(f"{o}_exp")).filter(ok).sum().alias(f"{o}_sum"),
                 ok.sum().alias(f"{o}_n")]  # fmt: skip
        outs.append(_shrunk(o))
    if extra is not None:
        d = d.join(extra, on=plays.KEYS, how="left")
        for x in [col for col in extra.columns if col not in plays.KEYS]:
            aggs += [c(x).sum().alias(f"{x}_sum"), c(x).is_not_null().sum().alias(f"{x}_n")]
            outs.append(_shrunk(x))
    g = d.drop_nulls(unit).group_by(unit, "season").agg(*aggs, known=c("h_as_of").max())
    return g.select(unit, "season", "known", *outs)


def attach(features: pl.DataFrame, rates: pl.DataFrame, unit: str, keys: list[str],
           prefix: str) -> pl.DataFrame:  # fmt: skip
    """Last season's rates on each board row (keys + the columns, named `<prefix>_<col>`),
    only where they were known by the row's moment; missing otherwise."""
    cols = [x for x in rates.columns if x.endswith("_oe")]
    board_unit = "gsis_id" if unit == "passer_id" else "team"
    prior = rates.select(c(unit).alias(board_unit), (c("season") + 1).alias("season"), "known",
                         *[c(x).alias(f"{prefix}_{x}") for x in cols])  # fmt: skip
    need = list(dict.fromkeys([*keys, "as_of", "season", board_unit]))
    rows = features.select(need).unique(keys)
    out = rows.join(prior, on=[board_unit, "season"], how="left")
    late = c("known").is_not_null() & (c("known") > c("as_of"))
    out = out.with_columns([pl.when(late).then(None).otherwise(c(f"{prefix}_{x}")).alias(
        f"{prefix}_{x}") for x in cols])  # fmt: skip
    return out.select(*keys, *[f"{prefix}_{x}" for x in cols])


def arm_rates(arm: str, data: pl.DataFrame, retro: pl.DataFrame, live: pl.DataFrame,
              unit: str) -> pl.DataFrame:  # fmt: skip
    if arm == "plain":
        return season_rates(data, None, unit)
    if arm == "live":
        return season_rates(data, expectations(live, {o: v[2] for o, v in SHARED.items()}), unit)
    exp = expectations(retro, {o: v[3] for o, v in SHARED.items()})
    if arm == "retro":
        return season_rates(data, exp, unit)
    parts = play_parts(retro, data).select(*plays.KEYS, "after_part", "pressure_part")
    return season_rates(data, exp, unit, extra=parts)


def run(tag: str = "backtest", boards: Sequence[tuple[str, str]] = BOARDS) -> dict:
    """Every arm on every board: alone against the crude forecast, and retro against live (the
    H88 test), written to projects/context-retro/build/h88.txt."""
    from pcf.baselines.crude import yardstick
    from pcf.experts.context_retro.run import cache_dir, report_dir

    info = json.loads((cache_dir() / tag / "run.json").read_text())
    retro = pl.read_parquet(info["path"])
    live_path = get_config().zone("outputs") / "context-live" / LIVE_RUN / "back_calls16.parquet"
    live = pl.read_parquet(live_path)
    data = plays.load(range(2017, 2025))
    out: dict = {"retro_run": info["run_id"], "live_run": LIVE_RUN, "boards": {}}
    lines = []
    for target, horizon in boards:
        board = yardstick.load_board(target, horizon)
        unit = "passer_id" if target == "passing" else "posteam"
        crude = board.forecast()
        preds, frames = {}, {}
        res: dict = {}
        for arm in ARMS:
            frame = attach(board.features, arm_rates(arm, data, retro, live, unit), unit,
                           board.keys, arm)  # fmt: skip
            frames[arm] = frame
            cols = [x for x in frame.columns if x not in board.keys]
            feats = board.features.join(frame, on=board.keys, how="left").with_columns(
                [c(x).fill_null(0.0) for x in cols])  # fmt: skip
            preds[arm] = board.forecast(extra=cols, feats=feats)
            g = yardstick.gain(preds[arm], crude, board.keys)
            res[arm] = {"alone": g.__dict__, "filled": float(frame.select(
                c(cols[0]).is_not_null().mean()).item())}  # fmt: skip
        for a, b in (("retro", "live"), ("live", "plain"), ("retro", "plain"),
                     ("retro_plus", "retro")):  # fmt: skip
            res[f"{a}_vs_{b}"] = yardstick.gain(preds[a], preds[b], board.keys).__dict__
        res["crude_removes"] = yardstick.removed(crude)
        out["boards"][f"{target}_{horizon}"] = res
        lines.append(
            f"== {target} {horizon} (the crude forecast removes "
            f"{100 * res['crude_removes']:.1f}% of the squared error around the average)"
        )
        for arm in ARMS:
            g = res[arm]["alone"]
            lines.append(f"  {arm:10s} alone over crude: {100 * g['share']:+.2f}% "
                         f"({100 * g['lo']:+.2f} to {100 * g['hi']:+.2f}); range score "
                         f"{100 * g['range_share']:+.2f}% ({100 * g['range_lo']:+.2f} to "
                         f"{100 * g['range_hi']:+.2f}); priors on {100 * res[arm]['filled']:.0f}%"
                         " of rows")  # fmt: skip
        for k in ("retro_vs_live", "live_vs_plain", "retro_vs_plain", "retro_plus_vs_retro"):
            g = res[k]
            lines.append(f"  {k:20s}: {100 * g['share']:+.2f}% of the second's squared error "
                         f"({100 * g['lo']:+.2f} to {100 * g['hi']:+.2f})")  # fmt: skip
        log.info("H88 %s %s done", target, horizon)
    beats = sum(r["retro_vs_live"]["lo"] > 0 for r in out["boards"].values())
    worse = sum(r["retro_vs_live"]["hi"] < 0 for r in out["boards"].values())
    verdict = "held" if beats >= 2 and worse == 0 else ("failed" if beats == 0 else "unclear")
    out["verdict"] = {"beats": beats, "worse": worse, "h88": verdict}
    text = ("H88: context-retro's season priors against context-live's on the crude forecaster "
            f"(retro run {info['run_id']}, live run {LIVE_RUN}; 2019-2024, lasso, walk-forward; "
            "90% intervals from resampled weeks)\n\n" + "\n".join(lines) +
            f"\n\nretro beats live on {beats} of {len(out['boards'])} boards, clearly worse on "
            f"{worse}: H88 {verdict} (the pre-registered rule)\n")  # fmt: skip
    report_dir().mkdir(parents=True, exist_ok=True)
    (report_dir() / "h88.txt").write_text(text, encoding="utf-8")
    return out


def main(argv: Sequence[str] | None = None) -> None:
    import argparse

    ap = argparse.ArgumentParser(prog="python -m pcf.experts.context_retro.priors")
    ap.add_argument("--tag", default="backtest")
    a = ap.parse_args(argv)
    res = run(a.tag)
    print(json.dumps(res["verdict"]))


if __name__ == "__main__":
    main()
