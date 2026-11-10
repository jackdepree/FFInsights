"""Scheme against scheme, option B (CEO, 2026-11-09): the play-by-play matchup map, then one game test.

F20 found a real pairing-specific part in an offense's result against a defense (about 9% of what
strength leaves, within a season), and that the season-level tendency pairs reach about 1% of it.
Game-level tests have ~4,000 games; plays number ~250,000. So the matchup is measured play by play,
then carried to games as ONE number per side (no game-level fitting, so no many-pairs penalty).

Plays: regular season 2016-2024, downs 1-3, win chance 5-95%, not the last two minutes of a half
(F17's `plays()`). FTN charting (play action, motion, RPO, screens) 2022-2024. Coverage (man,
two-high) and blitzes are charted on dropbacks only. The vault (2025) isn't read.

1. **The map.** EPA beyond the situation (a league model of EPA from down, distance, field position,
   score, win chance, time, home and season, fitted on other seasons) is regressed, per offense call
   a and defense call d, on a + d + a·d, each call also interacted with down and long distance.
   The a·d term (Δ) is how much more the offense gains from call a when the defense makes call d.
   Game-clustered standard errors.
2. **B1, styles against styles.** Each side's matchup term is the sum over pairs of
   Δ (fitted without that season) × (the offense's use of a less the league's) × (the defense's use
   of d less the league's) × the share of plays the pair applies to.
3. **B2, units against calls.** "An offense that beats man against a man-heavy defense": each
   offense's own gain against each defense call (its other games that season, shrunk to zero with
   800 plays' weight) × the defense's use of that call over the league's; plus the mirror for the
   defense's weakness against each offense call × the offense's use of it.
4. **The test.** Each term against the side's residual (F20's: EPA per play beyond both units'
   season strength, leaving out the game). Uses come in two versions: the season's other games
   (a ceiling version, like F20) and earlier games only (3+, what a forecast could know).
   Null: the defense's half of the term shuffled among sides in the same week (200 times).

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/matchups.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from rematch import Strength, fit, load
from restricted import SIT, crossfit, plays

from pcf.config import get_config
from pcf.data.tables.store import read_part

c = pl.col
RNG = np.random.default_rng(20261110)
SHUFFLES = 200
K_SHRINK = 800
CACHE = get_config().zone("interim") / "schemes_v2" / "matchup_plays.parquet"
OFF = ["pass", "shotgun", "no_huddle", "heavy", "play_action", "motion", "rpo", "screen"]
DEF = ["box8", "blitz", "man", "two_high"]
FTN = {
    "play_action": "is_play_action",
    "motion": "is_motion",
    "rpo": "is_rpo",
    "screen": "is_screen_pass",
}


def play_table() -> pl.DataFrame:
    if CACHE.exists():
        return pl.read_parquet(CACHE)
    p = plays().filter(c("season") >= 2016)
    X = p.select(SIT).to_numpy().astype(float)
    r = p["epa"].to_numpy() - crossfit(X, p["epa"].to_numpy(), p["season"].to_numpy() % 5, False)
    ftn = pl.concat(
        [
            read_part("play", "ftn", [s]).select("game_id", "play_id", *FTN.values()).collect()
            for s in (2022, 2023, 2024)
        ]
    )
    p = (
        p.with_columns(r=pl.Series(r), heavy=c("heavy_p"), pass_=c("pass").cast(pl.Float64))
        .join(ftn, on=["game_id", "play_id"], how="left")
        .with_columns(
            *[
                pl.when(c("season") >= 2022).then(c(v).cast(pl.Float64)).alias(k)
                for k, v in FTN.items()
            ]
        )
    )
    p = p.select(
        "game_id",
        "play_id",
        "season",
        "week",
        "posteam",
        "defteam",
        "down",
        "ydstogo",
        "qb_dropback",
        "r",
        c("pass_").alias("pass"),
        c("shotgun").cast(pl.Float64),
        c("no_huddle").cast(pl.Float64),
        "heavy",
        *FTN,
        *DEF,
    )
    p.write_parquet(CACHE)
    return p


def cluster_ols(y, X, g):
    """OLS with standard errors clustered by g."""
    XtX = np.linalg.inv(X.T @ X)
    b = XtX @ X.T @ y
    e = y - X @ b
    order = np.argsort(g, kind="stable")
    gs, Xe = g[order], X[order] * e[order, None]
    cuts = np.flatnonzero(np.diff(gs)) + 1
    S = np.add.reduceat(Xe, np.r_[0, cuts], axis=0)
    V = XtX @ (S.T @ S) @ XtX
    return b, np.sqrt(np.diag(V))


def design(q: pl.DataFrame, a: str, d: str):
    av, dv = q[a].to_numpy(), q[d].to_numpy()
    d2 = (q["down"] == 2).to_numpy().astype(float)
    d3 = (q["down"] == 3).to_numpy().astype(float)
    lg = (q["ydstogo"] >= 7).to_numpy().astype(float)
    X = np.column_stack(
        [
            np.ones(len(av)),
            av,
            dv,
            av * dv,
            d2,
            d3,
            lg,
            av * d2,
            av * d3,
            av * lg,
            dv * d2,
            dv * d3,
            dv * lg,
        ]
    )
    return X


def pair_rows(p: pl.DataFrame, a: str, d: str) -> pl.DataFrame:
    return p.filter(c(a).is_not_null() & c(d).is_not_null())


def the_map(p: pl.DataFrame) -> dict:
    """Δ per pair on all seasons (for the table) and leaving each season out (for the game test)."""
    out = {}
    print(
        "\n== 1. The play-by-play map: Δ = how much more the offense gains from its call when the defense makes its call (EPA per play)"
    )
    print(
        f"   {'offense call':<12} {'defense call':<9} {'Δ':>8} {'t':>6} {'plays':>8}  cells (a,d)=(1,1)/(1,0)/(0,1)/(0,0)   applies to"
    )
    total = p.height
    for a in OFF:
        for d in DEF:
            q = pair_rows(p, a, d)
            if q.height < 5000:
                continue
            cells = q.group_by(a, d).len()
            if cells.height < 4 or cells["len"].min() < 300:
                continue
            y = q["r"].to_numpy()
            X = design(q, a, d)
            g = q["game_id"].cast(pl.Categorical).to_physical().to_numpy()
            b, se = cluster_ols(y, X, g)
            loso = {}
            seasons = q["season"].to_numpy()
            for s in np.unique(seasons):
                k = seasons != s
                loso[int(s)] = float(np.linalg.lstsq(X[k], y[k], rcond=None)[0][3])
            share = q.height / p.filter(c("season").is_in(q["season"].unique().implode())).height
            out[(a, d)] = {
                "delta": b[3],
                "t": b[3] / se[3],
                "n": q.height,
                "loso": loso,
                "share": share,
            }
            cc = {(r[a], r[d]): r["len"] for r in cells.iter_rows(named=True)}
            print(
                f"   {a:<12} {d:<9} {b[3]:>+8.3f} {b[3] / se[3]:>6.1f} {q.height:>8,}  "
                f"{cc.get((1.0, 1.0), 0):>6,}/{cc.get((1.0, 0.0), 0):>6,}/{cc.get((0.0, 1.0), 0):>6,}/{cc.get((0.0, 0.0), 0):>7,}   {share:.0%}"
            )
    n_pairs = len(out)
    print(
        f"   {n_pairs} pairs; with that many, |t| above 3.0 is the bar (about 5% by chance overall). Above it: "
        f"{sum(abs(v['t']) > 3.0 for v in out.values())}; above 2: {sum(abs(v['t']) > 2 for v in out.values())} (chance: about {0.05 * n_pairs:.1f})"
    )
    print(f"   all-plays total {total:,}")
    return out


def uses(p: pl.DataFrame):
    """Per side (game, offense, defense): each unit's use of each call and splits, from its other
    games that season (leave out) and from its earlier games (3+)."""
    calls = OFF + DEF
    # offense game sums of its calls; defense game sums of its calls
    og = (
        p.group_by("game_id", "season", "week", "posteam")
        .agg(
            *[c(a).sum().alias(f"s_{a}") for a in OFF],
            *[c(a).is_not_null().sum().alias(f"n_{a}") for a in OFF],
            # the offense's gain against each defense call: r sums and counts in each cell
            *[c("r").filter(c(d) == 1).sum().alias(f"r1_{d}") for d in DEF],
            *[(c(d) == 1).sum().alias(f"k1_{d}") for d in DEF],
            *[c("r").filter(c(d) == 0).sum().alias(f"r0_{d}") for d in DEF],
            *[(c(d) == 0).sum().alias(f"k0_{d}") for d in DEF],
        )
        .rename({"posteam": "team"})
    )
    dg = (
        p.group_by("game_id", "season", "week", "defteam")
        .agg(
            *[c(d).sum().alias(f"s_{d}") for d in DEF],
            *[c(d).is_not_null().sum().alias(f"n_{d}") for d in DEF],
            *[c("r").filter(c(a) == 1).sum().alias(f"r1_{a}") for a in OFF],
            *[(c(a) == 1).sum().alias(f"k1_{a}") for a in OFF],
            *[c("r").filter(c(a) == 0).sum().alias(f"r0_{a}") for a in OFF],
            *[(c(a) == 0).sum().alias(f"k0_{a}") for a in OFF],
        )
        .rename({"defteam": "team"})
    )

    def windows(t: pl.DataFrame, own: list[str], other: list[str]) -> pl.DataFrame:
        cols = (
            [f"s_{x}" for x in own]
            + [f"n_{x}" for x in own]
            + [f"{k}_{x}" for x in other for k in ("r1", "k1", "r0", "k0")]
        )
        t = t.sort("team", "season", "week")
        grp = ["team", "season"]
        lo = [(c(x).sum().over(grp) - c(x)).alias(f"lo_{x}") for x in cols]
        pre = [(c(x).cum_sum().over(grp) - c(x)).alias(f"pre_{x}") for x in cols]
        return t.with_columns(*lo, *pre, ng=pl.int_range(pl.len()).over(grp))

    og = windows(og, OFF, DEF)
    dg = windows(dg, DEF, OFF)
    league = {
        x: p.filter(c(x).is_not_null()).group_by("season").agg(c(x).mean().alias(f"L_{x}"))
        for x in calls
    }
    return og, dg, league


def rates(
    t: pl.DataFrame, own: list[str], other: list[str], w: str, league: dict, side: str
) -> pl.DataFrame:
    """Use over the league's, and shrunk splits, for window w ('lo' or 'pre')."""
    exprs = []
    for x in own:
        exprs.append(
            pl.when(c(f"{w}_n_{x}") > 0)
            .then(c(f"{w}_s_{x}") / c(f"{w}_n_{x}") - c(f"L_{x}"))
            .alias(f"{side}u_{x}")
        )
    for x in other:
        k1, k0 = c(f"{w}_k1_{x}"), c(f"{w}_k0_{x}")
        neff = k1 * k0 / (k1 + k0)
        raw = c(f"{w}_r1_{x}") / k1 - c(f"{w}_r0_{x}") / k0
        exprs.append(
            pl.when((k1 > 0) & (k0 > 0)).then(raw * neff / (neff + K_SHRINK)).alias(f"{side}g_{x}")
        )
    for x in own:
        t = t.join(league[x], on="season", how="left")
    out = t.with_columns(*exprs)
    if w == "pre":
        out = out.with_columns(
            *[pl.when(c("ng") >= 3).then(c(f"{side}u_{x}")).alias(f"{side}u_{x}") for x in own],
            *[pl.when(c("ng") >= 3).then(c(f"{side}g_{x}")).alias(f"{side}g_{x}") for x in other],
        )
    return out.select(
        "game_id", "team", *[f"{side}u_{x}" for x in own], *[f"{side}g_{x}" for x in other]
    )


