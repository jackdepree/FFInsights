# ruff: noqa: E501
"""opportunity-quality, the CEO's spot-check of R17 and the luck measure (2026-11-22).

Pre-registered in RESULTS.md ("Spot-check") before this ran. Four versions of the measure:
- as built: situation-only expected points, chances independent;
- I101: game-level noise (φ per position, `regression.game_noise`);
- I100: position in the expected-points models (`build_opportunity_variant("position")`);
- both.
Each walks forward on 2016-2024 (picks the version) and on the 2025 vault (judges it). Then the
walk through R17 on the as-built rows: where B lost to A for tight ends, and what would change it.

Run from pcf/ (after `build_opportunity_variant("position")`):
    python projects/opportunity-quality/explore/spotcheck.py
It writes projects/opportunity-quality/build/spotcheck.txt.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.gateway import Gateway
from pcf.data.tables.build import read_opportunity_variant
from pcf.experts.opportunity_quality import checks

c = pl.col
BACKTEST = list(range(2016, 2025))
VAULT = [2025]
VERSIONS = {  # name: (expected-points models, game-level noise); the tie order is this order
    "as built": ("situation", False),
    "I101 (game noise)": ("situation", True),
    "I100 (position)": ("position", False),
    "both": ("position", True),
}
OUT = Path(__file__).resolve().parents[1] / "build" / "spotcheck.txt"
CACHE = get_config().zone("interim") / "opportunity_quality" / "spotcheck"


def skill(d: pl.DataFrame, a: str, b: str) -> float:
    """Share of `b`'s weighted squared error (rest-of-season gap) that `a` removes, %."""
    ea = float((d["m"] * (d["future"] - d[a]) ** 2).sum())
    eb = float((d["m"] * (d["future"] - d[b]) ** 2).sum())
    return 100 * (1 - ea / eb)


def summary(h: pl.DataFrame) -> dict:
    d = h.filter(c("scorable"))
    y = d["closed"].cast(pl.Float64).to_numpy()
    p = d["p_close_B_cal"].to_numpy()
    err, slope, _ = checks.calibration_bands(p, y)
    base = d["base_rate"].to_numpy()
    brier = float(np.mean((p - y) ** 2))
    brier_base = float(np.mean((base - y) ** 2))
    out = {
        "rows": d.height,
        "B_vs_A": skill(d, "mean_B", "mean_A"),
        "A_vs_luck": skill(d, "mean_A", "mean_luck"),
        "B_vs_luck": skill(d, "mean_B", "mean_luck"),
        "cal_err": err,
        "cal_slope": slope,
        "share_50_60": 100 * float(np.mean((p >= 0.5) & (p < 0.6))),
        "share_out_40_70": 100 * float(np.mean((p < 0.4) | (p >= 0.7))),
        "brier_skill": 100 * (1 - brier / brier_base),
        "inside": 100 * float(((d["future"] >= d["future_q10"]) & (d["future"] <= d["future_q90"])).mean()),
    }
    for pos in ("RB", "WR", "TE"):
        g = d.filter(c("position") == pos)
        out[f"B_vs_A_{pos}"] = skill(g, "mean_B", "mean_A")
        out[f"A_vs_luck_{pos}"] = skill(g, "mean_A", "mean_luck")
    bands = []
    for lo, hi in [(20, 50), (50, 100), (100, 200), (200, 400), (400, 10_000)]:
        g = d.filter(c("n").is_between(lo, hi - 1e-9))
        w, dx, dy = g["m"].to_numpy(), (g["gap"] - g["mu"]).to_numpy(), (g["future"] - g["mu"]).to_numpy()
        bands.append((lo, hi, g.height, float(g["k_B"].mean()), float(np.sum(w * dx * dy) / np.sum(w * dx * dx))))
    out["bands"] = bands
    out["phi"] = {pos: float(g["phi"].mean()) for (pos,), g in d.group_by("position")}
    return out


