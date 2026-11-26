"""The build's report (decision 0052): every measure's ladder, the expert's bar, ranges and the
ideas, for players and teams. Writes `projects/stabilization/build/<section>.txt` and returns
the verdicts the history and the results read.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import polars as pl

from pcf.experts.stabilization import common as K
from pcf.experts.stabilization import evaluate as E
from pcf.experts.stabilization import ladder as Lad
from pcf.experts.stabilization import rates as R
from pcf.experts.stabilization import walks as W

c = pl.col
SEED = 20261126


class Out:
    def __init__(self, name: str) -> None:
        self.name, self.lines, self.metrics = name, [], {}

    def __call__(self, *text: str) -> None:
        for t in text:
            self.lines.append(t)
            print(t, flush=True)

    def metric(self, key: str, value: float) -> None:
        if value is not None and np.isfinite(value):
            self.metrics[key] = float(value)

    def save(self) -> None:
        (K.report_dir() / f"{self.name}.txt").write_text("\n".join(self.lines) + "\n",
                                                         encoding="utf-8")  # fmt: skip


def walk_scale(f: pl.DataFrame, mean: str, var: str, season: str) -> pl.DataFrame:
    """The conformal scale for each season from earlier seasons' rows (VALIDATION §7)."""
    s = f[season].to_numpy()
    z = f.select(((c("y") - c(mean)).abs() / c(var).sqrt()).alias("z"))["z"].to_numpy()
    sc = np.full(f.height, np.nan)
    for t in np.unique(s):
        tr = (s < t) & np.isfinite(z)
        if tr.sum() >= 30:
            sc[s == t] = np.quantile(z[tr], 0.8) / K.Z80
    return f.with_columns(pl.Series("_scale", sc).fill_nan(None))


def range_block(te: pl.DataFrame, mean: str, var: str, scale: str | None, ent: str,
                out: Out, key: str) -> dict:  # fmt: skip
    """Coverage plain and (if outside 75-85%) conformal; then I14's widening (kept only where the
    range score improves clearly); coverage by thirds of reliability and of swing."""
    cov = E.coverage(te, mean, var)
    use = var
    conformal = False
    if not (0.75 <= cov <= 0.85) and scale is not None:
        te = te.with_columns((c(var) * c(scale) ** 2).alias("_v_conf"))
        use, conformal = "_v_conf", True
    te = te.with_columns((c(use) * c("sw")).alias("_v_sw"))
    if conformal and f"{scale}_sw" in te.columns:
        te = te.with_columns((c(var) * c("sw") * c(f"{scale}_sw") ** 2).alias("_v_sw"))
    rg = E.range_gain(te, "_v_sw", use, mean, ent, SEED)
    wide = rg.clear
    final = "_v_sw" if wide else use
    cov_final = E.coverage(te, mean, final)
    thirds_rel = E.coverage_by_thirds(te, mean, final, "reliability")
    thirds_sw = E.coverage_by_thirds(te, mean, final, "sw")
    width = float((2 * K.Z80 * te.drop_nulls([final])[final].sqrt()).mean())
    out(f"    ranges: plain {cov:.0%}" + (f", conformal {E.coverage(te, mean, use):.0%}"
                                          if conformal else "")
        + f"; I14 widening by swing: range score {rg.fmt()} -> {'kept' if wide else 'not kept'}; "
        f"shipped coverage {cov_final:.0%} (thirds of reliability "
        + ", ".join(f"{x:.0%}" for x in thirds_rel) + "; of swing "
        + ", ".join(f"{x:.0%}" for x in thirds_sw) + f"); mean width {width:.4g}")  # fmt: skip
    out.metric(f"{key}_coverage", cov_final)
    return {"coverage_plain": cov, "conformal": conformal, "widened": wide, "range_gain": rg,
            "coverage": cov_final, "thirds_rel": thirds_rel, "thirds_sw": thirds_sw,
            "frame": te, "var": final}  # fmt: skip


