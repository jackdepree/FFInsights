"""Shared machinery for the team-efficiency exploration (2026-11-12).

One pipeline for every hunch, so variants differ only in what they feed it:

1. **A measure** gives, per game and offense, a weight W and a weighted sum WY of some value
   (plays' EPA, series' EPA, WPA, ...). `sides()` builds it from plays.
2. **The rating** (`walk`): before each week of each season, a ridge regression on the games
   already played that season: value = league + home + offense + defense. Each game counts by its
   W times a recency weight (half-life in weeks). Ratings are pulled toward last season's final
   ratings times `pull`, with strength `lam` (in games' worth of W). Week 1 is the prior alone.
   Nothing from week w or later reaches the week-w rating.
3. **The main test** (the CEO, 2026-11-12: "its own future is the main test"): each team's EPA per
   play over its next 3 games and over the rest of the season, offense and defense, all plays,
   relative to the league that week. A variant predicts it from its own rating, the mean rating of
   the opponents it will face (the schedule is known) and its home share. The linear map is fitted
   on 2007-2015, as are the variant's settings; scored on 2016-2024. 2006 has no prior and is only
   a warm-up. The 2025 vault is never read.
4. **Skill** = 1 - squared error / the bar's squared error, with a 90% interval from resampling
   whole weeks (season-week moments).
"""

# ruff: noqa: E501
from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.clean import standard
from pcf.data.tables.store import read_part

c = pl.col
SEASONS = list(range(2006, 2025))
TUNE = list(range(2007, 2016))
SCORE = list(range(2016, 2025))
TEAMS = sorted(standard.TEAMS)
TIX = {t: i for i, t in enumerate(TEAMS)}
NT = len(TEAMS)


def plays() -> pl.DataFrame:
    p = pl.read_parquet(get_config().zone("interim") / "team-efficiency" / "plays.parquet")
    wk = p.group_by("season", "week").agg(league=c("epa").mean(), league_wpa=c("wpa").mean())
    return p.join(wk, on=["season", "week"]).with_columns(
        y_rel=c("epa") - c("league"),
        usual=(c("wp").is_between(0.1, 0.9) & (c("half_seconds_remaining") > 120)).fill_null(False),
    )


def schedule() -> pl.DataFrame:
    """Regular-season team-games: game_id, season, week, team, opponent, home (0/1)."""
    s = (
        read_part("team_game", "schedule", seasons=SEASONS)
        .filter(c("game_type") == "REG")
        .select("game_id", "season", "week", "team", "opponent", "home")
        .collect()
    )
    return standard.standard_teams(s, "team", "opponent").with_columns(c("home").cast(pl.Int8))


def results() -> pl.DataFrame:
    r = read_part("team_game", "result", seasons=SEASONS).select("game_id", "team", "points_for", "points_against").collect()
    return standard.standard_teams(r, "team")


def sides(p: pl.DataFrame, value: str = "epa", weight: str | None = None, unit: str | None = None) -> pl.DataFrame:
    """Per game and offense: W and WY. Plays weighted by `weight` (1 if None). With `unit`
    (e.g. "series_key"), the value is summed per unit first and each unit counts once (times the
    mean of its plays' weights): a rate per unit instead of per play."""
    w = c(weight) if weight else pl.lit(1.0)
    if unit is None:
        q = p.with_columns(_w=w.cast(pl.Float64))
        g = q.group_by("game_id", "posteam").agg(W=c("_w").sum(), WY=(c("_w") * c(value)).sum())
    else:
        q = p.with_columns(_w=w.cast(pl.Float64)).group_by("game_id", "posteam", unit).agg(
            S=c(value).sum(), _w=c("_w").mean()
        )
        g = q.group_by("game_id", "posteam").agg(W=c("_w").sum(), WY=(c("_w") * c("S")).sum())
    return g.rename({"posteam": "team"})


@dataclass(frozen=True)
class Params:
    half_life: float = 8.0  # weeks; 1000 = no recency
    lam: float = 5.0  # pull toward the prior, in games' worth of W
    pull: float = 0.5  # share of last season's final rating kept as this season's prior


