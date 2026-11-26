"""Stabilization's build, end to end (decision 0052):

    python -m pcf.experts.stabilization.run            # the report, the checks, the history, MLflow
    python -m pcf.experts.stabilization.run --no-log   # the same without the MLflow attempt

Writes `projects/stabilization/build/{players,teams,sides,leakage,history}.txt` and
`verdicts.json`, and (logged) `outputs/stabilization/<run_id>/{player_game,player_season,
team_game,team_season}.parquet`. The 2025 vault stays closed: no 2025 outcome is read.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

import polars as pl

from pcf.config import get_config
from pcf.experts.stabilization import career as Ca
from pcf.experts.stabilization import checks as Ch
from pcf.experts.stabilization import common as K
from pcf.experts.stabilization import data as D
from pcf.experts.stabilization import elsewhere as El
from pcf.experts.stabilization import history as Hs
from pcf.experts.stabilization import opponents as O
from pcf.experts.stabilization import report as Rp
from pcf.experts.stabilization import standins as St

c = pl.col


def _slim(d: dict) -> dict:
    """The verdicts only (what the history and RESULTS read), JSON-ready."""
    out = {}
    for name, v in d.items():
        r = v.get("ranges") or {}
        out[name] = {
            "shipped": v["shipped"], "champ": v["champ"],
            "gains": {k: [g.gain, g.lo, g.hi] for k, g in v["gains"].items()},
            "bar": [v["bar"]["gain"].gain, v["bar"]["gain"].lo, v["bar"]["gain"].hi,
                    v["bar"]["best_copy"], v["bar"]["passes"]],
            "ranges": {k: r[k] for k in ("coverage_plain", "conformal", "widened", "coverage")
                       if k in r},
        }  # fmt: skip
    return out


def history(inp, res: dict, run_id: str, out: Rp.Out) -> dict[str, pl.DataFrame]:
    out("== The walk-forward history (standard schema); ranges on expected attempts, their "
        "coverage on the scored rows 2018-2024", "", "| Table | Quantity | Rung shipped | Rows | "
        "Scored rows | Coverage (80%) |", "|---|---|---|---|---|---|")  # fmt: skip
    tabs: dict[str, list[pl.DataFrame]] = {k: [] for k in
                                           ("player_game", "player_season", "team_game", "team_season")}  # fmt: skip
    for m in K.MEASURES:
        v = res["next"][m.name]
        f = Hs.next_rows(inp, m, v, run_id)
        tabs["player_season"].append(f)
        cv = Hs.coverage(f)
        out(f"| player_season | {m.name}_next_season | {v['shipped']} | {f.height} | {cv['rows']} | "
            f"{cv['coverage']:.0%} |")
    for name, games, rows, lagged, kind, _label in Rp.player_units(inp):
        v = res["in"][name]
        f = Hs.in_rows(name, games, rows, lagged, kind, v, run_id)
        tabs["player_game"].append(f)
        cv = Hs.coverage(f)
        out(f"| player_game | {name}_next4 | {v['shipped']} | {f.height} | {cv['rows']} | "
            f"{cv['coverage']:.0%} |")
    for name, games, rows, lagged, kind, _label in Rp.team_units(inp):
        v = res["teams_next"][name]
        f = Hs.team_next_rows(inp, name, games, rows, v, run_id)
        tabs["team_season"].append(f)
        cv = Hs.coverage(f)
        out(f"| team_season | {name}_next_season | {v['shipped']} | {f.height} | {cv['rows']} | "
            f"{cv['coverage']:.0%} |")
        v = res["teams_in"][name]
        f = Hs.in_rows(name, games, rows, lagged, kind, v, run_id)
        tabs["team_game"].append(f)
        cv = Hs.coverage(f)
        out(f"| team_game | {name}_next4 | {v['shipped']} | {f.height} | {cv['rows']} | "
            f"{cv['coverage']:.0%} |")
    keys = {"player_game": ["gsis_id", "game_id"], "player_season": ["gsis_id", "season"],
            "team_game": ["team", "game_id"], "team_season": ["team", "season"]}  # fmt: skip
    final = {k: Hs.finish(pl.concat(v, how="diagonal_relaxed"), keys[k]) for k, v in tabs.items()}
    for k, v in final.items():
        out(f"- {k}: {v.height:,} rows, {v['quantity'].n_unique()} quantities, seasons "
            f"{v['season'].min()}-{v['season'].max()}")
    return final


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-log", action="store_true", help="no MLflow attempt, no saved history")
    ap.add_argument("--copies", type=int, default=K.COPIES)
    args = ap.parse_args(argv)
    res = Rp.run_all(args.copies)
    inp = res["inputs"]
    side = Rp.Out("sides")
    res["I155"] = O.report(D.team_games(), side)
    res["I156"] = El.report(side, Rp.SEED)
    res["I174"] = El.i174(side, args.copies, Rp.SEED)
    res["career"] = Ca.report(inp, side, Rp.SEED)
    res["standins"] = St.report(inp, side, Rp.SEED)
    side.save()
    leak = Rp.Out("leakage")
    res["leakage"] = Ch.run_all(inp, leak, Rp.SEED)
    leak(f"all passed: {res['leakage']['passed']}")
    leak.save()
    verdicts = {k: _slim(res[k]) for k in ("next", "in", "teams_next", "teams_in")}
    (K.report_dir() / "verdicts.json").write_text(json.dumps(verdicts, indent=1), encoding="utf-8")
    hist_out = Rp.Out("history")
    metrics = {**res["out_players"].metrics, **res["out_teams"].metrics}
    if args.no_log:
        history(inp, res, "no-log", hist_out)
        hist_out.save()
        return
    from pcf.core import tracking

    train_end = D.player_games()["known_at"].max()
    with tracking.attempt(K.PROJECT, train_end=train_end, name="stabilization v1",
                          params={"copies": args.copies, "test": "2018-2024",
                                  "measures": len(K.MEASURES),
                                  "team_measures": len(K.TEAM_MEASURES)}) as run:  # fmt: skip
        run_id = run.info.run_id
        tabs = history(inp, res, run_id, hist_out)
        hist_out.save()
        folder = get_config().zone("outputs") / K.PROJECT / run_id
        folder.mkdir(parents=True, exist_ok=True)
        for k, v in tabs.items():
            v.write_parquet(folder / f"{k}.parquet")
        tracking.log_metrics(metrics)
        tracking.log_checks({"leakage": res["leakage"]["passed"]})
        for name in ("players", "teams", "sides", "leakage", "history"):
            tracking.log_text((K.report_dir() / f"{name}.txt").read_text(encoding="utf-8"),
                              f"{name}.txt")  # fmt: skip
        print(f"history: {folder} (run {run_id})")


if __name__ == "__main__":
    main()
