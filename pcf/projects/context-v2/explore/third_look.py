# ruff: noqa: E501
"""context-v2, the third look (2026-11-20): I95. Does an offense's quick-pass rate over expected
to date forecast its next game's pressure and sack rate, beyond its pressure and sacks to date?

Discovery only: trained on 2023's offense-games, scored on 2024's; the 2025 vault untouched.
Design and pass rules committed before the run (EXPLORATION.md, "Third look"; commit cee8ba7).

Run from pcf/:  python projects/context-v2/explore/third_look.py > projects/context-v2/explore/third_look.txt
"""

from __future__ import annotations

import importlib.util
import pathlib

import numpy as np
import polars as pl
from sklearn.linear_model import LinearRegression

from pcf.data.gateway import Gateway
from pcf.validation.compare import compare

_spec = importlib.util.spec_from_file_location(
    "first_look", pathlib.Path(__file__).with_name("first_look.py")
)
fl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fl)

c = pl.col
TRAIN, TEST = fl.TRAIN, fl.TEST
K = 100  # plays of its own denominator that pull a to-date rate towards the league's
KEYS = ["posteam", "game_id"]


def quick_chances(d: pl.DataFrame, t2: list[str]) -> pl.DataFrame:
    """T2's quick-pass chance on every attempt with a time to throw and a depth (as in the first look)."""
    att = d.filter(
        c("is_attempt") & c("time_to_throw_y").is_not_null() & c("air_yards_y").is_not_null()
    )
    tr, te = att.filter(c("season") == TRAIN), att.filter(c("season") == TEST)
    m = fl.fit(tr, t2, "quick", "chance")
    return pl.concat(
        [
            tr.with_columns(pq=pl.Series(fl.crossfit(tr, t2, "quick", "chance"))),
            te.with_columns(pq=pl.Series(fl.predict(m, te, t2, "chance"))),
        ]
    ).select(*fl.plays.KEYS, "pq")


def games(d: pl.DataFrame) -> pl.DataFrame:
    """One row per offense and game: that game's rates and the offense's and opponent's to date."""
    g = d.group_by("season", "week", "game_id", "posteam", "defteam").agg(
        n=pl.len(),
        pr=c("pressure_y").cast(pl.Float64).sum(),
        sk=c("sack_y").cast(pl.Float64).sum(),
        nq=c("pq").is_not_null().sum(),
        q=c("quick").filter(c("pq").is_not_null()).sum(),
        qe=(c("quick") - c("pq")).filter(c("pq").is_not_null()).sum(),
        nt=c("time_to_throw_y").is_not_null().sum(),
        t=c("time_to_throw_y").sum(),
    )
    lg = (
        g.filter(c("season") == TRAIN)
        .select(
            pr=c("pr").sum() / c("n").sum(),
            sk=c("sk").sum() / c("n").sum(),
            q=c("q").sum() / c("nq").sum(),
            t=c("t").sum() / c("nt").sum(),
        )
        .row(0, named=True)
    )

    def to_date(team: str, cols: list[str], prefix: str) -> pl.DataFrame:
        s = g.sort("season", "week").select(
            "season",
            "game_id",
            c(team).alias("team"),
            *[c(x).cum_sum().shift(1).over("season", team).fill_null(0).alias(x) for x in cols],
            games_before=pl.int_range(pl.len()).over("season", team),
        )
        return s.select(
            "season",
            "game_id",
            "team",
            "games_before",
            **{
                f"{prefix}_pr": (c("pr") + K * lg["pr"]) / (c("n") + K),
                f"{prefix}_sr": (c("sk") + K * lg["sk"]) / (c("n") + K),
            },
            **(
                {
                    "qoe": c("qe") / (c("nq") + K),
                    "qraw": (c("q") + K * lg["q"]) / (c("nq") + K),
                    "ttt": (c("t") + K * lg["t"]) / (c("nt") + K),
                }
                if prefix == "off"
                else {}
            ),
        )

    off = to_date("posteam", ["n", "pr", "sk", "nq", "q", "qe", "nt", "t"], "off")
    dfn = to_date("defteam", ["n", "pr", "sk"], "opp").drop("games_before")
    out = (
        g.join(off.rename({"team": "posteam"}), on=["season", "game_id", "posteam"])
        .join(dfn.rename({"team": "defteam"}), on=["season", "game_id", "defteam"])
        .filter(c("games_before") >= 1)
        .with_columns(y_pr=c("pr") / c("n"), y_sr=c("sk") / c("n"))
    )
    return out, lg


SETS = {
    "base": ["off_pr", "off_sr", "opp_pr", "opp_sr"],
    "base + quick over expected": ["off_pr", "off_sr", "opp_pr", "opp_sr", "qoe"],
    "base + quick (raw)": ["off_pr", "off_sr", "opp_pr", "opp_sr", "qraw"],
    "base + time to throw": ["off_pr", "off_sr", "opp_pr", "opp_sr", "ttt"],
    "base + time to throw + quick over expected": [
        "off_pr",
        "off_sr",
        "opp_pr",
        "opp_sr",
        "ttt",
        "qoe",
    ],
}
COMPARE = [
    ("base + quick over expected", "base"),
    ("base + quick (raw)", "base"),
    ("base + time to throw", "base"),
    ("base + time to throw + quick over expected", "base + time to throw"),
    ("base + quick over expected", "base + quick (raw)"),
]