GRID = [Params(h, l, q) for h, l, q in itertools.product((4.0, 8.0, 16.0, 1000.0), (2.0, 5.0, 10.0, 20.0), (0.3, 0.5, 0.7))]


def _fit(rows: np.ndarray, ref_week: float, prior_o: np.ndarray, prior_d: np.ndarray, prm: Params, wscale: float) -> tuple[np.ndarray, np.ndarray]:
    """rows: week, off, def, home, W, WY. Returns offense and defense ratings."""
    if rows.shape[0] == 0:
        return prior_o.copy(), prior_d.copy()
    wk, a, b, h, W, WY = (rows[:, i] for i in range(6))
    r = 0.5 ** ((ref_week - wk) / prm.half_life)
    n = rows.shape[0]
    X = np.zeros((n, 2 + 2 * NT))
    X[:, 0] = 1.0
    X[:, 1] = h
    X[np.arange(n), 2 + a.astype(int)] = 1.0
    X[np.arange(n), 2 + NT + b.astype(int)] = 1.0
    om = r * W
    ybar = np.where(W > 0, WY / np.where(W > 0, W, 1), 0.0)
    A = X.T @ (X * om[:, None])
    rhs = X.T @ (om * ybar)
    lam = prm.lam * wscale
    pen = np.full(2 + 2 * NT, lam)
    pen[:2] = 1e-6
    A[np.diag_indices_from(A)] += pen
    rhs[2 : 2 + NT] += lam * prior_o
    rhs[2 + NT :] += lam * prior_d
    th = np.linalg.solve(A, rhs)
    return th[2 : 2 + NT], th[2 + NT :]


def walk(s: pl.DataFrame, prm: Params, sched: pl.DataFrame) -> pl.DataFrame:
    """Ratings before every week of every season: season, week, team, o, d."""
    g = sched.join(s, on=["game_id", "team"], how="inner").with_columns(
        a=c("team").replace_strict(TIX), b=c("opponent").replace_strict(TIX)
    )
    wscale = float(g["W"].mean())
    out = []
    po = np.zeros(NT)
    pdf = np.zeros(NT)
    for season in SEASONS:
        gs = g.filter(c("season") == season)
        rows = gs.select("week", "a", "b", "home", "W", "WY").to_numpy().astype(float)
        last = int(gs["week"].max())
        for w in range(1, last + 1):
            o, d = _fit(rows[rows[:, 0] < w], w, po, pdf, prm, wscale)
            out.append(pl.DataFrame({"season": season, "week": w, "team": TEAMS, "o": o, "d": d}))
        o, d = _fit(rows, last + 1, po, pdf, prm, wscale)
        po = prm.pull * (o - o.mean())
        pdf = prm.pull * (d - d.mean())
    return pl.concat(out)


def team_games(p: pl.DataFrame, sched: pl.DataFrame) -> pl.DataFrame:
    """Per team-game (offense view): the target value (EPA per play relative to the league that
    week) and its plays, plus the opponent and home."""
    t = p.group_by("game_id", "posteam").agg(ysum=c("y_rel").sum(), n=pl.len()).rename({"posteam": "team"})
    return sched.join(t, on=["game_id", "team"], how="inner")


def units(tg: pl.DataFrame, horizon: str) -> pl.DataFrame:
    """For each moment (season, week w) and team: its next 3 games (or the rest of the season)
    from week w on. One row per (season, w, team, game)."""
    moments = tg.select("season", "week").unique().rename({"week": "w"})
    x = tg.join(moments, on="season").filter(c("week") >= c("w"))
    if horizon.startswith("next"):
        x = x.with_columns(k=c("week").rank("ordinal").over("season", "w", "team")).filter(c("k") <= int(horizon[4:]))
    return x


