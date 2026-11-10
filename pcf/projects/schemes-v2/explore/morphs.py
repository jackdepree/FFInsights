"""The CEO's H13, first look (2026-11-08, discovery only): does each scheme morph consistently
against an opposing scheme?

"team a will fit into a cluster but whenever team a plays a cluster type-3 then that team a
utilizes a different than normal schematic cluster."

From `tendencies.py`'s team-game table (season-centered tendencies, regimes of head coach and
starting QB). For each game:
- **The morph:** the team's tendency in the game less its own normal, the mean of its *other*
  games in the same regime (regimes of 6+ games), so the game isn't measured against itself.
- **The condition:** the opponent's normal on the other side of the ball (the mean of its other
  games in its regime), standardized by season.

1. **The average response** (the usual way, ordinary opponent adjustment): how much the average
   team's tendency moves per sd of the opponent's tendency.
2. **The team-specific part (H13):** after the average response, each head coach's own slope
   against the condition, measured separately in even and odd seasons. If coaches morph their
   own way, and do it again, the two slopes correlate across coaches. Null: each game gets a
   random opponent from the same week (200 shuffles). The same with even and odd games.
3. **Clusters (the CEO's framing, 2018-2024, all tendencies):**
   - 6 offense clusters from game-level tendency vectors, and 6 defense clusters from opponents'
     normals;
   - how often a team's game sits in its usual cluster (its most common one in the regime);
   - whether the off-cluster rate against each opponent cluster is a repeatable coach trait
     (even against odd games), against shuffled opponents.
The vault (2025) isn't read.

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/morphs.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.cluster import KMeans

from pcf.config import get_config

c = pl.col
RNG = np.random.default_rng(20261108)
SHUFFLES = 200
O_M = ["proe", "shotgun_oe", "no_huddle_oe", "tempo", "adot", "deep_rate", "middle_rate", "outside_run", "p11", "heavy"]
D_M = ["d_man", "d_two_high", "d_blitz", "d_box_oe"]
D_COND = ["d_man", "d_two_high", "d_blitz", "d_box_oe", "d_proe_faced", "d_adot_faced", "d_pressure"]
O_COND = ["proe", "shotgun_oe", "no_huddle_oe", "tempo", "adot", "p11", "heavy"]


def table() -> pl.DataFrame:
    tg = pl.read_parquet(get_config().zone("interim") / "schemes_v2" / "team_game.parquet")
    cols = sorted(set(O_M + D_M + D_COND + O_COND))
    n = c("regime").count().over("regime")
    # leave-one-out regime normals: (regime sum - this game) / (count - 1), per column
    loo = []
    for m in cols:
        v = c(m).fill_nan(None)
        k = v.is_not_null().cast(pl.Int32)
        loo.append(pl.when(k.sum().over("regime") - k >= 5).then((v.fill_null(0).sum().over("regime") - v.fill_null(0)) / (k.sum().over("regime") - k)).alias(f"n_{m}"))
    tg = tg.with_columns(*loo).filter(n >= 6)
    opp = tg.select("game_id", c("team").alias("opp"), *[c(f"n_{m}").alias(f"o_{m}") for m in cols])
    t = tg.join(opp, on=["game_id", "opp"])
    # standardize the opponent's normals by season
    return t.with_columns(*[((c(f"o_{m}") - c(f"o_{m}").mean().over("season")) / c(f"o_{m}").std().over("season")) for m in cols])


def week_perm(t: pl.DataFrame) -> np.ndarray:
    idx = np.arange(t.height)
    keys = (t["season"] * 100 + t["week"]).to_numpy()
    perm = idx.copy()
    for k in np.unique(keys):
        w = idx[keys == k]
        perm[w] = RNG.permutation(w)
    return perm


def split_r(dev: np.ndarray, z: np.ndarray, coach: np.ndarray, half: np.ndarray, min_n: int = 20) -> float:
    """After the average response, each coach's slope in each half; their correlation across coaches."""
    ok = ~(np.isnan(dev) | np.isnan(z))
    dev, z, coach, half = dev[ok], z[ok], coach[ok], half[ok]
    beta = (dev * z).sum() / (z * z).sum()
    e = dev - beta * z
    df = pl.DataFrame({"coach": coach, "h": half, "ez": e * z, "zz": z * z}).group_by("coach", "h").agg(c("ez").sum(), c("zz").sum(), n=pl.len())
    df = df.filter(c("n") >= min_n).with_columns(slope=c("ez") / c("zz"))
    w = df.pivot(on="h", index="coach", values="slope").drop_nulls()
    if w.height < 10 or w.width < 3:
        return float("nan")
    a, b = w[w.columns[1]].to_numpy(), w[w.columns[2]].to_numpy()
    return float(np.corrcoef(a, b)[0, 1])


