"""Stabilization, method 2b (EXPLORATION.md): drift, ranges and the new-level question, players and
teams. A local-level filter (the true rate takes a random step each game, q, and a bigger one each
offseason, q_s) against static M1, on the next 4 games after games 4, 8 and 12 of a season.

Fit (the noise, the spread, q and q_s) on seasons before 2020; tested on 2020-2024. Discovery only;
the 2025 vault is closed.

Run from pcf/:  python projects/stabilization/explore/m2_drift.py   (writes m2_drift.txt)
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from stab_common import MEASURES, TEAM_MEASURES, Say, boot_gain, components, fit_m1, load, player_seasons  # noqa: E402

c = pl.col
RNG = np.random.default_rng(1)
CUT = 2020  # fit before, test from
Z80 = 1.2816
say = Say(Path(__file__).with_suffix(".txt"))
A_GRID = [0.0, 0.001, 0.003, 0.01, 0.03, 0.1]  # q as a share of the true spread, per game
B_GRID = [0.0, 0.03, 0.1, 0.3, 1.0]  # q_s, per offseason


def run_filter(L, q, qs, s2, t2):
    """Vectorised local-level filter over padded (entities x steps) arrays. Returns the post-game
    level and variance at each step, and the training log-likelihood."""
    D, N, NS, TR, REAL = L["D"], L["N"], L["NS"], L["TR"], L["REAL"]
    P_, J = D.shape
    m, P = np.zeros(P_), np.full(P_, t2)
    mp, pp, zz = np.zeros((P_, J)), np.zeros((P_, J)), np.zeros((P_, J))
    ll = 0.0
    for j in range(J):
        r = REAL[:, j]
        P = P + np.where(r, np.where(NS[:, j], qs, q), 0.0)
        R = np.where(r, s2 / np.maximum(N[:, j], 1e-9), np.inf)
        S = P + R
        v = D[:, j] - m
        t = r & TR[:, j]
        ll += float(np.sum(-0.5 * (np.log(S[t]) + v[t] ** 2 / S[t])))
        zz[:, j] = np.where(r, v**2 / S, 0.0)
        K = np.where(r, P / S, 0.0)
        m = m + K * np.where(r, v, 0.0)
        P = P * (1 - K)
        mp[:, j], pp[:, j] = m, P
    return mp, pp, ll, zz


def pad(df: pl.DataFrame, ent: str):
    """df: one row per entity-game (ent, season, week, d, n), sorted. Padded arrays plus the row map."""
    df = df.sort(ent, "season", "week").with_columns(
        j=pl.int_range(pl.len()).over(ent), e=c(ent).rank("dense") - 1,
        ns=(c("season") != c("season").shift(1).over(ent)).fill_null(False),
    )
    P_, J = int(df["e"].max()) + 1, int(df["j"].max()) + 1
    e, j = df["e"].to_numpy(), df["j"].to_numpy()
    L = {k: np.zeros((P_, J)) for k in ("D", "N")}
    L["D"][e, j], L["N"][e, j] = df["d"].to_numpy(), df["n"].to_numpy()
    for k, col in (("NS", "ns"), ("TR", None), ("REAL", None)):
        L[k] = np.zeros((P_, J), bool)
    L["NS"][e, j] = df["ns"].to_numpy()
    L["TR"][e, j] = (df["season"] < CUT).to_numpy()
    L["REAL"][e, j] = True
    return df, L


def evaluate(df: pl.DataFrame, ent: str, s2: float, t2: float, kind: str):
    """Fit q and q_s on training seasons, then score the filter against static M1 on the next 4 games."""
    df, L = pad(df, ent)
    best = None
    for a in A_GRID:
        for b in B_GRID:
            _, _, ll, _ = run_filter(L, a * t2, b * t2, s2, t2)
            if best is None or ll > best[0]:
                best = (ll, a, b)
    _, a, b = best
    q, qs = a * t2, b * t2
    mp, pp, _, zz = run_filter(L, q, qs, s2, t2)
    e, j = df["e"].to_numpy(), df["j"].to_numpy()
    k = s2 / t2
    df = df.with_columns(m=pl.Series(mp[e, j]), P=pl.Series(pp[e, j]), nd=c("n") * c("d"), z2=pl.Series(zz[e, j]))
    df = df.with_columns(swing=c("z2").cum_sum().over(ent) / pl.int_range(1, pl.len() + 1).over(ent), gcount=pl.int_range(1, pl.len() + 1).over(ent))
    # static M1: last season plus this one so far, no drift: sum(n d) / (sum(n) + k); and the whole career
    tot = df.group_by(ent, "season").agg(pn=c("n").sum(), pnd=c("nd").sum())
    df = df.join(tot.with_columns(c("season") + 1), on=[ent, "season"], how="left").with_columns(c("pn", "pnd").fill_null(0))
    df = df.with_columns(gi=pl.int_range(1, pl.len() + 1).over(ent, "season"),
                         cn=c("n").cum_sum().over(ent, "season"), cnd=c("nd").cum_sum().over(ent, "season"),
                         kn=c("n").cum_sum().over(ent), knd=c("nd").cum_sum().over(ent))  # fmt: skip
    df = df.with_columns(st=(c("pnd") + c("cnd")) / (c("pn") + c("cn") + k), st_v=s2 / (c("pn") + c("cn") + k),
                         car=c("knd") / (c("kn") + k))  # fmt: skip
    rows = []
    for g in (4, 8, 12):
        at = df.filter((c("season") >= CUT) & (c("gi") == g))
        nxt = df.filter((c("gi") > g) & (c("gi") <= g + 4)).group_by(ent, "season").agg(wn=c("n").sum(), ynd=c("nd").sum(), cnt=pl.len())
        rec = df.filter((c("gi") > g - 4) & (c("gi") <= g)).group_by(ent, "season").agg(rn=c("n").sum(), rnd=c("nd").sum())
        x = at.join(nxt.filter(c("cnt") == 4), on=[ent, "season"]).join(rec, on=[ent, "season"])
        x = x.with_columns(y=c("ynd") / c("wn"), w=c("wn"), g=pl.lit(g), recent=c("rnd") / c("rn"),
                           bn=c("kn") - c("rn"), before=(c("knd") - c("rnd")) / (c("kn") - c("rn")))  # fmt: skip
        rows.append(x)
    R = pl.concat(rows).with_columns(
        f_v=c("P") + 2.5 * q + s2 / c("w"), s_v=c("st_v") + s2 / c("w"))
    R = R.with_columns(f_in=((c("y") - c("m")).abs() <= Z80 * c("f_v").sqrt()), s_in=((c("y") - c("st")).abs() <= Z80 * c("s_v").sqrt()))
    return R.rename({ent: "gsis_id"}), a, b, k


def kept(R):
    """New level: the share of a recent-against-before gap kept in the next 4 games, observed and the filter's."""
    out = []
    X = R.filter(c("bn") >= c("rn")).with_columns(gap=c("recent") - c("before"))
    if X.height < 300:
        return out
    qs = np.quantile(X["rn"].to_numpy(), [1 / 3, 2 / 3])
    for lab, lo, hi in (("low", -np.inf, qs[0]), ("mid", qs[0], qs[1]), ("high", qs[1], np.inf)):
        b = X.filter((c("rn") > lo) & (c("rn") <= hi))
        gap = b["gap"].to_numpy()
        w = b["w"].to_numpy()
        obs = np.sum(w * gap * (b["y"] - b["before"]).to_numpy()) / np.sum(w * gap**2)
        fil = np.sum(w * gap * (b["m"] - b["before"]).to_numpy()) / np.sum(w * gap**2)
        idx = RNG.integers(0, b.height, (300, b.height))
        yb = (b["y"] - b["before"]).to_numpy()
        boots = [np.sum(w[i] * gap[i] * yb[i]) / np.sum(w[i] * gap[i] ** 2) for i in idx]
        out.append((lab, float(np.median(b["rn"].to_numpy())), obs, np.quantile(boots, 0.05), np.quantile(boots, 0.95), fil, b.height))
    return out