def fit(tr: pl.DataFrame, fields: list[str], y: str) -> LinearRegression:
    return LinearRegression().fit(
        tr.select(fields).to_numpy(), tr[y].to_numpy(), tr["n"].to_numpy()
    )


def scored(te: pl.DataFrame, p: np.ndarray, y: str) -> pl.DataFrame:
    w = te["n"].to_numpy() / te["n"].mean()
    return te.select(*KEYS, block=pl.format("{}-{}", c("season"), c("week"))).with_columns(
        loss=pl.Series(w * (te[y].to_numpy() - p) ** 2)
    )


def run_direction(tr: pl.DataFrame, te: pl.DataFrame, label: str) -> None:
    print(f"\n== Trained on {label}")
    for y, name in (("y_sr", "sack rate"), ("y_pr", "pressure rate")):
        yt, wt = te[y].to_numpy(), te["n"].to_numpy()
        base_mean = float(np.average(tr[y].to_numpy(), weights=tr["n"].to_numpy()))
        sse0 = float(np.sum(wt * (yt - base_mean) ** 2))
        rows, preds, coefs = [], {}, {}
        for k, fields in SETS.items():
            m = fit(tr, fields, y)
            preds[k] = m.predict(te.select(fields).to_numpy())
            coefs[k] = dict(zip(fields, m.coef_.round(4).tolist(), strict=True))
            rows.append(
                {
                    "model": k,
                    "share_pct": 100 * (1 - np.sum(wt * (yt - preds[k]) ** 2) / sse0),
                }
            )
        print(f"-- {name}: share of the weighted squared error removed against the training mean")
        print(pl.DataFrame(rows).with_columns(c("share_pct").round(2)))
        for k in ("base + quick over expected", "base + time to throw + quick over expected"):
            print(f"   weights, {k}: {coefs[k]}")
        out = []
        for a, b in COMPARE:
            sa, sb = scored(te, preds[a], y), scored(te, preds[b], y)
            cmp = compare(sa, sb, KEYS, "block", (a, b), seed=fl.SEED)
            mb = float(sb["loss"].mean())
            out.append(
                {
                    "a": a,
                    "b": b,
                    "gain_pct": -100 * cmp.diff / mb,
                    "lo_pct": -100 * cmp.hi / mb,
                    "hi_pct": -100 * cmp.lo / mb,
                    "clear": cmp.beats,
                }
            )
        print("-- gain = % of b's error that a removes (90% interval from resampling weeks)")
        print(pl.DataFrame(out).with_columns(pl.selectors.float().round(2)))


def main() -> None:
    src = Gateway().source
    d, _, t2, _ = fl.table(src)
    d = d.join(quick_chances(d, t2), on=fl.plays.KEYS, how="left")
    g, lg = games(d)
    tr, te = g.filter(c("season") == TRAIN), g.filter(c("season") == TEST)
    print(
        f"Offense-games after the first of the season: {tr.height} ({TRAIN}), {te.height} ({TEST}); mean dropbacks a game {g['n'].mean():.1f}. League ({TRAIN}): pressure {lg['pr']:.3f}, sack {lg['sk']:.3f}, quick {lg['q']:.3f}, time to throw {lg['t']:.2f} s"
    )

    # the room: the share of a game's rate variance that isn't the coin flip's
    for y, _p, name in (("y_sr", "sk", "sack rate"), ("y_pr", "pr", "pressure rate")):
        for s, part in ((TRAIN, tr), (TEST, te)):
            yv, w = part[y].to_numpy(), part["n"].to_numpy()
            mu = np.average(yv, weights=w)
            var = np.average((yv - mu) ** 2, weights=w)
            noise = mu * (1 - mu) * len(yv) / w.sum()
            print(
                f"The room, {name}, {s}: weighted variance {var:.5f}, the coin flip's {noise:.5f}; at most {100 * (1 - noise / var):.1f}% of the error is not luck"
            )

    print(
        "\nCorrelations, 2024 rows: "
        + str(
            te.select(
                q_ttt=pl.corr("qoe", "ttt"),
                q_offpr=pl.corr("qoe", "off_pr"),
                q_offsr=pl.corr("qoe", "off_sr"),
                q_raw=pl.corr("qoe", "qraw"),
            ).row(0, named=True)
        )
    )

    run_direction(tr, te, f"{TRAIN}, scored on {TEST} (the pre-registered test)")
    run_direction(te, tr, f"{TEST}, scored on {TRAIN} (the reverse, a robustness check only)")

    # the sign of the quick-pass weight on the sack rate: bootstrap of 2023's offense-games by week
    rng = np.random.default_rng(fl.SEED)
    weeks = tr["week"].unique().to_numpy()
    fields = SETS["base + quick over expected"]
    b = []
    for _ in range(1000):
        pick = pl.DataFrame({"week": rng.choice(weeks, len(weeks))})
        m = fit(pick.join(tr, on="week"), fields, "y_sr")
        b.append(m.coef_[-1])
    print(
        f"\nThe weight of quick over expected on the sack rate ({TRAIN}, base + quick): 90% from resampling weeks {np.quantile(b, 0.05):.4f} to {np.quantile(b, 0.95):.4f}; share negative {np.mean(np.array(b) < 0):.0%}"
    )


if __name__ == "__main__":
    main()
