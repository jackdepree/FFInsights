"""The CEO's H14, first look (2026-11-08, discovery only): are schemes like conditions?

"Each scheme itself should show almost zero association with epa or winning, however when two
teams' schemes are compared against each other then we should expect a significant result."

Each row is one side of a game: an offense O against a defense D, 2006-2024 regular season
(participation tendencies 2016-2024). Built from `tendencies.py`'s team-game table.
- **Known before the game:** each tendency is O's (or D's) mean over earlier games in the same
  regime (head coach and starting QB), needing 3+; strength is O's offensive EPA per play and D's
  EPA allowed, season to date, shrunk toward last season (4 games' weight).
- **Outcome:** O's EPA per play in the game, less what the two strengths expect (a regression).
  The residual is "beyond strength".
1. **Main effects:** each tendency's association with raw EPA (talent shows up here), then with the
   residual (H14 says near zero), in EPA per play per standard deviation of the tendency.
2. **Interactions:** for every offense × defense tendency pair, the product term's t on the
   residual (with both main effects in). The null: each offense gets a random defense's
   tendencies from the same week (200 shuffles); the largest |t| among all pairs in each shuffle.
3. **Held out:** the interaction terms fitted on even seasons predict the residual in odd seasons,
   and the reverse. Against the same with shuffled opponents.
4. **Clusters (the CEO's framing):** k-means into 6 offense and 6 defense clusters (2016-2024, the
   full tendency set); the residual's spread by offense cluster, by defense cluster, and the
   offense × defense interaction, each against shuffled clusters.
The vault (2025) isn't read.

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/conditions.py
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
OFF = ["proe", "shotgun_oe", "no_huddle_oe", "adot", "deep_rate", "middle_rate", "outside_run", "scramble_rate", "tempo", "p11", "heavy"]
DEF = ["d_proe_faced", "d_adot_faced", "d_pressure", "d_man", "d_two_high", "d_blitz", "d_box_oe"]


def prior(tg: pl.DataFrame, cols: list[str], by: str, prefix: str) -> pl.DataFrame:
    """Mean of each column over the earlier games in the same `by` group, and how many."""
    g = tg.sort("team", "season", "week")
    exprs = []
    for m in cols:
        v = c(m).fill_nan(None)
        cs = v.fill_null(0).cum_sum().over(by) - v.fill_null(0)
        cn = v.is_not_null().cast(pl.Int32).cum_sum().over(by) - v.is_not_null().cast(pl.Int32)
        exprs.append(pl.when(cn >= 3).then(cs / cn).alias(f"{prefix}{m}"))
    return g.select("game_id", "team", *exprs)


def sides() -> pl.DataFrame:
    tg = pl.read_parquet(get_config().zone("interim") / "schemes_v2" / "team_game.parquet").with_columns(
        ts=pl.concat_str(c("team"), pl.lit("-"), c("season").cast(pl.String)))
    ten = prior(tg, OFF + DEF, "regime", "z_")
    # strength: season to date, shrunk toward last season's mean with 4 games' weight
    last = tg.group_by("team", "season").agg(c("off_epa").mean().alias("off_last"), c("def_epa").mean().alias("def_last")).with_columns(season=c("season") + 1)
    st = tg.sort("team", "season", "week").with_columns(
        n=pl.int_range(pl.len()).over("ts"),
        so=c("off_epa").cum_sum().over("ts") - c("off_epa"),
        sd=c("def_epa").cum_sum().over("ts") - c("def_epa"),
    ).join(last, on=["team", "season"], how="left").with_columns(
        s_off=(c("so") + 4 * c("off_last").fill_null(0)) / (c("n") + 4),
        s_def=(c("sd") + 4 * c("def_last").fill_null(0)) / (c("n") + 4),
    ).select("game_id", "team", "s_off", "s_def")
    o = (tg.select("game_id", "season", "week", "team", "opp", "off_epa", "off_plays")
         .join(ten.select("game_id", "team", *[f"z_{m}" for m in OFF]), on=["game_id", "team"])
         .join(st.select("game_id", "team", "s_off"), on=["game_id", "team"]))
    d = (ten.select("game_id", "team", *[f"z_{m}" for m in DEF])
         .join(st.select("game_id", "team", "s_def"), on=["game_id", "team"]).rename({"team": "opp"}))
    s = o.join(d, on=["game_id", "opp"]).filter(c("week") >= 4).drop_nulls(["off_epa", "s_off", "s_def"])
    X = np.column_stack([np.ones(s.height), s["s_off"].to_numpy(), s["s_def"].to_numpy()])
    b = np.linalg.lstsq(X, s["off_epa"].to_numpy(), rcond=None)[0]
    s = s.with_columns(resid=c("off_epa") - (b[0] + b[1] * c("s_off") + b[2] * c("s_def")))
    print(f"sides {s.height} (weeks 4+, 2006-2024); strength explains r² {1 - s['resid'].var() / s['off_epa'].var():.3f} of game EPA per play; "
          f"strength weights offense {b[1]:.2f}, defense {b[2]:.2f}")
    # standardize every tendency within season, so effects are per standard deviation
    return s.with_columns(*[((c(f"z_{m}") - c(f"z_{m}").mean().over("season")) / c(f"z_{m}").std().over("season")) for m in OFF + DEF])


def ols_t(y, cols):
    X = np.column_stack([np.ones(len(y)), *cols])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b
    cov = np.linalg.inv(X.T @ X) * (e @ e) / (len(y) - X.shape[1])
    return b, b / np.sqrt(np.diag(cov))


def pair_ts(s: pl.DataFrame, dz: dict[str, np.ndarray]) -> dict[tuple[str, str], tuple[float, float, int]]:
    y = s["resid"].to_numpy()
    out = {}
    for a in OFF:
        za = s[f"z_{a}"].to_numpy()
        for d in DEF:
            zd = dz[d]
            ok = ~(np.isnan(za) | np.isnan(zd) | np.isnan(y))
            if ok.sum() < 500:
                continue
            b, t = ols_t(y[ok], [za[ok], zd[ok], za[ok] * zd[ok]])
            out[(a, d)] = (b[3], t[3], int(ok.sum()))
    return out


def shuffled(s: pl.DataFrame) -> dict[str, np.ndarray]:
    """Each side gets a random defense's tendencies from the same season and week."""
    idx = np.arange(s.height)
    keys = (s["season"] * 100 + s["week"]).to_numpy()
    perm = idx.copy()
    for k in np.unique(keys):
        w = idx[keys == k]
        perm[w] = RNG.permutation(w)
    return {d: s[f"z_{d}"].to_numpy()[perm] for d in DEF}