def unit_frame(tg: pl.DataFrame, horizon: str) -> pl.DataFrame:
    """Per (season, w, team, side): the target (EPA per play over the horizon's games, offense:
    gained, defense: allowed) and which games. Offense rows use tg as is; defense rows swap."""
    x = units(tg, horizon)
    off = x.select("season", "w", "team", "opponent", "home", "ysum", "n").with_columns(side=pl.lit("off"))
    # Defense: the same games seen from the defending team (the opponent's offense rows).
    d = tg.select("game_id", def_team="opponent", off_team="team", ysum_d="ysum", n_d="n")
    xd = units(tg, horizon).join(d, left_on=["game_id", "team"], right_on=["game_id", "def_team"])
    dfn = xd.select("season", "w", "team", opponent="off_team", home=1 - c("home"), ysum="ysum_d", n="n_d").with_columns(side=pl.lit("def"))
    return pl.concat([off, dfn])


def predict_frame(ratings: pl.DataFrame, uf: pl.DataFrame, extra: dict[str, pl.DataFrame] | None = None) -> pl.DataFrame:
    """Features per unit: own rating, mean opponent rating, home share, target y, plays n.
    `extra`: other ratings tables (name -> ratings) added as own_<name>/opp_<name>."""
    tabs = {"": ratings} | (extra or {})
    x = uf
    for name, r in tabs.items():
        sfx = f"_{name}" if name else ""
        rr = r.select("season", c("week").alias("w"), "team", c("o").alias(f"o{sfx}"), c("d").alias(f"d{sfx}"))
        x = x.join(rr, on=["season", "w", "team"], how="left")
        x = x.join(rr.rename({"team": "opponent", f"o{sfx}": f"oo{sfx}", f"d{sfx}": f"od{sfx}"}), on=["season", "w", "opponent"], how="left")
        x = x.with_columns(
            pl.when(c("side") == "off").then(c(f"o{sfx}")).otherwise(c(f"d{sfx}")).alias(f"own{sfx}"),
            pl.when(c("side") == "off").then(c(f"od{sfx}")).otherwise(c(f"oo{sfx}")).alias(f"opp{sfx}"),
        )
    feats = [f"own{'_' + n if n else ''}" for n in tabs] + [f"opp{'_' + n if n else ''}" for n in tabs]
    return x.group_by("season", "w", "team", "side").agg(
        *[c(f).mean() for f in feats], home=c("home").mean(), y=c("ysum").sum() / c("n").sum(), n=c("n").sum()
    )


def fit_score(pf: pl.DataFrame, feats: list[str]) -> pl.DataFrame:
    """Linear map per side fitted on TUNE; returns pf with `pred` (all seasons)."""
    outs = []
    for side in ("off", "def"):
        x = pf.filter(c("side") == side)
        tr = x.filter(c("season").is_in(TUNE))
        X = np.column_stack([np.ones(tr.height)] + [tr[f].to_numpy() for f in feats])
        b = np.linalg.lstsq(X, tr["y"].to_numpy(), rcond=None)[0]
        Xa = np.column_stack([np.ones(x.height)] + [x[f].to_numpy() for f in feats])
        outs.append(x.with_columns(pred=pl.Series(Xa @ b)))
    return pl.concat(outs)


def mse(pf: pl.DataFrame, seasons: list[int]) -> float:
    x = pf.filter(c("season").is_in(seasons))
    return float(((x["y"] - x["pred"]) ** 2).mean())


def run(s: pl.DataFrame, prm: Params, sched: pl.DataFrame, ufs: dict[str, pl.DataFrame]) -> dict[str, pl.DataFrame]:
    """Ratings -> scored predictions for each horizon."""
    r = walk(s, prm, sched)
    return {h: fit_score(predict_frame(r, uf), ["own", "opp", "home"]) for h, uf in ufs.items()} | {"_ratings": r}


