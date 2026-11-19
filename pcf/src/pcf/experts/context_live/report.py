"""context-live's text report from a backtest's saved frames and results: per outcome the rungs'
shares, what ships and why, the nulls, calibration by tenth and range coverage (decision 0036).

    python -m pcf.experts.context_live.report <tag>   # writes projects/context-live/build/<tag>.txt
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence

import numpy as np
import polars as pl

from pcf.experts.context_live import run
from pcf.experts.context_live.outcomes import OUTCOMES
from pcf.validation import calibration
from pcf.validation import sanity as shared_sanity

c = pl.col


def deciles(frame: pl.DataFrame, rung: str) -> pl.DataFrame:
    """Calibration by tenth of the forecast (the brief's "calibrated by tenth"): rows, mean
    forecast and actual rate in each tenth."""
    p = frame[f"{rung}:mean"]
    cuts = np.quantile(p.to_numpy(), np.linspace(0.1, 0.9, 9))
    tenth = np.searchsorted(cuts, p.to_numpy(), side="right")
    return (
        frame.with_columns(tenth=pl.Series(tenth + 1), p=p)
        .group_by("tenth")
        .agg(rows=pl.len(), forecast=c("p").mean(), actual=c("y").mean())
        .sort("tenth")
    )


def tenth_error(table: pl.DataFrame) -> float:
    """The row-weighted gap between forecast and actual across tenths, in points."""
    return float(100 * ((table["forecast"] - table["actual"]).abs() * table["rows"]).sum()
                 / table["rows"].sum())  # fmt: skip


def calibration_of(frame: pl.DataFrame, rung: str, kind: str) -> dict:
    sub = frame.select(
        "y", "season", mean=c(f"{rung}:mean"),
        **({q: c(f"{rung}:{q}") for q in ("q10", "q50", "q90")} if kind == "amount" else {}),
    )  # fmt: skip
    if kind == "probability":
        rep = calibration.probability_report(sub)
        t = deciles(frame, rung)
        return {"error": rep["error"], "slope": rep["slope"], "passed": rep["passed"],
                "tenth_error": tenth_error(t), "tenths": t.rows()}  # fmt: skip
    cov = calibration.coverage(sub.with_columns(c("season").cast(pl.String)), ["season"])
    t = deciles(frame, rung)
    return {"inside": cov["inside"], "above": cov["above"], "width": cov["width"],
            "passed": cov["passed"], "groups": cov["groups"].rows(),
            "tenth_gap": float(((t["forecast"] - t["actual"]).abs() * t["rows"]).sum()
                               / t["rows"].sum()), "tenths": t.rows()}  # fmt: skip


def _cmp(d: dict) -> str:
    return f"{d['diff']:+.5f} ({d['lo']:+.5f} to {d['hi']:+.5f}), {d['blocks']} weeks"


def lines(tag: str, names: Sequence[str] | None = None) -> list[str]:
    work = run.cache_dir() / tag
    res = json.loads((work / "results.json").read_text())
    out = [f"context-live {tag}: share of the base rate's squared error removed (%), held out",
           "rungs: base | sit-lin | sit-trees | live-lin | live-trees | traits | offense | defense",
           ""]  # fmt: skip
    rung_names = [r.name for r in (*run.RUNGS, *run.SIDES)]
    for o in OUTCOMES:
        if o.name not in res or (names and o.name not in names):
            continue
        r = res[o.name]
        frame = pl.read_parquet(work / f"{o.name}.parquet")
        ch = r["choice"]
        shares = " | ".join(f"{r['share'][k]:6.2f}" if k in r["share"] else "   -  "
                            for k in rung_names)  # fmt: skip
        out.append(f"== {o.label} ({o.name}; {o.kind}; seasons {r['seasons']}; "
                   f"{r['rows']:,} plays; mean {frame['y'].mean():.3f})")  # fmt: skip
        out.append(f"  share: {shares}")
        out.append("  main loss: " + ", ".join(f"{k} {v:.4f}" for k, v in r["loss"].items()))
        out.append(f"  situation model: {ch['situation']}; vs base {_cmp(ch['situation_vs_base'])}")
        if not o.situation_only:
            out.append(f"  live model: {ch['live']}; vs situation {_cmp(ch['live_vs_situation'])};"
                       f" gain {ch['live_gain']:.2f}% of the loss; fitting noise "
                       f"{r['noise']['gain_sd']:.2f}")  # fmt: skip
            out.append(f"  traits vs live: {_cmp(ch['traits_vs_live'])}")
            s = r["sides"]
            out.append(f"  H65: offense vs situation {_cmp(s['offense_vs_situation'])}; defense "
                       f"{_cmp(s['defense_vs_situation'])}; together beyond each "
                       f"{s['together_beyond_each']:+.2f} points of share")  # fmt: skip
        out.append(f"  SHIPPED: {ch['shipped']}")
        for null in ("signal", "calls_null"):
            if null in r:
                n = r[null]
                out.append(f"  null ({n['kind']}): beats {n['beaten']} of {n['n']}; real "
                           f"{n['real']:.5f}, best null {n['null_best']:.5f}")  # fmt: skip
        cal = calibration_of(frame, ch["shipped"], o.kind)
        r["calibration"] = {k: v for k, v in cal.items() if k not in ("tenths", "groups")}
        if o.kind == "probability":
            out.append(f"  calibration: error {cal['error']:.2f} points (10 bins), by tenth "
                       f"{cal['tenth_error']:.2f}, slope {cal['slope']:.2f}, "
                       f"{'passes' if cal['passed'] else 'FAILS'}")  # fmt: skip
            out.append("  tenths (forecast/actual): " + " ".join(
                f"{f:.3f}/{a:.3f}" for _, _, f, a in cal["tenths"]))  # fmt: skip
        else:
            out.append(f"  range: q10-q90 holds {100 * cal['inside']:.1f}%, above q50 "
                       f"{100 * cal['above']:.1f}%, width {cal['width']:.2f}; by season "
                       + ", ".join(f"{v} {100 * i:.1f}%" for _, v, _, i, *_ in cal["groups"])
                       + f"; {'passes' if cal['passed'] else 'FAILS'}")  # fmt: skip
            out.append(f"  mean by tenth (forecast/actual; average gap {cal['tenth_gap']:.2f}): "
                       + " ".join(f"{f:.2f}/{a:.2f}" for _, _, f, a in cal["tenths"]))  # fmt: skip
        if r.get("importance"):
            out.append("  top fields (permutation): " + ", ".join(
                f"{k} {v:.4g}" for k, v in list(r["importance"].items())[:6]))  # fmt: skip
        out.append("")
    (work / "results_with_calibration.json").write_text(json.dumps(res, indent=1, default=str))
    return out


def main(argv: Sequence[str] | None = None) -> None:
    argv = list(argv if argv is not None else sys.argv[1:])
    tag = argv[0] if argv else "backtest"
    text = "\n".join(lines(tag))
    path = run.report_dir() / f"{tag}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    (run.report_dir() / f"sanity_{tag}.txt").write_text("\n".join(sanity(tag)), encoding="utf-8")
    (run.report_dir() / f"misses_{tag}.txt").write_text("\n".join(misses(tag)), encoding="utf-8")
    print(text)


SHOW = ["season", "week", "game_id", "play_id", "down", "ydstogo", "yardline_100", "qtr",
        "score_differential", "shotgun", "is_play_action", "is_screen_pass", "n_defense_box",
        "n_blitzers", "n_pass_rushers"]  # fmt: skip


def sanity_rules(o) -> list[shared_sanity.Rule]:
    """The shared rules (a chance in 0-1, q10 <= q50 <= q90) and context-live's own: no yards
    past the end zone (or its back line for a target's depth) or behind the own goal line, and
    no negative time to throw."""
    rules = shared_sanity.shared(o.kind)
    if o.end_zone is not None:
        back = o.end_zone + 1e-6
        rules.append(shared_sanity.Rule(
            "mean or q90 past the end zone",
            lambda df: df.filter((c("mean") > c("yardline_100") + back)
                                 | (c("q90") > c("yardline_100") + back)).height))  # fmt: skip
        rules.append(shared_sanity.Rule(
            "q10 behind the own goal line",
            lambda df: df.filter(c("q10") < c("yardline_100") - 100 - 1e-6).height))  # fmt: skip
    if o.name == "time_to_throw_exp":
        rules.append(shared_sanity.non_negative("q10"))
    return rules


def sanity(tag: str, n: int = 20) -> list[str]:
    """The football sanity check (VALIDATION.md §10): automatic rules on every shipped outcome,
    and the CEO's review lists (the top and bottom `n` plays by the main outputs, and the plays
    where the calls move the forecast most from the situation alone)."""
    work = run.cache_dir() / tag
    res = json.loads((work / "results.json").read_text())
    seasons = sorted({s for r in res.values() if isinstance(r, dict) for s in r.get("seasons", [])})
    data = run.load(seasons)
    out = [f"context-live {tag}: football sanity", ""]
    for o in OUTCOMES:
        if o.name not in res:
            continue
        ch = res[o.name]["choice"]
        f = pl.read_parquet(work / f"{o.name}.parquet").join(
            data.select(*SHOW), on=["game_id", "play_id", "season", "week"], how="left"
        )
        top = ch["shipped"]
        f = f.rename({f"{top}:{k}": k for k in ("mean", "q10", "q50", "q90")
                      if f"{top}:{k}" in f.columns})  # fmt: skip
        table = shared_sanity.run_rules(f, sanity_rules(o))
        out.append(f"== {o.label}: shipped {top}; " + ", ".join(
            f"{r} {v}" for r, v, _ in table.iter_rows()))  # fmt: skip
        f = f.rename({k: f"{top}:{k}" for k in ("mean", "q10", "q50", "q90") if k in f.columns})
        m = c(f"{top}:mean")
        if o.name in ("pressure_prob", "completion_prob", "rush_yards_exp", "run_success_prob",
                      "dropback_success_prob", "air_yards_exp"):  # fmt: skip
            sit = ch["situation"]
            f = f.with_columns(calls=m - c(f"{sit}:mean"))
            cols = [*SHOW[4:], "y", f"{top}:mean", "calls"]
            for label, part in (("highest", f.sort(m, descending=True).head(n)),
                                ("lowest", f.sort(m).head(n)),
                                ("calls move it up most", f.sort("calls", descending=True).head(n)),
                                ("calls move it down most", f.sort("calls").head(n))):  # fmt: skip
                out.append(f"  {label}:")
                out.append("    " + " | ".join(x.replace(f"{top}:", "") for x in cols))
                for row in part.select(cols).iter_rows():
                    out.append("    " + " | ".join(
                        f"{v:.3f}" if isinstance(v, float) else str(v) for v in row))  # fmt: skip
        out.append("")
    return out


MISS_NAMES = (
    "rush_yards_exp", "run_success_prob", "pressure_prob", "sack_prob",
    "time_to_throw_exp", "dropback_yards_exp", "air_yards_exp", "completion_prob",
)  # fmt: skip


def play_lenses(d: pl.DataFrame) -> dict[str, pl.Expr]:
    """Play-level lenses (the miss-lenses list is per player-game): groups to read the misses by,
    never inputs the model lacks, except the season and the top tenth."""
    return {
        "season": c("season").cast(pl.String),
        "down": c("down").cast(pl.Int32).cast(pl.String),
        "quarter": pl.when(c("qtr") >= 5).then(pl.lit("OT")).otherwise(
            c("qtr").cast(pl.Int32).cast(pl.String)),
        "score": pl.when(c("score_differential") <= -9).then(pl.lit("down 9+"))
        .when(c("score_differential") >= 9).then(pl.lit("up 9+")).otherwise(pl.lit("within 8")),
        "field": pl.when(c("yardline_100") <= 20).then(pl.lit("red zone"))
        .when(c("yardline_100") >= 80).then(pl.lit("own 20")).otherwise(pl.lit("middle")),
        "screen": c("is_screen_pass").cast(pl.String),
        "play action": c("is_play_action").cast(pl.String),
        "trick play": c("is_trick_play").cast(pl.String),
    }  # fmt: skip


def misses(tag: str, names: Sequence[str] = MISS_NAMES, min_rows: int = 300) -> list[str]:
    """The shipped rung's average miss (actual minus forecast) by play lens, with a 90% interval
    from the spread of the week blocks' average misses."""
    work = run.cache_dir() / tag
    res = json.loads((work / "results.json").read_text())
    seasons = sorted({s for r in res.values() if isinstance(r, dict) for s in r.get("seasons", [])})
    cols = ["game_id", "play_id", "down", "qtr", "score_differential", "yardline_100",
            "is_screen_pass", "is_play_action", "is_trick_play"]  # fmt: skip
    data = run.load(seasons).select(cols)
    out = [f"context-live {tag}: average miss (actual - forecast) by play lens, groups of "
           f"{min_rows}+ plays; * where the 90% interval (by week) misses zero", ""]  # fmt: skip
    for name in names:
        if name not in res:
            continue
        top = res[name]["choice"]["shipped"]
        f = pl.read_parquet(work / f"{name}.parquet").join(data, on=["game_id", "play_id"])
        f = f.with_columns(miss=c("y") - c(f"{top}:mean"))
        cut = f[f"{top}:mean"].quantile(0.9)
        lenses = {**play_lenses(f), "top tenth": (c(f"{top}:mean") >= cut).cast(pl.String)}
        out.append(f"== {name} ({top})")
        for lens, expr in lenses.items():
            g = (f.with_columns(group=expr)
                 .group_by("group", "block").agg(m=c("miss").mean(), n=pl.len())
                 .group_by("group").agg(rows=c("n").sum(), miss=(c("m") * c("n")).sum()
                                        / c("n").sum(), sd=c("m").std(), blocks=pl.len())
                 .filter(c("rows") >= min_rows).sort("group"))  # fmt: skip
            parts = []
            for grp, rows, miss, sd, blocks in g.iter_rows():
                half = 1.645 * (sd or 0) / max(blocks, 1) ** 0.5
                flag = "*" if abs(miss) > half else ""
                parts.append(f"{grp} {miss:+.3f}{flag} ({rows:,})")
            out.append(f"  {lens}: " + "; ".join(parts))
        out.append("")
    return out


if __name__ == "__main__":
    main()