def main() -> None:
    t = table()
    coach = t["coach"].to_numpy()
    season_half = (t["season"] % 2).to_numpy()
    game_half = (t["game_in_regime"] % 2).to_numpy()
    print(f"team-games in regimes of 6+ games with the opponent's normals: {t.height}")

    pairs = [(m, z, "offense") for m in O_M for z in D_COND] + [(m, z, "defense") for m in D_M for z in O_COND]
    perms = [week_perm(t) for _ in range(SHUFFLES)]
    print("\n== 1-2. Average response, and whether coaches' own morphs repeat (even against odd seasons; even against odd games)")
    print(f"{'side':<8} {'tendency':<13} {'against opponent':<15} {'avg response':>12} {'t':>6} {'seasons r':>10} {'null 95th':>10} {'games r':>8} {'null 95th':>10}")
    rows = []
    for m, z, side in pairs:
        dev = (t[m] - t[f"n_{m}"]).fill_nan(None).to_numpy().astype(float)
        sd = np.nanstd(dev)
        dev = dev / sd
        zz = t[f"o_{z}"].to_numpy().astype(float)
        ok = ~(np.isnan(dev) | np.isnan(zz))
        if ok.sum() < 1000:
            continue
        beta = (dev[ok] * zz[ok]).sum() / (zz[ok] ** 2).sum()
        e = dev[ok] - beta * zz[ok]
        tstat = beta / np.sqrt((e @ e) / (ok.sum() - 1) / (zz[ok] ** 2).sum())
        rs = split_r(dev, zz, coach, season_half)
        rg = split_r(dev, zz, coach, game_half)
        ns = np.array([split_r(dev, zz[p], coach, season_half) for p in perms[:50]])
        ng = np.array([split_r(dev, zz[p], coach, game_half) for p in perms[:50]])
        rows.append((side, m, z, beta, tstat, rs, np.nanquantile(ns, 0.95), rg, np.nanquantile(ng, 0.95), ns, ng))
        print(f"{side:<8} {m:<13} {z:<15} {beta:>+12.3f} {tstat:>6.1f} {rs:>+10.2f} {np.nanquantile(ns, 0.95):>+10.2f} {rg:>+8.2f} {np.nanquantile(ng, 0.95):>+10.2f}")
    print(f"\n   {len(rows)} pairs. Average response clear of zero (|t| > 3): {sum(abs(r[4]) > 3 for r in rows)}")
    for lab, i, j in (("seasons", 5, 9), ("games", 7, 10)):
        real = np.nanmean([r[i] for r in rows])
        null = np.nanmean(np.column_stack([r[j] for r in rows]), axis=1)
        above = sum(r[i] > np.nanquantile(r[j], 0.95) for r in rows)
        print(f"   coaches' own morphs, {lab}: mean split r across pairs {real:+.3f}; shuffled opponents' mean {np.nanmean(null):+.3f} (95th {np.nanquantile(null, 0.95):+.3f}); pairs above their own null's 95th: {above} of {len(rows)} (about {0.05 * len(rows):.0f} by chance)")

    print("\n== 2b. Could it have seen a morph? Plant coach-specific slopes (sd s, in sd of the game deviation per sd of the opponent) and measure again")
    m, z = "proe", "d_man"
    dev = (t[m] - t[f"n_{m}"]).fill_nan(None).to_numpy().astype(float)
    dev = dev / np.nanstd(dev)
    zz = t[f"o_{z}"].to_numpy().astype(float)
    coaches = np.unique(coach)
    for s in (0.0, 0.05, 0.1, 0.15, 0.2):
        got = []
        for _ in range(20):
            slope = dict(zip(coaches, RNG.normal(0, s, len(coaches))))
            planted = dev + np.array([slope[k] for k in coach]) * np.nan_to_num(zz)
            got.append(split_r(planted, zz, coach, season_half))
        print(f"   planted sd {s:.2f}: split r across seasons {np.nanmean(got):+.2f} (this pair: real +0.10, shuffled-opponent 95th +0.36)")

    print("\n== 3. Clusters, the CEO's framing (2018-2024): 6 offense clusters of games, 6 defense clusters of opponents")
    cl = t.filter(c("season") >= 2018).drop_nulls([*O_M, *[f"o_{z}" for z in D_COND]]).drop_nans([*O_M, *[f"o_{z}" for z in D_COND]])
    X = cl.select(O_M).to_numpy()
    X = (X - X.mean(0)) / X.std(0)
    oc = KMeans(6, n_init=10, random_state=0).fit_predict(X)
    dc = KMeans(6, n_init=10, random_state=0).fit_predict(cl.select([f"o_{z}" for z in D_COND]).to_numpy())
    cl = cl.with_columns(oc=pl.Series(oc), dc=pl.Series(dc))
    usual = cl.group_by("regime", "oc").len().sort("len", descending=True).group_by("regime").first().select("regime", usual=c("oc"))
    cl = cl.join(usual, on="regime").with_columns(off=c("oc") != c("usual"))
    print(f"   {cl.height} team-games. A game sits in its regime's usual cluster {1 - cl['off'].mean():.0%} of the time (cluster sizes {np.bincount(oc).tolist()})")
    print("   off-cluster rate by opponent's defense cluster: " + ", ".join(f"D{k} {v:.0%}" for k, v in cl.group_by("dc").agg(c("off").mean()).sort("dc").iter_rows()))

    def cell_r(dc_arr: np.ndarray) -> float:
        q = cl.with_columns(dc=pl.Series(dc_arr), h=c("game_in_regime") % 2)
        base = q.group_by("dc").agg(base=c("off").mean())
        q = q.join(base, on="dc").with_columns(x=c("off").cast(pl.Float64) - c("base"))
        g = q.group_by("coach", "dc", "h").agg(c("x").mean(), n=pl.len()).filter(c("n") >= 3)
        w = g.pivot(on="h", index=["coach", "dc"], values="x").drop_nulls()
        return float(np.corrcoef(w[w.columns[2]].to_numpy(), w[w.columns[3]].to_numpy())[0, 1]), w.height

    rr, n = cell_r(dc)
    perm_c = [cl["dc"].to_numpy()[week_perm(cl)] for _ in range(SHUFFLES)]
    nn = np.array([cell_r(p)[0] for p in perm_c])
    print(f"   a coach's off-cluster rate against a defense cluster, even games against odd: r {rr:+.3f} over {n} coach × cluster cells; shuffled opponents 95th {np.quantile(nn, 0.95):+.3f}, at or above the real r {np.mean(nn >= rr):.1%}")


if __name__ == "__main__":
    main()
