"""The walk-forward history in the standard schema (rule e; decision 0052, call 25).

Four tables, each made by the shipped rung of each measure (the report's verdicts), every row
from parameters fit on seasons before it:
- `player_game`: before each of a player's games 2 to 17 (after his game 1 to 16), his rate
  over his next 4 games; `as_of` the next game's kickoff, `game_id` that game.
- `player_season`: his rate next season, from each season 2006-2024 (the 2025 rows are the prior
  for the vault season, made from 2024 and earlier only); `as_of` 1 September of the target
  season, after every input was known.
- `team_game` and `team_season`: the same for each team's side.

`mean` is the rate itself (the pull target added back); `q10`-`q90` the shipped 80% range;
`k` the 50% point fit on seasons before the row, `reliability` attempts / (attempts + k) (`N`
in season, `n` next season), `swing` his games' scatter against the noise alone (shrunk toward 1;
it widens the range only where the build kept I14's widening).
**The ranges use expected attempts** (his attempts a game so far times 4, or last season's
attempts next season), not the realised ones the report scored, which aren't known at `as_of`.
Next season the attempts usually fall, so the noise is understated: each season's ranges are
scaled by earlier seasons' scored rows (`range_scale`, call 32), and their coverage on the
scored rows is reported beside them. Where a season is too
early for a rung's slope or drift term, the row falls back to M1 (column `rung`), with no drift
term and no conformal scale.
"""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import polars as pl

from pcf.core.contract import UTC_TIME, check_output
from pcf.experts.stabilization import common as K
from pcf.experts.stabilization import inseason as I
from pcf.experts.stabilization import walks as W

c = pl.col
MODEL, VERSION = "stabilization", "v1"
CPS_ALL = tuple(range(1, 17))
H = float(K.HORIZON)


def _train_end(games: pl.DataFrame, before: int) -> datetime:
    return games.filter(c("season") < before)["known_at"].max()


def _range(df: pl.DataFrame, fc: str, var: str, ranges: dict | None) -> pl.DataFrame:
    """mean, q10-q90 from a centred forecast and its variance, with the shipped scale and
    widening (None for a rung that ships no checked range: plain)."""
    v = c(var)
    if ranges:
        if ranges.get("conformal"):
            v = v * c("_scale").fill_null(1.0) ** 2
        if ranges.get("widened"):
            v = v * c("sw").fill_null(1.0)
    return df.with_columns(mean=c("mu") + c(fc), _var=v, _fc=c(fc))


def history_scale(f: pl.DataFrame) -> pl.DataFrame:
    """The ranges on expected attempts, scaled for each season by earlier seasons' scored rows
    (decision 0052, call 32): the 80th percentile of |actual - forecast| / sd there, over the
    normal's (1 before 30 such rows). Then q10-q90 and the coverage flag."""
    scored = c("_w").is_not_null() & (c("_w") > 0) & c("y").is_not_null()
    z = f.select(pl.when(scored).then((c("y") - c("_fc")).abs() / c("_var").sqrt()).alias("z"))[
        "z"
    ].to_numpy()
    s = f["season"].to_numpy()
    sc = np.ones(f.height)
    for t in np.unique(s):
        tr = (s < t) & np.isfinite(z)
        if tr.sum() >= 30:
            sc[s == t] = np.quantile(z[tr], 0.8) / K.Z80
    sd = c("_var").sqrt() * c("range_scale")
    return f.with_columns(range_scale=pl.Series(sc)).with_columns(
        q10=c("mean") - K.Z80 * sd,
        q50=c("mean"),
        q90=c("mean") + K.Z80 * sd,
        _cov=pl.when(scored).then(((c("y") - c("_fc")).abs() <= K.Z80 * sd).cast(pl.Float64)),
    )


def _frame(df: pl.DataFrame, keys: list[str], quantity: str, cadence: str) -> pl.DataFrame:
    out = df.with_columns(
        quantity=pl.lit(quantity),
        model=pl.lit(MODEL),
        model_version=pl.lit(VERSION),
        cadence=pl.lit(cadence),
        as_of=c("as_of").cast(UTC_TIME),
        train_end=c("train_end").cast(UTC_TIME),
    ).filter(c("mean").is_not_null())
    return out


