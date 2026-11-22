"""The build's checks beyond the harness (decision 0041). Each returns report lines; `run` writes
them to `projects/opportunity-quality/build/`.

- `facts`: the expected-points model against nflverse's, what the situation explains per chance,
  points per kind of chance (H56), and the consistency of every new measure (H59, H58).
- `regression_backtest`: methods A and B (and B with yards after the catch) walk forward by
  season: accuracy against "all luck" and "it all lasts", the shuffled null, the chance the gap
  closes in bands (calibration), ranges, and kept share against chances (the assumption test).

The forecast's checks after the harness (no-noise, yardstick, the ladder, fitting noise) are in
`downstream`.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
import polars as pl

from pcf.data.gateway import Gateway
from pcf.experts.opportunity_quality import regression as R
from pcf.experts.opportunity_quality.common import known_games
from pcf.validation.consistency import consistency

c = pl.col
UTC = pl.Datetime("us", "UTC")
REPORTED = list(range(2016, 2025))
DRAWS = 2000


def _source():
    return Gateway().source


def player_games(
    scoring: str = "ppr", season_type: str = "REG", opportunity: pl.DataFrame | None = None
) -> pl.DataFrame:
    """Every known RB, WR and TE player-game with expected points (2012 on), with season type.
    `opportunity` replaces the part's expected sums with another set of expected models' (I100),
    keeping the part's rows and known-at."""
    src = _source()
    opp = src.part("player_game", "opportunity")
    if opportunity is not None:
        exp = [x for x in opportunity.columns if x.endswith("_exp")]
        opp = opp.drop(exp).join(
            opportunity.select("gsis_id", "game_id", *exp), on=["gsis_id", "game_id"], how="left"
        )
    pg = (
        src.part("player_game", "roster")
        .join(opp, on=["gsis_id", "game_id"], suffix="_o")
        .rename({"known_at_o": "opportunity_known_at"})
        .drop("season_o")
    )
    sched = src.part("game", "schedule").select("game_id", "game_type")
    pg = pg.join(sched, on="game_id", how="left")
    if season_type == "REG":
        pg = pg.filter(c("game_type") == "REG")
    return known_games(pg, scoring, ["game_type", "years_exp"])


def fisher(r: float, n: int) -> str:
    if n < 6 or math.isnan(r) or abs(r) >= 1:
        return f"{r:+.2f} (n {n})"
    z, se = math.atanh(r), 1 / math.sqrt(n - 3)
    return f"{r:+.2f} ({math.tanh(z - 1.645 * se):+.2f} to {math.tanh(z + 1.645 * se):+.2f}, n {n})"


