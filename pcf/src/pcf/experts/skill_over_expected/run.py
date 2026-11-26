"""The build's run (decision 0051): I90 and I91 first (as the brief says), the ladder for every
trait, the pass rushers' sacks target, owners, ranges, the yardstick, the backlog's ideas, the
saved trait table and the report.

    python -m pcf.experts.skill_over_expected.run            # everything, logged to MLflow
    python -m pcf.experts.skill_over_expected.run --no-log   # the report only
    python -m pcf.experts.skill_over_expected.run --no-yardstick
"""

from __future__ import annotations

import argparse
import warnings
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.experts.skill_over_expected import data as D
from pcf.experts.skill_over_expected import evaluate as E
from pcf.experts.skill_over_expected import table as H
from pcf.experts.skill_over_expected import traits as T
from pcf.validation import owners

c = pl.col
PROJECT = "skill-over-expected"
REPORT = Path(__file__).resolve().parents[4] / "projects" / PROJECT / "build" / "report.txt"
ROLES_RUN = "696a3f0b827f48549dfc9e3393655df1"  # roles-archetypes' pinned history (I113's table)
ALL_INPUTS = ("x", "n", "tp_x", "tp_n")


class Report:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.metrics: dict[str, float] = {}

    def __call__(self, *text: str) -> None:
        for t in text:
            self.lines.append(t)
            print(t, flush=True)

    def metric(self, name: str, value: float) -> None:
        if np.isfinite(value):
            self.metrics[name] = float(value)


def pct(x: float) -> str:
    return f"{100 * x:+.1f}%"


def kept_pairs(rows: pl.DataFrame) -> pl.DataFrame:
    """Season pairs in `owners.kept`'s shape (pid, season, rate, rate_n, moved)."""
    nxt = rows.select("gsis_id", season=c("season") - 1, rate_n=c("rate"), team_n=c("team"))
    p = rows.select("gsis_id", "season", "team", "rate").join(nxt, on=["gsis_id", "season"])
    return p.select(pid="gsis_id", season="season", rate="rate", rate_n="rate_n",
                    moved=(c("team") != c("team_n")))  # fmt: skip


def owner_of(rows: pl.DataFrame, seed: int) -> dict:
    p = kept_pairs(rows)
    k = owners.kept(p, "rate", seed=seed)
    lo, hi = owners.kept_interval(p, "rate", seed=seed)
    return k | {"kept_lo": lo, "kept_hi": hi, "owner": E.kept_label(k["share_kept"])}


# ---------------------------------------------------------------- I90 and I91 (first)
def i90(d: dict, out: Report, seed: int) -> None:
    out(
        "\n== I90 (first, as the brief says): QB sacks per pressure on one pressure source, with "
        "an interval on share kept (a sack counted as a pressure; each season's level out)"
    )
    q = T.season_rows(d["games"], d["teams"], T.BY_NAME["qb_sack_per_press"])
    halves = {
        "2016-2022 (the old provider)": (2016, 2021),
        "2023-2024 (the new provider)": (2023, 2023),
    }
    for name, (a, b) in halves.items():
        p = kept_pairs(q).filter(c("season").is_between(a, b))
        k = owners.kept(p, "rate", seed=seed)
        lo, hi = owners.kept_interval(p, "rate", seed=seed)
        out(f"  {name}: {k['pairs']} pairs ({k['movers']} movers); repeat {k['repeat']:.2f} "
            f"({k['lo90']:.2f} to {k['hi90']:.2f}); movers keep {100 * k['share_kept']:.0f}% "
            f"(90% {100 * lo:.0f}% to {100 * hi:.0f}%)")  # fmt: skip
        out.metric(f"i90_kept_{a}", k["share_kept"])
    for name, trait in (
        ("QB sacks per dropback", "qb_sack_rate"),
        ("a lineman's team's sacks per dropback on his dropbacks", "ol_sack_rate"),
    ):
        r = T.season_rows(d["games"], d["teams"], T.BY_NAME[trait])
        o = owner_of(r, seed)
        out(f"  {name}, 2016-2024: repeat {o['repeat']:.2f}; movers keep "
            f"{100 * o['share_kept']:.0f}% (90% {100 * o['kept_lo']:.0f}% to "
            f"{100 * o['kept_hi']:.0f}%; {o['movers']} movers)")  # fmt: skip
        out.metric(f"i90_{trait}_kept", o["share_kept"])


