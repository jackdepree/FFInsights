"""The leakage checks (the agreed brief, "every leakage check"; decision 0052, call 24).

1. **Future deletion, in season:** at many cutoffs, every game known after the cutoff is deleted
   and the season's frame rebuilt; each checkpoint whose forecast moment (the next kickoff) is
   before the cutoff must give the same forecasts and ranges' inputs.
2. **Test-label scrambling:** the attempts' outcomes (`num`) in every game after a cutoff are
   shuffled among those games; forecasts made before the cutoff must not move. In season (the
   same cutoffs) and next season (each target season's own games scrambled, for every measure, so
   the ridge's other rates are scrambled too).
3. **PFR's lag:** for every PFR checkpoint, the last game it read was known (PFR's `known_at`) by
   the forecast moment, and how often the lag bites (the forecast reads an earlier game).
4. **The code scan** (`pcf.validation.leakage.scan_code`) on the package's files.
5. **Known-at sanity:** no input row is known before its game kicks off.
The shuffled-player null runs in the report (19 copies a rung).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import polars as pl

from pcf.experts.stabilization import common as K
from pcf.experts.stabilization import inseason as I
from pcf.experts.stabilization import nextseason as N
from pcf.experts.stabilization import rates as R
from pcf.experts.stabilization import walks as W
from pcf.validation import leakage as Lk

c = pl.col
FORECASTS = ("N", "m1", "m1_v", "raw", "m", "P", "m_phi", "P_phi", "m_om", "P_om", "swing", "G",
             "m1_k104", "gi_known")  # fmt: skip
NEXT_FORECASTS = ("m1", "pull", "ridge", "ridge_trend", "pull_mv", "layered", "v_m1", "v_pull",
                  "v_ridge")  # fmt: skip
TOL = 1e-9


def _cutoffs(games: pl.DataFrame, T: int, n: int, seed: int) -> list[datetime]:
    k = games.filter((c("season") == T) & c("week").is_between(3, 17))["kickoff"].unique().sort()
    rng = np.random.default_rng(seed)
    return sorted(k.to_list()[i] for i in rng.choice(len(k), size=min(n, len(k)), replace=False))


def _diff(a: pl.DataFrame, b: pl.DataFrame, keys: list[str], cols: tuple[str, ...]) -> tuple[int, int]:
    cols_ = [x for x in cols if x in a.columns and x in b.columns]
    j = a.select(*keys, *cols_).join(b.select(*keys, *cols_), on=keys, how="inner", suffix="_b")
    bad = 0
    for x in cols_:
        d = (j[x].cast(pl.Float64) - j[f"{x}_b"].cast(pl.Float64)).abs()
        scale = j[x].cast(pl.Float64).abs().fill_null(0) + 1e-12
        both_null = j[x].is_null() & j[f"{x}_b"].is_null()
        one_null = j[x].is_null() ^ j[f"{x}_b"].is_null()
        bad += int(((d / scale > TOL) & ~both_null).fill_null(False).sum() + one_null.sum())
    return j.height, bad


def _scramble_after(games: pl.DataFrame, cutoff: datetime, seed: int) -> pl.DataFrame:
    late = c("known_at") > cutoff
    g = games.with_row_index("_i")
    a = g.filter(late)
    rng = np.random.default_rng(seed)
    perm = rng.permutation(a.height)
    rate = (a["num"] / a["den"]).to_numpy()[perm]
    a = a.with_columns(num=pl.Series(rate) * c("den"))
    return pl.concat([g.filter(~late), a]).sort("_i").drop("_i")


def in_season(inp: W.Inputs, measures: tuple[str, ...], seasons: tuple[int, ...], n: int,
              seed: int, out) -> dict:  # fmt: skip
    """Checks 1 and 2 in season, for `measures` (player) at `n` cutoffs in each of `seasons`."""
    res = {}
    for m in measures:
        meas = K.BY_NAME[m]
        lagged, eff = m in K.LAGGED, meas.kind == "efficiency"
        games, rows = inp.games[m], inp.rows[m]
        rows_seen, bad_del, bad_scr, cps = 0, 0, 0, 0
        for T in seasons:
            full, _ = I.season_frame(games, rows, T, lagged=lagged, efficiency=eff)
            full = full.filter(c("season") == T)
            for i, cut in enumerate(_cutoffs(games, T, n, seed + T)):
                before = full.filter(c("next_kick") <= cut)
                cps += before.height
                g_del = games.filter(c("known_at") <= cut)
                d, _ = I.season_frame(g_del, R.season_rows(g_del), T, lagged=lagged, efficiency=eff)
                h, b = _diff(before, d.filter(c("season") == T), ["gsis_id", "season", "gi"],
                             FORECASTS)  # fmt: skip
                rows_seen += h
                bad_del += b
                g_scr = _scramble_after(games, cut, seed + i)
                s, _ = I.season_frame(g_scr, R.season_rows(g_scr), T, lagged=lagged,
                                      efficiency=eff)  # fmt: skip
                _, b2 = _diff(before, s.filter(c("season") == T), ["gsis_id", "season", "gi"],
                              FORECASTS)  # fmt: skip
                bad_scr += b2
        ok = bad_del == 0 and bad_scr == 0
        out(f"- {m}: {len(seasons) * n} cutoffs ({', '.join(map(str, seasons))}), {cps} "
            f"checkpoints before them; future deleted: {rows_seen} rows compared, {bad_del} "
            f"differ; outcomes after the cutoff scrambled: {bad_scr} differ -> "
            f"{'pass' if ok else 'FAIL'}")  # fmt: skip
        res[m] = {"compared": rows_seen, "deleted_bad": bad_del, "scrambled_bad": bad_scr,
                  "passed": ok}  # fmt: skip
    return res


def next_season(inp: W.Inputs, measures: tuple[str, ...], targets: tuple[int, ...], seed: int,
                out) -> dict:  # fmt: skip
    """Check 2 next season: every measure's games in target seasons >= t scrambled; the target t's
    forecasts (made before t) must not move."""
    res = {}
    for m in measures:
        meas = K.BY_NAME[m]
        p, oth, cc, ks = W.next_frame(inp, meas)
        base = W.next_rungs(p, oth, cc, ks)
        bad, seen = 0, 0
        for t in targets:
            cut = inp.games[m].filter(c("season") == t)["kickoff"].min()
            x = _scrambled_inputs(inp, cut, seed + t)
            p2, oth2, cc2, ks2 = W.next_frame(x, meas)
            f2 = W.next_rungs(p2, oth2, cc2, ks2)
            h, b = _diff(base.filter(c("target") == t), f2.filter(c("target") == t),
                         ["gsis_id", "target"], NEXT_FORECASTS)  # fmt: skip
            seen += h
            bad += b
        ok = bad == 0
        out(f"- {m}: targets {', '.join(map(str, targets))}, every measure's outcomes from the "
            f"target season on scrambled: {seen} forecasts compared, {bad} differ -> "
            f"{'pass' if ok else 'FAIL'}")  # fmt: skip
        res[m] = {"compared": seen, "bad": bad, "passed": ok}
    return res


def _scrambled_inputs(inp: W.Inputs, cut: datetime, seed: int) -> W.Inputs:
    x = object.__new__(W.Inputs)
    x.games = {m: _scramble_after(g, cut, seed) for m, g in inp.games.items()}
    x.rows = {m: R.season_rows(g) for m, g in x.games.items()}
    x.cond = inp.cond
    x.team_games, x.team_rows = inp.team_games, inp.team_rows
    x._sm = {}
    return x


def pfr_lag(inp: W.Inputs, out) -> dict:
    """Check 3: the last game a PFR checkpoint read was known by its forecast moment."""
    res = {}
    for m in K.LAGGED:
        games, rows = inp.games[m], inp.rows[m]
        g = games.sort("gsis_id", "season", "week").with_columns(
            gi=pl.int_range(1, pl.len() + 1).over("gsis_id", "season")
        ).select("gsis_id", "season", gi_known="gi", known_used="known_at")
        cps, late, lag = 0, 0, 0
        for T in (t for t in K.TEST if t > int(rows["season"].min())):
            cp, _ = I.season_frame(games, rows, T, lagged=True, efficiency=True)
            cp = cp.filter(c("season") == T)
            j = cp.join(g, on=["gsis_id", "season", "gi_known"], how="left")
            cps += j.height
            late += int(j.filter(c("known_used") > c("next_kick")).height)
            lag += int(j.filter(c("gi_known") < c("gi")).height)
        out(f"- {m}: {cps} checkpoints; read a game not yet known: {late}; the lag bites (an "
            f"earlier game is the latest known) in {lag} ({lag / max(cps, 1):.0%}) -> "
            f"{'pass' if late == 0 else 'FAIL'}")  # fmt: skip
        res[m] = {"checkpoints": cps, "late": late, "lag_share": lag / max(cps, 1),
                  "passed": late == 0}  # fmt: skip
    return res


def code_scan(out) -> dict:
    """Check 4. Two reads are expected and named: `data.py` reads its own cache of rows it read
    through the gateway (as other experts' data modules do); `elsewhere.py` reads opportunity-
    quality's backtest cache for I156, an idea check no forecast uses; `checks.py` reads the
    package's own source to scan it."""
    expected = {"checks.py", "data.py", "elsewhere.py"}
    files = sorted(Path(__file__).parent.glob("*.py"))
    files.append(Path(Lk.__file__).with_name("stabilize.py"))
    res, ok = {}, True
    for f in files:
        gw, sp = Lk.scan_code(f.read_text(encoding="utf-8"))
        if sp or (gw and f.name not in expected):
            ok = False
        if gw or sp:
            res[f.name] = gw + sp
    out(f"- code scan of {len(files)} files: random splitters none; reads around the gateway "
        + ("; ".join(f"{k}: {', '.join(v)}" for k, v in res.items()) or "none")
        + f" (expected: {', '.join(sorted(expected))}) -> {'pass' if ok else 'FAIL'}")
    return {"flags": res, "passed": ok}


def known_at(inp: W.Inputs, out) -> dict:
    """Check 5."""
    bad = sum(int(g.filter(c("known_at") < c("kickoff")).height) for g in inp.games.values())
    tbad = sum(int(g.filter(c("known_at") < c("kickoff")).height) for g in inp.team_games.values())
    ok = bad == 0 and tbad == 0
    out(f"- known-at sanity: player rows known before kickoff {bad}, team rows {tbad} -> "
        f"{'pass' if ok else 'FAIL'}")
    return {"passed": ok}


def run_all(inp: W.Inputs, out, seed: int) -> dict:
    out("", "== The leakage checks")
    res = {"known_at": known_at(inp, out), "code": code_scan(out), "pfr": pfr_lag(inp, out)}
    res["in_season"] = in_season(inp, ("tprr", "catch_oe", "pressured", "tgt_per_cov"),
                                 (2019, 2023), 4, seed, out)  # fmt: skip
    res["next_season"] = next_season(inp, ("yprr", "press_per_snap", "qb_adot"), (2020, 2024),
                                     seed, out)  # fmt: skip
    res["passed"] = all(v["passed"] if "passed" in v else all(x["passed"] for x in v.values())
                        for v in res.values())  # fmt: skip
    return res


__all__ = ["run_all", "N"]