def interval_score(y, m, v):
    lo, hi = m - Z80 * np.sqrt(v), m + Z80 * np.sqrt(v)
    return (hi - lo) + 10 * np.maximum(lo - y, 0) + 10 * np.maximum(y - hi, 0)


def scatter_cov(R):
    """I14: the filter's coverage by terciles of how much a player's games have swung so far; then the ranges
    widened by his swing (shrunk toward 1 with 20 games' weight), and the range score (80% interval score) before and after."""
    R = R.with_columns(sw=(c("gcount") * c("swing") + 20) / (c("gcount") + 20))
    R = R.with_columns(f_v2=c("f_v") * c("sw"))
    R = R.with_columns(f_in2=((c("y") - c("m")).abs() <= Z80 * c("f_v2").sqrt()))
    qs = np.quantile(R["swing"].to_numpy(), [1 / 3, 2 / 3])
    bands = ((-np.inf, qs[0]), (qs[0], qs[1]), (qs[1], np.inf))
    cv = [float(R.filter((c("swing") > lo) & (c("swing") <= hi))["f_in"].mean()) for lo, hi in bands]
    cv2 = [float(R.filter((c("swing") > lo) & (c("swing") <= hi))["f_in2"].mean()) for lo, hi in bands]
    y, m, w = R["y"].to_numpy(), R["m"].to_numpy(), R["w"].to_numpy()
    s1 = np.average(interval_score(y, m, R["f_v"].to_numpy()), weights=w)
    s2 = np.average(interval_score(y, m, R["f_v2"].to_numpy()), weights=w)
    return cv, cv2, qs, s1, s2


