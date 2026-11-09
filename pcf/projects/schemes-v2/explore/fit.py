"""The CEO's H12, first look (2026-11-08, discovery only): does a player's efficiency depend on the
fit between player and scheme, beyond the talent around them? Wide receivers and QBs (the CEO's
choice), by the movers design, with a simple regression as the yardstick and double machine
learning (cross-fitted) as the causal version.

**Rows:** players who change teams between consecutive seasons (2006-2024 regular season, from
play-by-play): wide receivers with 40+ targets in both seasons, QBs with 200+ dropbacks in both.
Stayers (same team both seasons) are the comparison and a larger second sample.

**Outcome:** the change in efficiency, next season less this season: EPA per target for
receivers, EPA per dropback for QBs (scrambles included).

**The scheme**, per team-season: seven tendencies that `tendencies.py` found follow the play caller
(pass rate over expected, shotgun, no-huddle, tempo, aDOT, deep rate, middle share), each
standardized. **Known before the move:** if the new team's head coach next season was a head
coach this season, the scheme is the one that coach ran this season (schemes follow the coach,
F4); otherwise the new team's scheme this season.
- **Distance (H12):** how far the old scheme is from the new one (root mean square of the seven
  differences). H12 expects a larger distance to cost efficiency, beyond the controls.
- **Depth fit (I23, receivers):** the receiver's own aDOT × the new scheme's aDOT. Expected
  positive: deep threats lose most moving to a short-passing scheme.
- **Controls (the confounders, H12's assumptions):** this season's efficiency (regression to the
  mean), volume, age, the old and the new supporting cast *without the player* (team pass EPA per
  dropback on plays not involving them; for receivers that includes the QB), the old scheme, and
  the new scheme's own levels.

**Estimates:** (1) OLS with every control; (2) double machine learning: outcome and treatment
each predicted from the controls by gradient boosting, 5-fold cross-fitted, then residual on
residual; (3) the placebo move: each mover gets a random other team's scheme from the same
season, 200 times. Regression to the mean shows up in the placebo just as much, so a real effect
has to stand outside it.

**Learning curve (I24):** movers' efficiency in their first 4 games with the new team against
games 9+, against the same gap for stayers, and whether it grows with distance.
The vault (2025) isn't read.

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/fit.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import KFold

from pcf.config import get_config
from pcf.data.tables.store import read_part

c = pl.col
RNG = np.random.default_rng(20261108)
SEASONS = range(2006, 2025)
SCHEME = ["proe", "shotgun_oe", "no_huddle_oe", "tempo", "adot", "deep_rate", "middle_rate"]
PBP = ["game_id", "season", "season_type", "week", "posteam", "passer_player_id", "rusher_player_id", "receiver_player_id",
       "qb_dropback", "qb_scramble", "pass_attempt", "sack", "air_yards", "epa", "pass_location"]


def plays() -> pl.DataFrame:
    out = []
    for s in SEASONS:
        p = read_part("play", "pbp", [s]).select(PBP).collect().filter((c("season_type") == "REG") & (c("qb_dropback") == 1) & c("epa").is_not_null())
        out.append(p.with_columns(qb=pl.when(c("qb_scramble") == 1).then(c("rusher_player_id")).otherwise(c("passer_player_id"))))
    return pl.concat(out)


def positions() -> pl.DataFrame:
    r = read_part("player_game", "roster").select("gsis_id", "season", "position", "birth_date").collect()
    return r.group_by("gsis_id").agg(position=c("position").mode().first(), birth=c("birth_date").drop_nulls().first())


def schemes() -> tuple[pl.DataFrame, pl.DataFrame]:
    tg = pl.read_parquet(get_config().zone("interim") / "schemes_v2" / "team_game.parquet")
    ts = tg.group_by("team", "season").agg(*[c(m).mean() for m in SCHEME], coach=c("coach").mode().first())
    ts = ts.with_columns(*[((c(m) - c(m).mean()) / c(m).std()) for m in SCHEME])
    return ts, ts.select("coach", "season", *[c(m).alias(f"c_{m}") for m in SCHEME])


def player_seasons(p: pl.DataFrame, who: str) -> pl.DataFrame:
    """One row per player-season with their main team, efficiency, volume, style and the team's
    passing EPA without them."""
    if who == "wr":
        x = p.filter((c("pass_attempt") == 1) & (c("sack") == 0) & c("receiver_player_id").is_not_null()).rename({"receiver_player_id": "pid"})
        min_n = 40
    else:
        x = p.filter(c("qb").is_not_null()).rename({"qb": "pid"})
        min_n = 200
    main = x.group_by("season", "pid", "posteam").len().sort("len", descending=True).group_by("season", "pid").first().select("season", "pid", team="posteam")
    x = x.join(main, on=["season", "pid"]).filter(c("posteam") == c("team"))
    agg = x.group_by("season", "pid", "team").agg(
        n=pl.len(), eff=c("epa").mean(), own_adot=c("air_yards").mean(),
        own_deep=(c("air_yards") >= 20).mean(), own_middle=(c("pass_location") == "middle").mean())
    team_pass = p.group_by("season", "posteam").agg(t_sum=c("epa").sum(), t_n=pl.len()).rename({"posteam": "team"})
    agg = agg.join(team_pass, on=["season", "team"]).with_columns(
        cast=(c("t_sum") - c("eff") * c("n")) / (c("t_n") - c("n"))).drop("t_sum", "t_n")
    return agg.filter(c("n") >= min_n)


def pairs(ps: pl.DataFrame, ts: pl.DataFrame, cs: pl.DataFrame, pos: pl.DataFrame, who: str) -> pl.DataFrame:
    nxt = ps.with_columns(season=c("season") - 1).rename({k: f"{k}_next" for k in ["team", "n", "eff", "own_adot", "own_deep", "own_middle", "cast"]})
    j = ps.join(nxt, on=["season", "pid"]).join(pos, left_on="pid", right_on="gsis_id", how="left")
    if who == "wr":
        j = j.filter(c("position") == "WR")
    else:
        j = j.filter(c("position") == "QB")
    j = j.with_columns(mover=c("team") != c("team_next"), age=(pl.date(c("season"), 9, 1) - c("birth")).dt.total_days() / 365.25)
    old = ts.select("team", "season", *[c(m).alias(f"old_{m}") for m in SCHEME])
    # the new team's head coach next season, and that coach's scheme this season if they were a head coach
    new_coach = ts.select(c("team").alias("team_next"), (c("season") - 1).alias("season"), new_coach=c("coach"))
    new_team = ts.select(c("team").alias("team_next"), "season", *[c(m).alias(f"nt_{m}") for m in SCHEME])
    j = (j.join(old, on=["team", "season"]).join(new_coach, on=["team_next", "season"], how="left")
         .join(cs.rename({"coach": "new_coach"}), on=["new_coach", "season"], how="left")
         .join(new_team, on=["team_next", "season"], how="left"))
    j = j.with_columns(*[pl.coalesce(c(f"c_{m}"), c(f"nt_{m}")).alias(f"new_{m}") for m in SCHEME],
                       coach_known=c(f"c_{SCHEME[0]}").is_not_null()).drop([f"c_{m}" for m in SCHEME] + [f"nt_{m}" for m in SCHEME])
    arr = ts.select(c("team").alias("team_next"), (c("season") - 1).alias("season"), *[c(m).alias(f"arr_{m}") for m in SCHEME])
    j = j.join(arr, on=["team_next", "season"], how="left")
    j = j.with_columns(
        distance=pl.sum_horizontal([(c(f"new_{m}") - c(f"old_{m}")) ** 2 for m in SCHEME]).truediv(len(SCHEME)).sqrt(),
        distance_arr=pl.sum_horizontal([(c(f"arr_{m}") - c(f"old_{m}")) ** 2 for m in SCHEME]).truediv(len(SCHEME)).sqrt(),
        d_eff=c("eff_next") - c("eff"),
    )
    j = j.with_columns(adot_z=(c("own_adot") - c("own_adot").mean()) / c("own_adot").std())
    j = j.with_columns(depth_fit=c("adot_z") * c("new_adot")).drop_nulls(["d_eff", "distance", "distance_arr", "cast", "cast_next", "age"])
    return j.filter(pl.all_horizontal([c(k).cast(pl.Float64).is_finite() for k in controls(j)]))


def controls(j: pl.DataFrame) -> list[str]:
    return ["eff", "n", "age", "cast", "cast_next", "adot_z", "own_deep", "own_middle", "season"] + [f"old_{m}" for m in SCHEME] + [f"new_{m}" for m in SCHEME]


def ols(y, T, X):
    A = np.column_stack([np.ones(len(y)), T, X])
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    e = y - A @ b
    cov = np.linalg.pinv(A.T @ A) * (e @ e) / (len(y) - A.shape[1])
    return b[1], np.sqrt(cov[1, 1])


def dml(y, T, X, seed=0):
    """Cross-fitted partialling out: residualize y and T on X with gradient boosting, then regress."""
    ry, rt = np.zeros_like(y), np.zeros_like(T)
    for tr, te in KFold(5, shuffle=True, random_state=seed).split(X):
        for target, out in ((y, ry), (T, rt)):
            m = HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=20)
            m.fit(X[tr], target[tr])
            out[te] = target[te] - m.predict(X[te])
    theta = (rt * ry).sum() / (rt * rt).sum()
    e = ry - theta * rt
    se = np.sqrt((rt ** 2 * e ** 2).sum()) / (rt * rt).sum()
    return theta, se


def placebo(j: pl.DataFrame, ts: pl.DataFrame, treat: str) -> np.ndarray:
    """Each mover gets the scheme of a random other team (not its old team) from the same season."""
    out = []
    seasons = j["season"].to_numpy()
    olds = j["team"].to_list()
    by_season = {s: ts.filter(c("season") == s) for s in np.unique(seasons)}
    X = j.select(controls(j)).to_numpy()
    y = j["d_eff"].to_numpy()
    for _ in range(200):
        new = np.zeros((j.height, len(SCHEME)))
        for i, (s, o) in enumerate(zip(seasons, olds)):
            pool = by_season[s].filter(c("team") != o)
            new[i] = pool.row(int(RNG.integers(pool.height)))[2:2 + len(SCHEME)]
        oldv = j.select([f"old_{m}" for m in SCHEME]).to_numpy()
        if treat == "distance":
            T = np.sqrt(((new - oldv) ** 2).mean(axis=1))
        else:
            T = j["adot_z"].to_numpy() * new[:, SCHEME.index("adot")]
        Xp = X.copy()
        k0 = len(controls(j)) - len(SCHEME)
        Xp[:, k0:] = new
        out.append(ols(y, T, Xp)[0])
    return np.array(out)


def report(j: pl.DataFrame, ts: pl.DataFrame, label: str, treats: list[str], unit: str) -> None:
    mv = j.filter(c("mover"))
    st = j.filter(~c("mover"))
    print(f"\n== {label}: {mv.height} movers ({mv['coach_known'].mean():.0%} with the new coach's own scheme known), {st.height} stayers")
    print(f"   change in {unit}: movers {mv['d_eff'].mean():+.3f}, stayers {st['d_eff'].mean():+.3f}; scheme distance: movers {mv['distance'].mean():.2f}, stayers {st['distance'].mean():.2f}")
    for treat in treats:
        y, T, X = mv["d_eff"].to_numpy(), mv[treat].to_numpy(), mv.select(controls(mv)).to_numpy()
        b, se = ols(y, T, X)
        th, sth = dml(y, T, X)
        pl_ = placebo(mv, ts, treat) if treat != "distance_arr" else np.array([np.nan])
        sd = T.std()
        print(f"   {treat:<10} OLS {b:+.4f} ({b - 1.645 * se:+.4f} to {b + 1.645 * se:+.4f}) per unit; per sd of {treat}: {b * sd:+.4f} {unit}")
        print(f"   {'':<10} DML {th:+.4f} ({th - 1.645 * sth:+.4f} to {th + 1.645 * sth:+.4f}); placebo moves: 90% of OLS estimates {np.quantile(pl_, 0.05):+.4f} to {np.quantile(pl_, 0.95):+.4f}, real beyond {np.mean(np.abs(pl_) < abs(b)):.0%} of them")
        if treat == "distance_arr":
            # stayers: their own team's scheme changing around them, measured the same way (a bigger sample)
            bs, ses = ols(st["d_eff"].to_numpy(), st[treat].to_numpy(), st.select(controls(st)).to_numpy())
            print(f"   {'':<10} stayers ({st.height}, scheme change around them {st[treat].mean():.2f}): OLS {bs:+.4f} ({bs - 1.645 * ses:+.4f} to {bs + 1.645 * ses:+.4f})")


def learning(p: pl.DataFrame, j: pl.DataFrame, who: str, unit: str) -> None:
    col = "receiver_player_id" if who == "wr" else "qb"
    x = p.filter(c(col).is_not_null()) if who == "qb" else p.filter((c("pass_attempt") == 1) & (c("sack") == 0) & c(col).is_not_null())
    x = x.rename({col: "pid"}).with_columns(g=c("week").rank("dense").over("season", "pid", "posteam"))
    nxt = j.select("pid", (c("season") + 1).alias("season"), c("team_next").alias("posteam"), "mover", "distance")
    q = x.join(nxt, on=["pid", "season", "posteam"]).group_by("pid", "season", "mover", "distance").agg(
        early=c("epa").filter(c("g") <= 4).mean(), late=c("epa").filter(c("g") >= 9).mean()).drop_nulls().with_columns(gap=c("early") - c("late"))
    for mv in (True, False):
        s = q.filter(c("mover") == mv)
        print(f"   {'movers' if mv else 'stayers':<8} first 4 games less games 9+: {s['gap'].mean():+.3f} {unit} (± {1.645 * s['gap'].std() / np.sqrt(s.height):.3f}, n {s.height})")
    m = q.filter(c("mover"))
    b, se = ols(m["gap"].to_numpy(), m["distance"].to_numpy(), np.zeros((m.height, 0)))
    print(f"   movers' gap against scheme distance: {b:+.3f} per unit of distance ({b - 1.645 * se:+.3f} to {b + 1.645 * se:+.3f})")


def coverage_fit() -> None:
    """I22: a QB's EPA against man less against zone, as a lasting trait, times the opponent's man
    rate (2018-2024, when participation has coverage)."""
    rows = []
    for s in range(2018, 2025):
        p = read_part("play", "pbp", [s]).select("game_id", "play_id", "season", "season_type", "week", "posteam", "defteam", "passer_player_id", "rusher_player_id", "qb_dropback", "qb_scramble", "epa").collect()
        part = read_part("play", "participation", [s]).select("game_id", "play_id", "defense_man_zone_type").collect()
        rows.append(p.filter((c("season_type") == "REG") & (c("qb_dropback") == 1) & c("epa").is_not_null()).join(part, on=["game_id", "play_id"], how="left")
                    .with_columns(qb=pl.when(c("qb_scramble") == 1).then(c("rusher_player_id")).otherwise(c("passer_player_id")),
                                  man=(c("defense_man_zone_type") == "MAN_COVERAGE").cast(pl.Float64))
                    .filter(c("defense_man_zone_type").is_in(["MAN_COVERAGE", "ZONE_COVERAGE"])))
    d = pl.concat(rows)
    qs = d.group_by("qb", "season").agg(
        n_man=(c("man") == 1).sum(), n_zone=(c("man") == 0).sum(),
        e_man=c("epa").filter(c("man") == 1).mean(), e_zone=c("epa").filter(c("man") == 0).mean(), e_all=c("epa").mean(),
    ).filter((c("n_man") >= 60) & (c("n_zone") >= 150)).with_columns(split=c("e_man") - c("e_zone"))
    nx = qs.select("qb", (c("season") - 1).alias("season"), split_next=c("split"), e_next=c("e_all"))
    j = qs.join(nx, on=["qb", "season"])
    r1 = np.corrcoef(j["split"], j["split_next"])[0, 1]
    # split-half within a season: odd against even weeks
    h = d.with_columns(odd=c("week") % 2).group_by("qb", "season", "odd").agg(
        e_man=c("epa").filter(c("man") == 1).mean(), e_zone=c("epa").filter(c("man") == 0).mean(), n=pl.len()).filter(c("n") >= 120).with_columns(split=c("e_man") - c("e_zone"))
    hh = h.filter(c("odd") == 1).join(h.filter(c("odd") == 0), on=["qb", "season"], suffix="_e").drop_nulls(["split", "split_e"])
    r2 = np.corrcoef(hh["split"], hh["split_e"])[0, 1]
    print(f"\n== QB coverage fit (I22), 2018-2024: {qs.height} QB-seasons with 60+ dropbacks against man and 150+ against zone")
    print(f"   the man-less-zone EPA split repeats: odd against even weeks r {r2:+.2f} (n {hh.height}); season to season r {r1:+.2f} (n {j.height})")
    # game level: the QB's split from last season × the opponent's man rate in its earlier games this season
    g = d.group_by("game_id", "season", "week", "qb", "posteam", "defteam").agg(epa=c("epa").mean(), n=pl.len()).filter(c("n") >= 15)
    dm = d.group_by("game_id", "season", "week", "defteam").agg(m=c("man").sum(), k=pl.len()).sort("defteam", "season", "week").with_columns(
        opp_man=(c("m").cum_sum().over("defteam", "season") - c("m")) / (c("k").cum_sum().over("defteam", "season") - c("k")))
    da = d.group_by("game_id", "defteam").agg(e=c("epa").sum(), k=pl.len()).join(dm.select("game_id", "defteam", "season", "week"), on=["game_id", "defteam"]).sort("defteam", "season", "week").with_columns(
        opp_def=(c("e").cum_sum().over("defteam", "season") - c("e")) / (c("k").cum_sum().over("defteam", "season") - c("k")))
    prior = qs.select("qb", (c("season") + 1).alias("season"), "split", prior_e="e_all")
    x = (g.join(prior, on=["qb", "season"]).join(dm.select("game_id", "defteam", "opp_man"), on=["game_id", "defteam"])
         .join(da.select("game_id", "defteam", "opp_def"), on=["game_id", "defteam"]).filter(c("week") >= 4).drop_nulls().drop_nans())
    z = lambda v: (v - v.mean()) / v.std()  # noqa: E731
    sp, om = z(x["split"].to_numpy()), z(x["opp_man"].to_numpy())
    y = x["epa"].to_numpy()
    X = np.column_stack([x["prior_e"].to_numpy(), x["opp_def"].to_numpy(), sp, om])
    b, se = ols(y, sp * om, X)
    weeks = (x["season"] * 100 + x["week"]).to_numpy()
    null = []
    for _ in range(200):
        perm = np.arange(x.height)
        for k in np.unique(weeks):
            w = np.where(weeks == k)[0]
            perm[w] = RNG.permutation(w)
        Xp = X.copy()
        Xp[:, 3] = om[perm]
        Xp[:, 1] = x["opp_def"].to_numpy()[perm]
        null.append(ols(y, sp * om[perm], Xp)[0])
    null = np.array(null)
    print(f"   game level ({x.height} QB-games, weeks 4+, 2019-2024): split × opponent man rate {b:+.4f} EPA per dropback per sd² ({b - 1.645 * se:+.4f} to {b + 1.645 * se:+.4f}); "
          f"shuffled opponents' 90% {np.quantile(null, 0.05):+.4f} to {np.quantile(null, 0.95):+.4f}, real beyond {np.mean(np.abs(null) < abs(b)):.0%}")


def main() -> None:
    coverage_fit()
    p = plays()
    pos = positions()
    ts, cs = schemes()
    for who, label, unit, treats in (("wr", "Wide receivers (40+ targets both seasons)", "EPA per target", ["distance", "distance_arr", "depth_fit"]),
                                     ("qb", "QBs (200+ dropbacks both seasons)", "EPA per dropback", ["distance", "distance_arr"])):
        j = pairs(player_seasons(p, who), ts, cs, pos, who)
        report(j, ts, label, treats, unit)
        print("   learning curve (I24):")
        learning(p, j, who, unit)


if __name__ == "__main__":
    main()
