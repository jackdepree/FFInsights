"""team-efficiency exploration, round two (2026-11-13), idea 1: how much is left to find?

The target (a team's EPA per play over its next 3 games, or the rest of the season) is itself noisy:
about 180 plays over three games. No rating can remove that noise, so the skill any rating could
reach has a ceiling. Three estimates, from generous to strict:

- **Play-noise bound** (generous): if we knew each team's true average exactly, the only error left
  is the plays' own scatter, var(play) / plays. Ignores that whole games swing too (weather, game
  plan, injuries), so it overstates what's reachable.
- **Hindsight oracle, next 3 games** (realistic): rate every team on the whole season *except* the
  target team's next 3 games (its earlier and later games, and every other game), then predict
  through the same calibration. It knows far more than any forecast could (the future), so it's a
  ceiling for a rating that treats a team's season as one ability.
- **Split-half reliability, rest of season** (strict): the rest-of-season games split into odd and
  even, the correlation of the two halves stepped up to the full length (Spearman-Brown). It counts
  the opponents' share as noise, so it understates the ceiling a little.

Compared with what we reach now: all plays equal (rung 1's winner) and F8's combination.
Writes r2_ceiling.txt. PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/explore/r2_ceiling.py
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import common as C  # noqa: E402

c = pl.col
HERE = Path(__file__).parent
CACHE = C.get_config().zone("interim") / "team-efficiency"
BUCKETS = (("weeks 1-4", 1, 4), ("weeks 5-9", 5, 9), ("weeks 10+", 10, 99))


def bucket(df: pl.DataFrame, lo: int, hi: int) -> pl.DataFrame:
    return df.filter(c("w").is_between(lo, hi))


def noise_bound(p: pl.DataFrame, sched: pl.DataFrame, horizon: str) -> pl.DataFrame:
    """Per unit: the target y and the play-noise variance of y, var(play) / plays."""
    t = p.group_by("game_id", "posteam").agg(s1=c("y_rel").sum(), s2=(c("y_rel") ** 2).sum(), n=pl.len()).rename({"posteam": "team"})
    tg = sched.join(t, on=["game_id", "team"], how="inner")
    x = C.units(tg, horizon)
    off = x.select("season", "w", "team", "s1", "s2", "n").with_columns(side=pl.lit("off"))
    d = tg.select("game_id", def_team="opponent", s1d="s1", s2d="s2", nd="n")
    xd = C.units(tg, horizon).join(d, left_on=["game_id", "team"], right_on=["game_id", "def_team"])
    dfn = xd.select("season", "w", "team", s1="s1d", s2="s2d", n="nd").with_columns(side=pl.lit("def"))
    u = pl.concat([off, dfn]).group_by("season", "w", "team", "side").agg(S1=c("s1").sum(), S2=c("s2").sum(), N=c("n").sum())
    return u.with_columns(y=c("S1") / c("N"), noise=((c("S2") - c("S1") ** 2 / c("N")) / (c("N") - 1)) / c("N"))


def oracle_next3(tg: pl.DataFrame, lam_games: float = 2.0) -> pl.DataFrame:
    """Hindsight ratings per (season, w, team): a ridge (league + home + offense + defense, no
    recency, a light pull toward 0) on the whole season except the team's next 3 games from week w.
    Returns per (season, w, team, side): own and the mean opponent rating over those 3 games."""
    g = tg.with_columns(a=c("team").replace_strict(C.TIX), b=c("opponent").replace_strict(C.TIX))
    wscale = float(g["n"].mean())
    lam = lam_games * wscale
    out = []
    P = 2 + 2 * C.NT
    for season in C.SEASONS:
        gs = g.filter(c("season") == season).sort("week")
        wk = gs["week"].to_numpy()
        a = gs["a"].to_numpy()
        b = gs["b"].to_numpy()
        h = gs["home"].to_numpy().astype(float)
        W = gs["n"].to_numpy().astype(float)
        ybar = gs["ysum"].to_numpy() / W
        X = np.zeros((gs.height, P))
        X[:, 0] = 1.0
        X[:, 1] = h
        X[np.arange(gs.height), 2 + a] = 1.0
        X[np.arange(gs.height), 2 + C.NT + b] = 1.0
        A0 = X.T @ (X * W[:, None])
        r0 = X.T @ (W * ybar)
        pen = np.full(P, lam)
        pen[:2] = 1e-6
        A0[np.diag_indices_from(A0)] += pen
        gid = gs["game_id"].to_numpy()
        # Each team's games in week order: its next 3 from week w.
        for w in sorted(set(wk)):
            for t in range(C.NT):
                mine = np.where(((a == t) | (b == t)) & (wk >= w))[0]
                if mine.size == 0:
                    continue
                games = []
                for i in mine:
                    if gid[i] not in games:
                        games.append(gid[i])
                games = games[:3]
                ex = np.isin(gid, games)
                Xe = X[ex]
                A = A0 - Xe.T @ (Xe * W[ex][:, None])
                r = r0 - Xe.T @ (W[ex] * ybar[ex])
                th = np.linalg.solve(A, r)
                o, d = th[2 : 2 + C.NT], th[2 + C.NT :]
                # Opponents in those games (rows where the team is on offense).
                opp = b[ex & (a == t)]
                hm = h[ex & (a == t)]
                out.append((season, w, C.TEAMS[t], "off", o[t], d[opp].mean(), hm.mean()))
                out.append((season, w, C.TEAMS[t], "def", d[t], o[opp].mean(), 1 - hm.mean()))
    return pl.DataFrame(out, schema=["season", "w", "team", "side", "own", "opp", "home"], orient="row")


def split_half_rest(tg: pl.DataFrame) -> pl.DataFrame:
    """Per (season, w, team, side) with at least 4 games left: EPA per play in the odd and the even
    games of the rest of the season."""
    x = C.units(tg, "rest").with_columns(k=c("week").rank("ordinal").over("season", "w", "team"), m=pl.len().over("season", "w", "team"))
    d = tg.select("game_id", def_team="opponent", ysum_d="ysum", n_d="n")
    x = x.join(d, left_on=["game_id", "team"], right_on=["game_id", "def_team"]).filter(c("m") >= 4)
    rows = []
    for side, ys, ns in (("off", "ysum", "n"), ("def", "ysum_d", "n_d")):
        g = x.group_by("season", "w", "team", par=c("k") % 2).agg(Y=c(ys).sum() / c(ns).sum())
        g = g.pivot(on="par", index=["season", "w", "team"], values="Y").rename({"0": "even", "1": "odd"})
        rows.append(g.select("season", "w", "team", "odd", "even").with_columns(side=pl.lit(side)))
    return pl.concat(rows)


def sb(r: float) -> float:
    return 2 * r / (1 + r)


def main() -> None:
    p = C.plays()
    sched = C.schedule()
    tg = C.team_games(p, sched)
    ufs = {h: C.unit_frame(tg, h) for h in ("next3", "rest")}
    eq = {h: pl.read_parquet(CACHE / f"equal_{h}.parquet") for h in ("next3", "rest")}
    combo = C.score_ratings(pl.read_parquet(CACHE / "ratings_combo.parquet"), ufs)
    lines = []

    def say(s=""):
        print(s, flush=True)
        lines.append(s)

    def sk(pf, side=None, seasons=C.SCORE):
        x = pf.filter(c("season").is_in(seasons))
        if side:
            x = x.filter(c("side") == side)
        return 1 - float(((x["y"] - x["pred"]) ** 2).sum()) / float((x["y"] ** 2).sum())

    # The oracle, through the same calibration (fitted on TUNE).
    orc = oracle_next3(tg)
    of = ufs["next3"].group_by("season", "w", "team", "side").agg(y=c("ysum").sum() / c("n").sum(), n=c("n").sum())
    of = of.join(orc, on=["season", "w", "team", "side"])
    orc_pf = C.fit_score(of, ["own", "opp", "home"])

    nb = {h: noise_bound(p, sched, h) for h in ("next3", "rest")}
    sh = split_half_rest(tg)

    say("How much of the target's error any rating could remove (skill against the league average, 2016-2024).")
    say("Now = what we reach; ceilings from generous (play noise only) to realistic (hindsight oracle) to strict (split half).")
    say("")
    for h in ("next3", "rest"):
        say(f"{h}:")
        for side in (None, "off", "def"):
            nm = side or "pooled"
            u = nb[h].filter(c("season").is_in(C.SCORE))
            if side:
                u = u.filter(c("side") == side)
            bound = 1 - float(u["noise"].sum()) / float((u["y"] ** 2).sum())
            parts = [f"now: all plays {100 * sk(eq[h], side):.1f}%, F8 combo {100 * sk(combo[h], side):.1f}%", f"play-noise bound {100 * bound:.1f}%"]
            if h == "next3":
                parts.append(f"hindsight oracle {100 * sk(orc_pf, side):.1f}%")
            else:
                s = sh.filter(c("season").is_in(C.SCORE))
                if side:
                    s = s.filter(c("side") == side)
                r = float(np.corrcoef(s["odd"].to_numpy(), s["even"].to_numpy())[0, 1])
                parts.append(f"split-half reliability {100 * sb(r):.1f}% (half r {r:.2f})")
            say(f"  {nm:6s} " + "; ".join(parts))
        say("")
    say("By week of the season (pooled offense and defense), 2016-2024:")
    for h in ("next3", "rest"):
        for nm, lo, hi in BUCKETS:
            u = bucket(nb[h], lo, hi).filter(c("season").is_in(C.SCORE))
            bound = 1 - float(u["noise"].sum()) / float((u["y"] ** 2).sum())
            parts = [f"all plays {100 * sk(bucket(eq[h], lo, hi)):.1f}%", f"combo {100 * sk(bucket(combo[h], lo, hi)):.1f}%", f"play-noise bound {100 * bound:.1f}%"]
            if h == "next3":
                parts.append(f"oracle {100 * sk(bucket(orc_pf, lo, hi)):.1f}%")
            else:
                s = bucket(sh, lo, hi).filter(c("season").is_in(C.SCORE))
                r = float(np.corrcoef(s["odd"].to_numpy(), s["even"].to_numpy())[0, 1])
                parts.append(f"split half {100 * sb(r):.1f}%")
            say(f"  {h:5s} {nm:10s} " + "; ".join(parts))
    say("")
    say("Share of the reachable room already taken (now / oracle for next 3; now / split half for the rest), pooled:")
    s = sh.filter(c("season").is_in(C.SCORE))
    rel = sb(float(np.corrcoef(s["odd"].to_numpy(), s["even"].to_numpy())[0, 1]))
    say(f"  next3: combo {sk(combo['next3']) / sk(orc_pf):.0%} of the oracle's skill; rest: combo {sk(combo['rest']) / rel:.0%} of the split-half ceiling")
    (HERE / "r2_ceiling.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