def main() -> None:
    s = sides()
    y = s["resid"].to_numpy()
    print("\n== 1. Main effects, EPA per play per standard deviation of the tendency (known before the game)")
    print(f"{'tendency':<14} {'raw EPA':>9} {'t':>6} {'beyond strength':>16} {'t':>6} {'n':>6}")
    for m in OFF + DEF:
        z = s[f"z_{m}"].to_numpy()
        ok = ~np.isnan(z)
        b0, t0 = ols_t(s["off_epa"].to_numpy()[ok], [z[ok]])
        b1, t1 = ols_t(y[ok], [z[ok]])
        print(f"{m:<14} {b0[1]:>+9.4f} {t0[1]:>6.1f} {b1[1]:>+16.4f} {t1[1]:>6.1f} {ok.sum():>6}")

    print("\n== 2. Offense × defense interactions on the residual: the product term per pair")
    real = pair_ts(s, {d: s[f"z_{d}"].to_numpy() for d in DEF})
    null_max = np.array([max(abs(v[1]) for v in pair_ts(s, shuffled(s)).values()) for _ in range(SHUFFLES)])
    cut = np.quantile(null_max, 0.95)
    top = sorted(real.items(), key=lambda kv: -abs(kv[1][1]))
    print(f"   {len(real)} pairs. Null: largest |t| among all pairs with shuffled opponents, 95th percentile {cut:.2f} (median {np.median(null_max):.2f})")
    print(f"   real pairs above it: {sum(abs(v[1]) > cut for v in real.values())}; real largest |t| {abs(top[0][1][1]):.2f}")
    for (a, d), (b, t, n) in top[:10]:
        print(f"   {a:<14} × {d:<14} {b:>+8.4f} EPA per play per sd², t {t:>5.1f}, n {n}")

    print("\n== 3. Held out: all pair terms fitted on even seasons predict odd seasons, and the reverse")

    def held(dz):
        preds = np.full(s.height, np.nan)
        season = s["season"].to_numpy()
        for fold in (0, 1):
            tr, te = season % 2 == fold, season % 2 != fold
            p = np.zeros(s.height)
            for a in OFF:
                za = s[f"z_{a}"].to_numpy()
                for d in DEF:
                    zd = dz[d]
                    ok = tr & ~(np.isnan(za) | np.isnan(zd))
                    if ok.sum() < 500:
                        continue
                    b, _ = ols_t(y[ok], [za[ok], zd[ok], za[ok] * zd[ok]])
                    p += np.nan_to_num(b[3] * za * zd)
            preds[te] = p[te]
        return float(np.corrcoef(preds, y)[0, 1])

    hr = held({d: s[f"z_{d}"].to_numpy() for d in DEF})
    hn = np.array([held(shuffled(s)) for _ in range(SHUFFLES)])
    print(f"   r between the summed interaction prediction and the residual: {hr:+.3f}; shuffled opponents: mean {hn.mean():+.3f}, 95th percentile {np.quantile(hn, 0.95):+.3f}; "
          f"shuffles at or above the real r: {np.mean(hn >= hr):.1%}")

    print("\n== 4. Clusters (2016-2024, every tendency): 6 offense and 6 defense clusters")
    q = s.filter(c("season") >= 2016).drop_nulls([f"z_{m}" for m in OFF + DEF]).drop_nans([f"z_{m}" for m in OFF + DEF])
    yo = q["resid"].to_numpy()
    oc = KMeans(6, n_init=10, random_state=0).fit_predict(q.select([f"z_{m}" for m in OFF]).to_numpy())
    dc = KMeans(6, n_init=10, random_state=0).fit_predict(q.select([f"z_{m}" for m in DEF]).to_numpy())

    def ss_parts(o, d):
        """Variance of the residual explained by offense cluster, defense cluster, and the pair beyond both."""
        mu = yo.mean()
        so = sum((yo[o == k].mean() - mu) ** 2 * (o == k).sum() for k in range(6))
        sd = sum((yo[d == k].mean() - mu) ** 2 * (d == k).sum() for k in range(6))
        X = np.column_stack([np.ones(len(yo))] + [(o == k) * 1.0 for k in range(1, 6)] + [(d == k) * 1.0 for k in range(1, 6)])
        e_main = yo - X @ np.linalg.lstsq(X, yo, rcond=None)[0]
        cell = np.zeros(len(yo))
        for i in range(6):
            for j in range(6):
                w = (o == i) & (d == j)
                if w.any():
                    cell[w] = e_main[w].mean()
        return so, sd, float((cell ** 2).sum())

    ro = ss_parts(oc, dc)
    nul = np.array([ss_parts(RNG.permutation(oc), RNG.permutation(dc)) for _ in range(SHUFFLES)])
    tot = ((yo - yo.mean()) ** 2).sum()
    for k, name in enumerate(["offense cluster alone", "defense cluster alone", "offense × defense, beyond both"]):
        print(f"   {name:<32} explains {ro[k] / tot:.4%} of the residual's variance; shuffled clusters: median {np.median(nul[:, k]) / tot:.4%}, 95th {np.quantile(nul[:, k], 0.95) / tot:.4%}; real above {np.mean(nul[:, k] < ro[k]):.0%} of shuffles")
    print(f"   rows {len(yo)}; cluster sizes offense {np.bincount(oc).tolist()}, defense {np.bincount(dc).tolist()}")
    tab = pl.DataFrame({"o": oc, "d": dc, "y": yo}).group_by("o", "d").agg(m=c("y").mean(), n=pl.len()).sort("o", "d")
    print("   residual EPA per play by offense cluster (rows) × defense cluster (columns):")
    for i in range(6):
        r = tab.filter(c("o") == i)
        print("   " + f"O{i}: " + " ".join(f"{v:+.3f}" for v in r["m"].to_list()))


if __name__ == "__main__":
    main()
