"""The CEO's H15, first look (2026-11-09, discovery only): restricted schemes and anti-clusters.

"a team will always deploy the most favorable scheme and game plan against their opponent, unless
their personnel or coaching prowess is incapable of effective implementation ... An anti-cluster
describes the limits of a team or personnel or coach, therefore it should predict performance loss
when they either attempt that scheme (unlikely) or when they have a clearly favorable plan that is
avoided."

**Clearly favorable (the CEO, 2026-11-09):** "what teams usually do against that opponent combined
with standard football strategy". So for each play and each option (a yes/no choice: pass, shotgun,
no-huddle, a deep throw, heavy personnel; man coverage, two-high, a blitz, an 8+ man box), the
favorable plan is the league's expected choice: a gradient-boosted model of what the average team
does given
- the situation: down, distance, field position, score, win chance, time, home, season;
- for defensive options, the offense's look before the snap: shotgun, running backs and tight ends
  on the field, and its pass chance (nflfastR `xpass`);
- this opponent's normal tendencies (leave-one-game-out regime means, as in `morphs.py`).
It's fitted on other seasons (5 folds by season), so a team never sets its own expectation.

A team's **use over expected** of an option is its mean (choice - expected) per regime (head coach
and starting QB) and per half of the regime's games (odd and even games). Low use over expected is
avoidance: the anti-trait. Clusters were noise at game level (F12), so this works per option.

(a) **Using the avoided option.** EPA residual on each play: EPA less a league model of EPA given
    the situation *and* the choice (other seasons). A unit's **gap** is its mean residual when it
    makes the choice, less when it doesn't: how much better than the league it is at the option,
    relative to its own alternative. Team strength cancels. For defensive options EPA is flipped
    (EPA prevented), so higher is always better for the team making the choice. H15 (a limit): units that avoid an
    option (in one half) have a lower gap (in the other half). The game-theory alternative (mixed
    strategies, a preference): no relation. Selection works *against* H15 here: rare users pick
    their best spots.
(b) **Passing up a favorable plan.** EPA residual given the situation only (not the choice), within
    each team-game (strength cancels). H15: avoiders lose more on plays where the option is
    favored, so residual ~ avoidance (other half) × expected choice is negative. Also with only the
    opponent's part of the expected choice (the expected choice less the same with a league-average
    opponent). All plays mix two losses: being worse at the option when using it (that's (a)) and
    passing it up; so (b) is also run on the passed-up plays alone, the CEO's literal case.
    Option tables are cached in interim/schemes_v2/h15/ (delete them to refit the league models).
(c) **Whose limit.** Is the gap a repeating trait (split halves)? And season to season, by what
    changed (nothing, the QB, the head coach), as in F3.
Nulls: avoidance shuffled across units within a season (200 times).

Plays: regular season 2006-2024, downs 1-3, win chance 5-95%, not the last two minutes of a half;
participation options 2016-2024 (coverage 2018-2024, dropbacks only: coverage isn't charted on
runs), and after the season only (retrospective). The vault (2025) isn't read.

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/restricted.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

from pcf.config import get_config
from pcf.data.tables.store import read_part

c = pl.col
RNG = np.random.default_rng(20261109)
SHUFFLES = 200
SEASONS = range(2006, 2025)
OUT = get_config().zone("interim") / "schemes_v2"
SIT = ["down", "ydstogo", "yardline_100", "score_differential", "wp", "half_seconds_remaining", "qtr", "home", "season"]
LOOK = ["shotgun", "rb", "te", "xpass"]
D_NORM = ["d_proe_faced", "d_adot_faced", "d_pressure", "d_man", "d_two_high", "d_blitz", "d_box_oe"]
O_NORM = ["proe", "shotgun_oe", "no_huddle_oe", "tempo", "adot", "p11", "heavy"]
# option: (side, column, the plays it's defined on)
OPTIONS = {
    "pass": ("off", "pass", c("down").is_not_null()),
    "shotgun": ("off", "shotgun", c("down").is_not_null()),
    "no_huddle": ("off", "no_huddle", c("down").is_not_null()),
    "deep": ("off", "deep", c("att")),
    "heavy": ("off", "heavy_p", c("rb").is_not_null()),
    "man": ("def", "man", c("man").is_not_null()),
    "two_high": ("def", "two_high", c("two_high").is_not_null()),
    "blitz": ("def", "blitz", c("blitz").is_not_null()),
    "box8": ("def", "box8", c("box8").is_not_null()),
}


def plays() -> pl.DataFrame:
    cols = ["game_id", "play_id", "season", "season_type", "week", "posteam", "defteam", "home_team", "down", "ydstogo",
            "yardline_100", "score_differential", "wp", "half_seconds_remaining", "qtr", "shotgun", "no_huddle", "pass", "rush",
            "qb_dropback", "qb_kneel", "qb_spike", "xpass", "air_yards", "pass_attempt", "sack", "epa"]
    frames = []
    for s in SEASONS:
        p = read_part("play", "pbp", [s]).select(cols).collect().filter(
            (c("season_type") == "REG") & ((c("pass") == 1) | (c("rush") == 1)) & (c("qb_kneel") == 0) & (c("qb_spike") == 0)
            & c("down").is_between(1, 3) & c("wp").is_between(0.05, 0.95) & (c("half_seconds_remaining") > 120) & (c("qtr") <= 4)
            & c("epa").is_not_null())
        if s >= 2016:
            part = read_part("play", "participation", [s]).select(
                "game_id", "play_id", "offense_personnel", "defenders_in_box", "number_of_pass_rushers",
                "defense_man_zone_type", "defense_coverage_type").collect()
            p = p.join(part, on=["game_id", "play_id"], how="left")
        frames.append(p)
    p = pl.concat(frames, how="diagonal_relaxed")
    mz, cov = c("defense_man_zone_type"), c("defense_coverage_type")
    shells = ["COVER_0", "COVER_1", "COVER_2", "COVER_3", "COVER_4", "COVER_6", "2_MAN"]
    p = p.with_columns(
        home=(c("posteam") == c("home_team")).cast(pl.Int8),
        att=(c("pass_attempt") == 1) & (c("sack") == 0) & c("air_yards").is_not_null(),
        rb=c("offense_personnel").str.extract(r"(\d) RB").cast(pl.Float64, strict=False),
        te=c("offense_personnel").str.extract(r"(\d) TE").cast(pl.Float64, strict=False),
    ).with_columns(
        deep=(c("air_yards") >= 20).cast(pl.Float64),
        heavy_p=pl.when(c("rb").is_not_null()).then(((c("rb") + c("te")) >= 3).cast(pl.Float64)),
        man=pl.when(mz.is_in(["MAN_COVERAGE", "ZONE_COVERAGE"]) & (c("qb_dropback") == 1)).then((mz == "MAN_COVERAGE").cast(pl.Float64)),
        two_high=pl.when(cov.is_in(shells) & (c("qb_dropback") == 1)).then(cov.is_in(["COVER_2", "COVER_4", "COVER_6", "2_MAN"]).cast(pl.Float64)),
        blitz=pl.when((c("qb_dropback") == 1) & c("number_of_pass_rushers").is_not_null()).then((c("number_of_pass_rushers") >= 5).cast(pl.Float64)),
        box8=pl.when(c("defenders_in_box").is_not_null()).then((c("defenders_in_box") >= 8).cast(pl.Float64)),
    )
    # regimes, and each team's leave-one-game-out regime normals (the opponent's "who they are")
    tg = pl.read_parquet(OUT / "team_game.parquet")
    loo = []
    for m in D_NORM + O_NORM:
        v = c(m).fill_nan(None)
        k = v.is_not_null().cast(pl.Int32)
        loo.append(pl.when(k.sum().over("regime") - k >= 3).then((v.fill_null(0).sum().over("regime") - v.fill_null(0)) / (k.sum().over("regime") - k)).alias(m))
    norms = tg.with_columns(*loo).select("game_id", "team", "regime", "coach", "qb", "game_in_regime", *D_NORM, *O_NORM)
    off = norms.select("game_id", c("team").alias("posteam"), c("regime").alias("o_regime"), c("coach").alias("o_coach"), c("qb").alias("o_qb"),
                       c("game_in_regime").alias("o_gir"), *[c(m).alias(f"on_{m}") for m in O_NORM])
    dfn = norms.select("game_id", c("team").alias("defteam"), c("regime").alias("d_regime"), c("coach").alias("d_coach"),
                       c("game_in_regime").alias("d_gir"), *[c(m).alias(f"dn_{m}") for m in D_NORM])
    return p.join(off, on=["game_id", "posteam"], how="inner").join(dfn, on=["game_id", "defteam"], how="inner")


def crossfit(X: np.ndarray, y: np.ndarray, fold: np.ndarray, classify: bool) -> np.ndarray:
    out = np.full(len(y), np.nan)
    for f in np.unique(fold):
        tr, te = fold != f, fold == f
        if classify:
            m = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.1, random_state=0).fit(X[tr], y[tr])
            out[te] = m.predict_proba(X[te])[:, 1]
        else:
            m = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.1, random_state=0).fit(X[tr], y[tr])
            out[te] = m.predict(X[te])
    return out


def option_table(p: pl.DataFrame, name: str) -> pl.DataFrame:
    side, col, rows = OPTIONS[name]
    q = p.filter(rows & c(col).is_not_null())
    feats = SIT + (LOOK + [f"on_{m}" for m in O_NORM] if side == "def" else [f"dn_{m}" for m in D_NORM])
    opp = [f for f in feats if f.startswith(("on_", "dn_"))]
    X = q.select(feats).to_numpy().astype(float)
    y = q[col].to_numpy().astype(float)
    fold = (q["season"].to_numpy() % 5)
    X0 = X.copy()
    X0[:, [feats.index(f) for f in opp]] = 0.0          # a league-average opponent (normals are season-centered)
    e, e0 = np.full(len(y), np.nan), np.full(len(y), np.nan)
    for f in np.unique(fold):
        tr, te = fold != f, fold == f
        m = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.1, random_state=0).fit(X[tr], y[tr])
        e[te] = m.predict_proba(X[te])[:, 1]             # the favorable (usual) choice
        e0[te] = m.predict_proba(X0[te])[:, 1]           # the same against a league-average opponent
    epa = q["epa"].to_numpy() * (1.0 if side == "off" else -1.0)   # defenses: EPA prevented, so higher is better for the chooser
    r1 = epa - crossfit(np.column_stack([X, y]), epa, fold, False)   # given the situation and the choice
    r0 = epa - crossfit(X, epa, fold, False)                         # given the situation only
    unit = "o_regime" if side == "off" else "d_regime"
    gir = "o_gir" if side == "off" else "d_gir"
    return q.select("game_id", "season", "posteam", "defteam", "o_coach", "o_qb", "d_coach", c(unit).alias("unit"),
                    (c(gir) % 2).alias("half")).with_columns(
        choice=pl.Series(y), exp=pl.Series(e), exp_opp=pl.Series(e - e0), r1=pl.Series(r1), r0=pl.Series(r0),
        team=c("posteam") if side == "off" else c("defteam"),
        coach=c("o_coach") if side == "off" else c("d_coach"),
        own_qb=c("o_qb") if side == "off" else pl.lit(None, pl.String))


def unit_halves(t: pl.DataFrame, min_each: int = 15) -> pl.DataFrame:
    """Per unit and half: use over expected, and the gap (residual when choosing less when not)."""
    h = t.group_by("unit", "half").agg(
        season=c("season").min(), n=pl.len(), use_oe=(c("choice") - c("exp")).mean(),
        n1=(c("choice") == 1).sum(), n0=(c("choice") == 0).sum(),
        g1=c("r1").filter(c("choice") == 1).mean(), g0=c("r1").filter(c("choice") == 0).mean(),
    ).with_columns(gap=pl.when((c("n1") >= min_each) & (c("n0") >= min_each)).then(c("g1") - c("g0")))
    a = h.filter(c("half") == 0).drop("half")
    b = h.filter(c("half") == 1).drop("half", "season")
    return a.join(b, on="unit", suffix="_b")


def perm_within(groups: np.ndarray) -> np.ndarray:
    idx = np.arange(len(groups))
    out = idx.copy()
    for g in np.unique(groups):
        w = idx[groups == g]
        out[w] = RNG.permutation(w)
    return out


def slope(x: np.ndarray, y: np.ndarray) -> float:
    x = x - x.mean()
    return float((x * (y - y.mean())).sum() / (x * x).sum())


def test_a(u: pl.DataFrame) -> dict:
    """Use over expected in one half against the gap in the other, both directions stacked."""
    x = np.concatenate([u["use_oe"].to_numpy(), u["use_oe_b"].to_numpy()])
    y = np.concatenate([u["gap_b"].to_numpy(), u["gap"].to_numpy()])
    g = np.concatenate([u["season"].to_numpy()] * 2)
    unit = np.concatenate([np.arange(u.height)] * 2)
    ok = ~(np.isnan(x) | np.isnan(y))
    x, y, g, unit = x[ok], y[ok], g[ok], unit[ok]
    sx = x.std()
    b = slope(x, y) * sx
    r = float(np.corrcoef(x, y)[0, 1])
    # bootstrap over units for the interval
    uu = np.unique(unit)
    where = {k: np.flatnonzero(unit == k) for k in uu}
    bs = []
    for _ in range(500):
        pick = RNG.choice(uu, len(uu))
        rows = np.concatenate([where[k] for k in pick])
        bs.append(slope(x[rows], y[rows]) * x[rows].std())
    # shuffled avoidance within season
    null = [slope(x[perm_within(g)], y) * sx for _ in range(SHUFFLES)]
    q = np.quantile(x, [0.2, 0.8])
    lo, hi = y[x <= q[0]].mean(), y[x >= q[1]].mean()
    # split-half reliability of the gap and of use over expected (per unit)
    both = u.drop_nulls(["gap", "gap_b"])
    rel_gap = float(np.corrcoef(both["gap"], both["gap_b"])[0, 1]) if both.height > 10 else float("nan")
    rel_use = float(np.corrcoef(u["use_oe"], u["use_oe_b"])[0, 1])
    return dict(n=int(ok.sum() // 2), b=b, lo90=np.quantile(bs, 0.05), hi90=np.quantile(bs, 0.95), r=r,
                p_null=float(np.mean(np.array(null) >= b)), avoiders=lo, frequent=hi, rel_gap=rel_gap, rel_use=rel_use, sd_use=sx)


def test_b(t: pl.DataFrame, u: pl.DataFrame) -> dict:
    """Within each team-game: residual (situation only) ~ avoidance from the other half × expected choice."""
    av = pl.concat([u.select("unit", half=pl.lit(1, pl.Int64), avoid=-c("use_oe")),
                    u.select("unit", half=pl.lit(0, pl.Int64), avoid=-c("use_oe_b"))])
    d = t.with_columns(c("half").cast(pl.Int64)).join(av, on=["unit", "half"], how="inner").with_columns(
        tg=pl.concat_str(c("game_id"), c("team")))
    d = d.with_columns(
        y=c("r0") - c("r0").mean().over("tg"),
        f=c("exp") - c("exp").mean().over("tg"),
        fo=c("exp_opp") - c("exp_opp").mean().over("tg"),
        z=(c("avoid") - c("avoid").mean()) / c("avoid").std(),
    )
    y, f, fo, z = (d[k].to_numpy() for k in ("y", "f", "fo", "z"))
    codes = d["unit"].cast(pl.Categorical).to_physical().to_numpy()
    uz = d.with_columns(code=pl.Series(codes)).group_by("code").agg(c("z").first(), c("season").first()).sort("code")
    assert (uz["code"].to_numpy() == np.arange(uz.height)).all()

    def coef(fv, zv):
        X = np.column_stack([fv, zv * fv])
        return float(np.linalg.lstsq(X, y, rcond=None)[0][1])

    out = {}
    for key, fv in (("all", f), ("opp", fo)):
        b = coef(fv, z)
        # shuffle avoidance across units within season (unit-level, then mapped to plays)
        null = []
        for _ in range(SHUFFLES):
            pz = uz["z"].to_numpy()[perm_within(uz["season"].to_numpy())]
            null.append(coef(fv, pz[codes]))
        null = np.array(null)
        out[key] = dict(b=b, sd_f=float(fv.std()), p_null=float(np.mean(null <= b)), lo=float(np.quantile(null, 0.05)), hi=float(np.quantile(null, 0.95)))
    out["plays"] = d.height
    return out


def test_c(t: pl.DataFrame) -> dict:
    """Season-to-season r of the gap and of use over expected, per team-season, by what changed."""
    ts = t.group_by("team", "season").agg(
        use=(c("choice") - c("exp")).mean(), n1=(c("choice") == 1).sum(), n0=(c("choice") == 0).sum(),
        g1=c("r1").filter(c("choice") == 1).mean(), g0=c("r1").filter(c("choice") == 0).mean(),
        coach=c("coach").mode().first(), qb=c("own_qb").mode().first(),
    ).with_columns(gap=pl.when((c("n1") >= 30) & (c("n0") >= 30)).then(c("g1") - c("g0")))
    nxt = ts.with_columns(season=c("season") - 1)
    pr = ts.join(nxt, on=["team", "season"], suffix="_n").with_columns(
        kind=pl.when(c("coach") != c("coach_n")).then(pl.lit("new coach")).when(c("qb") != c("qb_n")).then(pl.lit("new QB only")).otherwise(pl.lit("same both")))
    res = {}
    for k in ["same both", "new QB only", "new coach"]:
        s = pr.filter(c("kind") == k)
        g = s.drop_nulls(["gap", "gap_n"])
        res[k] = (float(np.corrcoef(s["use"], s["use_n"])[0, 1]) if s.height > 5 else np.nan,
                  float(np.corrcoef(g["gap"], g["gap_n"])[0, 1]) if g.height > 5 else np.nan, s.height, g.height)
    return res


def main() -> None:
    cache = OUT / "h15"
    cache.mkdir(parents=True, exist_ok=True)
    p = None
    rows = []
    for name in OPTIONS:
        f = cache / f"{name}.parquet"
        if f.exists():
            t = pl.read_parquet(f)
        else:
            if p is None:
                p = plays()
                print(f"plays {p.height:,} (2006-2024, downs 1-3, win chance 5-95%)")
            t = option_table(p, name)
            t.write_parquet(f)
        u = unit_halves(t)
        a = test_a(u)
        b = test_b(t, u)
        b_up = test_b(t.filter(c("choice") == 0), u)   # only the plays where the team passed the option up
        cc = test_c(t)
        rows.append((name, t, a, b, cc, b_up))
        print(f"\n== {name} ({OPTIONS[name][0]}): {t.height:,} plays, usual rate {t['choice'].mean():.2f}; "
              f"the league model's fit: mean |choice - expected| {np.abs(t['choice'] - t['exp']).mean():.3f}")
        print(f"  use over expected: sd across regime halves {a['sd_use']:.3f}, split-half r {a['rel_use']:+.2f}")
        print(f"  (a) gap (EPA/play, choosing less not choosing, beyond the league) per sd of use over expected (other half): "
              f"{a['b']:+.4f} (90% {a['lo90']:+.4f} to {a['hi90']:+.4f}), r {a['r']:+.3f}, shuffled at or above {a['p_null']:.0%}, units {a['n']}")
        print(f"      avoiders (bottom fifth) gap {a['avoiders']:+.4f}, frequent users (top fifth) {a['frequent']:+.4f}; gap split-half r {a['rel_gap']:+.2f}")
        for k, lab in (("all", "situation + opponent"), ("opp", "opponent part only")):
            v = b[k]
            print(f"  (b) {lab}: EPA/play per sd avoidance per unit of expected choice {v['b']:+.4f} "
                  f"(per sd of expected choice {v['b'] * v['sd_f']:+.4f}); shuffled 90% {v['lo']:+.4f} to {v['hi']:+.4f}, shuffled at or below {v['p_null']:.0%}")
        for k, lab in (("all", "situation + opponent"), ("opp", "opponent part only")):
            v = b_up[k]
            print(f"  (b) passed-up plays only, {lab}: per sd of expected choice {v['b'] * v['sd_f']:+.4f}; shuffled at or below {v['p_null']:.0%}")
        print("  (c) season to season r (use over expected, gap):", "; ".join(f"{k} {v[0]:+.2f}, {v[1]:+.2f} (n {v[2]}, {v[3]})" for k, v in cc.items()))
    print("\n== Summary")
    print(f"{'option':<10} {'use r':>6} {'(a) b/sd':>9} {'90%':>20} {'shuf>=':>7} {'gap rel':>8} {'(b) all':>9} {'p':>5} {'(b) opp':>9} {'p':>5} {'up all':>8} {'p':>5} {'up opp':>8} {'p':>5}")
    for name, _t, a, b, _cc, bu in rows:
        print(f"{name:<10} {a['rel_use']:>+6.2f} {a['b']:>+9.4f} {a['lo90']:>+9.4f} {a['hi90']:>+9.4f} {a['p_null']:>7.0%} {a['rel_gap']:>+8.2f} "
              f"{b['all']['b'] * b['all']['sd_f']:>+9.4f} {b['all']['p_null']:>5.0%} {b['opp']['b'] * b['opp']['sd_f']:>+9.4f} {b['opp']['p_null']:>5.0%} "
              f"{bu['all']['b'] * bu['all']['sd_f']:>+8.4f} {bu['all']['p_null']:>5.0%} {bu['opp']['b'] * bu['opp']['sd_f']:>+8.4f} {bu['opp']['p_null']:>5.0%}")


if __name__ == "__main__":
    main()