def fmt(name: str, s: dict) -> list[str]:
    phi = ", ".join(f"{k} {v:.2f}" for k, v in sorted(s["phi"].items()))
    return [
        f"  {name} ({s['rows']} rows; φ {phi})",
        f"    B against A {s['B_vs_A']:+.2f}% (RB {s['B_vs_A_RB']:+.2f}, WR {s['B_vs_A_WR']:+.2f}, TE {s['B_vs_A_TE']:+.2f}); "
        f"A against all luck {s['A_vs_luck']:+.2f}% (TE {s['A_vs_luck_TE']:+.2f}); B against all luck {s['B_vs_luck']:+.2f}%",
        f"    chance the gap closes (B, recalibrated): error {s['cal_err']:.1f} points, slope {s['cal_slope']:.2f}; "
        f"{s['share_50_60']:.1f}% of chances in 50-60%, {s['share_out_40_70']:.1f}% outside 40-70%; "
        f"Brier skill against the base rate {s['brier_skill']:+.2f}%",
        f"    future-gap range holds {s['inside']:.1f}%; kept share by chances (B's / seen): "
        + ", ".join(f"{lo}-{hi if hi < 10_000 else '+'} {k:.2f}/{seen:.2f}" for lo, hi, _, k, seen in s["bands"]),
    ]


def histories() -> dict[str, dict[str, pl.DataFrame]]:
    CACHE.mkdir(parents=True, exist_ok=True)
    frames = {"situation": checks.regression_frames(), "position": checks.regression_frames(variant=read_opportunity_variant("position"))}
    out = {}
    for name, (xfp, noise) in VERSIONS.items():
        out[name] = {}
        for tag, seasons in (("backtest", BACKTEST), ("vault", VAULT)):
            path = CACHE / f"{name.split(' ')[0].lower()}_{tag}.parquet"
            h = checks.regression_history(seasons, frames=frames[xfp], game_noise=noise)
            h.write_parquet(path)
            out[name][tag] = h
    return out


def pick(sums: dict[str, dict]) -> str:
    best = max(s["backtest"]["B_vs_A"] for s in sums.values())
    for name in VERSIONS:  # the tie order: simplest first
        if sums[name]["backtest"]["B_vs_A"] >= best - 0.1:
            return name
    raise AssertionError


def bar(s: dict, before: dict) -> list[tuple[str, bool, str]]:
    v, b = s["vault"], s["backtest"]
    t1 = v["B_vs_A"] >= 0.0 and v["B_vs_A_TE"] >= -0.5 and b["B_vs_A"] >= 0.5
    t2 = all(x["cal_err"] <= 2.0 and 0.80 <= x["cal_slope"] <= 1.25 for x in (v, b))
    t3 = b["share_50_60"] <= 60.0 and v["share_50_60"] <= 60.0 and v["brier_skill"] > before["vault"]["brier_skill"]
    return [
        ("1. B at least as good as A", t1, f"vault {v['B_vs_A']:+.2f}% (TE {v['B_vs_A_TE']:+.2f}), 2016-2024 {b['B_vs_A']:+.2f}%"),
        ("2. calibration stays honest", t2, f"vault {v['cal_err']:.1f} points, slope {v['cal_slope']:.2f}; 2016-2024 {b['cal_err']:.1f}, {b['cal_slope']:.2f}"),
        ("3. chances separate players more", t3, f"50-60% share {b['share_50_60']:.1f}% / {v['share_50_60']:.1f}% (2016-2024 / vault); "
         f"vault Brier skill {v['brier_skill']:+.2f}% against the build's {before['vault']['brier_skill']:+.2f}%"),
    ]