def tune(s: pl.DataFrame, sched: pl.DataFrame, ufs: dict[str, pl.DataFrame], grid: list[Params] = GRID) -> tuple[Params, dict]:
    """Pick the settings with the lowest next-3 squared error on TUNE (offense and defense pooled)."""
    best, best_v, best_out = None, np.inf, None
    for prm in grid:
        out = run(s, prm, sched, {"next3": ufs["next3"]})
        v = mse(out["next3"], TUNE)
        if v < best_v:
            best, best_v, best_out = prm, v, out
    return best, run(s, best, sched, ufs)


def skill(pf: pl.DataFrame, bar: pl.DataFrame, seasons: list[int] = SCORE, n: int = 500, seed: int = 0, side: str | None = None) -> tuple[float, float, float]:
    """1 - SE/SE_bar on `seasons`, with a 90% interval from resampling season-week moments."""
    k = ["season", "w", "team", "side"]
    j = pf.select(*k, "y", "pred").join(bar.select(*k, pred_bar="pred"), on=k).filter(c("season").is_in(seasons))
    if side:
        j = j.filter(c("side") == side)
    m = j.group_by("season", "w").agg(se=((c("y") - c("pred")) ** 2).sum(), sb=((c("y") - c("pred_bar")) ** 2).sum())
    se, sb = m["se"].to_numpy(), m["sb"].to_numpy()
    est = 1 - se.sum() / sb.sum()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(se), size=(n, len(se)))
    boots = 1 - se[idx].sum(1) / sb[idx].sum(1)
    lo, hi = np.percentile(boots, [5, 95])
    return float(est), float(lo), float(hi)


def zero_pred(pf: pl.DataFrame) -> pl.DataFrame:
    """The league average (relative target 0) as a prediction."""
    return pf.with_columns(pred=pl.lit(0.0))


def fmt(t: tuple[float, float, float], pct: bool = True) -> str:
    e, lo, hi = t
    if pct:
        return f"{100 * e:+.1f}% (90% {100 * lo:+.1f} to {100 * hi:+.1f})"
    return f"{e:+.4f} ({lo:+.4f} to {hi:+.4f})"


# ---- H41: representativeness weights -------------------------------------------------------
WEIGHT_FIT = list(range(2006, 2016))
SITUATION = ["wp", "score_differential", "qtr", "half_seconds_remaining", "game_seconds_remaining", "down", "ydstogo", "yardline_100", "is_pass"]


def future(tg: pl.DataFrame) -> pl.DataFrame:
    """Per team-game: the team's EPA per play (relative to the league) in its later games that
    season, on offense (F_off) and allowed on defense (F_def). Null after its last game."""
    d = tg.select("game_id", team="opponent", ysum_a="ysum", n_a="n")
    x = tg.join(d, on=["game_id", "team"]).sort("season", "team", "week")
    rev = lambda col: c(col).reverse().cum_sum().reverse().over("season", "team") - c(col)  # noqa: E731
    x = x.with_columns(
        F_off=rev("ysum") / rev("n"),
        F_def=rev("ysum_a") / rev("n_a"),
        F_n=rev("n"),
    )
    return x.select("game_id", "team", F_off=pl.when(c("F_n") > 0).then(c("F_off")), F_def=pl.when(c("F_n") > 0).then(c("F_def")))


def learn_weights(units: pl.DataFrame, feats: list[str], f_col: str, y_col: str = "y_rel", n_col: str | None = None, seed: int = 0):
    """The representativeness weight: per unit, E[y F | X] / E[y^2 | X], the slope of the team's
    future on this unit's value in units like it (through the origin), from two gradient-boosted
    models fitted on WEIGHT_FIT seasons only. Clipped at 0, scaled to mean 1 on the fit seasons.
    Returns (weights for all units, the two models)."""
    from sklearn.ensemble import HistGradientBoostingRegressor as H

    tr = units.filter(c("season").is_in(WEIGHT_FIT) & c(f_col).is_not_null())
    X = tr.select(feats).to_numpy().astype(float)
    y = tr[y_col].to_numpy()
    f = tr[f_col].to_numpy()
    sw = tr[n_col].to_numpy().astype(float) if n_col else None
    kw = dict(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=2000 if n_col is None else 300, l2_regularization=1.0, random_state=seed)
    ma = H(**kw).fit(X, y * f, sample_weight=sw)
    mb = H(**kw).fit(X, y * y, sample_weight=sw)
    Xa = units.select(feats).to_numpy().astype(float)
    w = np.clip(ma.predict(Xa), 0, None) / np.clip(mb.predict(Xa), 1e-9, None)
    trm = units.select(c("season").is_in(WEIGHT_FIT)).to_series().to_numpy()
    w = w / w[trm].mean()
    return w, (ma, mb)