# ---------------------------------------------------------------- facts
def facts(scoring: str = "ppr") -> list[str]:
    src = _source()
    out = ["== The expected-points model (play.xfp), fit on earlier seasons only, 2009 on"]
    pg = player_games(scoring)
    ffo = src.part("player_game", "ff_opportunity").select(
        "gsis_id", "game_id",
        ffo=c("ffo_rec_fantasy_points_exp").fill_null(0)
        + c("ffo_rush_fantasy_points_exp").fill_null(0),
    )  # fmt: skip
    j = pg.filter(c("chances") > 0).join(ffo, on=["gsis_id", "game_id"])
    out.append(f"  against nflverse's ff_opportunity, per player-game with a chance: r "
               f"{np.corrcoef(j['xfp'], j['ffo'])[0, 1]:.3f} ({j.height} player-games); means "
               f"{j['xfp'].mean():.2f} against {j['ffo'].mean():.2f}")  # fmt: skip
    for s, g in sorted(j.group_by("season"), key=lambda t: t[0][0]):
        out.append(f"    {s[0]}: r {np.corrcoef(g['xfp'], g['ffo'])[0, 1]:.3f} (n {g.height})")
    plays = src.part("play", "xfp").filter(c("oq_catch_exp").is_not_null())
    pbp = src.part("play", "pbp").select("game_id", "play_id", "season_type", "yardline_100",
                                         "air_yards")  # fmt: skip
    plays = plays.join(pbp, on=["game_id", "play_id"]).filter(c("season_type") == "REG")
    from pcf.experts.opportunity_quality.common import weights

    rec, yard, td = weights(scoring)
    plays = plays.with_columns(
        pts=rec * c("oq_catch") + yard * c("oq_yards") + td * c("oq_td"),
        xp=rec * c("oq_catch_exp") + yard * c("oq_yards_exp") + td * c("oq_td_exp"),
    )
    te = plays.filter(c("season").is_between(2019, 2024))
    for kind in ("target", "carry"):
        e = te.filter(c("oq_kind") == kind)
        y, p = e["pts"].to_numpy(), e["xp"].to_numpy()
        out.append(f"  one {kind}: {y.mean():.2f} points on average; the situation removes "
                   f"{100 * (1 - ((p - y) ** 2).sum() / ((y - y.mean()) ** 2).sum()):.1f}% of its "
                   f"squared error (2019-2024, {e.height} chances); "
                   f"expected {p.mean():.2f}")  # fmt: skip
    out += ["", "== H56: points per chance by kind (2019-2024, regular season)"]
    yl, air = c("yardline_100"), c("air_yards")
    kind = (
        pl.when(c("oq_kind") == "carry").then(
            pl.when(yl <= 2).then(pl.lit("carry, inside the 2"))
            .when(yl <= 5).then(pl.lit("carry, 3 to 5 out"))
            .when(yl <= 10).then(pl.lit("carry, 6 to 10 out"))
            .when(yl <= 20).then(pl.lit("carry, 11 to 20 out"))
            .otherwise(pl.lit("carry, outside the 20"))
        ).otherwise(
            pl.when(air >= yl).then(
                pl.when(yl <= 10).then(pl.lit("target into the end zone, from the 10 or closer"))
                .otherwise(pl.lit("target into the end zone, from further out")))
            .when(yl <= 10).then(pl.lit("target short of the goal line, inside the 10"))
            .when(air >= 20).then(pl.lit("target 20+ yards downfield"))
            .when(air >= 10).then(pl.lit("target 10 to 19 downfield"))
            .when(air > 0).then(pl.lit("target 1 to 9 downfield"))
            .otherwise(pl.lit("target at or behind the line"))
        )
    )  # fmt: skip
    k = (
        te.with_columns(k=kind)
        .group_by("k")
        .agg(n=pl.len(), pts=c("pts").mean(), xp=c("xp").mean(), td=c("oq_td").mean())
        .sort("pts", descending=True)
    )
    tot = k["n"].sum()
    for r in k.iter_rows(named=True):
        out.append(f"  {r['k']:<50} {r['pts']:5.2f} points ({r['xp']:5.2f} expected), "
                   f"touchdown {100 * r['td']:4.1f}%, "
                   f"{100 * r['n'] / tot:4.1f}% of chances")  # fmt: skip
    avg = te.group_by("oq_kind").agg(c("pts").mean())
    out.append("  average: " + ", ".join(f"{a} {b:.2f}" for a, b in avg.iter_rows()))

    out += [
        "",
        "== Consistency (pcf.validation.consistency), player-games with a chance, 2012-2024",
    ]
    d = pg.filter((c("chances") > 0) & (c("season") <= 2024)).with_columns(
        xfp_ch=c("xfp") / c("chances"), poe_ch=c("poe") / c("chances"),
        yac_tgt=pl.when(c("targets") > 0).then(c("yac") / c("targets")),
        gl_share=pl.when(c("carries") > 0).then(c("gl") / c("carries")),
        deep_share=pl.when(c("targets") > 0).then(c("deep") / c("targets")),
    )  # fmt: skip
    measures = ["xfp", "fp", "poe", "xfp_ch", "poe_ch", "yac_tgt", "gl_share", "deep_share"]
    with pl.Config(tbl_cols=20, tbl_width_chars=220, tbl_rows=40):
        out.append(str(consistency(d, measures, unit="gsis_id")))
        for pos in ("RB", "WR", "TE"):
            out.append(f"  {pos}:")
            out.append(str(consistency(d.filter(c("position") == pos), ["xfp", "poe_ch", "yac_tgt"],
                                       unit="gsis_id")))  # fmt: skip
    return out