def walk_through(bt: pl.DataFrame, vault: pl.DataFrame) -> list[str]:
    """R17 in depth, on the as-built rows."""
    out = ["== R17 in depth (the as-built measure)"]
    d = pl.concat([bt, vault], how="diagonal_relaxed").filter(c("scorable"))
    out.append("  The position's level μ (fit on the 6 seasons before) against the rest of the season's actual average gap, per chance (weighted by chances):")
    lv = d.group_by("season", "position").agg(
        mu=c("mu").mean(), seen=(c("future") * c("m")).sum() / c("m").sum(), gap=(c("gap") * c("m")).sum() / c("m").sum(), rows=pl.len()
    ).sort("position", "season")
    for (pos,), g in lv.group_by("position", maintain_order=True):
        out.append(f"    {pos}: " + "; ".join(f"{r['season']} μ {r['mu']:+.3f} seen {r['seen']:+.3f}" for r in g.iter_rows(named=True)))
    te = vault.filter(c("scorable") & (c("position") == "TE"))
    out.append(f"  Vault tight ends: {te.height} rows, {te['gsis_id'].n_unique()} players")
    for lo, hi in [(20, 100), (100, 200), (200, 10_000)]:
        g = te.filter(c("n").is_between(lo, hi - 1e-9))
        if g.height:
            out.append(f"    {lo}-{hi if hi < 10_000 else '+'} chances behind: {g.height} rows, B against A {skill(g, 'mean_B', 'mean_A'):+.2f}%, "
                       f"B's kept share {g['k_B'].mean():.2f}, A's {g['kA'].mean():.2f}")
    # what would change it: the right level, and A's kept share inside B
    for label, frame in (("2016-2024", bt.filter(c("scorable"))), ("2025", vault.filter(c("scorable")))):
        seen = frame.group_by("season", "position").agg(mu_seen=(c("future") * c("m")).sum() / c("m").sum())
        o = frame.join(seen, on=["season", "position"]).with_columns(
            A_o=c("mu_seen") + c("kA") * (c("gap") - c("mu_seen")), B_o=c("mu_seen") + c("k_B") * (c("gap") - c("mu_seen"))
        )
        tes = o.filter(c("position") == "TE")
        out.append(f"  {label}, if μ had been the season's actual level (hindsight): B against A {skill(o, 'B_o', 'A_o'):+.2f}% (TE {skill(tes, 'B_o', 'A_o'):+.2f}%)")
    names = Gateway().source.part("player_game", "roster").select("gsis_id", "full_name").unique("gsis_id")
    loss = (
        te.with_columns(diff=c("m") * ((c("future") - c("mean_B")) ** 2 - (c("future") - c("mean_A")) ** 2))
        .group_by("gsis_id")
        .agg(rows=pl.len(), diff=c("diff").sum(), gap=c("gap").last(), n=c("n").last(), future=c("future").last(),
             k_B=c("k_B").last(), kA=c("kA").last(), mu=c("mu").last())
        .join(names, on="gsis_id", how="left")
        .sort("diff", descending=True)
    )
    total = float(loss["diff"].sum())
    top = loss.head(5)
    out.append(f"  The tight ends B lost most on (share of B's whole extra error over A for tight ends; total {total:.1f}):")
    for r in top.iter_rows(named=True):
        out.append(f"    {r['full_name']}: {100 * r['diff'] / total:.0f}%, {r['rows']} games; last gap {r['gap']:+.3f} on {r['n']:.0f} chances, "
                   f"rest of the season {r['future']:+.3f}; μ {r['mu']:+.3f}; kept B {r['k_B']:.2f} / A {r['kA']:.2f}")
    out.append(f"    the top 5 make {100 * float(top['diff'].sum()) / total:.0f}% of it")
    return out


def main() -> None:
    hs = histories()
    sums = {name: {tag: summary(h) for tag, h in v.items()} for name, v in hs.items()}
    lines = ["Spot-check of R17 and the luck measure (pre-registered in RESULTS.md, 2026-11-22)", ""]
    for tag, label in (("backtest", "2016-2024 (picks the version)"), ("vault", "the 2025 vault (judges the picked version; the others only reported)")):
        lines.append(f"== {label}")
        for name in VERSIONS:
            lines += fmt(name, sums[name][tag])
        lines.append("")
    chosen = pick(sums)
    lines.append(f"== The picked version (best B against A on 2016-2024, ties to the simpler): {chosen}")
    tests = bar(sums[chosen], sums["as built"])
    for label, ok, why in tests:
        lines.append(f"  {label}: {'passes' if ok else 'fails'} ({why})")
    lines.append(f"  better than before (all three): {'yes' if all(t[1] for t in tests) else 'no'}")
    lines.append("")
    lines += walk_through(hs["as built"]["backtest"], hs["as built"]["vault"])
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
