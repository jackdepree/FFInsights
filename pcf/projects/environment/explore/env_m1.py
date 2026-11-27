"""Environment, the noise ceiling and method 1 (pre-registered in EXPLORATION.md before this ran; discovery only).

1. The noise ceiling: per outcome, trees on the conditions alone (leave a season out; 5 seeds), and split halves
   (the conditions-only linear model on odd against even seasons).
2. H123: Welch t-tests for each condition's contrast on each outcome, Benjamini-Hochberg at 5% over all of them.
3. Side a: every condition together beside the team's and opponent's previous-8-game means, the closing spread and
   total, with robust errors and the same false-discovery rate.
4. Side b: total points less the closing total on the conditions, walk-forward (train on earlier seasons, test
   2016-2024), against the closing total alone; 90% interval from 1,000 resamples of weeks.
5. H127: the conditions-only linear model's out-of-fold share of each outcome's variation (a season held out at a time).
6. H126: home margin less Elo's margin forecast (2016-2024) on the home-by-weather terms, a season held out at a time;
   the same against the closing spread, 2000-2024.
7. The forecast against the observed weather, 2022-2024.

Run from pcf/:  python projects/environment/explore/env_m1.py   (writes env_m1.txt)
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl
from scipy import stats
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).parent))
from env_common import LABEL, OUTCOMES, Say, games, team_games, weather  # noqa: E402

c = pl.col
RNG = np.random.default_rng(7)
say = Say(Path(__file__).with_suffix(".txt"))
TEAM_X = ["wind", "cold", "precip", "dome", "turf", "short_rest", "long_rest", "altitude", "primetime"]
GAME_LEVEL = ("game_total", "home_margin")


def bh(p: np.ndarray, q: float = 0.05) -> np.ndarray:
    """Benjamini-Hochberg: which p-values survive at false-discovery rate q."""
    n = len(p)
    o = np.argsort(p)
    ok = p[o] <= q * (np.arange(1, n + 1) / n)
    k = np.max(np.nonzero(ok)[0]) + 1 if ok.any() else 0
    out = np.zeros(n, bool)
    out[o[:k]] = True
    return out


def rows_for(o: str, t: pl.DataFrame, g: pl.DataFrame) -> pl.DataFrame:
    """Team-game rows for team outcomes; game rows (either team's rest) for the total and the margin."""
    if o in GAME_LEVEL:
        r = t.group_by("game_id").agg(c("short_rest").any(), c("long_rest").any())
        return g.join(r, on="game_id", how="inner").with_columns(cold=(50 - c("temp")).clip(0, None), y=c(o)).filter(c("y").is_not_null())
    return t.with_columns(cold=(50 - c("temp")).clip(0, None), y=c(o)).filter(c("y").is_not_null() & c("y").is_finite())


def X_of(x: pl.DataFrame) -> np.ndarray:
    return np.column_stack([x[k].cast(pl.Float64).fill_null(0).to_numpy() for k in TEAM_X])


def ols(X, y):
    A = np.column_stack([np.ones(len(y)), X])
    b = np.linalg.lstsq(A, y, rcond=None)[0]
    return b, A


def robust_t(X, y):
    b, A = ols(X, y)
    e = y - A @ b
    inv = np.linalg.pinv(A.T @ A)
    V = inv @ (A.T * e**2) @ A @ inv * len(y) / (len(y) - A.shape[1])
    return b, b / np.sqrt(np.diag(V)), len(y) - A.shape[1]


def loso_r2(x: pl.DataFrame, pred_fn) -> float:
    y = x["y"].to_numpy()
    p = np.zeros(len(y))
    seas = x["season"].to_numpy()
    for s in np.unique(seas):
        tr, te = seas != s, seas == s
        p[te] = pred_fn(tr, te)
    return 1 - np.sum((y - p) ** 2) / np.sum((y - y.mean()) ** 2)


def contrasts(x: pl.DataFrame):
    out = (x["dome"] == False)  # noqa: E712
    return {
        "wind": (out & (x["wind"] >= 15), out & (x["wind"] < 10)),
        "cold": (out & (x["temp"] <= 32), out & (x["temp"] >= 50)),
        "rain": (out & (x["precip"] >= 0.02), out & (x["precip"] <= 0.0)),
        "dome": (x["dome"] == True, out),  # noqa: E712
        "surface": (x["turf"] == True, x["turf"] == False),  # noqa: E712
        "short rest": (x["short_rest"] == True, (x["short_rest"] == False) & (x["long_rest"] == False)),  # noqa: E712
        "long rest": (x["long_rest"] == True, (x["short_rest"] == False) & (x["long_rest"] == False)),  # noqa: E712
        "altitude": (x["altitude"] == True, x["altitude"] == False),  # noqa: E712
        "prime time": (x["primetime"] == True, x["primetime"] == False),  # noqa: E712
    }


def main() -> None:
    g = games()
    t = team_games()
    say("# Environment: the noise ceiling and method 1 (2026-11-27)", "",
        f"Regular-season games 1999-2024: {g.height:,}; outdoor or open with weather: {g.filter(~c('dome') & c('wind').is_not_null()).height:,}; "
        f"team-games 2000-2024: {t.height:,}.", "",
        f"Weather shares (outdoor games): 15+ mph {g.filter(~c('dome'))['wind'].ge(15).mean():.1%}; 32°F or colder {g.filter(~c('dome'))['temp'].le(32).mean():.1%}; "
        f"rain or snow (0.02+ in/h) {g.filter(~c('dome'))['precip'].ge(0.02).mean():.1%}; altitude games {g['altitude'].mean():.1%}; prime time {g['primetime'].mean():.1%}; turf {g['turf'].mean():.1%}; dome or closed {g['dome'].mean():.1%}.")
    m = g.filter(~c("dome") & c("wind_reading").is_not_null() & c("wind").is_not_null())
    say(f"Check: Open-Meteo's observed wind against the schedule's game-time reading, r {np.corrcoef(m['wind'], m['wind_reading'])[0, 1]:.2f}; temperature r {np.corrcoef(m['temp'], m['temp_reading'].cast(pl.Float64))[0, 1]:.2f} ({m.height:,} games).", "")

    # 1. the noise ceiling, and 5. H127's ranking
    say("## The noise ceiling, and the share each outcome's variation the conditions explain (H127)", "",
        "| Outcome | Rows | Trees' share, out of fold (5 seeds: mean, range) | Linear share, out of fold | Split halves: predictions r (odd against even seasons) |", "|---|---|---|---|---|")
    share = {}
    for o in OUTCOMES:
        x = rows_for(o, t, g)
        X, y = X_of(x), x["y"].to_numpy()
        lin = loso_r2(x, lambda tr, te, X=X, y=y: np.column_stack([np.ones(te.sum()), X[te]]) @ ols(X[tr], y[tr])[0])
        tree = [loso_r2(x, lambda tr, te, X=X, y=y, s=s: HistGradientBoostingRegressor(max_iter=150, learning_rate=0.05, max_leaf_nodes=15, random_state=s).fit(X[tr], y[tr]).predict(X[te])) for s in range(5)]
        odd = x["season"].to_numpy() % 2 == 1
        bo, _ = ols(X[odd], y[odd])
        be, _ = ols(X[~odd], y[~odd])
        A = np.column_stack([np.ones(len(y)), X])
        r_half = np.corrcoef(A @ bo, A @ be)[0, 1]
        share[o] = lin
        say(f"| {LABEL[o]} | {x.height:,} | {np.mean(tree):+.2%} ({min(tree):+.2%} to {max(tree):+.2%}) | {lin:+.2%} | {r_half:.2f} |")
    rank = sorted(share, key=share.get, reverse=True)
    say("", "Ranked by the linear share: " + "; ".join(f"{LABEL[o]} {share[o]:+.2%}" for o in rank), "")

    # 2. H123: simple tests
    say("## H123: simple tests (Welch's t, Benjamini-Hochberg at 5% over every condition and outcome)", "")
    tests = []
    for o in OUTCOMES:
        x = rows_for(o, t, g)
        for k, (a, b) in contrasts(x).items():
            ya, yb = x.filter(a)["y"].to_numpy(), x.filter(b)["y"].to_numpy()
            if len(ya) < 20 or len(yb) < 20:
                continue
            tt = stats.ttest_ind(ya, yb, equal_var=False)
            tests.append((k, o, ya.mean() - yb.mean(), len(ya), tt.pvalue))
    p = np.array([z[4] for z in tests])
    keep = bh(p)
    say("| Condition | Outcomes that survive (difference, rows in the condition) |", "|---|---|")
    conds = sorted({z[0] for z in tests}, key=lambda k: list(contrasts(t.head(1).with_columns(cold=pl.lit(0.0))).keys()).index(k))
    passed = set()
    for k in conds:
        hits = [f"{LABEL[z[1]]} {z[2]:+.3g} (n {z[3]:,})" for z, ok in zip(tests, keep, strict=True) if ok and z[0] == k]
        if hits:
            passed.add(k.split()[-1] if k in ("short rest", "long rest") else k)
        say(f"| {k} | {'; '.join(hits) if hits else 'none'} |")
    say("", f"Conditions with at least one surviving outcome (rest counted once): {len(passed)} of 8 ({', '.join(sorted(passed))}). "
        f"H123 (3+): {'held' if len(passed) >= 3 else 'failed'}.", "")

    # 3. side a: beside the obvious inputs
    say("## Side a: every condition together, beside the previous-8-game means and the closing spread and total", "")
    rows = []
    for o in OUTCOMES:
        x = rows_for(o, t, g)
        if o in GAME_LEVEL:
            pre = t.filter(c("home")).select("game_id", "spread", "total_line")
            x = x.join(pre, on="game_id", how="left")
            ctrl = ["spread", "total_line"]
        else:
            ctrl = [f"{o}_prior", f"{o}_opp", "spread", "total_line"]
        x = x.drop_nulls(ctrl)
        X = np.column_stack([X_of(x), *[x[k].to_numpy() for k in ctrl]])
        b, tv, df = robust_t(X, x["y"].to_numpy())
        for i, k in enumerate(TEAM_X):
            rows.append((k, o, b[i + 1], 2 * stats.t.sf(abs(tv[i + 1]), df)))
    keep = bh(np.array([r[3] for r in rows]))
    say("| Condition | Outcomes that survive beside the obvious inputs (coefficient) |", "|---|---|")
    pa = set()
    for k in TEAM_X:
        hits = [f"{LABEL[r[1]]} {r[2]:+.3g}" for r, ok in zip(rows, keep, strict=True) if ok and r[0] == k]
        if hits:
            pa.add("rest" if "rest" in k else k)
        say(f"| {k} | {'; '.join(hits) if hits else 'none'} |")
    say("", f"Side a (3+ of 8 beside the obvious inputs): {len(pa)} ({', '.join(sorted(pa))}): {'held' if len(pa) >= 3 else 'failed'}.", "")

    # 4. side b: beyond the closing total, walk-forward
    x = rows_for("game_total", t, g).join(t.filter(c("home")).select("game_id", "total_line"), on="game_id", how="left").drop_nulls("total_line")
    X, y, line = X_of(x), x["y"].to_numpy(), x["total_line"].to_numpy()
    seas, wk = x["season"].to_numpy(), (x["season"] * 100 + x["week"]).to_numpy()
    e0, e1, ids = [], [], []
    for s in range(2016, 2025):
        tr, te = seas < s, seas == s
        b, _ = ols(X[tr], (y - line)[tr])
        pr = line[te] + np.column_stack([np.ones(te.sum()), X[te]]) @ b
        e0.append((y[te] - line[te]) ** 2)
        e1.append((y[te] - pr) ** 2)
        ids.append(wk[te])
    e0, e1, ids = np.concatenate(e0), np.concatenate(e1), np.concatenate(ids)
    u, inv = np.unique(ids, return_inverse=True)
    A, B = np.bincount(inv, e1), np.bincount(inv, e0)
    idx = RNG.integers(0, len(u), (1000, len(u)))
    gb = 1 - A[idx].sum(1) / B[idx].sum(1)
    gain = 1 - e1.sum() / e0.sum()
    say("## Side b: total points beyond the closing total, walk-forward 2016-2024", "",
        f"Gain over the closing total: {gain:+.3%} (90%: {np.quantile(gb, 0.05):+.3%} to {np.quantile(gb, 0.95):+.3%}), {len(e0):,} games. "
        f"Side b: {'held' if np.quantile(gb, 0.05) > 0 else 'failed'}.")
    b_all, tv, _ = robust_t(X, y - line)
    say("Leftover against the close, all seasons (points; robust t): " + "; ".join(f"{k} {b_all[i + 1]:+.2f} (t {tv[i + 1]:+.1f})" for i, k in enumerate(TEAM_X)), "")
    raw = rows_for("game_total", t, g)
    w15 = raw.filter(~c("dome") & (c("wind") >= 15))["y"].mean() - raw.filter(~c("dome") & (c("wind") < 10))["y"].mean()
    say(f"Raw: 15+ mph games against calm (under 10), total points {w15:+.2f}; the closing total's own gap {raw.join(t.filter(c('home')).select('game_id', 'total_line'), on='game_id').filter(~c('dome') & (c('wind') >= 15))['total_line'].mean() - raw.join(t.filter(c('home')).select('game_id', 'total_line'), on='game_id').filter(~c('dome') & (c('wind') < 10))['total_line'].mean():+.2f}.", "")

    # 5. H127 verdicts
    top = rank[0]
    four = {"plays", "tempo_seconds", "dropbacks", "epa_sd", "game_total"}  # pace (plays or seconds a play), passing volume (dropbacks), spread, totals
    say("## H127", "", f"Largest share: {LABEL[top]} ({share[top]:+.2%}). The CEO's H127 (not margin, interceptions, sacks or yards a play): "
        f"{'held' if top not in ('home_margin', 'int_rate', 'sack_rate', 'yards_per_play') else 'failed'}.")
    top4 = rank[:4]
    groups = {"pace": {"plays", "tempo_seconds"}, "passing volume": {"dropbacks"}, "spread": {"epa_sd"}, "totals": {"game_total"}}
    n_in = sum(bool(v & set(top4)) for v in groups.values())
    say(f"Top four: {', '.join(LABEL[o] for o in top4)}. The first wording's four (pace counted by its best measure) in the top four: {n_in} of 4. "
        f"Exactly the top four: {'held' if n_in == 4 else 'failed'}; 3+: {'held' if n_in >= 3 else 'failed'}.", "")
    _ = four

    # 6. H126: home field with the weather, beyond Elo (2016-2024) and the closing spread (2000-2024)
    elo = pl.read_parquet(Path(__import__("pcf.config", fromlist=["get_config"]).get_config().zone("outputs")) / "elo/margin/21082e26cec94ea1920081554197d201/history.parquet").select("game_id", elo="mean")
    climate = (g.filter(~c("dome") & c("kickoff").dt.month().is_in([11, 12, 1])).group_by("stadium_id").agg(late_temp=c("temp").mean()))
    home_st = g.group_by("season", "home_team").agg(st=c("stadium_id").mode().first(), home_dome=c("dome").mean() > 0.5).join(climate, left_on="st", right_on="stadium_id", how="left")
    gg = (g.join(home_st.select("season", "home_team", "home_dome", h_late="late_temp"), on=["season", "home_team"], how="left")
          .join(home_st.select("season", away_team="home_team", away_dome="home_dome", a_late="late_temp"), on=["season", "away_team"], how="left")
          .join(t.filter(c("home")).select("game_id", "spread"), on="game_id", how="left").join(elo, on="game_id", how="left"))
    gg = gg.with_columns(cold_mix=(~c("dome") & (c("temp") < 40) & (c("h_late") < 40) & (c("away_dome") | (c("a_late") >= 50))).fill_null(False),
                         windy=(~c("dome") & (c("wind") >= 15)).fill_null(False), wet=(~c("dome") & (c("precip") >= 0.02)).fill_null(False),
                         dome_out=(~c("dome") & c("away_dome")).fill_null(False))
    H = ["cold_mix", "windy", "wet", "dome_out"]
    say("## H126: the home edge with the weather", "")
    for base, s0 in (("elo", 2016), ("spread", 2000)):
        x = gg.filter((c("season") >= s0) & c(base).is_not_null() & c("home_margin").is_not_null())
        y = (x["home_margin"] - x[base]).to_numpy()
        X = np.column_stack([x[k].cast(pl.Float64).to_numpy() for k in H])
        seas = x["season"].to_numpy()
        pr = np.zeros(len(y))
        for s in np.unique(seas):
            tr, te = seas != s, seas == s
            b, _ = ols(X[tr], y[tr])
            pr[te] = np.column_stack([np.ones(te.sum()), X[te]]) @ b
        b0 = np.array([y[seas != s].mean() for s in seas])  # the base's own leftover mean, a season out
        e0, e1 = (y - b0) ** 2, (y - pr) ** 2
        gid = np.arange(len(y))
        idx = RNG.integers(0, len(gid), (1000, len(gid)))
        gb = 1 - e1[idx].sum(1) / e0[idx].sum(1)
        bf, tv, _ = robust_t(X, y)
        say(f"- Beyond {'Elo' if base == 'elo' else 'the closing spread'} ({s0}-2024, {len(y):,} games): gain {1 - e1.sum() / e0.sum():+.3%} (90%: {np.quantile(gb, 0.05):+.3%} to {np.quantile(gb, 0.95):+.3%}); "
            + "; ".join(f"{k} {bf[i + 1]:+.2f} points (t {tv[i + 1]:+.1f}, n {int(X[:, i].sum())})" for i, k in enumerate(H)))
        if base == "elo":
            h126 = np.quantile(gb, 0.05) > 0
            cm = x.filter(c("cold_mix"))
            side = (cm["home_margin"] - cm["elo"]).mean() if cm.height else float("nan")
    say("", f"H126 (beyond Elo, clear): {'held' if h126 else 'failed'}. Side: the cold mix beats Elo's margin by {side:+.2f} points in sample ({cm.height} games): {'held' if side == side and side >= 1 else 'failed'}.", "")

    # 7. the forecast against the observed weather
    f = weather("forecast")
    if f.height:
        o = weather("archive").join(f, on="game_id", suffix="_f").join(g.select("game_id", "season"), on="game_id").filter(c("season") >= 2022).drop_nulls(["wind", "wind_f"])
        say("## The forecast against the observed weather (2022-2024)", "",
            f"{o.height:,} outdoor games. Wind: r {np.corrcoef(o['wind'], o['wind_f'])[0, 1]:.2f}, mean miss {(o['wind'] - o['wind_f']).abs().mean():.2f} mph, 15+ mph flags agree {((o['wind'] >= 15) == (o['wind_f'] >= 15)).mean():.1%}. "
            f"Temperature: r {np.corrcoef(o['temp'], o['temp_f'])[0, 1]:.2f}, mean miss {(o['temp'] - o['temp_f']).abs().mean():.1f}°F, 32°F flags agree {((o['temp'] <= 32) == (o['temp_f'] <= 32)).mean():.1%}. "
            f"Rain: r {np.corrcoef(o['precip'], o['precip_f'])[0, 1]:.2f}, 0.02+ flags agree {((o['precip'] >= 0.02) == (o['precip_f'] >= 0.02)).mean():.1%}.")
        say("Caveat: Open-Meteo's archive of forecasts stitches each run's first hours together, so this is a short-lead forecast, not one issued a day before.")
    say.save()


if __name__ == "__main__":
    main()