# ---------------------------------------------------------------- the regression measure
def regression_frames(
    scoring: str = "ppr", variant: tuple[pl.DataFrame, pl.DataFrame] | None = None
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """windows, player-seasons, the chance spread and the player-games, regular season, 2012 on.
    `variant` is another set of expected models' (plays, player-games), e.g. I100's."""
    pg = player_games(scoring, opportunity=None if variant is None else variant[1])
    win = R.windows(pg)
    ps = R.player_seasons(pg)
    src = _source()
    plays = src.part("play", "xfp") if variant is None else variant[0]
    plays = plays.join(
        src.part("play", "pbp").select("game_id", "play_id", "season_type"),
        on=["game_id", "play_id"],
    ).filter(c("season_type") == "REG")
    return win, ps, R.chance_spread(plays, scoring), pg


def regression_history(
    seasons: Sequence[int],
    scoring: str = "ppr",
    frames: tuple | None = None,
    game_noise: bool = False,
) -> pl.DataFrame:
    """The measure walk forward: each test season from parameters fit on earlier seasons only.
    Every row with a window of `MIN_WINDOW` chances; `scorable` marks rows with `MIN_FUTURE`
    chances left. `frames` from `regression_frames` (default: the table's); `game_noise` turns
    on I101's φ. `base_rate` is how often gaps closed in the training seasons (for Brier skill)."""
    win, ps, spread, pg = frames if frames is not None else regression_frames(scoring)
    out = []
    for s in seasons:
        params = R.fit(win, ps, spread, s, pg if game_noise else None)
        rows = win.filter((c("season") == s) & (c("n") >= R.MIN_WINDOW) & (c("n_t") > 0))
        m = R.measure(rows, params).with_columns(train_end_season=pl.lit(s - 1))
        # The chance the gap closes, recalibrated on the training seasons' scored rows (Platt)
        train = R.scored(win.filter(c("season").is_in(params["seasons"])))
        train = R.measure(train, params).with_columns(closed=R.closed())
        m = m.with_columns(base_rate=pl.lit(float(train["closed"].mean())))
        for meth in ("B", "B_yac"):
            cal = R.fit_platt(train[f"p_close_{meth}"].to_numpy(), train["closed"].to_numpy())
            m = m.with_columns(
                pl.Series(f"p_close_{meth}_cal", R.platt(cal, m[f"p_close_{meth}"].to_numpy()))
            )
        out.append(m)
    hist = pl.concat(out, how="diagonal_relaxed").with_columns(
        scorable=c("m") >= R.MIN_FUTURE, closed=R.closed()
    )
    return hist


def _wse(d: pl.DataFrame, col: str) -> pl.Expr:
    return (c("m") * (c("future") - c(col)) ** 2).alias(col)


def _skill(d: pl.DataFrame, a: str, b: str, seed: int = 0) -> str:
    """Share of `b`'s weighted squared error that `a` removes, resampling whole weeks."""
    w = (
        d.with_columns(blk=c("season") * 100 + c("week"))
        .group_by("blk")
        .agg(
            ea=(c("m") * (c("future") - c(a)) ** 2).sum(),
            eb=(c("m") * (c("future") - c(b)) ** 2).sum(),
        )
    )
    ea, eb = w["ea"].to_numpy(), w["eb"].to_numpy()
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(ea), size=(DRAWS, len(ea)))
    boot = 1 - ea[pick].sum(1) / eb[pick].sum(1)
    lo, hi = np.quantile(boot, [0.05, 0.95])
    return f"{100 * (1 - ea.sum() / eb.sum()):+6.2f}% (90% {100 * lo:+.2f} to {100 * hi:+.2f})"