# ---------------------------------------------------------------- players, next season
def next_season(inp: W.Inputs, out: Out, copies: int = K.COPIES) -> dict:
    out("== Players, next season (targets 2018-2024; gains are shares of the base's squared "
        "error weighted by next season's attempts; 90% from resampled players)")  # fmt: skip
    res = {}
    for m in K.MEASURES:
        p, oth, cc, ks = W.next_frame(inp, m)
        f = W.next_rungs(p, oth, cc, ks)
        f = f.with_columns(season=c("target"))
        sw = W.N.swing(W.R.game_rows(inp.games[m.name], inp.sm(m.name)), inp.sm(m.name))
        f = f.join(sw, on=["gsis_id", "season"], how="left").with_columns(
            c("sw").fill_null(1.0), reliability=c("n") / (c("n") + c("k"))
        ) if "sw" not in f.columns else f
        te = f.filter(c("target").is_in(list(K.TEST)))
        g = {
            "m1_avg": E.gain(te, "m1", "avg", seed=SEED), "m1_raw": E.gain(te, "m1", "raw", seed=SEED),
            "pull_m1": E.gain(te, "pull", "m1", seed=SEED),
        }  # fmt: skip
        r2 = "pull" if g["pull_m1"].clear else "m1"
        g["ridge_r2"] = E.gain(te, "ridge", r2, seed=SEED)
        champ = "ridge" if g["ridge_r2"].clear else r2
        cp = Lad.copies(lambda s: W.next_rungs(p, oth, cc, ks, s).filter(
            c("target").is_in(list(K.TEST))), champ, "gsis_id", copies, SEED)  # fmt: skip
        b = Lad.bar(te, champ, cp, "gsis_id", SEED)
        shipped = champ if b["passes"] else "avg"
        won = E.seasons_won(te.with_columns(season=c("target")), shipped, "avg")
        out(f"- {m.name} ({m.label}; {m.kind}; per {m.attempts}): {te.height} pairs; "
            f"k {float(te['k'].mean()):.0f}; M1 vs average {g['m1_avg'].fmt()}, vs raw "
            f"{g['m1_raw'].fmt()}; second pull vs M1 {g['pull_m1'].fmt()} (slope "
            f"{float(te['b_pull'].mean()):.2f}); ridge vs {r2} {g['ridge_r2'].fmt()} "
            f"({float(te['n_consistent'].mean()):.1f} consistent rates chosen)")  # fmt: skip
        out(f"    champion {champ}: vs average {b['gain'].fmt()}, best of {copies} copies "
            f"{E.pct(b['best_copy'])} -> ships {shipped}; seasons won {won[0]} of {won[1]}")
        # ideas
        ideas = {"I152": E.gain(te, "ridge_trend", "ridge", seed=SEED),
                 "I181": E.gain(te, "layered", "m1", seed=SEED)}  # fmt: skip
        mv = te.filter(c("moved"))
        ideas["I173"] = E.gain(mv, "pull_mv", "pull", seed=SEED)
        ideas["movers_pull_m1"] = E.gain(mv, "pull", "m1", seed=SEED)
        out(f"    I152 (trend) vs ridge {ideas['I152'].fmt()}; I181 (layered) vs M1 "
            f"{ideas['I181'].fmt()}; movers ({mv.height}): own slope vs shared (I173) "
            f"{ideas['I173'].fmt()}, second pull vs M1 {ideas['movers_pull_m1'].fmt()}")
        rb = None
        if shipped != "avg":
            f2 = walk_scale(f, shipped, f"v_{shipped}", "target")
            f2 = f2.with_columns(**{f"scale_{shipped}": c("_scale")})
            wide = f2.with_columns(_vw=c(f"v_{shipped}") * c("sw"))
            wide = walk_scale(wide.drop("_scale"), shipped, "_vw", "target")
            f2 = f2.with_columns(**{f"scale_{shipped}_sw": wide["_scale"]})
            te2 = f2.filter(c("target").is_in(list(K.TEST)))
            rb = range_block(te2, shipped, f"v_{shipped}", f"scale_{shipped}", "gsis_id", out,
                             f"next_{m.name}")  # fmt: skip
        for k_, v in g.items():
            out.metric(f"next_{m.name}_{k_}", v.gain)
        res[m.name] = {"frame": f, "gains": g, "champ": champ, "shipped": shipped, "bar": b,
                       "copies": cp, "ideas": ideas, "won": won, "ranges": rb}  # fmt: skip
    return res