def main() -> None:
    s, game = player_seasons()
    say("# Method 2b: drift, ranges and new levels (2026-11-25)", "",
        f"A local-level filter: each game the true rate takes a step (variance q), each offseason a bigger one (q_s); q and q_s chosen by likelihood on seasons before {CUT}",
        "from q in {0, 0.1%, 0.3%, 1%, 3%, 10%} of the true spread per game and q_s in {0, 3%, 10%, 30%, 100%} of it. Against static M1: last season and this one so far pooled",
        "and pulled back by k, no drift (and a side column: the whole career pooled the same way). Rates centred by the position's mean last season (known before the season).",
        f"Scored on the next 4 games' rate after games 4, 8 and 12 of seasons {CUT}-2024, weighted by those games' attempts; players resampled.", "",
        "| Measure | k | q (share of spread a game) | q_s (a season) | Rows | Filter against static M1 | 90% interval | Clear | Static career against static M1 | Filter's 80% range coverage | Static's coverage |",
        "|---|---|---|---|---|---|---|---|---|---|---|")
    psm = (s.filter((c("den") >= 10) & c("pos").is_not_null()).group_by("measure", "pos", "season")
           .agg(mu=c("num").sum() / c("den").sum(), m=pl.len()).filter(c("m") >= 20).drop("m"))  # fmt: skip
    wins, cover, keeps, all_R = 0, [], {}, {}
    for measure in MEASURES:
        mus, s2, t2, k = fit_m1(s, game, measure, CUT)
        g = game.filter((c("measure") == measure) & c("pos").is_not_null())
        cen = psm.filter(c("measure") == measure).select("pos", season=c("season") + 1, mu="mu")
        own = psm.filter(c("measure") == measure).select("pos", "season", mu0="mu")
        g = g.join(cen, on=["pos", "season"], how="left").join(own, on=["pos", "season"], how="left")
        g = g.with_columns(mu=pl.coalesce("mu", "mu0")).drop_nulls("mu")
        g = g.group_by("gsis_id", "season", "week").agg(num=c("num").sum(), den=c("den").sum(), mu=c("mu").first())
        g = g.select("gsis_id", "season", "week", d=c("num") / c("den") - c("mu"), n="den")
        R, a, b, kk = evaluate(g, "gsis_id", s2, t2, "player")
        all_R[measure] = R
        gain = boot_gain(R.with_columns(y=c("y")), "m", "st", RNG)
        gcar = boot_gain(R, "car", "st", RNG)
        ok = gain[1] > 0
        wins += ok
        fc, sc = float(R["f_in"].mean()), float(R["s_in"].mean())
        cover.append((measure, fc, sc))
        keeps[measure] = kept(R)
        say(f"| {measure} | {kk:.0f} | {a:.1%} | {b:.0%} | {R.height} | {gain[0]:+.1%} | {gain[1]:+.1%} to {gain[2]:+.1%} | {'yes' if ok else 'no'} | {gcar[0]:+.1%} | {fc:.0%} | {sc:.0%} |")
    held = sum(75 <= 100 * f <= 85 for _, f, _ in cover)
    say("", f"Drift: the filter beats static M1 clearly for {wins} of {len(MEASURES)} measures (the bet: half or more). Ranges: {held} of {len(cover)} measures' filter ranges hold 75-85%.")

    say("", "### I14: coverage by how much a player's games swing", "",
        "Each row's swing: the spread of his games' rates around the filter's level before the test point, against what the noise alone gives (1 = as expected). Terciles.", "",
        "Then the ranges widened by his swing (shrunk toward 1 with 20 games' weight). I14 passes for a measure if the spread of coverage across the bands narrows by 5 points or more",
        "and the range score (the 80% interval score, lower is better) doesn't get worse.", "",
        "| Measure | Low swing | Mid | High swing | Widened: low, mid, high | Spread narrows by (points) | Range score change | I14 |", "|---|---|---|---|---|---|---|---|")
    i14 = 0
    for measure, R in all_R.items():
        cv, cv2, qs, s1, s2 = scatter_cov(R)
        narrow = 100 * ((max(cv) - min(cv)) - (max(cv2) - min(cv2)))
        ok = narrow >= 5 and s2 <= s1
        i14 += ok
        say(f"| {measure} | {cv[0]:.0%} (swing under {qs[0]:.2f}) | {cv[1]:.0%} | {cv[2]:.0%} (over {qs[1]:.2f}) | {cv2[0]:.0%}, {cv2[1]:.0%}, {cv2[2]:.0%} | {narrow:.0f} | {s2 / s1 - 1:+.1%} | {'yes' if ok else 'no'} |")
    say("", f"I14: {i14} of {len(all_R)} measures pass.")

    say("", "### Peak, new level or noise: how much of a recent gap lasts", "",
        "The gap: his last 4 games' rate less his career rate before them (players with more attempts before than in the 4 games). The kept share: the slope of the next 4",
        "games' rate (less the career rate before) on the gap, by the recent games' attempts (terciles); the filter's kept share is the same slope for its forecast.", "",
        "| Measure | Recent attempts (median): observed kept share (90%), the filter's | Bins within 0.1 |", "|---|---|---|")
    nk = 0
    for measure, kp in keeps.items():
        if not kp:
            continue
        within = sum(abs(o - f) <= 0.1 for _, _, o, _, _, f, _ in kp)
        nk += within == len(kp)
        say(f"| {measure} | " + "; ".join(f"{lab} ({n:.0f}): {o:.2f} ({lo:.2f} to {hi:.2f}), {f:.2f}" for lab, n, o, lo, hi, f, _ in kp) + f" | {within} of {len(kp)} |")
    say("", f"New level: {nk} of {len(keeps)} measures match within 0.1 in every bin.")

    # teams
    say("", "## Teams, game by game", "",
        "| Measure | Side | k (plays) | q | q_s | Rows | Filter against static M1 | 90% interval (teams resampled) | Clear | Filter's coverage | Static's |", "|---|---|---|---|---|---|---|---|---|---|---|")
    tg = load("team_game")
    tw = 0
    for side in ("off", "def"):
        for measure in TEAM_MEASURES:
            g = tg.filter((c("side") == side) & (c("measure") == measure))
            lm = g.group_by("season").agg(mu=c("num").sum() / c("den").sum())
            g = g.join(lm.with_columns(c("season") + 1), on="season", how="left").join(lm.rename({"mu": "mu0"}), on="season").with_columns(mu=pl.coalesce("mu", "mu0"))
            gc = g.with_columns(num=c("num") - c("mu0") * c("den"), key=pl.concat_str("team", pl.lit("|"), c("season").cast(pl.Utf8)))
            tr = gc.filter(c("season") < CUT)
            ts = tr.group_by("key").agg(num=c("num").sum(), den=c("den").sum(), games=pl.len())
            _, s2, t2 = components(ts, tr)
            d = g.select(gsis_id="team", season="season", week="week", d=c("num") / c("den") - c("mu"), n="den")
            R, a, b, kk = evaluate(d, "gsis_id", s2, t2, "team")
            gain = boot_gain(R, "m", "st", RNG)
            ok = gain[1] > 0
            tw += ok
            say(f"| {measure} | {side} | {kk:.0f} | {a:.1%} | {b:.0%} | {R.height} | {gain[0]:+.1%} | {gain[1]:+.1%} to {gain[2]:+.1%} | {'yes' if ok else 'no'} | {R['f_in'].mean():.0%} | {R['s_in'].mean():.0%} |")
    say("", f"Teams: the filter beats static M1 clearly for {tw} of {2 * len(TEAM_MEASURES)}.")
    say.save()


if __name__ == "__main__":
    main()
