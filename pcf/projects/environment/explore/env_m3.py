"""Environment, method 3 (exploratory; pre-registered in EXPLORATION.md before this ran; discovery only):
agronomy's stability analysis (Finlay-Wilkinson regression).

1. The environment index: each team-game's out-of-fold forecast from the conditions-only linear model (a season held out
   at a time), for pass rate over expected, dropbacks, EPA a play and points, centred on the league.
2. Sensitivity: each team's slope of its outcome (less its block mean) on the index, in blocks of 3 seasons
   (2000-2002 ... 2021-2023). 1 is average; below 1 is weather-proof.
3. Does it repeat? Split halves (alternate games within a block), and the next block's slope against this one's,
   correlated across team-blocks (90% from 1,000 resamples of teams). QBs with 40+ outdoor starts, on EPA a pass play
   and air yards an attempt: split halves of their careers.
4. Does it forecast? Walk-forward: the previous block's slope, shrunk toward 1 by its reliability, times this game's
   index, added to the previous-8 mean, against the same with a slope of 1, scored on bad-weather games.

Run from pcf/:  python projects/environment/explore/env_m3.py   (writes env_m3.txt)
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from env_common import Say, _part, team_games  # noqa: E402

c = pl.col
RNG = np.random.default_rng(13)
say = Say(Path(__file__).with_suffix(".txt"))
COND = ["wind", "cold", "precip", "dome", "turf", "short_rest", "long_rest", "altitude", "primetime"]
OUT = {"proe": "pass rate over expected", "dropbacks": "dropbacks", "epa_per_play": "EPA a play", "points": "points scored"}


def index(t: pl.DataFrame, o: str) -> np.ndarray:
    X = np.column_stack([np.ones(t.height)] + [t[k].cast(pl.Float64).fill_null(0).to_numpy() for k in COND])
    y = t[o].to_numpy()
    seas = t["season"].to_numpy()
    p = np.zeros(len(y))
    for s in np.unique(seas):
        tr = seas != s
        b = np.linalg.lstsq(X[tr], y[tr], rcond=None)[0]
        p[seas == s] = X[seas == s] @ b
    return p - p.mean()


def slope(y, x):
    x, y = x - x.mean(), y - y.mean()
    v = (x**2).sum()
    return (x * y).sum() / v if v > 0 else np.nan, v


def corr_boot(a, b, groups):
    ok = np.isfinite(a) & np.isfinite(b)
    a, b, groups = a[ok], b[ok], groups[ok]
    r0 = np.corrcoef(a, b)[0, 1]
    u, inv = np.unique(groups, return_inverse=True)
    rs = []
    for _ in range(1000):
        pick = RNG.integers(0, len(u), len(u))
        idx = np.concatenate([np.nonzero(inv == k)[0] for k in pick])
        rs.append(np.corrcoef(a[idx], b[idx])[0, 1])
    return r0, np.nanquantile(rs, 0.05), np.nanquantile(rs, 0.95), len(a)


def main() -> None:
    t = team_games().with_columns(cold=(50 - c("temp")).clip(0, None)).filter(c("season") <= 2023)
    t = t.with_columns(block=((c("season") - 2000) // 3)).sort("team", "kickoff")
    say("# Environment, method 3: agronomy's stability analysis (2026-11-27)", "",
        "| Outcome | Split halves r (90%; team-blocks) | Next block's slope r (90%) | Forecast gain on bad-weather games (90%) |", "|---|---|---|---|")
    passed = {}
    for o, lab in OUT.items():
        x = t.drop_nulls([o]).filter(c(o).is_finite())
        x = x.with_columns(idx=pl.Series(index(x, o)), n=pl.int_range(pl.len()).over("team", "block"))
        rows = []
        for (team, blk), d in x.group_by(["team", "block"]):
            y, ix, n = d[o].to_numpy(), d["idx"].to_numpy(), d["n"].to_numpy()
            sa, _ = slope(y[n % 2 == 0], ix[n % 2 == 0])
            sb, _ = slope(y[n % 2 == 1], ix[n % 2 == 1])
            s_all, v = slope(y, ix)
            resid = y - y.mean() - s_all * (ix - ix.mean())
            se2 = resid.var() / v if v > 0 else np.nan
            rows.append({"team": team, "block": blk, "sa": sa, "sb": sb, "s": s_all, "se2": se2})
        R = pl.DataFrame(rows)
        half = corr_boot(R["sa"].to_numpy(), R["sb"].to_numpy(), R["team"].to_numpy())
        nxt = R.join(R.select("team", block=c("block") - 1, s_next="s"), on=["team", "block"], how="inner")
        rnext = corr_boot(nxt["s"].to_numpy(), nxt["s_next"].to_numpy(), nxt["team"].to_numpy())
        # shrink each block's slope toward 1 by its reliability: true spread of slopes over (true spread + its noise)
        tau2 = max(np.nanvar(R["s"].to_numpy()) - np.nanmedian(R["se2"].to_numpy()), 0.0)
        R = R.with_columns(shrunk=1 + (c("s") - 1) * (tau2 / (tau2 + c("se2"))))
        prev = R.select("team", block=c("block") + 1, k="shrunk")
        z = x.join(prev, on=["team", "block"], how="inner").drop_nulls([f"{o}_prior"]).filter(~c("dome") & ((c("wind") >= 10) | (c("precip") >= 0.02) | (c("temp") <= 40)))
        y, pr, ix, k = z[o].to_numpy(), z[f"{o}_prior"].to_numpy(), z["idx"].to_numpy(), z["k"].fill_nan(1.0).to_numpy()
        e0, e1 = (y - pr - ix) ** 2, (y - pr - k * ix) ** 2
        gid = z["game_id"].to_numpy()
        u, inv = np.unique(gid, return_inverse=True)
        A, B = np.bincount(inv, e1), np.bincount(inv, e0)
        ii = RNG.integers(0, len(u), (1000, len(u)))
        gb = 1 - A[ii].sum(1) / B[ii].sum(1)
        g = (1 - e1.sum() / e0.sum(), np.quantile(gb, 0.05), np.quantile(gb, 0.95))
        passed[o] = (half[1] > 0, g[1] > 0)
        say(f"| {lab} | {half[0]:+.2f} ({half[1]:+.2f} to {half[2]:+.2f}; {half[3]}) | {rnext[0]:+.2f} ({rnext[1]:+.2f} to {rnext[2]:+.2f}; {rnext[3]}) | "
            f"{g[0]:+.3%} ({g[1]:+.3%} to {g[2]:+.3%}; {len(y):,} team-games) |")
    say("", f"Spread of team slopes (pass rate over expected): reliability-shrunk; the bets: slopes repeat for pass rate over expected: "
        f"{'held' if passed['proe'][0] else 'failed'}; the slopes forecast (any outcome): {'held' if any(v[1] for v in passed.values()) else 'failed'}.", "")

    # QBs: split halves of their careers' outdoor-and-dome starts
    S = list(range(2000, 2024))
    pre = _part("team_game", "pregame", ["game_id", "team", "qb_id"], S)
    ef = _part("team_game", "efficiency", ["game_id", "team", "eff_pass_plays", "eff_pass_epa"], S)
    ten = _part("team_game", "tendencies", ["game_id", "team", "air_yards_per_att"], S)
    q = t.select("game_id", "team", "season", "kickoff", *COND).join(pre, on=["game_id", "team"]).join(ef, on=["game_id", "team"]).join(ten, on=["game_id", "team"])
    q = q.with_columns(pass_epa=c("eff_pass_epa") / c("eff_pass_plays")).filter(c("eff_pass_plays") >= 15)
    say("**QBs** (40+ outdoor starts; split halves of the career, alternate starts):", "")
    res = []
    for o, lab in (("pass_epa", "EPA a pass play"), ("air_yards_per_att", "air yards an attempt")):
        x = q.drop_nulls([o]).filter(c(o).is_finite())
        x = x.with_columns(idx=pl.Series(index(x, o))).sort("qb_id", "kickoff")
        keep = x.filter(~c("dome")).group_by("qb_id").agg(n=pl.len()).filter(c("n") >= 40)["qb_id"]
        x = x.filter(c("qb_id").is_in(keep.implode())).with_columns(n=pl.int_range(pl.len()).over("qb_id"))
        sa, sb, ids = [], [], []
        for qb, d in x.group_by("qb_id"):
            y, ix, n = d[o].to_numpy(), d["idx"].to_numpy(), d["n"].to_numpy()
            sa.append(slope(y[n % 2 == 0], ix[n % 2 == 0])[0])
            sb.append(slope(y[n % 2 == 1], ix[n % 2 == 1])[0])
            ids.append(qb[0] if isinstance(qb, tuple) else qb)
        r = corr_boot(np.array(sa), np.array(sb), np.array(ids))
        res.append(r[1] > 0)
        say(f"- {lab}: split halves r {r[0]:+.2f} (90%: {r[1]:+.2f} to {r[2]:+.2f}; {r[3]} QBs)")
    say("", f"QB slopes repeat (either outcome, clear): {'held' if any(res) else 'failed'}.")
    say.save()


if __name__ == "__main__":
    main()