def roles(path: Path | None = None) -> pl.DataFrame:
    """roles-archetypes' fine role per defensive player-season (his main team's row: most snaps)."""
    path = path or get_config().zone("outputs") / "roles-archetypes" / ROLES_RUN / "history.parquet"
    h = pl.read_parquet(path).filter(c("side") == "defense")
    return (h.sort("snaps", descending=True).group_by("gsis_id", "season", maintain_order=True)
            .first().select("gsis_id", "season", "role", "sure"))  # fmt: skip


def sacks_target(d: dict, out: Report, seed: int, role: pl.DataFrame) -> dict:
    """The brief's pass-rusher test (next season's sacks against past sacks) and I91/I170
    (within the pass-rusher role). Forecasts of next season's centred sacks per dropback:
    raw past sacks; past sacks shrunk (M1); and a walk-forward fit on shrunk past sacks and
    shrunk pressures (each with its own k)."""
    out("\n== Pass rushers: next season's sacks per on-field dropback (centred), the brief's "
        "no-noise target for them, and I91 / I170 within the pass-rusher role")  # fmt: skip
    res = {}
    pooled = []
    s_all = T.season_rows(d["games"], d["teams"], T.BY_NAME["def_sack_rate"])
    p_all = T.season_rows(d["games"], d["teams"], T.BY_NAME["press_rate"])
    for grp in ("DL", "OLB"):
        s, pr = s_all.filter(c("group") == grp), p_all.filter(c("group") == grp)
        ps = T.rungs(T.pairs(s, d["games"], s_all))
        pp = T.rungs(T.pairs(pr, d["games"], p_all)).select(
            "gsis_id", "season", m1_press="m1", x_press="x", n_press="n", k_press="k"
        )
        p = ps.join(pp, on=["gsis_id", "season"]).join(role, on=["gsis_id", "season"], how="left")
        pooled.append(p)
        p = with_both(p)
        out(
            f"  {grp} roles in the input season: "
            + ", ".join(
                f"{r} {n}"
                for r, n in p.group_by("role").len().sort("len", descending=True).iter_rows()
            )
        )
        for label, q in (("all", p), ("pass-rusher role", p.filter(c("role") == "pass rusher"))):
            q = q.drop_nulls("both")
            if q.height < 60:
                out(f"  {grp} {label}: {q.height} rows, too few")
                continue
            g_m1 = E.gain(q, "m1", "raw", seed)
            g_add = E.gain(q, "both", "pull", seed)
            g_raw = E.gain(q, "both", "raw", seed)
            cp = copies_both(p, label, seed)
            counts = g_add.clear() and g_add.share > max(cp)
            won = E.seasons_won(q, "both", "pull")
            out(f"  {grp} {label} ({q.height} rows, target seasons "
                f"{q['season'].min() + 1}-{q['season'].max() + 1}): shrunk sacks against raw "
                f"{E.fmt(g_m1)}; pressures added to shrunk sacks {E.fmt(g_add)} (copies' best "
                f"{pct(max(cp))}; counts: {counts}; seasons won {won[0]} of {won[1]}); the pair "
                f"against raw past sacks {E.fmt(g_raw)}")  # fmt: skip
            tag = f"sacks_{grp}_{'role' if label != 'all' else 'all'}"
            out.metric(f"{tag}_added", g_add.share)
            res[(grp, label)] = (g_add, counts)
    # both groups' pass rushers together (each still centred on its own group)
    p = with_both(pl.concat(pooled, how="diagonal_relaxed").sort("season"))
    q = p.filter(c("role") == "pass rusher").drop_nulls("both")
    g_add = E.gain(q, "both", "pull", seed)
    cp = copies_both(p, "role", seed)
    out(f"  DL and OLB pass-rusher role together ({q.height} rows): pressures added to shrunk "
        f"sacks {E.fmt(g_add)} (copies' best {pct(max(cp))}; counts: "
        f"{g_add.clear() and g_add.share > max(cp)})")  # fmt: skip
    out.metric("sacks_pooled_role_added", g_add.share)
    return res