def calibration_bands(p: np.ndarray, y: np.ndarray, bins: int = 10) -> tuple[float, float, list]:
    """Calibration error (points, weighted by rows), slope (logistic of y on logit p) and bands."""
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges) - 1, 0, bins - 1)
    rows, err = [], 0.0
    for b in range(bins):
        on = idx == b
        if on.sum():
            rows.append(
                (edges[b], edges[b + 1], int(on.sum()), float(p[on].mean()), float(y[on].mean()))
            )
            err += on.sum() * abs(p[on].mean() - y[on].mean())
    from sklearn.linear_model import LogisticRegression

    lp = np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6))).reshape(-1, 1)
    slope = float(LogisticRegression(C=1e6, max_iter=2000).fit(lp, y.astype(int)).coef_[0, 0])
    return 100 * err / len(p), slope, rows


def regression_report(hist: pl.DataFrame, shuffles: int = 100, seed: int = 0) -> list[str]:
    d = hist.filter(c("scorable"))
    out = [f"== The regression measure, walk forward by season ({d['season'].min()}-"
           f"{d['season'].max()}): {d.height} player-games scored (window {R.MIN_WINDOW}+ chances, "
           f"{R.MIN_FUTURE}+ left), {d['gsis_id'].n_unique()} players"]  # fmt: skip
    out.append(
        "  Target: points over expected per chance over the rest of the season, weighted by "
        "chances. Skill = share of the 'all luck' forecast's error removed (90%, weeks resampled)."
    )
    rows = {"everyone": d, "week 1 (next season)": d.filter(c("week") == 1)}
    for pos in ("RB", "WR", "TE"):
        rows[pos] = d.filter(c("position") == pos)
    for label, g in rows.items():
        out.append(f"  {label} ({g.height}):")
        out.append(f"    A against all luck        {_skill(g, 'mean_A', 'mean_luck', seed)}")
        out.append(f"    B against all luck        {_skill(g, 'mean_B', 'mean_luck', seed)}")
        out.append(f"    B against A               {_skill(g, 'mean_B', 'mean_A', seed)}")
        out.append(f"    B with yac against B      {_skill(g, 'mean_B_yac', 'mean_B', seed)}")
        out.append(
            f"    'it all lasts' against all luck {_skill(g, 'mean_same', 'mean_luck', seed)}"
        )
    # the shuffled null: each week's gaps (with their chances) moved to other players
    rng = np.random.default_rng(seed)
    real = float((d["m"] * (d["future"] - d["mean_B"]) ** 2).sum())
    beat = 0
    for i in range(shuffles):
        sh = d.with_columns(
            mean_B=c("mean_B")
            .shuffle(seed=int(rng.integers(1 << 30)))
            .over("season", "week", "position")
        )
        if real < float((sh["m"] * (sh["future"] - sh["mean_B"]) ** 2).sum()):
            beat += 1
        del i
    out.append(f"  Shuffled null: B beats {beat} of {shuffles} copies with its forecasts moved "
               f"between players within each week and position (needs 95)")  # fmt: skip
    out.append("")
    out.append(
        "  Kept share by chances in the window (the assumption test: does it rise as B says?)"
    )
    out.append("    band            rows   B's kept share   seen (weighted slope of future on gap)")
    bands = [(20, 50), (50, 100), (100, 200), (200, 400), (400, 10_000)]
    for lo, hi in bands:
        g = d.filter(c("n").is_between(lo, hi - 1e-9))
        if g.height < 50:
            continue
        w = g["m"].to_numpy()
        dx = (g["gap"] - g["mu"]).to_numpy()
        dy = (g["future"] - g["mu"]).to_numpy()
        seen = np.sum(w * dx * dy) / np.sum(w * dx * dx)
        top = hi if hi < 10_000 else "+"
        out.append(f"    {lo:>4}-{top:<6} {g.height:>7}   {g['k_B'].mean():.2f}"
                   f"             {seen:.2f}")  # fmt: skip
    out.append("")
    out.append("  The chance the gap closes by half or more (calibration in 10 bands)")
    y = d["closed"].cast(pl.Float64).to_numpy()
    for meth in ("A", "B", "B_yac", "B_cal", "B_yac_cal"):
        p = d[f"p_close_{meth}"].to_numpy()
        err, slope, bands_ = calibration_bands(p, y)
        out.append(
            f"    {meth}: calibration error {err:.1f} points, slope {slope:.2f}, "
            f"closed {100 * y.mean():.1f}% of the time, forecast {100 * p.mean():.1f}%"
        )
        if meth in ("B", "B_yac_cal"):
            for lo, hi, n, pm, ym in bands_:
                out.append(
                    f"      {lo:.1f}-{hi:.1f}: {n:>6} rows, forecast {100 * pm:5.1f}%, "
                    f"closed {100 * ym:5.1f}%"
                )
    inside = ((d["future"] >= d["future_q10"]) & (d["future"] <= d["future_q90"])).mean()
    out.append(
        "  Range for the future gap (q10-q90, over his expected chances): "
        f"holds {100 * inside:.1f}%"
    )
    for pos in ("RB", "WR", "TE"):
        g = d.filter(c("position") == pos)
        inside = ((g["future"] >= g["future_q10"]) & (g["future"] <= g["future_q90"])).mean()
        out.append(f"    {pos}: {100 * inside:.1f}% ({g.height})")
    w1 = d.filter(c("week") == 1)
    inside = ((w1["future"] >= w1["future_q10"]) & (w1["future"] <= w1["future_q90"])).mean()
    out.append(f"    week 1 (next season): {100 * inside:.1f}% ({w1.height})")
    return out