# ---------------------------------------------------------------- teams, next season
def teams_next(inp: W.Inputs, out: Out, copies: int = K.COPIES) -> dict:
    """Rungs 1-2 for each team rate (M1, the second pull); the ridge isn't tried (32 teams a
    season leave it under 100 training pairs until the last test seasons; decision 0052)."""
    out("== Teams, next season (targets 2018-2024; teams resampled)")
    res = {}
    for name, games, rows, _lag, kind, label in team_units(inp):
        sm = W.N.season_m1(rows, games)
        p = W.N.pairs(sm, rows)
        p = W.N.features(p, {}, None, None, sm, None, None)
        f = W.next_rungs(p, [], [], {}).with_columns(season=c("target"))
        sw = W.N.swing(R.game_rows(games, sm), sm)
        f = f.join(sw, on=["gsis_id", "season"], how="left").with_columns(
            c("sw").fill_null(1.0), reliability=c("n") / (c("n") + c("k")))
        te = f.filter(c("target").is_in(list(K.TEST)))
        g = {"m1_avg": E.gain(te, "m1", "avg", seed=SEED),
             "pull_m1": E.gain(te, "pull", "m1", seed=SEED)}  # fmt: skip
        champ = "pull" if g["pull_m1"].clear else "m1"
        cp = Lad.copies(lambda s: W.next_rungs(p, [], [], {}, s).filter(
            c("target").is_in(list(K.TEST))), champ, "gsis_id", copies, SEED)  # fmt: skip
        b = Lad.bar(te, champ, cp, "gsis_id", SEED)
        shipped = champ if b["passes"] else "avg"
        out(f"- {name} ({label}; {kind}): {te.height} team pairs; k {float(te['k'].mean()):.0f}; "
            f"M1 vs average {g['m1_avg'].fmt()}; second pull vs M1 {g['pull_m1'].fmt()} (slope "
            f"{float(te['b_pull'].mean()):.2f}); champion {champ} vs average {b['gain'].fmt()}, "
            f"best of {copies} copies {E.pct(b['best_copy'])} -> ships {shipped}")  # fmt: skip
        rb = None
        if shipped != "avg":
            f2 = walk_scale(f, shipped, f"v_{shipped}", "target")
            f2 = f2.with_columns(**{f"scale_{shipped}": c("_scale")})
            wide = walk_scale(f2.with_columns(_vw=c(f"v_{shipped}") * c("sw")).drop("_scale"),
                              shipped, "_vw", "target")  # fmt: skip
            f2 = f2.with_columns(**{f"scale_{shipped}_sw": wide["_scale"]})
            rb = range_block(f2.filter(c("target").is_in(list(K.TEST))), shipped,
                             f"v_{shipped}", f"scale_{shipped}", "gsis_id", out,
                             f"next_{name}")  # fmt: skip
        for k_, v in g.items():
            out.metric(f"next_{name}_{k_}", v.gain)
        res[name] = {"frame": f, "gains": g, "champ": champ, "shipped": shipped, "bar": b,
                     "copies": cp, "ranges": rb}  # fmt: skip
    return res


