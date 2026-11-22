# ruff: noqa: E501
"""context-v2, the first look (2026-11-20): method A (the chain, with boosted trees) on four tiers
of information, outcome by outcome; H86 and H87.

Discovery only: trained on 2023, scored on 2024; the 2025 vault untouched. Designs and pass rules
were committed before the run (EXPLORATION.md, "First look"; commit 1872101).

Run from pcf/:  python projects/context-v2/explore/first_look.py > projects/context-v2/explore/first_look.txt
"""

from __future__ import annotations

import json

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

from pcf.config import get_config
from pcf.data.gateway import Gateway
from pcf.experts.context_live import models, plays, run
from pcf.validation.compare import compare

c = pl.col
TRAIN, TEST = 2023, 2024
SEED = get_config().seed
COVS = [
    "COVER_0",
    "COVER_1",
    "COVER_2",
    "2_MAN",
    "COVER_3",
    "COVER_4",
    "COVER_6",
    "COVER_9",
    "COMBO",
    "PREVENT",
    "BLOWN",
]
FTN_PLAY = [
    "is_qb_out_of_pocket",
    "is_throw_away",
    "is_catchable_ball",
    "is_contested_ball",
    "is_drop",
    "is_interception_worthy",
    "is_qb_fault_sack",
]
# outcome: (column, kind, rows, the earlier outcomes it is given, in the chain's order)
OUT = {
    "pressure": ("pressure_y", "chance", "dropback", []),
    "time_to_throw": ("time_to_throw_y", "amount", "dropback", ["pressure_y"]),
    "sack": ("sack_y", "chance", "dropback", ["pressure_y", "time_to_throw_y"]),
    "depth": ("air_yards_y", "amount", "attempt", ["pressure_y", "time_to_throw_y"]),
    "completion": (
        "complete_y",
        "chance",
        "attempt",
        ["pressure_y", "time_to_throw_y", "air_yards_y"],
    ),
    "dropback_yards": (
        "yards",
        "amount",
        "dropback",
        ["pressure_y", "time_to_throw_y", "sack_y", "air_yards_y", "complete_y"],
    ),
}
CODES = {"qb_location": ["U", "S", "P"], "starting_hash": ["L", "M", "R"]}


def table(src) -> tuple[pl.DataFrame, list[str], list[str], list[str]]:
    d = pl.concat(
        [pl.read_parquet(run.cache_dir() / f"plays_{s}.parquet") for s in (TRAIN, TEST)],
        how="diagonal_relaxed",
    )
    d = d.filter(c("is_dropback"))
    d = d.with_columns(
        **{
            k: c(k).replace_strict(
                {v: float(i) for i, v in enumerate(vals)}, default=None, return_dtype=pl.Float64
            )
            for k, vals in CODES.items()
        },
        # FTN's "0 pass rushers" with a box of 2 or fewer is an uncharted play (I72)
        n_pass_rushers=pl.when((c("n_pass_rushers") == 0) & (c("n_defense_box") <= 2))
        .then(None)
        .otherwise(c("n_pass_rushers")),
    )
    pa = (
        src.part("play", "participation")
        .filter(c("season").is_between(TRAIN, TEST))
        .select(
            "game_id",
            c("play_id").cast(pl.Int64),
            cov=c("defense_coverage_type"),
            mz=c("defense_man_zone_type"),
            route=c("route"),
        )
    )
    d = d.join(pa, on=plays.KEYS, how="left")
    routes = sorted(x for x in d["route"].drop_nulls().unique().to_list() if x)
    d = d.with_columns(
        *[(c("cov") == k).cast(pl.Float64).fill_null(0).alias(f"cov_{k}") for k in COVS],
        *[(c("route") == r).cast(pl.Float64).fill_null(0).alias(f"route_{r}") for r in routes],
        cov_missing=c("cov").is_null().cast(pl.Float64),
        man=pl.when(c("mz") == "MAN_COVERAGE")
        .then(1.0)
        .when(c("mz") == "ZONE_COVERAGE")
        .then(0.0)
        .otherwise(None),
    )
    ftn = (
        src.part("play", "ftn")
        .filter(c("season").is_between(TRAIN, TEST))
        .select("game_id", c("play_id").cast(pl.Int64), *FTN_PLAY, read=c("read_thrown"))
    )
    d = d.join(ftn, on=plays.KEYS, how="left")
    reads = sorted(x for x in d["read"].drop_nulls().unique().to_list() if x)
    d = d.with_columns(
        *[c(x).cast(pl.Float64) for x in FTN_PLAY],
        read=c("read").replace_strict(
            {v: float(i) for i, v in enumerate(reads)}, default=None, return_dtype=pl.Float64
        ),
        quick=((c("time_to_throw_y") < 2.5) & (c("air_yards_y") < 5)).cast(pl.Float64),
    )
    t1 = plays.FIELD_SETS["live"]
    t2 = t1 + [f"cov_{k}" for k in COVS] + ["cov_missing", "man"]
    hind = [f"route_{r}" for r in routes] + FTN_PLAY + ["read"]
    return d, t1, t2, hind