def residuals() -> pl.DataFrame:
    s = load()
    st = Strength(s)
    b, _, _ = fit(s, st)
    rows = []
    for r in s.iter_rows(named=True):
        so, sd = st.pair(r["season"], r["off"], r["dfn"], {r["game_id"]})
        rows.append(
            (
                r["game_id"],
                r["off"],
                r["dfn"],
                r["season"],
                r["week"],
                r["y"] - (b[0] + b[1] * so + b[2] * sd),
            )
        )
    return pl.DataFrame(
        rows, schema=["game_id", "off", "dfn", "season", "week", "resid"], orient="row"
    ).filter(c("season") >= 2016)


def terms(
    sides: pl.DataFrame, m: dict, perm: np.ndarray | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """B1 and B2 per side; perm reorders the defense's columns (the shuffled null)."""
    n = sides.height
    D = {k: sides[k].to_numpy() for k in sides.columns if k.startswith("d")}
    if perm is not None:
        D = {k: v[perm] for k, v in D.items()}
    season = sides["season"].to_numpy()
    b1, b2 = np.zeros(n), np.zeros(n)
    for (a, d), v in m.items():
        delta = np.array([v["loso"].get(int(s), np.nan) for s in season])
        ou, du = sides[f"ou_{a}"].to_numpy(), D[f"du_{d}"]
        b1 += np.nan_to_num(delta * ou * du * v["share"])
    for d in DEF:
        b2 += np.nan_to_num(sides[f"og_{d}"].to_numpy() * D[f"du_{d}"])
    for a in OFF:
        b2 += np.nan_to_num(D[f"dg_{a}"] * sides[f"ou_{a}"].to_numpy())
    return b1, b2


def test(sides: pl.DataFrame, m: dict, label: str) -> None:
    y = sides["resid"].to_numpy()
    wk = (sides["season"] * 100 + sides["week"]).to_numpy()
    b1, b2 = terms(sides, m)
    null = []
    idx = np.arange(sides.height)
    for _ in range(SHUFFLES):
        perm = idx.copy()
        for k in np.unique(wk):
            w = idx[wk == k]
            perm[w] = RNG.permutation(w)
        n1, n2 = terms(sides, m, perm)
        null.append(
            (
                np.corrcoef(n1, y)[0, 1],
                np.corrcoef(n2, y)[0, 1],
                np.corrcoef(n1 + n2 / max(n2.std(), 1e-9) * n1.std(), y)[0, 1],
            )
        )
    null = np.array(null)
    print(f"\n== {label}: {sides.height:,} sides")
    for k, (name, t) in enumerate((("B1 styles × styles", b1), ("B2 units × calls", b2))):
        r = float(np.corrcoef(t, y)[0, 1])
        slope = np.polyfit(t / t.std(), y, 1)[0]
        print(
            f"   {name:<20} r {r:+.3f}; shuffled defenses at or above: {np.mean(null[:, k] >= r):.1%} (95th {np.quantile(null[:, k], 0.95):+.3f}); "
            f"{slope:+.4f} EPA per play per sd; share of F20's ceiling (9.2%): {max(r, 0) ** 2 / 0.092:.1%}"
        )


def main() -> None:
    p = play_table()
    print(
        f"plays {p.height:,} (2016-2024); FTN plays {p.filter(c('motion').is_not_null()).height:,}"
    )
    m = the_map(p)
    og, dg, league = uses(p)
    res = residuals()
    for w, label in (
        ("lo", "2. The season's other games (ceiling version, like F20)"),
        ("pre", "3. Earlier games only, 3+ (what a forecast could know)"),
    ):
        o = rates(og, OFF, DEF, w, league, "o")
        d = rates(dg, DEF, OFF, w, league, "d")
        sides = res.join(o.rename({"team": "off"}), on=["game_id", "off"]).join(
            d.rename({"team": "dfn"}), on=["game_id", "dfn"]
        )
        if w == "pre":
            sides = sides.drop_nulls(["ou_pass", "du_box8"])
        test(sides, m, label)


if __name__ == "__main__":
    main()