# ---------------------------------------------------------------- players and teams, in season
def in_season(units: list[tuple[str, pl.DataFrame, pl.DataFrame, bool, str, str]], out: Out,
              copies: int = K.COPIES, ent: str = "gsis_id") -> dict:  # fmt: skip
    """`units`: (name, games, rows, lagged, kind, label). Usage and mixed rates and team rates
    try the plain filter; efficiency rates the filter with I154's factor (and I182's twin)."""
    res = {}
    for name, games, rows, lagged, kind, label in units:
        eff = kind == "efficiency"
        frames = W.in_frames(games, rows, ent, "pos", lagged, eff)
        f = W.in_rungs(frames, "next")
        g = {"m1_avg": E.gain(f, "m1", "avg", ent, SEED), "m1_raw": E.gain(f, "m1", "raw", ent, SEED),
             "pull_m1": E.gain(f, "pull", "m1", ent, SEED)}  # fmt: skip
        r2 = "pull" if g["pull_m1"].clear else "m1"
        filt = "filt_phi" if eff else "filt"
        g["filt_r2"] = E.gain(f, filt, r2, ent, SEED)
        g["filt_plain_r2"] = E.gain(f, "filt", r2, ent, SEED)
        g["filt_m1"] = E.gain(f, "filt", "m1", ent, SEED)
        champ = filt if g["filt_r2"].clear else r2
        cp = Lad.copies(lambda s: W.in_rungs(frames, "next", s), champ, ent, copies, SEED)
        b = Lad.bar(f, champ, cp, ent, SEED)
        shipped = champ if b["passes"] else "avg"
        won = E.seasons_won(f, shipped, "avg")
        par = f.select("q", "qs", "tau2", "phi", "omega").mean().row(0, named=True)
        out(f"- {name} ({label}; {kind}): {f.height} checkpoints; M1 vs average "
            f"{g['m1_avg'].fmt()}; second pull vs M1 {g['pull_m1'].fmt()}; filter"
            f"{' (I154 factor)' if eff else ''} vs {r2} {g['filt_r2'].fmt()}"
            + (f", plain filter vs {r2} {g['filt_plain_r2'].fmt()}" if eff else "")
            + f"; filter q {par['q'] / par['tau2']:.3f} and q_s {par['qs'] / par['tau2']:.2f} "
            "of the true spread")  # fmt: skip
        out(f"    champion {champ}: vs average {b['gain'].fmt()}, best of {copies} copies "
            f"{E.pct(b['best_copy'])} -> ships {shipped}; seasons won {won[0]} of {won[1]}")
        ideas = {"I104": E.gain(f, "m1_k104", "m1", ent, SEED)}
        if eff:
            ideas["I154_vs_m1"] = E.gain(f, "filt_phi", "m1", ent, SEED)
            ideas["I182_vs_m1"] = E.gain(f, "filt_om", "m1", ent, SEED)
            ideas["I182_vs_I154"] = E.gain(f, "filt_om", "filt_phi", ent, SEED)
            out(f"    I154: phi {par['phi']:.2f} (mean over seasons); factor filter vs static M1 "
                f"{ideas['I154_vs_m1'].fmt()}; I182: omega {par['omega'] / par['tau2']:.2f} of "
                f"the spread, vs static M1 {ideas['I182_vs_m1'].fmt()}, vs I154 "
                f"{ideas['I182_vs_I154'].fmt()}")  # fmt: skip
        out(f"    I104 (this season's k blended) vs M1 {ideas['I104'].fmt()}")
        rb = None
        if shipped != "avg":
            rb = range_block(f, shipped, f"v_{shipped}", f"scale_{shipped}", ent, out,
                             f"in_{name}")  # fmt: skip
        rest = W.in_rungs(frames, "rest")
        rg = E.gain(rest, shipped, "avg", ent, SEED) if shipped != "avg" else None
        if rg is not None:
            out(f"    rest of season ({rest.height}): {shipped} vs average {rg.fmt()}; coverage "
                f"{E.coverage(rest, shipped, f'v_{shipped}'):.0%}")
        for k_, v in g.items():
            out.metric(f"in_{name}_{k_}", v.gain)
        res[name] = {"frame": f, "rest": rest, "gains": g, "champ": champ, "shipped": shipped,
                     "bar": b, "copies": cp, "ideas": ideas, "won": won, "ranges": rb,
                     "frames": frames}  # fmt: skip
    return res


def player_units(inp: W.Inputs) -> list:
    return [(m.name, inp.games[m.name], inp.rows[m.name], m.name in K.LAGGED, m.kind, m.label)
            for m in K.MEASURES]  # fmt: skip


def team_units(inp: W.Inputs) -> list:
    return [(f"{s}_{m}", inp.team_games[(s, m)], inp.team_rows[(s, m)], False,
             K.TEAM_KIND[m] if s == "off" else "efficiency" if m in ("explosive", "success")
             else "faced" if m in ("proe", "shotgun", "no_huddle") else "mixed",
             f"{K.TEAM_LABEL[m]}, {'offense' if s == 'off' else 'defense (allowed or faced)'}")
            for s in ("off", "def") for m in K.TEAM_MEASURES]  # fmt: skip