def X(d: pl.DataFrame, fields: list[str]) -> np.ndarray:
    return d.select([c(f).cast(pl.Float64) for f in fields]).to_numpy()


def fit(d: pl.DataFrame, fields: list[str], y: str, kind: str):
    est = (HistGradientBoostingClassifier if kind == "chance" else HistGradientBoostingRegressor)(
        **models.TREES, random_state=SEED
    )
    return est.fit(X(d, fields), d[y].to_numpy())


def predict(m, d: pl.DataFrame, fields: list[str], kind: str) -> np.ndarray:
    x = X(d, fields)
    return m.predict_proba(x)[:, 1] if kind == "chance" else m.predict(x)


def rows_for(d: pl.DataFrame, name: str) -> pl.DataFrame:
    col, _, pop, _ = OUT[name]
    r = d.filter(c("is_attempt")) if pop == "attempt" else d
    return r.filter(c(col).is_not_null())


def crossfit(
    train: pl.DataFrame, fields: list[str], y: str, kind: str, folds: int = 5
) -> np.ndarray:
    """Out-of-fold predictions on the training rows, folds by game."""
    games = train["game_id"].unique().sort().to_numpy()
    rng = np.random.default_rng(SEED)
    fold_of = dict(zip(games, rng.integers(0, folds, len(games)), strict=True))
    f = np.array([fold_of[g] for g in train["game_id"].to_list()])
    out = np.full(train.height, np.nan)
    for k in range(folds):
        m = fit(train.filter(pl.Series(f != k)), fields, y, kind)
        out[f == k] = predict(m, train.filter(pl.Series(f == k)), fields, kind)
    return out


def loss(y: np.ndarray, p: np.ndarray, kind: str) -> np.ndarray:
    if kind == "chance":
        p = np.clip(p, 1e-6, 1 - 1e-6)
        return -(y * np.log(p) + (1 - y) * np.log(1 - p))
    return (y - p) ** 2


def summary(y: np.ndarray, p: np.ndarray, base: float, kind: str) -> dict:
    out = {"share": 100 * (1 - np.sum((y - p) ** 2) / np.sum((y - base) ** 2))}
    if kind == "chance":
        out["logloss_gain"] = 100 * (
            1 - loss(y, p, kind).sum() / loss(y, np.full_like(p, base), kind).sum()
        )
        out["p10"], out["p90"] = float(np.quantile(p, 0.1)), float(np.quantile(p, 0.9))
    return out


def paired(
    test: pl.DataFrame,
    y: np.ndarray,
    pa: np.ndarray,
    pb: np.ndarray,
    kind: str,
    names: tuple[str, str],
):
    """Mean loss of a minus b, with a 90% interval from resampling weeks; and the gain in % of b's loss."""
    k = test.select(*plays.KEYS, block=pl.format("{}-{}", c("season"), c("week")))
    a = k.with_columns(loss=pl.Series(loss(y, pa, kind)))
    b = k.with_columns(loss=pl.Series(loss(y, pb, kind)))
    cmp = compare(a, b, plays.KEYS, "block", names, seed=SEED)
    mb = float(b["loss"].mean())
    return {
        "gain_pct": -100 * cmp.diff / mb,
        "lo_pct": -100 * cmp.hi / mb,
        "hi_pct": -100 * cmp.lo / mb,
        "clear": cmp.beats,
    }


