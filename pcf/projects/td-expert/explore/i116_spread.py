"""I116 (the CEO, 2026-11-24: "we need to resolve the wider spread fits"): a count wider than
Poisson for the rest-of-season forecasts. The champions' means (saved walks, 2016-2024) stay as
they are; only the spread around them changes. A negative binomial (variance mean + alpha *
mean^2) whose alpha is fit on the seasons before each tested one (their outcomes were known by
then), so 2017-2024 are tested. Versions: Poisson; alpha per position (the family's for teams);
alpha per position and window length (games left 1-5, 6-11, 12+); and, the second look, a spread
that grows more slowly with the mean (variance mean + alpha mean^power, both fit) per position and
window. Each judged on the chance of 1+ and 2+ and on the q10-q90 range.
Odds written before (IDEAS.md I116): 70% the players' 1+ error falls under 3 points with slope
in 0.9-1.1; 45% for thrown touchdowns. The vault (2025) is spent; the live 2026 ledger is the
only clean test.
"""
from pathlib import Path

import numpy as np
import polars as pl

from pcf.experts.td_expert.run import cache_dir, saved_dir
from pcf.validation import backtest, calibration
from pcf.validation.scores import fit_spread, negbin_log_loss, negbin_quantile

c = pl.col
OUT = Path(__file__).with_suffix(".txt")
TESTED = list(range(2017, 2025))
CHAMPIONS = {"skill": "volume+qb_rz", "thrown": "volume", "team": "volume"}

out = [__doc__.strip().split("\n")[0], f"tested {TESTED[0]}-{TESTED[-1]}", ""]


def bucket(g: pl.Expr) -> pl.Expr:
    return pl.when(g <= 5).then(pl.lit("1-5")).when(g <= 11).then(pl.lit("6-11")).otherwise(pl.lit("12+"))


def with_alpha(p: pl.DataFrame, by: list[str], power: float | None = 2.0) -> pl.DataFrame:
    """alpha for each tested season's rows, fit on the earlier seasons' rows of the same group."""
    parts = []
    for s in TESTED:
        train, test = p.filter(c("season") < s), p.filter(c("season") == s)
        groups = test.select(by).unique() if by else pl.DataFrame({"_": [0]})
        for g in groups.iter_rows(named=True):
            sel = pl.all_horizontal([c(k) == v for k, v in g.items()]) if by else pl.lit(True)
            tr, te = train.filter(sel), test.filter(sel)
            a, pw = fit_spread(tr["y"].to_numpy(), tr["mean"].to_numpy(), power)
            parts.append(te.with_columns(alpha=pl.lit(a), power=pl.lit(pw)))
    return pl.concat(parts)


def line(label: str, p: pl.DataFrame) -> str:
    rep = calibration.count_report(p)
    one, two = rep["one"], rep["two"]
    ok = "passes" if rep["passed"] else "fails"
    y, mu = p["y"].to_numpy(), p["mean"].to_numpy()
    a = p["alpha"].to_numpy() if "alpha" in p.columns else 0.0
    pw = p["power"].to_numpy() if "power" in p.columns else 2.0
    ll = negbin_log_loss(y, mu, a, pw).mean()
    inside = ((y >= negbin_quantile(mu, a, 0.1, pw)) & (y <= negbin_quantile(mu, a, 0.9, pw))).mean()
    return (f"  {label:<34} 1+: error {one['error']:.2f} points, slope {one['slope']:.2f}; "
            f"2+: error {two['error']:.2f}, slope {two['slope']:.2f} ({ok}); q10-q90 holds "
            f"{100 * inside:.1f}%; log loss {ll:.4f}")


for family, rung in CHAMPIONS.items():
    p = pl.read_parquet(cache_dir() / f"walk_{family}_rest_{rung}.parquet")
    feats, _ = backtest.load_features(saved_dir(family, "rest", ""))
    keys = ["team", "game_id"] if family == "team" else ["gsis_id", "game_id"]
    p = p.join(feats.select(*keys, "games_left").unique(keys), on=keys, how="left").with_columns(
        window=bucket(c("games_left")))
    if "position" not in p.columns:
        p = p.with_columns(position=pl.lit("team"))
    out.append(f"== {family}, rest of season ({family}_rest_{rung}; {p.filter(c('season').is_in(TESTED)).height:,} rows)")
    poisson = p.filter(c("season").is_in(TESTED))
    one = with_alpha(p, ["position"])
    two = with_alpha(p, ["position", "window"])
    three = with_alpha(p, ["position", "window"], power=None)
    out.append(line("Poisson", poisson))
    out.append(line("negative binomial, by position", one))
    out.append(line("negative binomial, position x window", two))
    out.append(line("slower spread, position x window", three))
    base = negbin_log_loss(poisson["y"].to_numpy(), poisson["mean"].to_numpy(), 0.0).mean()
    for n, q in (("by position", one), ("position x window", two), ("slower spread", three)):
        ll = negbin_log_loss(q["y"].to_numpy(), q["mean"].to_numpy(), q["alpha"].to_numpy(),
                             q["power"].to_numpy()).mean()  # fmt: skip
        out.append(f"    log loss against Poisson, {n}: {100 * (base - ll) / base:+.2f}% (positive: better)")
    last = three.filter(c("season") == TESTED[-1]).group_by("position", "window").agg(
        alpha=c("alpha").first(), power=c("power").first()).sort("position", "window")
    out.append("    the slower spread fit for 2024 (position, window: alpha, power): " + "; ".join(
        f"{r['position']} {r['window']} {r['alpha']:.2f}, {r['power']:.2f}" for r in last.iter_rows(named=True)))
    if family != "team":
        for pos in sorted(three["position"].unique().to_list()):
            out.append(line(f"  {pos}, slower spread", three.filter(c("position") == pos)))
    for w in ("1-5", "6-11", "12+"):
        out.append(line(f"  games left {w}, slower spread", three.filter(c("window") == w)))
    out.append("")
    print("\n".join(out[-12:]), flush=True)

OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