# ---------------------------------------------------------------- in season
def in_rows(
    name: str,
    games: pl.DataFrame,
    rows: pl.DataFrame,
    lagged: bool,
    kind: str,
    verdict: dict,
    run_id: str,
    ent: str = "gsis_id",
) -> pl.DataFrame:
    eff = kind == "efficiency"
    shipped = verdict["shipped"]
    ranges = verdict.get("ranges")
    first = int(rows["season"].min())
    gc = I.centred_games(games, rows, ent, "pos")
    out = []
    for T in range(first + 1, K.LAST + 1):
        cp, info = I.season_frame(games, rows, T, ent, "pos", lagged, eff, gc=gc, cps=CPS_ALL)
        a = I.rungs(cp, info, "next")
        par_cols = ["b_pull", "c_m1", "c_pull", *[x for x in a.columns if x.startswith("scale_")]]
        par = (
            a.filter(c("season") == T)
            .group_by("season", "gi")
            .agg([c(x).drop_nulls().first() for x in par_cols])
        )
        cur = cp.filter(c("season") == T).join(par, on=["season", "gi"], how="left")
        sig, tau2 = info["sigma2"], info["tau2"]
        w_exp = (
            pl.when(c("gi_known") > 0)
            .then(H * c("cn") / c("gi_known"))
            .otherwise(H * c("pn") / 17.0)
        )
        cur = cur.with_columns(
            w_exp=pl.max_horizontal(w_exp, pl.lit(1.0)),
            sw=(c("G") * c("swing") + K.SWING_WEIGHT) / (c("G") + K.SWING_WEIGHT),
        )
        cur = cur.with_columns(
            avg=pl.lit(0.0),
            pull=c("b_pull") * c("m1"),
            filt=c("m"),
            filt_phi=c("m_phi"),
            filt_om=c("m_om"),
            v_avg=tau2 + sig / c("w_exp"),
            v_m1=c("m1_v") + c("c_m1").fill_null(0.0) + sig / c("w_exp"),
            v_pull=c("b_pull") ** 2 * c("m1_v") + c("c_pull").fill_null(0.0) + sig / c("w_exp"),
        )
        for suf, p in (("", info["par"]), ("_phi", info["par_phi"]), ("_om", info["par_om"])):
            cur = cur.with_columns(
                (
                    c(f"P{suf}")
                    + p["q"] * (H + 1) / 2
                    + p["phi"] * sig / c("w_exp")
                    + p["omega"] / H
                ).alias(f"v_filt{suf}")
            )
        rung = pl.when(c(shipped).is_not_null()).then(pl.lit(shipped)).otherwise(pl.lit("m1"))
        cur = cur.with_columns(
            rung=rung,
            fc=pl.coalesce(shipped, "m1"),
            var=pl.coalesce(f"v_{shipped}", "v_m1"),
            _scale=c(f"scale_{shipped}{'_sw' if ranges and ranges.get('widened') else ''}")
            if f"scale_{shipped}" in cur.columns
            else pl.lit(None, pl.Float64),
            as_of=c("next_kick"),
            train_end=pl.lit(_train_end(games, T)),
            k=pl.lit(float(info["k"])),  # this test season's k, fit on seasons before it
            swing=c("sw"),
        )
        cur = cur.with_columns(reliability=c("N") / (c("N") + c("k")))
        out.append(_range(cur, "fc", "var", ranges if shipped != "avg" else None))
    f = history_scale(pl.concat(out, how="diagonal_relaxed").with_columns(_w=c("w")))
    keys = [ent, "game_id"]
    f = f.rename({"next_game": "game_id"})
    if ent == "gsis_id" and name.startswith(("off_", "def_")):
        f = f.drop("team", strict=False).rename({"gsis_id": "team"})
        keys = ["team", "game_id"]
    f = _frame(f, keys, f"{name}_next4", "in_season").with_columns(run_id=pl.lit(run_id))
    return f.select(
        *keys,
        "season",
        "as_of",
        "quantity",
        "mean",
        "q10",
        "q50",
        "q90",
        "model",
        "model_version",
        "run_id",
        "train_end",
        "cadence",
        "rung",
        "gi",
        "N",
        "k",
        "reliability",
        "swing",
        "range_scale",
        _cov="_cov",
        _w="_w",
    )


