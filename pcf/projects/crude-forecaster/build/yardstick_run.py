# ruff: noqa: E501
"""crude-forecaster build: the ladder, the yardstick table (methods A and C), its own noise, the
hunch checks and SHAP, for each target and horizon. Package code does the work
(`pcf.baselines.crude`); this script runs it and writes the numbers RESULTS.md cites.

Run from pcf/ (PCF_DATA_DIR set to the shared data folder):
    python projects/crude-forecaster/build/yardstick_run.py passing,rushing,receiving,team next,next3,rest > projects/crude-forecaster/build/yardstick.txt

Tables go to data/outputs/crude-forecaster/yardstick/<target>_<horizon>/*.parquet.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import polars as pl

from pcf.baselines.crude import features as F
from pcf.baselines.crude import fitting
from pcf.baselines.crude import yardstick as Y
from pcf.baselines.crude.model import variant
from pcf.config import get_config
from pcf.validation.consistency import consistency
from pcf.validation.scores import mean_pinball

c = pl.col
T0 = time.time()
OUT = get_config().zone("outputs") / "crude-forecaster" / "yardstick"
PROGRESS = get_config().zone("logs") / "crude-forecaster-progress.txt"
PICS = Path(__file__).parent


def log(*a) -> None:
    line = f"[{time.time() - T0:6.0f}s] " + " ".join(str(x) for x in a)
    print(line, file=sys.stderr, flush=True)
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    with PROGRESS.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def pct(x: float) -> str:
    return f"{100 * x:+.2f}%"


def iv(g) -> str:
    return f"{pct(g.share)} ({pct(g.lo)} to {pct(g.hi)}); range score {pct(g.range_share)} ({pct(g.range_lo)} to {pct(g.range_hi)})"


def describe(p: pl.DataFrame) -> dict:
    y, m = p["y"].to_numpy(), p["mean"].to_numpy()
    return {
        "rows": p.height,
        "average": float(y.mean()),
        "removes": Y.removed(p),
        "range_score": float(p.select(mean_pinball()).mean().item()),
        "mae_q50": float((p["q50"] - p["y"]).abs().mean()),
        "covered": float(((p["y"] >= p["q10"]) & (p["y"] <= p["q90"])).mean()),
        "above_q50": float((p["y"] > p["q50"]).mean()),
        "width": float((p["q90"] - p["q10"]).mean()),
        "typical_miss": float(np.abs(m - y).mean() / y.mean()),
    }


def champion(gains: dict) -> str:
    """The champion is the lasso everywhere (the CEO, 2026-11-19: "We can keep lasso everywhere";
    decision 0037 call 12), provided it beats the season average; the trees and the mix are
    still fitted and reported as rungs."""
    return "lasso" if gains["lasso>season"].range_lo > 0 else "season"


def keep_sets(board: Y.Board) -> dict[str, tuple[str, ...]]:
    cols = board.base.crude_columns()

    def stat(col: str) -> str:
        return col.removeprefix("off_").removeprefix("def_").split("_")[0]

    dummies = tuple(x for x in cols if x.startswith("is_"))
    yards = tuple(x for x in cols if stat(x) in ("y",)) + dummies
    recent = {x for x in cols if x.endswith("_l4") or x.endswith("y_trend")}
    spread = {x for x in cols if x.endswith("y_sd") or x.endswith("y_ls_sd")}
    return {
        "yards only": yards,
        "yards + first downs": yards + tuple(x for x in cols if stat(x) == "fd"),
        "without recent": tuple(x for x in cols if x not in recent),
        "without spread": tuple(x for x in cols if x not in spread),
    }


def table_lines(t: pl.DataFrame) -> list[str]:
    out = [f"    all members together: {pct(t['all_members'][0])} ({pct(t['all_lo'][0])} to {pct(t['all_hi'][0])}), {t['rows'][0]} rows"]
    out.append(f"    {'member':<14}{'added alone (A)':<34}{'fair share (C)':<34}{'range score alone':<34}verdict")
    for r in t.sort("share", descending=True).iter_rows(named=True):
        out.append(
            f"    {r['member']:<14}{pct(r['alone']) + ' (' + pct(r['alone_lo']) + ' to ' + pct(r['alone_hi']) + ')':<34}"
            f"{pct(r['share']) + ' (' + pct(r['share_lo']) + ' to ' + pct(r['share_hi']) + ')':<34}"
            f"{pct(r['range_alone']) + ' (' + pct(r['range_lo']) + ' to ' + pct(r['range_hi']) + ')':<34}{r['verdict']}"
        )
    return out


def run(target: str, horizon: str) -> None:
    name = f"{target}_{horizon}"
    out = OUT / name
    out.mkdir(parents=True, exist_ok=True)
    path = Y.board_path(target, horizon)
    if (path / "features.parquet").exists():
        board = Y.load_board(target, horizon)
        log(name, "board loaded", board.features.shape)
    else:
        board = Y.build_board(target, horizon)
        log(name, "board built", board.features.shape)
    players = target != "team"
    played = Y.played_rows() if players else None
    print(f"\n==================== {name} ({board.base.quantity}) ====================")

    # ---- 1. the ladder (crude inputs only)
    preds, rows = {}, []
    for m in fitting.METHODS:
        board.base = variant(target, horizon, m)
        preds[m] = board.forecast()
        d = {"rung": m, **describe(preds[m])}
        if players:
            p = preds[m].join(played, on=board.keys, how="semi")
            d |= {"played_rows": p.height, "played_removes": Y.removed(p)}
        rows.append(d)
        log(name, "rung", m)
    ladder = pl.DataFrame(rows)
    ladder.write_parquet(out / "ladder.parquet")
    print("== 1. The ladder (crude inputs; held out 2019-2024)")
    for r in ladder.iter_rows(named=True):
        extra = f"; took a snap: {pct(r['played_removes'])} of {r['played_rows']}" if players else ""
        print(f"  {r['rung']:<7} removes {pct(r['removes'])}{extra}; range score {r['range_score']:.2f}; MAE {r['mae_q50']:.2f}; "
              f"80% range holds {100 * r['covered']:.1f}%, above q50 {100 * r['above_q50']:.1f}%, width {r['width']:.1f}; typical miss {r['typical_miss']:.2f} of the average {r['average']:.1f}")
    keys = board.keys
    gains = {
        "lasso>season": Y.gain(preds["lasso"], preds["season"], keys),
        "trees>lasso": Y.gain(preds["trees"], preds["lasso"], keys),
        "mix>lasso": Y.gain(preds["mix"], preds["lasso"], keys),
        "mix>trees": Y.gain(preds["mix"], preds["trees"], keys),
    }
    for k, g in gains.items():
        print(f"  {k:<14} {iv(g)}")
    best = champion(gains)
    print(f"  champion: {best}")
    board.base = variant(target, horizon, best)

    # ---- 2. the yardstick: methods A and C
    print(f"== 2. The yardstick ({best}; share of the crude forecast's squared error)")
    t = Y.shapley(board)
    t.write_parquet(out / "table.parquet")
    print("  rows expected to play (the headline)" if players else "  every team-game")
    print("\n".join(table_lines(t)))
    if players:
        tp = Y.shapley(board, rows=played)
        tp.write_parquet(out / "table_played.parquet")
        print("  check: rows where he took a snap (a filter on the outcome, never the headline)")
        print("\n".join(table_lines(tp)))
    seasons = {s.index: s.season for s in board.steps}
    halves = {}
    for label, keep in (("2019-2021", Y.FIRST_HALF), ("2022-2024", (2022, 2023, 2024))):
        steps = [i for i in board.test if seasons[i] in keep]
        halves[label] = Y.shapley(board, steps=steps)
        halves[label].write_parquet(out / f"table_{label}.parquet")
    a, b = halves["2019-2021"], halves["2022-2024"]
    order_a = a.sort("share", descending=True)["member"].to_list()
    order_b = b.sort("share", descending=True)["member"].to_list()
    print(f"  halves: 2019-2021 order {order_a}; 2022-2024 order {order_b}")
    for r in a.join(b, on="member", suffix="_b").iter_rows(named=True):
        print(f"    {r['member']:<14} share {pct(r['share'])} / {pct(r['share_b'])}; alone {pct(r['alone'])} / {pct(r['alone_b'])}")
    log(name, "yardstick done")

    if horizon != "next":
        return
    # ---- 3. the yardstick's own noise
    nz = Y.noise(board)
    nz.write_parquet(out / "noise.parquet")
    print("== 3. Fitting noise: added-alone gain across refits (seeds, one early season left out)")
    for (member,), g in nz.group_by("member", maintain_order=True):
        print(f"  {member:<14} alone {pct(g['alone'].min())} to {pct(g['alone'].max())} (spread {100 * (g['alone'].max() - g['alone'].min()):.2f} pts);"
              f" range {pct(g['range_alone'].min())} to {pct(g['range_alone'].max())}; crude removes {pct(g['crude_removes'].min())} to {pct(g['crude_removes'].max())}")
    log(name, "noise done")

    # ---- 4. hunch checks on the champion
    print("== 4. Hunch checks")
    full = board.forecast()
    sets = keep_sets(board)
    for label in ("yards only", "yards + first downs"):
        p = board.forecast(keep=sets[label])
        print(f"  H51 {label:<22} removes {pct(Y.removed(p))} = {100 * Y.removed(p) / Y.removed(full):.1f}% of the full crude forecast's {pct(Y.removed(full))}")
    for label, hunch in (("without recent", "H54 recent (last 4, trend)"), ("without spread", "H55 spread")):
        p = board.forecast(keep=sets[label])
        print(f"  {hunch:<28} adds {iv(Y.gain(full, p, keys))}")
        if players:
            fp = board.forecast(added=("participation",))
            pp = board.forecast(added=("participation",), keep=sets[label])
            print(f"  {hunch + ' w/ particip.':<28} adds {iv(Y.gain(fp, pp, keys))}")
    if players:
        d = full.join(played, on=keys, how="semi").join(
            board.features.select(*keys, "position"), on=keys
        )
        for (pos,), g in d.group_by("position", maintain_order=True):
            y, m = g["y"].to_numpy(), g["mean"].to_numpy()
            r2 = 1 - ((m - y) ** 2).sum() / ((y - y.mean()) ** 2).sum()
            print(f"  H52 {pos} {target:<10} took a snap: rows {g.height:>6}; removes {pct(r2)}; typical miss {np.abs(m - y).mean() / y.mean():.2f} of the average ({y.mean():.1f})")
        # H55: is the game-to-game spread a trait? (pcf.validation.consistency)
        g = board.features.select(*keys, "season", "week").join(d.select(*keys, "y"), on=keys)
        g = g.with_columns(m=c("y").mean().over("gsis_id", "season"), n=pl.len().over("gsis_id", "season"))
        g = g.filter((c("n") >= 6) & (c("m") > 0)).with_columns(
            spread=(c("y") - c("m")).abs(), spread_rel=(c("y") - c("m")).abs() / c("m")
        )
        cons = consistency(g, ["spread", "spread_rel"], unit="gsis_id")
        cons.write_parquet(out / "consistency_spread.parquet")
        for r in cons.iter_rows(named=True):
            print(f"  H55 consistency {r['measure']:<11} week to week {r['week_r']:+.2f} ({r['week_lo']:+.2f} to {r['week_hi']:+.2f}); "
                  f"season to season {r['season_r']:+.2f} ({r['season_lo']:+.2f} to {r['season_hi']:+.2f}); {r['verdict']}")
    log(name, "hunches done")

    # ---- 5. SHAP on held-out rows (the explanation)
    members = list(board.base.expert_groups())
    sv = Y.shap_values(board, members)
    groups = Y.group_of(board)
    sv = sv.with_columns(group=c("column").replace_strict(groups, default="crude"))
    if players:
        sv = sv.join(board.features.select(*keys, "position"), on=keys)
    by = ["group", "position"] if players else ["group"]
    summary = sv.group_by(*by, "gsis_id" if players else "team", *[k for k in keys if k not in ("gsis_id", "team")]).agg(
        c("shap").sum()
    ).group_by(by).agg(mean_abs=c("shap").abs().mean()).sort(by)
    summary.write_parquet(out / "shap.parquet")
    print("== 5. SHAP on held-out rows, all experts in: mean |SHAP| per row, by group (yards)")
    for r in summary.iter_rows(named=True):
        where = f" {r['position']}" if players else ""
        print(f"  {r['group']:<14}{where:<4} {r['mean_abs']:.2f}")
    plot_shap(summary, name, players)
    log(name, "shap done")


def plot_shap(summary: pl.DataFrame, name: str, players: bool) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 3.2), dpi=110)
    groups = [g for g in ["crude", *F.TEAM_EXPERTS, "participation", Y.SHUFFLED]
              if g in summary["group"].to_list()]  # fmt: skip
    if players:
        positions = sorted(summary["position"].unique().to_list())
        width = 0.8 / len(positions)
        for i, pos in enumerate(positions):
            s = summary.filter(c("position") == pos)
            vals = [s.filter(c("group") == g)["mean_abs"].sum() for g in groups]
            ax.bar(np.arange(len(groups)) + i * width, vals, width, label=pos)
        ax.legend(frameon=False)
    else:
        vals = [summary.filter(c("group") == g)["mean_abs"].sum() for g in groups]
        ax.bar(np.arange(len(groups)), vals, 0.6)
    n = summary["position"].n_unique() if players else 1
    ax.set_xticks(np.arange(len(groups)) + (0.8 / n) * (n - 1) / 2)
    ax.set_xticklabels(groups)
    ax.set_ylabel("mean |SHAP| (yards)")
    ax.set_title(f"{name}: what the forecast leans on, held-out rows (explanation, not a test)", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(PICS / f"shap_{name}.png")
    plt.close(fig)


def main() -> None:
    targets = sys.argv[1].split(",") if len(sys.argv) > 1 else ["passing", "rushing", "receiving", "team"]
    horizons = sys.argv[2].split(",") if len(sys.argv) > 2 else ["next", "next3", "rest"]
    print("crude-forecaster build: the yardstick. Held out 2019-2024, fit from 2016 at the Saturday run; "
          "'removes' = share of squared error removed; intervals are 90%, resampling whole weeks.")
    for t in targets:
        for h in horizons:
            run(t, h)
    log("all done")


if __name__ == "__main__":
    main()