def with_both(p: pl.DataFrame, shuffle_press: bool = False, seed: int = 0) -> pl.DataFrame:
    """`both`: next season's sacks on shrunk past sacks and shrunk pressures, each target
    season fit on earlier pairs (no intercept, weighted by next season's dropbacks)."""
    if shuffle_press:
        p = T.shuffled(p, ("m1_press",), seed)
    s = p["season"].to_numpy()
    X = np.column_stack([p["m1"].to_numpy(), p["m1_press"].to_numpy()])
    y, w = p["y"].to_numpy(), p["w"].to_numpy()
    both = np.full(p.height, np.nan)
    for t in np.unique(s):
        tr = s < t
        if tr.sum() < 30:
            continue
        b = T._wls(X[tr], y[tr], w[tr])
        both[s == t] = X[s == t] @ b
    return p.with_columns(both=pl.Series(both).fill_nan(None))


def copies_both(p: pl.DataFrame, label: str, seed: int) -> list[float]:
    out = []
    for i in range(E.COPIES):
        q = with_both(p, True, seed + 9000 + i)
        if label != "all":
            q = q.filter(c("role") == "pass rusher")
        out.append(E.gain(q.drop_nulls("both"), "both", "pull", draws=10).share)
    return out


# ---------------------------------------------------------------- the ladder
def ladder(trait: T.Trait, grp: str, rows: pl.DataFrame, games: pl.DataFrame, out: Report,
           seed: int, k_rows: pl.DataFrame | None = None) -> dict:  # fmt: skip
    """The ladder for one trait and group: raw -> shrunk (M1) -> second pull -> owner split,
    each kept only where it clears the rung below; the champion's signal test; ranges."""
    pr = T.pairs(rows, games, k_rows)
    p = T.rungs(pr)
    q = E.scored(p)
    g = {
        "m1_raw": E.gain(q, "m1", "raw", seed), "m1_avg": E.gain(q, "m1", "avg", seed),
        "flat_raw": E.gain(q, "flat", "raw", seed), "m1_flat": E.gain(q, "m1", "flat", seed),
        "pull_m1": E.gain(q, "pull", "m1", seed), "split_m1": E.gain(q, "split", "m1", seed),
        "pull_flat": E.gain(q, "pull", "flat", seed),
    }  # fmt: skip
    cp_n = E.copies(pr, "m1", "raw", ("n",), seed=seed)  # a diagnostic (decision 0051, call 23)
    champ = T.SHRINK if g[f"{T.SHRINK}_raw"].clear() else "raw"  # decision 0051 call 30
    if champ == "m1" and g["pull_m1"].clear():
        champ = "pull"
    below = champ
    g["split_below"] = E.gain(q, "split", below, seed)
    cp_t = E.copies(pr, "split", below, ("team_change",), seed=seed)
    split_counts = g["split_below"].clear() and g["split_below"].share > max(cp_t)
    if split_counts and champ != "raw":
        champ = "split"
    sig = E.gain(q, champ, "avg", seed)
    cp_all = E.copies(pr, champ, "avg", ("x", "n", "team_change"), seed=seed)
    signal = sig.share > max(cp_all)
    mv = q.filter(c("moved"))
    g_mv0 = E.gain(mv, "split0", "m1", seed) if mv.height >= 25 else None
    g_mv = E.gain(mv, "split", below, seed) if mv.height >= 25 else None
    won = E.seasons_won(q, champ, "raw")
    rr = E.range_report(q, champ)
    name = f"{trait.name} {grp}"
    rel = float(np.median(q["n"] / (q["n"] + q["k"])))
    out(f"\n  {name}: {trait.label}; {q.height} scored pairs ({int(q['moved'].sum())} movers), "
        f"target seasons {q['season'].min() + 1}-{q['season'].max() + 1}; k {q['k'][-1]:.0f} "
        f"(per {trait.unit}; a typical season's reliability {rel:.2f})")  # fmt: skip
    out(f"    rung 2 (shrunk) against rung 1 (raw): {E.fmt(g['m1_raw'])}; against the position's "
        f"average {E.fmt(g['m1_avg'])}")  # fmt: skip
    out(f"    do his chances matter? one flat pull against raw {E.fmt(g['flat_raw'])}; shrunk "
        f"against the flat pull {E.fmt(g['m1_flat'])}; chances shuffled (copies' best against "
        f"raw) {pct(max(cp_n))}")  # fmt: skip
    out(f"    rung 2b (second pull, I156) against rung 2: {E.fmt(g['pull_m1'])} (slope "
        f"{q['b_pull'][-1]:.2f}); against the flat pull {E.fmt(g['pull_flat'])}")  # fmt: skip
    out(f"    rung 3 (owner split) against {below}: {E.fmt(g['split_below'])}; copies' best "
        f"{pct(max(cp_t))}; counts: {split_counts} (own {q['b_own'][-1]:.2f}, team change "
        f"{q['b_team'][-1]:.2f})")  # fmt: skip
    if g_mv is not None:
        out(f"    movers only ({mv.height}): rung 3 against {below} {E.fmt(g_mv)}; I171 as "
            f"pre-registered (rung 3 as first built against rung 2) {E.fmt(g_mv0)}")  # fmt: skip
    out(
        f"    champion: {champ}; against the average {E.fmt(sig)}, copies' best "
        f"{pct(max(cp_all))}, signal: {signal}; against raw: seasons won {won[0]} of {won[1]}"
    )
    out(
        f"    80% ranges: coverage {100 * rr['coverage']:.1f}% (thirds of chances "
        + ", ".join(f"{100 * x:.0f}%" for x in rr["by_third"])
        + f"); range score against the average's range {pct(rr['range_gain'])}"
    )
    for k_, v in g.items():
        out.metric(f"{trait.name}_{grp}_{k_}", v.share)
    out.metric(f"{trait.name}_{grp}_coverage", rr["coverage"])
    return {"p": p, "q": q, "gains": g, "champ": champ, "below": below,
            "split_counts": split_counts,
            "signal": signal, "ranges": rr, "movers": g_mv, "movers0": g_mv0, "won": won,
            "sig": sig, "copies_n": max(cp_n), "copies_all": max(cp_all)}  # fmt: skip


