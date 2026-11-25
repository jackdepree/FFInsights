"""Stabilization, method 1 (EXPLORATION.md): reliability curves, the noise ceiling and the plain
pull-back (M1), players and teams. Discovery only, 2006-2024; the 2025 vault is closed.

Run from pcf/:  python projects/stabilization/explore/m1_curves.py   (writes m1_curves.txt)
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from stab_common import MEASURES, TEAM_MEASURES, Say, components, fit_m1, load, player_seasons, wls_r  # noqa: E402

c = pl.col
RNG = np.random.default_rng(1)
BINS = [10, 25, 50, 100, 200, 400, 800]
say = Say(Path(__file__).with_suffix(".txt"))


def halves(game: pl.DataFrame, keys: list[str]) -> pl.DataFrame:
    """Odd and even games of each season (by week order), summed."""
    g = game.sort("week").with_columns(h=(c("week").rank("ordinal").over(keys) % 2))
    a = g.group_by(*keys, "h").agg(num=c("num").sum(), den=c("den").sum())
    return a.filter(c("h") == 1).join(a.filter(c("h") == 0), on=keys, suffix="_e").select(
        *keys, xo=c("num") / c("den"), no="den", xe=c("num_e") / c("den_e"), ne="den_e")


def curve(h: pl.DataFrame, mu_col=None):
    """Split-half r by the halves' attempts (the smaller half), weighted by it."""
    h = h.with_columns(n=pl.min_horizontal("no", "ne"))
    rows = []
    for lo, hi in zip([0] + BINS[:-1], BINS):
        b = h.filter((c("n") > lo * 0.7) & (c("n") <= hi * 1.4) & (c("n") >= max(lo, 3)))
        if b.height < 40:
            continue
        x, y = b["xo"].to_numpy(), b["xe"].to_numpy()
        if mu_col:
            x, y = x - b[mu_col].to_numpy(), y - b[mu_col].to_numpy()
        rows.append((hi, float(np.median(b["n"].to_numpy())), float(np.corrcoef(x, y)[0, 1]), b.height))
    return rows


def fit_ck(rows):
    """r(n) = c n / (n + k): grid over k, c by least squares."""
    best = None
    ns = np.array([r[1] for r in rows])
    rs = np.array([r[2] for r in rows])
    for k in np.geomspace(1, 5000, 400):
        f = ns / (ns + k)
        cc = float(np.clip((f @ rs) / (f @ f), 0, 1.2))
        e = float(((rs - cc * f) ** 2).sum())
        if best is None or e < best[0]:
            best = (e, cc, k)
    return best[1], best[2]


def forecast(s: pl.DataFrame, game: pl.DataFrame, measure: str, first_target: int):
    """Next season's rate: raw, the position's average, M1; walk-forward (fit before the target)."""
    out = []
    m = s.filter(c("measure") == measure)
    for T in range(first_target, 2025):
        mus, s2, t2, k = fit_m1(s, game, measure, T)
        a = m.filter(c("season") == T - 1).select("gsis_id", "pos", x=c("num") / c("den"), n="den")
        b = m.filter(c("season") == T).select("gsis_id", y=c("num") / c("den"), w="den")
        d = a.join(b, on="gsis_id").filter(c("pos").is_in(list(mus)))
        if d.height == 0:
            continue
        mu = d["pos"].replace_strict(mus).to_numpy()
        x, n = d["x"].to_numpy(), d["n"].to_numpy()
        out.append(pl.DataFrame({"gsis_id": d["gsis_id"], "T": T, "y": d["y"], "w": d["w"], "raw": x, "pos_mean": mu,
                                 "m1": mu + n / (n + k) * (x - mu), "n": n, "s2": s2, "t2": t2}))  # fmt: skip
    return pl.concat(out) if out else None


def gains(f: pl.DataFrame, a: str, b: str, draws=1000):
    """Share of b's weighted squared error that a removes; players resampled."""
    e = f.with_columns(ea=c("w") * (c("y") - c(a)) ** 2, eb=c("w") * (c("y") - c(b)) ** 2)
    p = e.group_by("gsis_id").agg(ea=c("ea").sum(), eb=c("eb").sum())
    ea, eb = p["ea"].to_numpy(), p["eb"].to_numpy()
    idx = RNG.integers(0, len(ea), (draws, len(ea)))
    g = 1 - ea[idx].sum(1) / eb[idx].sum(1)
    return 1 - ea.sum() / eb.sum(), np.quantile(g, 0.05), np.quantile(g, 0.95)