def combine(r_off: pl.DataFrame, r_def: pl.DataFrame) -> pl.DataFrame:
    """Offense ratings from one walk, defense ratings from another."""
    return r_off.select("season", "week", "team", "o").join(r_def.select("season", "week", "team", "d"), on=["season", "week", "team"])


def score_ratings(r: pl.DataFrame, ufs: dict[str, pl.DataFrame], extra: dict[str, pl.DataFrame] | None = None, feats: list[str] | None = None) -> dict[str, pl.DataFrame]:
    feats = feats or ["own", "opp", "home"]
    return {h: fit_score(predict_frame(r, uf, extra), feats) for h, uf in ufs.items()}


def tune_split(s_off: pl.DataFrame, s_def: pl.DataFrame, sched: pl.DataFrame, ufs: dict[str, pl.DataFrame]) -> tuple[tuple[Params, Params], pl.DataFrame, dict]:
    """Offense ratings from s_off, defense from s_def, each walk's settings tuned on TUNE for its
    own side's next-3 error. Returns settings, the combined ratings and scored predictions."""
    best = {}
    for side, s in (("off", s_off), ("def", s_def)):
        bv, bp, br = np.inf, None, None
        for prm in GRID:
            r = walk(s, prm, sched)
            pf = fit_score(predict_frame(r, ufs["next3"]), ["own", "opp", "home"])
            v = mse(pf.filter(c("side") == side), TUNE)
            if v < bv:
                bv, bp, br = v, prm, r
        best[side] = (bp, br)
    r = combine(best["off"][1], best["def"][1])
    return (best["off"][0], best["def"][0]), r, score_ratings(r, ufs)


# ---- H41, second build: representativeness by kind of play, learned across teams ---------------
def play_classes(p: pl.DataFrame, gap: bool = False) -> pl.DataFrame:
    """A kind for every play: win-chance band (7) x pass or run, plus the last two minutes of a
    half as its own kind; with `gap`, plays in the top or bottom 5% of the EPA-WPA gap get their
    own kinds (by pass or run)."""
    band = (
        pl.when(c("wp") < 0.1).then(pl.lit("wp<.10"))
        .when(c("wp") < 0.25).then(pl.lit("wp.10-.25"))
        .when(c("wp") < 0.4).then(pl.lit("wp.25-.40"))
        .when(c("wp") < 0.6).then(pl.lit("wp.40-.60"))
        .when(c("wp") < 0.75).then(pl.lit("wp.60-.75"))
        .when(c("wp") < 0.9).then(pl.lit("wp.75-.90"))
        .otherwise(pl.lit("wp>.90"))
    )
    kind = pl.when(c("half_seconds_remaining") <= 120).then(pl.lit("last2min")).otherwise(band)
    if gap:
        lo, hi = p.filter(c("season").is_in(WEIGHT_FIT))["gap"].quantile(0.05), p.filter(c("season").is_in(WEIGHT_FIT))["gap"].quantile(0.95)
        kind = pl.when(c("gap") <= lo).then(pl.lit("gap-low")).when(c("gap") >= hi).then(pl.lit("gap-high")).otherwise(kind)
    return p.with_columns(kind=pl.concat_str(kind, pl.when(c("is_pass") == 1).then(pl.lit("|pass")).otherwise(pl.lit("|run"))))


