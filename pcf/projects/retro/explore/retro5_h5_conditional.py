# ruff: noqa: E501
"""Retro 5, the quick group: H5, strength is conditional (the CEO's, 2026-11-07), the test retro 4 pre-registered
(RETRO.md, retro 4, step 3) and rated retro-sized, not run until now.

Elo's saved walk-forward home margins (the pinned run 21082e26), 2016-2024 regular and post season; the 2025 vault is
never read. A team-game's residual is its margin less Elo's forecast of it. Four conditions, each a split of a team's
games into two kinds:
- home or away;
- the opponent's offense in the top or bottom third by dropback EPA a play to date this season (the middle third left
  out; weeks 1-3 left out, too few plays);
- the opponent pass-heavy or run-heavy (the top or bottom third of pass rate over expected to date, same rules);
- leading or trailing at the half (a game state: it can repeat but isn't known before kickoff, so it gets the repeat
  test only).
**Repeat:** for each team-season, the condition gap (mean residual in kind A less kind B) in odd weeks against even
weeks; r over team-seasons, 90% interval from resampled team-seasons.
**Pays:** a team-by-condition term, walk-forward: for each game, each side's gap to date (this season's earlier games
and last season's, its mean residual in this game's kind less its overall mean residual), shrunk by a slope fit on
earlier seasons (2017 on), added to Elo's home margin as the home side's term less the away side's. The gain is the
share of Elo's squared error removed, 90% interval from resampled weeks.

Pass rule (retro 4): held if at least one non-home condition repeats (split-half r 0.2+, interval above 0) **and** its
term adds with an interval above 0.
Odds (written before any test): the CEO, 2026-11-15: 30% a large effect; 50% nothing worth keeping. Claude: 10% for a
large effect; 75% that only home holds (P2, matchups tie). Scored as the CEO's 30% (held, large) against Claude's 10%.
Run from pcf/:  PCF_DATA_DIR=... python projects/retro/explore/retro5_h5_conditional.py > projects/retro/explore/retro5_h5_conditional.txt
"""

import os
from pathlib import Path

import numpy as np
import polars as pl

c = pl.col
D = Path(os.environ["PCF_DATA_DIR"])
T = D / "tables"
S = range(2015, 2025)
rng = np.random.default_rng(5)


def rd(p, cols):
    return pl.concat([pl.read_parquet(T / p / f"season={s}" / "data.parquet", columns=cols) for s in S], how="diagonal_relaxed")


elo = pl.read_parquet(D / "outputs/elo/margin/21082e26cec94ea1920081554197d201/history.parquet", columns=["game_id", "mean"])
sch = rd("team_game/schedule", ["game_id", "season", "week", "team", "opponent", "home"])
res = rd("team_game/result", ["game_id", "team", "margin"])
pbp = rd("play/pbp", ["game_id", "season", "week", "posteam", "qb_dropback", "epa", "pass_oe", "game_half", "posteam_score", "defteam_score", "half_seconds_remaining"])

g = sch.join(res, on=["game_id", "team"]).join(elo, on="game_id").with_columns(
    fc=pl.when(c("home")).then(c("mean")).otherwise(-c("mean"))
).with_columns(r=c("margin") - c("fc"))
print(f"team-games {g.height} ({g['season'].min()}-{g['season'].max()}); residual sd {g['r'].std():.2f} points")

# offenses' to-date rates (games before this week, this season)
wk = pbp.filter(c("posteam").is_not_null()).group_by("posteam", "season", "week").agg(
    db_epa=c("epa").filter(c("qb_dropback") == 1).sum(), db=(c("qb_dropback") == 1).sum(),
    proe=c("pass_oe").drop_nans().sum(), n_oe=c("pass_oe").drop_nans().count(),
).sort("week")
wk = wk.with_columns(
    cum_epa=c("db_epa").cum_sum().over("posteam", "season") - c("db_epa"),
    cum_db=c("db").cum_sum().over("posteam", "season") - c("db"),
    cum_oe=c("proe").cum_sum().over("posteam", "season") - c("proe"),
    cum_n=c("n_oe").cum_sum().over("posteam", "season") - c("n_oe"),
).with_columns(opp_epa=c("cum_epa") / c("cum_db"), opp_proe=c("cum_oe") / c("cum_n"))
opp = wk.select(c("posteam").alias("opponent"), "season", "week", "opp_epa", "opp_proe")
g = g.join(opp, on=["opponent", "season", "week"], how="left")
g = g.with_columns(
    q_epa=pl.when(c("week") > 3).then(c("opp_epa").rank().over("season", "week") / c("opp_epa").count().over("season", "week")),
    q_oe=pl.when(c("week") > 3).then(c("opp_proe").rank().over("season", "week") / c("opp_proe").count().over("season", "week")),
)
# halftime score: the last first-half play's score for each team
half = pbp.filter((c("game_half") == "Half1") & c("posteam").is_not_null()).sort("half_seconds_remaining", descending=True).group_by("game_id", "posteam").agg(
    lead=(c("posteam_score") - c("defteam_score")).last()
)
g = g.join(half.rename({"posteam": "team"}), on=["game_id", "team"], how="left")
COND = {
    "home or away": pl.when(c("home")).then(1).otherwise(0),
    "opponent's offense top or bottom third (dropback EPA)": pl.when(c("q_epa") > 2 / 3).then(1).when(c("q_epa") <= 1 / 3).then(0),
    "opponent pass-heavy or run-heavy (pass rate over expected)": pl.when(c("q_oe") > 2 / 3).then(1).when(c("q_oe") <= 1 / 3).then(0),
    "leading or trailing at the half": pl.when(c("lead") > 0).then(1).when(c("lead") < 0).then(0),
}
g = g.with_columns(**{f"k{i}": e for i, e in enumerate(COND.values())}).with_columns(blk=c("season") * 100 + c("week"))