def regression_params(seasons: Sequence[int], scoring: str = "ppr") -> list[str]:
    win, ps, spread, _ = regression_frames(scoring)
    out = ["  Parameters per test season (μ, τ = √τ², A's k, γ for yac), points per chance:"]
    for s in seasons:
        p = R.fit(win, ps, spread, s)
        parts = [
            f"{pos} μ {v['mu']:+.3f} τ {math.sqrt(v['tau2']):.3f} kA {v['kA']:.2f} "
            f"τy {math.sqrt(v['tau2_y']):.3f} γ {v['gamma']:+.2f}"
            for pos, v in p["pos"].items()
        ]
        out.append(f"    {s}: " + "; ".join(parts))
    return out


def regression_output(hist: pl.DataFrame, run_id: str) -> pl.DataFrame:
    """The published measure in the standard output schema: per player and regular-season game,
    made at the game's Saturday-run moment from parameters fit on earlier seasons. `mean` and
    q10-q90 are his points over expected per chance over the rest of the season by method A (one
    pull-back rate per position: method B lost to it on the 2025 vault, RESULTS R17), with B's
    range moved onto A's mean; beside them B's mean and kept share, the range for his true level
    and B's recalibrated chance the gap closes."""
    from pcf.core.contract import check_output
    from pcf.data.timeline.moments import game_moments

    gw = Gateway()
    moments = game_moments(gw.calendar, "saturday").select("game_id", as_of="moment")
    ends = gw.calendar.games.group_by("season").agg(
        train_end=(c("kickoff").max() + pl.duration(days=1))
    )
    shift = c("mean_A") - c("mean_B")
    out = (
        hist.join(moments, on="game_id", how="inner")
        .join(ends.with_columns(season=c("season") + 1), on="season", how="left")
        .select(
            "gsis_id",
            "game_id",
            c("as_of").cast(UTC),
            "position",
            quantity=pl.lit("poe_per_chance_rest_of_season"),
            mean=c("mean_A"),
            q10=c("future_q10") + shift,
            q50=c("future_q50") + shift,
            q90=c("future_q90") + shift,
            model=pl.lit("opportunity-quality/regression"),
            model_version=pl.lit("1"),
            run_id=pl.lit(run_id),
            train_end=c("train_end").cast(UTC),
            cadence=pl.lit("in_season"),
            gap="gap",
            chances="n",
            kept_share="k_B",
            true_q10="true_q10",
            true_q90="true_q90",
            p_gap_closes="p_close_B_cal",
            mean_B="mean_B",
            mean_B_yac="mean_B_yac",
        )  # fmt: skip
    )
    check_output(out, ["gsis_id", "game_id"])
    return out