# ---------------------------------------------------------------- rookies (I5)
def rookies(res: dict, inp: W.Inputs, out: Out) -> dict:
    out("", "== I5 in stabilization's form: rookies' usage rates, next 4 games after games 8 and 12")
    out_ = {}
    for name in ("tprr", "car_per_run", "adot", "tgt_per_cov"):
        if name not in res:
            continue
        f = res[name]["frame"]
        first = inp.rows[name].group_by("gsis_id").agg(first=c("season").min())
        rk = f.join(first, on="gsis_id").filter((c("season") == c("first")) & (c("gi") >= 8))
        rk = rk.filter(c("first") > K.BY_NAME[name].first)  # a real first season, not the data's
        if rk.height < 30:
            continue
        miss = {r: float((rk["w"] * (rk["y"] - rk[r])).sum() / rk["w"].sum())
                for r in ("m1", "filt")}  # fmt: skip
        rng = np.random.default_rng(SEED)
        ids = rk["gsis_id"].to_numpy()
        u, inv = np.unique(ids, return_inverse=True)
        e = (rk["w"] * (rk["y"] - rk["m1"])).to_numpy()
        ww = rk["w"].to_numpy()
        se = np.bincount(inv, e, len(u))
        sw = np.bincount(inv, ww, len(u))
        idx = rng.integers(0, len(u), (K.DRAWS, len(u)))
        bs = se[idx].sum(1) / sw[idx].sum(1)
        lo, hi = np.quantile(bs, [0.05, 0.95])
        out(f"- {name}: {rk.height} rookie checkpoints; static M1's mean miss (actual less "
            f"forecast) {miss['m1']:+.4f} (90% {lo:+.4f} to {hi:+.4f}); the filter's "
            f"{miss['filt']:+.4f}")  # fmt: skip
        out_[name] = {"m1": miss["m1"], "lo": lo, "hi": hi, "filt": miss["filt"]}
    return out_


# ---------------------------------------------------------------- the ceiling
def ceiling(inp: W.Inputs, out: Out) -> pl.DataFrame:
    """Per measure, fit on every season through 2024 (a description, not a forecast): k, the
    typical season's attempts and reliability, and the true rate's season r."""
    out("== The noise ceiling, fit on 2006-2024 (each measure from its first season)", "",
        "| Measure | Kind | Attempts | k (the 50% point) | Typical season | Reliability there | "
        "True rate's season r |", "|---|---|---|---|---|---|---|")  # fmt: skip
    rows = []
    for m in K.MEASURES:
        f = R.fit_k(inp.rows[m.name], inp.games[m.name], K.LAST)
        sm = inp.sm(m.name)
        p = W.N.pairs(sm, inp.rows[m.name]).with_columns(y=c("rate_next") - c("mu"))
        nxt = R.centred(inp.rows[m.name]).select("gsis_id", season=c("season") - 1, x2="x")
        p2 = p.join(nxt, on=["gsis_id", "season"]).with_columns(y=c("x2"))
        r = R.season_r(p2, f["k"])
        typ = float(np.median(inp.rows[m.name].filter(c("den") >= R.MIN_DEN)["den"].to_numpy()))
        rows.append({"measure": m.name, "kind": m.kind, "k": f["k"], "typical": typ,
                     "reliability": typ / (typ + f["k"]), "season_r": r,
                     "sigma2": f["sigma2"], "tau2": f["tau2"]})  # fmt: skip
        out(f"| {m.name} | {m.kind} | {m.attempts} | {f['k']:.0f} | {typ:.0f} | "
            f"{typ / (typ + f['k']):.2f} | {r:.2f} |")
    return pl.DataFrame(rows)


def run_all(copies: int = K.COPIES, sections: tuple[str, ...] = ("players", "teams")) -> dict:
    inp = W.Inputs()
    res: dict = {"inputs": inp}
    if "players" in sections:
        o = Out("players")
        res["ceiling"] = ceiling(inp, o)
        o("")
        res["next"] = next_season(inp, o, copies)
        o("", "== Players, in season: the next 4 games after games 4, 8 and 12 (2018-2024; "
          "fit on earlier seasons; PFR's rows at their lag)")  # fmt: skip
        res["in"] = in_season(player_units(inp), o, copies)
        res["I5"] = rookies(res["in"], inp, o)
        o.save()
        res["out_players"] = o
    if "teams" in sections:
        o = Out("teams")
        res["teams_next"] = teams_next(inp, o, copies)
        o("", "== Teams, in season: the next 4 games after games 4, 8 and 12 (2018-2024; teams "
          "resampled)")  # fmt: skip
        res["teams_in"] = in_season(team_units(inp), o, copies)
        o.save()
        res["out_teams"] = o
    return res


Make = Callable[[int], pl.DataFrame]