def r_ci(x, y, n=2000):
    x, y = np.asarray(x), np.asarray(y)
    est = np.corrcoef(x, y)[0, 1]
    idx = rng.integers(0, len(x), (n, len(x)))
    v = [np.corrcoef(x[i], y[i])[0, 1] for i in idx]
    return est, *np.percentile(v, [5, 95])


print("\n== repeat: a team-season's condition gap, odd weeks against even weeks")
rep = {}
for i, name in enumerate(COND):
    k = f"k{i}"
    gaps = g.filter(c(k).is_not_null()).with_columns(half=c("week") % 2).group_by("team", "season", "half").agg(
        gap=c("r").filter(c(k) == 1).mean() - c("r").filter(c(k) == 0).mean()
    ).drop_nulls().drop_nans()
    w = gaps.pivot(on="half", index=["team", "season"], values="gap").drop_nulls()
    est, lo, hi = r_ci(w["0"], w["1"])
    rep[name] = (est, lo, hi)
    print(f"  {name:<62} team-seasons {w.height:>4}: r {est:+.2f} ({lo:+.2f} to {hi:+.2f})")

# ---------------------------------------------------------------- pays: the walk-forward term
g = g.sort("season", "week")


def to_date(frame, k):
    """Each team-game's gap to date in its own kind: mean residual in this game's kind less the overall mean residual,
    over the team's earlier games this season and all of last season's."""
    rows = []
    for (team,), t in frame.group_by("team"):
        t = t.sort("season", "week")
        ss, kk, rr = t["season"].to_numpy(), t[k].to_numpy(), t["r"].to_numpy()
        d = np.full(len(t), np.nan)
        for j in range(len(t)):
            if kk[j] is None or np.isnan(kk[j]):
                continue
            m = (np.arange(len(t)) < j) & (ss >= ss[j] - 1)
            same = m & (kk == kk[j])
            if same.sum() >= 3 and m.sum() >= 6:
                d[j] = rr[same].mean() - rr[m].mean()
        rows.append(t.select("game_id", "team").with_columns(d=pl.Series(d)))
    return pl.concat(rows)


def boot_gain(e0, e1, blk, n=2000):
    ub = np.unique(blk)
    idx = {b: np.where(blk == b)[0] for b in ub}
    est = 1 - e1.sum() / e0.sum()
    v = []
    for _ in range(n):
        pick = np.concatenate([idx[b] for b in rng.choice(ub, len(ub))])
        v.append(1 - e1[pick].sum() / e0[pick].sum())
    return est, *np.percentile(v, [5, 95])


print("\n== pays: a team-by-condition term beside Elo, walk-forward (home margin; share of Elo's squared error removed)")
pays = {}
for i, name in enumerate(list(COND)[:3]):
    k = f"k{i}"
    gk = g.with_columns(c(k).cast(pl.Float64))
    dd = to_date(gk, k)
    hm = gk.filter(c("home")).join(dd, on=["game_id", "team"], how="left").select("game_id", "season", "week", "blk", "margin", "fc", d_home="d")
    aw = gk.filter(~c("home")).join(dd, on=["game_id", "team"], how="left").select("game_id", d_away="d")
    x = hm.join(aw, on="game_id").with_columns(x=(c("d_home").fill_nan(None).fill_null(0) - c("d_away").fill_nan(None).fill_null(0)), y=c("margin") - c("fc"))
    out = []
    for s in range(2017, 2025):
        tr = x.filter(c("season") < s)
        b = float((tr["x"] * tr["y"]).sum() / (tr["x"] ** 2).sum()) if (tr["x"] ** 2).sum() > 0 else 0.0
        out.append(x.filter(c("season") == s).with_columns(b=pl.lit(b)))
    o = pl.concat(out).with_columns(e0=c("y") ** 2, e1=(c("y") - c("b") * c("x")) ** 2)
    est, lo, hi = boot_gain(o["e0"].to_numpy(), o["e1"].to_numpy(), o["blk"].to_numpy())
    pays[name] = (est, lo, hi)
    print(f"  {name:<62} games {o.height:>5}, slope by season {[round(v, 2) for v in o.group_by('season').agg(c('b').first()).sort('season')['b'].to_list()]}: {100 * est:+.2f}% ({100 * lo:+.2f}% to {100 * hi:+.2f}%)")

ok = [n for n in list(COND)[1:3] if rep[n][0] >= 0.2 and rep[n][1] > 0 and pays[n][1] > 0]
print(f"\n== verdict (retro 4's rule: a non-home condition repeats at r 0.2+ with interval above 0 and its term adds): {'held: ' + ', '.join(ok) if ok else 'failed'}")
print(f"   home's own: repeat r {rep['home or away'][0]:+.2f}; term {100 * pays['home or away'][0]:+.2f}%")