# ---------------------------------------------------------------- next season
def next_rows(inp: W.Inputs, m: K.Measure, verdict: dict, run_id: str) -> pl.DataFrame:
    shipped = verdict["shipped"]
    ranges = verdict.get("ranges")
    p, oth, cc, ks = W.next_frame(inp, m, open_last=True)
    f = W.next_rungs(p, oth, cc, ks)
    sw = W.N.swing(W.R.game_rows(inp.games[m.name], inp.sm(m.name)), inp.sm(m.name))
    return _next_common(f, sw, shipped, ranges, inp.games[m.name], m.name, run_id, "gsis_id")


def _next_common(
    f: pl.DataFrame,
    sw: pl.DataFrame,
    shipped: str,
    ranges: dict | None,
    games: pl.DataFrame,
    name: str,
    run_id: str,
    ent: str,
) -> pl.DataFrame:
    f = f.join(sw.select(ent, "season", "sw"), on=[ent, "season"], how="left")
    b = {
        "m1": pl.lit(1.0),
        "pull": c("b_pull"),
        "ridge": c("b_ridge"),
        "ridge_trend": c("b_ridge_trend"),
    }

    def base(r: str) -> pl.Expr:
        return (
            b[r] ** 2 * c("sigma2") / (c("n") + c("k"))
            + c(f"c_{r}").fill_null(0.0)
            + c("sigma2") / c("n")
        )

    f = f.with_columns(
        v_avg_h=c("tau2") + c("sigma2") / c("n"),
        **{f"v_{r}_h": base(r) for r in ("m1", "pull", "ridge", "ridge_trend")},
    )
    f = f.with_columns(
        rung=pl.when(c(shipped).is_not_null()).then(pl.lit(shipped)).otherwise(pl.lit("m1")),
        fc=pl.coalesce(shipped, "m1"),
        var=pl.coalesce(f"v_{shipped}_h", "v_m1_h"),
        _scale=c(f"scale_{shipped}")
        if f"scale_{shipped}" in f.columns
        else pl.lit(None, pl.Float64),
        as_of=pl.datetime(c("target"), 9, 1, time_zone="UTC"),
    )
    te = {s: _train_end(games, s + 1) for s in f["season"].unique().to_list()}
    f = f.with_columns(train_end=c("season").replace_strict(te, return_dtype=UTC_TIME))
    f = _range(f, "fc", "var", ranges if shipped != "avg" else None)
    keys = [ent, "season"]
    f = history_scale(f.with_columns(input_season=c("season"), season=c("target"), _w=c("w")))
    if name.startswith(("off_", "def_")):
        f = f.drop("team", strict=False).rename({ent: "team"})
        keys = ["team", "season"]
    f = _frame(f, keys, f"{name}_next_season", "in_season").with_columns(run_id=pl.lit(run_id))
    return f.select(
        *keys,
        "input_season",
        "as_of",
        "quantity",
        "mean",
        "q10",
        "q50",
        "q90",
        "model",
        "model_version",
        "run_id",
        "train_end",
        "cadence",
        "rung",
        "n",
        "k",
        reliability=c("n") / (c("n") + c("k")),
        swing=c("sw"),
        range_scale="range_scale",
        _cov="_cov",
        _w="_w",
    )


def team_next_rows(
    inp: W.Inputs, name: str, games: pl.DataFrame, rows: pl.DataFrame, verdict: dict, run_id: str
) -> pl.DataFrame:
    sm = W.N.season_m1(rows, games)
    p = W.N.pairs(sm, rows, open_last=True)
    p = W.N.features(p, {}, None, None, sm, None, None)
    f = W.next_rungs(p, [], [], {})
    sw = W.N.swing(W.R.game_rows(games, sm), sm)
    return _next_common(
        f, sw, verdict["shipped"], verdict.get("ranges"), games, name, run_id, "gsis_id"
    )


def coverage(f: pl.DataFrame) -> dict:
    """The history ranges' coverage on rows with a scored target (2018-2024)."""
    s = f.filter(c("_w").is_not_null() & (c("_w") > 0) & c("_cov").is_not_null())
    s = s.filter((c("season") >= K.TEST[0]) & (c("season") <= K.TEST[-1]))
    return {"rows": s.height, "coverage": float(s["_cov"].mean()) if s.height else float("nan")}


def finish(f: pl.DataFrame, keys: list[str]) -> pl.DataFrame:
    f = f.drop("_cov", "_w", strict=False)
    check_output(f, keys)
    return f


def now() -> datetime:
    return datetime.now(UTC)