def pooled_k(trait: T.Trait, rows: pl.DataFrame, games: pl.DataFrame, out: Report, seed: int):
    """I172: one k per group against one k over the trait's groups (pooled noise and spread,
    each group still centred on its own mean; what ships, decision 0051 call 24), rung 2, on
    the same rows."""
    pooled = T.rungs(T.pairs(rows, games)).rename({"m1": "m1_pooled"})
    per = pl.concat([T.rungs(T.pairs(rows.filter(c("group") == g), games))
                     for g in trait.groups], how="diagonal_relaxed")  # fmt: skip
    q = per.join(pooled.select("gsis_id", "season", "m1_pooled"), on=["gsis_id", "season"])
    q = E.scored(q)
    g = E.gain(q, "m1", "m1_pooled", seed)
    out(f"  I172 {trait.name} ({'+'.join(trait.groups)}): k per group against one pooled k "
        f"{E.fmt(g)} ({q.height} rows)")  # fmt: skip
    out.metric(f"i172_{trait.name}", g.share)


def line(d: dict, out: Report, seed: int) -> dict:
    """The line's pressure over expected, a team-season trait (the line, not one lineman)."""
    ln = d["line"].with_columns(gsis_id=c("team"))
    teams = ln.select(pid="team", season="season", team="team", position=pl.lit("QB")).unique()
    rows = T.season_rows(ln, teams, T.LINE)
    rows = rows.with_columns(group=pl.lit("TEAM"))
    p = T.rungs(T.pairs(rows, ln))
    q = p.drop_nulls("pull")
    g1, g2 = E.gain(q, "m1", "raw", seed), E.gain(q, "pull", "m1", seed)
    o = owners.kept(kept_pairs(rows), "rate", seed=seed)
    out(f"\n  line_poe (the line's pressure over expected, per team-season dropback): "
        f"{q.height} scored team-seasons; k {q['k'][-1]:.0f} dropbacks; repeat {o['repeat']:.2f}; "
        f"shrunk against raw {E.fmt(g1)}; second pull against shrunk {E.fmt(g2)}")  # fmt: skip
    out.metric("line_poe_m1_raw", g1.share)
    return {"rows": rows, "p": p}


# ---------------------------------------------------------------- consistency (test 2)
def consistency_rows(d: dict, out: Report) -> pl.DataFrame:
    from pcf.validation.consistency import consistency

    out("\n== Consistency (pcf.validation.consistency, per-game rates of players over each "
        "trait's season floor; unit = player)")  # fmt: skip
    res = []
    for t in T.TRAITS + T.EXTRA:
        rows = T.season_rows(d["games"], d["teams"], t)
        for grp in t.groups:
            ok = rows.filter(c("group") == grp).select("gsis_id", "season")
            g = d["games"].filter(c("trait") == t.name).join(ok, on=["gsis_id", "season"])
            g = g.group_by("gsis_id", "season", "week").agg(v=c("num").sum() / c("den").sum())
            r = consistency(g, ["v"], unit="gsis_id")
            r = r.with_columns(measure=pl.lit(f"{t.name} {grp}"))
            res.append(r)
    tab = pl.concat(res, how="diagonal_relaxed")
    for row in tab.iter_rows(named=True):
        out(
            f"  {row['measure']:24} "
            + ", ".join(
                f"{k} {v:.3f}" if isinstance(v, float) else f"{k} {v}"
                for k, v in row.items()
                if k != "measure"
            )
        )
    return tab