def main() -> None:
    s, game = player_seasons()
    say("# Method 1: reliability curves, the noise ceiling and M1 (2026-11-25)", "",
        "Per measure: mu by position, the noise per attempt and the true spread pooled around each position's mean (seasons 2006-2024, or from its first year),",
        "k = noise / spread (the 50% point, in attempts), the curve's ceiling c from split halves by games,",
        "the true rate's season-to-season correlation (observed r over the reliabilities), and M1's next-season test.", "")
    rows = []
    for measure in MEASURES:
        mus, s2, t2, k = fit_m1(s, game, measure, 2025)
        m = s.filter(c("measure") == measure)
        h = halves(game.filter(c("measure") == measure).join(m.select("key", "pos"), on="key", how="left").drop("pos_right", strict=False), ["key"])
        psm = m.filter(c("den") >= 10).group_by("pos", "season").agg(mu=c("num").sum() / c("den").sum())
        h = h.join(m.select("key", "pos", "season"), on="key").join(psm, on=["pos", "season"])
        cv = curve(h, "mu")
        cc, kk = fit_ck(cv) if len(cv) >= 3 else (float("nan"), float("nan"))
        # season to season
        a = m.select("gsis_id", "season", "pos", x=c("num") / c("den"), n="den")
        pr = a.join(a.with_columns(c("season") - 1), on=["gsis_id", "season"], suffix="2")
        pr = pr.filter((c("n") >= 10) & (c("n2") >= 10)).join(psm, on=["pos", "season"]).join(psm.select("pos", season=c("season") - 1, mu2="mu"), on=["pos", "season"])
        x, y, n1, n2 = (pr["x"] - pr["mu"]).to_numpy(), (pr["x2"] - pr["mu2"]).to_numpy(), pr["n"].to_numpy(), pr["n2"].to_numpy()
        w = 1 / (1 / n1 + 1 / n2)
        r_obs = wls_r(x, y, w)
        rel1, rel2 = np.average(n1 / (n1 + k), weights=w), np.average(n2 / (n2 + k), weights=w)
        rho = r_obs / np.sqrt(rel1 * rel2)
        typical = float(np.median(m.filter(c("den") >= 10)["den"].to_numpy()))
        first = int(m["season"].min())
        f = forecast(s, game, measure, max(first + 3, 2009))
        g_raw = gains(f, "m1", "raw") if f is not None else (np.nan,) * 3
        g_pos = gains(f, "m1", "pos_mean") if f is not None else (np.nan,) * 3
        ceil = float(np.average(f["w"] / (f["w"] + k), weights=f["w"])) if f is not None else np.nan
        rows.append(dict(measure=measure, group=MEASURES[measure], first=first, k=k, typical=typical,
                         rel_typical=typical / (typical + k), c=cc, k_split=kk, r_season=r_obs, rho=rho,
                         ceiling=ceil, m1_vs_raw=g_raw, m1_vs_pos=g_pos, pairs=pr.height, curve=cv))  # fmt: skip
    say("| Measure | Group | From | k (50% point, attempts) | Typical season (attempts) | Reliability at a typical season | Split-half ceiling c (its k) | Season r (observed) | True rate's season r | Ceiling next season | M1 against raw | M1 against the position's average |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        say(f"| {r['measure']} | {r['group']} | {r['first']} | {r['k']:.0f} | {r['typical']:.0f} | {r['rel_typical']:.2f} | {r['c']:.2f} ({r['k_split']:.0f}) | {r['r_season']:.2f} | {r['rho']:.2f} | {r['ceiling']:.2f} | "
            f"{r['m1_vs_raw'][0]:+.1%} ({r['m1_vs_raw'][1]:+.1%} to {r['m1_vs_raw'][2]:+.1%}) | {r['m1_vs_pos'][0]:+.1%} ({r['m1_vs_pos'][1]:+.1%} to {r['m1_vs_pos'][2]:+.1%}) |")
    say("", "Split-half curves (attempts in the smaller half: observed r, against n/(n+k) from the moments):")
    for r in rows:
        say(f"- {r['measure']}: " + "; ".join(f"{n:.0f}: {rr:.2f} (pred {n / (n + r['k']):.2f}, {cnt})" for _, n, rr, cnt in r["curve"]))

    # I104: k by season
    say("", "## I104: the 50% point by season (each season's own moments; pooled k in brackets)")
    for measure in ["tprr", "yprr", "adot", "catch_oe", "yac_oe", "hitsack", "cpoe", "press_per_snap", "catch_allowed"]:
        ks = []
        for T in range(2016, 2025):
            sub = s.filter((c("measure") == measure) & (c("season") == T))
            if sub.height < 50:
                continue
            mus, s2, t2, k = fit_m1(sub, game, measure, T + 1)
            ks.append(f"{T} {k:.0f}")
        pooled = [r["k"] for r in rows if r["measure"] == measure][0]
        say(f"- {measure} ({pooled:.0f}): " + ", ".join(ks))

    # teams: game halves, quarter halves, season to season
    say("", "## Teams (each team-season centred by its season's league rate)", "", "| Measure | Side | k (plays) | Typical season | Reliability, season | Split-half r, games (n) | Split-half r, quarters 1+3 against 2+4 (n) | Season r | True rate's season r |", "|---|---|---|---|---|---|---|---|---|")
    tg, tq = load("team_game"), load("team_quarter")
    for side in ("off", "def"):
        for measure in TEAM_MEASURES:
            g = tg.filter((c("side") == side) & (c("measure") == measure)).with_columns(key=pl.concat_str("team", pl.lit("|"), c("season").cast(pl.Utf8)))
            # centred by the season's league rate (league rates shift: shotgun use rose every year), so a season's level isn't read as the team's
            lm = g.group_by("season").agg(lm=c("num").sum() / c("den").sum())
            g = g.join(lm, on="season").with_columns(num=c("num") - c("lm") * c("den"))
            ts = g.group_by("key", "team", "season").agg(num=c("num").sum(), den=c("den").sum(), games=pl.len())
            mu, s2, t2 = components(ts, g)
            k = s2 / t2
            hg = halves(g, ["key"])
            r_g = wls_r(hg["xo"].to_numpy(), hg["xe"].to_numpy(), np.ones(hg.height))
            q = tq.filter((c("side") == side) & (c("measure") == measure) & c("qtr").cast(pl.Int64).is_in([1, 2, 3, 4])).with_columns(key=pl.concat_str("team", pl.lit("|"), c("season").cast(pl.Utf8)))
            q = q.join(lm, on="season").with_columns(num=c("num") - c("lm") * c("den"))
            qa = q.with_columns(h=c("qtr").cast(pl.Int64) % 2).group_by("key", "h").agg(num=c("num").sum(), den=c("den").sum())
            qh = qa.filter(c("h") == 1).join(qa.filter(c("h") == 0), on="key", suffix="_e").select(xo=c("num") / c("den"), xe=c("num_e") / c("den_e"), no="den", ne="den_e")
            r_q = wls_r(qh["xo"].to_numpy(), qh["xe"].to_numpy(), np.ones(qh.height))
            a = ts.select("team", "season", x=c("num") / c("den"), n="den")
            pr = a.join(a.with_columns(c("season") - 1), on=["team", "season"], suffix="2")
            r_s = wls_r(pr["x"].to_numpy(), pr["x2"].to_numpy(), np.ones(pr.height))
            n1, n2 = pr["n"].to_numpy(), pr["n2"].to_numpy()
            rho = r_s / np.sqrt(np.mean(n1 / (n1 + k)) * np.mean(n2 / (n2 + k)))
            typ = float(np.median(ts["den"].to_numpy()))
            say(f"| {measure} | {side} | {k:.0f} | {typ:.0f} | {typ / (typ + k):.2f} | {r_g:.2f} ({np.median(np.minimum(hg['no'], hg['ne'])):.0f}) | {r_q:.2f} ({np.median(np.minimum(qh['no'], qh['ne'])):.0f}) | {r_s:.2f} | {rho:.2f} |")
    say.save()


if __name__ == "__main__":
    main()