def class_weights(p: pl.DataFrame, side: str, col: str = "kind", y: str = "y_rel") -> pl.DataFrame:
    """Per kind of play: beta, how much one play of that kind (its EPA relative to the league)
    moves the team's EPA per play in its other games (odd weeks predict even weeks and back),
    from a regression across team-seasons of WEIGHT_FIT. The team's estimate is sum(beta * y) /
    plays, so beta is a per-play weight; all-equal betas are the plain average."""
    team = "posteam" if side == "off" else "defteam"
    x = p.filter(c("season").is_in(WEIGHT_FIT)).with_columns(par=c("week") % 2)
    kinds = sorted(x[col].unique().to_list())
    tot = x.group_by("season", team, "par").agg(N=pl.len(), Y=c(y).sum())
    s = x.group_by("season", team, "par", col).agg(S=c(y).sum()).pivot(on=col, index=["season", team, "par"], values="S").fill_null(0)
    m = tot.join(s, on=["season", team, "par"])
    other = tot.select("season", team, par=1 - c("par"), F=c("Y") / c("N"))
    m = m.join(other, on=["season", team, "par"])
    X = np.column_stack([np.ones(m.height)] + [(m[k] / m["N"]).to_numpy() for k in kinds])
    beta = np.linalg.lstsq(X, m["F"].to_numpy(), rcond=None)[0][1:]
    shares = x.group_by(col).agg(share=pl.len() / x.height)
    return pl.DataFrame({col: kinds, "beta": beta}).join(shares, on=col)


def sides_sum(p: pl.DataFrame, value: str, weight: str) -> pl.DataFrame:
    """Per game and offense: W = plays, WY = sum(weight * value): a weighted sum per play."""
    return p.group_by("game_id", "posteam").agg(W=pl.len().cast(pl.Float64), WY=(c(weight) * c(value)).sum()).rename({"posteam": "team"})


def class_weights_shrunk(p: pl.DataFrame, side: str, col: str = "kind", y: str = "y_rel", grid=(0.0, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 1e4)) -> tuple[pl.DataFrame, float, dict]:
    """class_weights, shrunk toward equal weights: beta_k = gamma + delta_k with a ridge penalty on
    delta, its strength picked by leaving one season out (2006-2015). A huge strength is equal
    weights. Returns the weights (as beta), the chosen strength, and each strength's CV error."""
    team = "posteam" if side == "off" else "defteam"
    x = p.filter(c("season").is_in(WEIGHT_FIT)).with_columns(par=c("week") % 2)
    kinds = sorted(x[col].unique().to_list())
    tot = x.group_by("season", team, "par").agg(N=pl.len(), Y=c(y).sum())
    s = x.group_by("season", team, "par", col).agg(S=c(y).sum()).pivot(on=col, index=["season", team, "par"], values="S").fill_null(0)
    m = tot.join(s, on=["season", team, "par"]).join(tot.select("season", team, par=1 - c("par"), F=c("Y") / c("N")), on=["season", team, "par"])
    D = np.column_stack([(m[k] / m["N"]).to_numpy() for k in kinds])
    X = np.column_stack([np.ones(m.height), D.sum(1), D])
    F = m["F"].to_numpy()
    seasons = m["season"].to_numpy()
    scale = float(np.mean(np.sum(D * D, 0)))

    def fit(Xt, Ft, lam):
        pen = np.zeros(X.shape[1])
        pen[2:] = lam * scale
        A = Xt.T @ Xt + np.diag(pen) + 1e-12 * np.eye(X.shape[1])
        return np.linalg.solve(A, Xt.T @ Ft)

    cv = {}
    for lam in grid:
        err = 0.0
        for sz in np.unique(seasons):
            tr, te = seasons != sz, seasons == sz
            b = fit(X[tr], F[tr], lam)
            err += float(((F[te] - X[te] @ b) ** 2).sum())
        cv[lam] = err / len(F)
    best = min(cv, key=cv.get)
    b = fit(X, F, best)
    beta = b[1] + b[2:]
    shares = x.group_by(col).agg(share=pl.len() / x.height)
    return pl.DataFrame({col: kinds, "beta": beta}).join(shares, on=col), best, cv