def main() -> None:
    src = Gateway().source
    d, t1, t2, hind = table(src)
    tr_all, te_all = d.filter(c("season") == TRAIN), d.filter(c("season") == TEST)
    print(
        f"Dropbacks: {tr_all.height} in {TRAIN} (training), {te_all.height} in {TEST} (scored). Coverage charted on {1 - te_all['cov_missing'].mean():.0%} of {TEST}'s dropbacks; the target's route on {te_all.filter(c('is_attempt'))['route'].is_in(['', None]).not_().mean():.0%} of attempts.\n"
    )

    # the chain before the snap: each earlier step's T2 expectation, cross-fitted on 2023
    exp_tr, exp_te = {}, {}
    for name, (col, kind, _, _) in OUT.items():
        tr = rows_for(tr_all, name)
        m = fit(tr, t2, col, kind)
        oof = crossfit(tr, t2, col, kind)
        oof_rows = tr.select(*plays.KEYS).with_columns(oof=pl.Series(oof))
        # an earlier step is wanted on every dropback; where its outcome isn't a training row of
        # its model (depth on a sack), the full model's value is out of sample anyway
        exp_tr[col] = (
            tr_all.select(*plays.KEYS)
            .with_columns(full=pl.Series(predict(m, tr_all, t2, kind)))
            .join(oof_rows, on=plays.KEYS, how="left")
            .select(pl.coalesce("oof", "full"))
            .to_series()
        )
        exp_te[col] = pl.Series(predict(m, te_all, t2, kind))
    tr_all = tr_all.with_columns(*[s.alias(f"x_{k}") for k, s in exp_tr.items()])
    te_all = te_all.with_columns(*[s.alias(f"x_{k}") for k, s in exp_te.items()])

    res, cmp_rows = [], []
    for name, (col, kind, _, earlier) in OUT.items():
        tr, te = rows_for(tr_all, name), rows_for(te_all, name)
        y = te[col].to_numpy().astype(float)
        base = float(tr[col].mean())
        sets = {
            "T1 calls": t1,
            "T2 + coverage": t2,
            "chain (before the snap)": t2 + [f"x_{e}" for e in earlier],
            "T2 + real pressure": t2 + (["pressure_y"] if name != "pressure" else []),
            "given (all earlier, real)": t2 + earlier,
            "hindsight (the room)": t2 + earlier + hind,
        }
        preds = {}
        for label, fields in sets.items():
            m = fit(tr, fields, col, kind)
            preds[label] = predict(m, te, fields, kind)
            res.append(
                {
                    "outcome": name,
                    "tier": label,
                    "rows": te.height,
                    **summary(y, preds[label], base, kind),
                }
            )
        # fitting noise: T2 on resampled games
        shares = []
        for i in range(3):
            g = tr["game_id"].unique().sort().to_numpy()
            pick = pl.DataFrame({"game_id": np.random.default_rng(100 + i).choice(g, len(g))})
            m = fit(pick.join(tr, on="game_id"), t2, col, kind)
            shares.append(summary(y, predict(m, te, t2, kind), base, kind)["share"])
        res.append(
            {
                "outcome": name,
                "tier": "T2 fitting noise (sd of share, 3 refits)",
                "rows": te.height,
                "share": float(np.std(shares, ddof=1)),
            }
        )
        for a, b in (
            ("T2 + coverage", "T1 calls"),
            ("chain (before the snap)", "T2 + coverage"),
            ("T2 + real pressure", "T2 + coverage"),
            ("given (all earlier, real)", "T2 + coverage"),
        ):
            if a == "T2 + real pressure" and name == "pressure":
                continue
            cmp_rows.append(
                {"outcome": name, "a": a, "b": b, **paired(te, y, preds[a], preds[b], kind, (a, b))}
            )

    pl.Config.set_tbl_rows(100)
    pl.Config.set_tbl_width_chars(220)
    pl.Config.set_fmt_str_lengths(60)
    print(
        "== Each outcome by tier, 2024 (share = % of squared error removed against 2023's average; logloss_gain = % of log loss removed; p10/p90 = the spread of chances)"
    )
    print(pl.DataFrame(res, infer_schema_length=None).with_columns(pl.selectors.float().round(2)))
    print(
        "\n== Comparisons (gain = % of b's mean loss that a removes, 90% interval from resampling weeks; clear = the interval is above zero)"
    )
    print(pl.DataFrame(cmp_rows).with_columns(pl.selectors.float().round(3)))

    # shipped context-live on the same 2024 plays, for reference (trained on 2022-2023; pressure and time to throw on 2023)
    rj = json.loads((run.cache_dir() / "backtest" / "run.json").read_text())
    h = (
        pl.read_parquet(rj["path"])
        .filter(c("season") == TEST)
        .select(*plays.KEYS, "quantity", "mean")
    )
    q = {
        "pressure": "pressure_prob",
        "time_to_throw": "time_to_throw_exp",
        "sack": "sack_prob",
        "depth": "air_yards_exp",
        "completion": "completion_prob",
        "dropback_yards": "dropback_yards_exp",
    }
    ref = []
    for name, (col, kind, _, _) in OUT.items():
        te = rows_for(te_all, name).join(h.filter(c("quantity") == q[name]), on=plays.KEYS)
        ref.append(
            {
                "outcome": name,
                "rows": te.height,
                **summary(
                    te[col].to_numpy().astype(float),
                    te["mean"].to_numpy(),
                    float(rows_for(tr_all, name)[col].mean()),
                    kind,
                ),
            }
        )
    print("\n== Shipped context-live (v1) on 2024, same yardstick")
    print(pl.DataFrame(ref, infer_schema_length=None).with_columns(pl.selectors.float().round(2)))

    # H87: an offense's quick-pass rate over T2's expectation
    att_tr = tr_all.filter(
        c("is_attempt") & c("time_to_throw_y").is_not_null() & c("air_yards_y").is_not_null()
    )
    att_te = te_all.filter(
        c("is_attempt") & c("time_to_throw_y").is_not_null() & c("air_yards_y").is_not_null()
    )
    m = fit(att_tr, t2, "quick", "chance")
    att = pl.concat(
        [
            att_tr.with_columns(pq=pl.Series(crossfit(att_tr, t2, "quick", "chance"))),
            att_te.with_columns(pq=pl.Series(predict(m, att_te, t2, "chance"))),
        ]
    )
    q_te = att_te["quick"].to_numpy()
    print(
        f"\n== H87: quick passes (thrown within 2.5 s, under 5 yards downfield) are {q_te.mean():.1%} of {TEST}'s attempts; T2 explains {summary(q_te, att.filter(c('season') == TEST)['pq'].to_numpy(), float(att_tr['quick'].mean()), 'chance')}"
    )
    att = att.with_columns(oe=c("quick") - c("pq"), half=(c("week") % 2))
    tm = att.group_by("posteam", "season", "half").agg(oe=c("oe").mean(), n=pl.len())
    oe = tm.pivot(on="half", index=["posteam", "season"], values="oe")
    r_half = {
        s: float(np.corrcoef(g["0"], g["1"])[0, 1])
        for s, g in oe.group_by("season")
        for s in [s[0]]
    }
    full = (
        att.group_by("posteam", "season")
        .agg(oe=c("oe").mean())
        .pivot(on="season", index="posteam", values="oe")
    )
    r_season = float(np.corrcoef(full[str(TRAIN)], full[str(TEST)])[0, 1])
    rng = np.random.default_rng(SEED)
    g24 = oe.filter(c("season") == TEST)
    boots = [
        np.corrcoef(*g24[rng.integers(0, g24.height, g24.height)].select("0", "1").to_numpy().T)[
            0, 1
        ]
        for _ in range(2000)
    ]
    boots_s = [
        np.corrcoef(
            *full[rng.integers(0, full.height, full.height)]
            .select(str(TRAIN), str(TEST))
            .to_numpy()
            .T
        )[0, 1]
        for _ in range(2000)
    ]
    print(
        f"An offense's quick-pass rate over expected: odd against even weeks r = {r_half} (2024 90%: {np.quantile(boots, 0.05):.2f} to {np.quantile(boots, 0.95):.2f}); {TRAIN} to {TEST} r = {r_season:.2f} (90%: {np.quantile(boots_s, 0.05):.2f} to {np.quantile(boots_s, 0.95):.2f}); spread across offenses (sd) {full[str(TEST)].std():.3f}"
    )


if __name__ == "__main__":
    main()