# ---------------------------------------------------------------- the yardstick
YARD = {"receiving": [("catch_rate", "WR")],
        "rushing": [("rb_yac", "RB"), ("rb_bt", "RB"), ("rb_multi_after", "RB")],
        "passing": [("qb_sack_rate", "QB"), ("qb_depth", "QB"), ("qb_ttt", "QB")]}  # fmt: skip


def _shuffled_prior(prior: pl.DataFrame, cols: Sequence[str], seed: int) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    key = prior["season"].cast(pl.String).to_numpy()
    order = np.arange(prior.height)
    for k in np.unique(key):
        idx = np.flatnonzero(key == k)
        order[idx] = idx[rng.permutation(len(idx))]
    return pl.concat([prior.select("gsis_id", "season"), prior.select(cols)[order]],
                     how="horizontal")  # fmt: skip


def yardstick(table: pl.DataFrame, out: Report, copies: int = 19) -> dict:
    from pcf.baselines.crude import yardstick as Y

    out("\n== The yardstick (crude forecaster, rest-of-season boards, beside participation; "
        f"{copies} copies shuffled within season and position)")  # fmt: skip
    res = {}
    for target, pieces in YARD.items():
        board = Y.load_board(target, "rest")
        keys = board.keys
        rows = board.features.select(*keys, "season")
        sets = {}
        for trait, grp in pieces:
            t = table.filter((c("trait") == trait) & (c("group") == grp))
            sets[f"{trait} shrunk"] = t.select("gsis_id", season=c("season") + 1,
                                              **{f"soe_{trait}": c("shrunk_c")})  # fmt: skip
            sets[f"{trait} raw"] = t.select("gsis_id", season=c("season") + 1,
                                           **{f"soe_{trait}_raw": c("rate_c")})  # fmt: skip
        if len(pieces) > 1:
            allp = None
            for trait, _ in pieces:
                f = sets[f"{trait} shrunk"]
                allp = f if allp is None else allp.join(f, on=["gsis_id", "season"], how="full",
                                                        coalesce=True)  # fmt: skip
            sets["all shrunk"] = allp
        for name, prior in sets.items():
            cols = [x for x in prior.columns if x not in ("gsis_id", "season")]
            frame = rows.join(prior, on=["gsis_id", "season"], how="left").drop("season")
            r = Y.score_input(board, frame, f"soe {name}", beside=("participation",))
            nulls = []
            for k in range(copies):
                sh = _shuffled_prior(prior.drop_nulls(), cols, get_config().seed + 5000 + k)
                fr = rows.join(sh, on=["gsis_id", "season"], how="left").drop("season")
                sc = Y.score_input(board, fr, f"copy {k}", beside=("participation",))
                nulls.append(sc["alone"])
            counts = r["alone_lo"] > 0 and r["alone"] > max(nulls)
            out(f"  {target:9} {name:22}: {100 * r['alone']:+.2f}% of the squared error (90% "
                f"{100 * r['alone_lo']:+.2f} to {100 * r['alone_hi']:+.2f}); range score "
                f"{100 * r['range_alone']:+.2f}%; copies' best {100 * max(nulls):+.2f}%; "
                f"{r['verdict']}; counts: {counts} ({r['rows']} rows)")  # fmt: skip
            res[(target, name)] = (r, max(nulls), counts)
            out.metric(f"yard_{target}_{name.replace(' ', '_')}", r["alone"])
    return res


# ---------------------------------------------------------------- sanity
def names() -> pl.DataFrame:
    from pcf.data.gateway import END_OF_TIME, Gateway, TableSource

    out = []
    for s in D.SEASONS:
        v = Gateway(TableSource(seasons=[s])).view(END_OF_TIME, "retrospective",
                                                   {"player_game": ("roster",)})  # fmt: skip
        out.append(v.table("player_game", seasons=[s]).select("gsis_id", name="full_name"))
    return pl.concat(out).drop_nulls().unique("gsis_id", keep="last")


def sanity(h: pl.DataFrame, nm: pl.DataFrame, out: Report, season: int = 2024) -> None:
    out(f"\n== Sanity lists: each trait's top and bottom 10 by the shrunk rate, {season}")
    h = h.filter(c("season") == season).join(nm, on="gsis_id", how="left")
    for (trait, grp), g in sorted(h.group_by("trait", "group"), key=lambda x: x[0]):
        top = g.sort("shrunk", descending=True).head(10)
        bot = g.sort("shrunk").head(10)

        def f(d):
            return ", ".join(f"{n} {t} {r:.3g}" for n, t, r in
                             zip(d["name"], d["team"], d["shrunk"], strict=True))  # fmt: skip

        out(f"  {trait} {grp} top: {f(top)}")
        out(f"  {trait} {grp} bottom: {f(bot)}")


# ---------------------------------------------------------------- main
def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-log", action="store_true", help="the report only: no MLflow run")
    ap.add_argument("--no-yardstick", action="store_true")
    args = ap.parse_args(argv)
    warnings.filterwarnings("ignore", message="Objective did not converge")
    seed = get_config().seed
    out = Report()
    d = D.load()
    role = roles()
    olb = d["teams"].filter(c("position") == "OLB").height
    d["teams"] = T.regroup(d["teams"], role)  # decision 0051 call 31
    moved = d["teams"].filter((c("roster_position") == "OLB") & (c("position") == "ILB")).height
    out(f"skill-over-expected build: {d['games'].height:,} player-game trait rows, "
        f"seasons 2016-2024 (PFR's charting 2018-2024); the 2025 vault closed; rung 2 is "
        f"{T.SHRINK}; {moved} of {olb} OLB player-seasons count as ILB (off-ball)")  # fmt: skip
    i90(d, out, seed)
    sacks_target(d, out, seed, role)
    out(
        "\n== The ladder, every trait and group (next season's centred rate; gains are shares "
        "of the base's squared error, weighted by next season's chances; 90% from players)"
    )
    results, history, owners_ = {}, [], {}
    for t in T.TRAITS + T.EXTRA:
        rows = T.season_rows(d["games"], d["teams"], t)
        for grp in t.groups:
            r = rows.filter(c("group") == grp)
            res = ladder(t, grp, r, d["games"], out, seed, rows)
            o = owner_of(r, seed)
            out(
                f"    owner: {o['owner']} (repeat {o['repeat']:.2f}, {o['lo90']:.2f} to "
                f"{o['hi90']:.2f}; movers keep {100 * o['share_kept']:.0f}%, 90% "
                f"{100 * o['kept_lo']:.0f}% to {100 * o['kept_hi']:.0f}%; {o['movers']} movers)"
            )
            results[(t.name, grp)], owners_[(t.name, grp)] = res, o
            if t in T.TRAITS:
                rung = res["champ"] if res["champ"] != "split" else res["below"]
                history.append(H.rows_for(r, d["games"], res["p"], rung, o["owner"],
                                          o["share_kept"], d["known"], rows))  # fmt: skip
        if len(t.groups) > 1:
            pooled_k(t, rows, d["games"], out, seed)
    line(d, out, seed)
    table = pl.concat(history)
    cons = consistency_rows(d, out)
    if not args.no_yardstick:
        yardstick(table, out)
    sanity(table, names(), out)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(out.lines) + "\n", encoding="utf-8")
    cons.write_csv(REPORT.with_name("consistency.csv"))
    if args.no_log:
        table.write_parquet(D.cache_dir() / "history_preview.parquet")
        return
    from pcf.core import tracking

    with tracking.attempt(PROJECT, train_end=table["train_end"].max(), name="skill-retro v1",
                          params={"traits": len(T.TRAITS), "copies": E.COPIES,
                                  "seasons": "2016-2024 (PFR 2018-2024)"}) as run:  # fmt: skip
        folder = get_config().zone("outputs") / PROJECT / run.info.run_id
        folder.mkdir(parents=True, exist_ok=True)
        table.write_parquet(folder / "history.parquet")
        tracking.log_metrics(out.metrics)
        tracking.log_text("\n".join(out.lines), "report.txt")
        print(
            f"\nhistory: {folder / 'history.parquet'} ({table.height:,} rows); "
            f"run {run.info.run_id}"
        )


if __name__ == "__main__":
    main()
