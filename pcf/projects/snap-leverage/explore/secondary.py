"""snap-leverage exploration (2026-11-14): the CEO's secondary tests for H45.

1. Contracts. Veteran contracts (not signed in the draft year) signed 2019-2024 (2025 left for
   later), each player's largest that year, as a share of the cap (OverTheCap's apy_cap_pct).
   Features from the season before: plain (snap share over his rostered games, games played, age
   at signing, draft pick, years in the league, position group) and the leverage measures (step 2,
   season means). Walk-forward by signing year (each of 2021-2024 fitted on 2019 to the year
   before), trees; gain = the share of the plain model's squared error removed, 90% interval from
   resampling players. Also within position: the correlation of each measure with what the plain
   model leaves over.
2. Plus-minus (the CEO: "how much worse the team plays when that player misses a game"). A
   player is newly missing when he played 30%+ of his side's snaps in his team's previous game
   and none in this one. The side's EPA per play this game (relative to the week's league mean;
   offense gained or defense allowed, sign set so + = worse for the team) less team-efficiency's
   champion forecast for it (made before the game, which doesn't know the absence). Regressed on
   the missing players' summed season-to-date snap share and their summed trust measures, with a
   90% interval from resampling weeks. 2017-2024.
Writes secondary.txt. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/snap-leverage/explore/secondary.py
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[2] / "team-efficiency" / "build"))
import playing_time as PT  # noqa: E402
import summary as S  # noqa: E402

from pcf.config import get_config  # noqa: E402
from pcf.data.tables.store import load  # noqa: E402
from pcf.experts.team_efficiency import features as F  # noqa: E402

c = pl.col
HERE = Path(__file__).parent
LEV = ["lev_share", "hi_share", "trust_gap", "trust_oe"]


def boot(e_base: np.ndarray, e_alt: np.ndarray, n: int = 500) -> str:
    rng = np.random.default_rng(0)
    i = rng.integers(0, len(e_base), size=(n, len(e_base)))
    g = 1 - e_alt[i].sum(1) / e_base[i].sum(1)
    lo, hi = np.percentile(g, [5, 95])
    return f"{1 - e_alt.sum() / e_base.sum():+.2%} ({lo:+.2%} to {hi:+.2%})"


def contracts(x: pl.DataFrame, say) -> None:
    raw = get_config().zone("raw") / "nflverse" / "contracts" / "historical_contracts.parquet"
    k = pl.read_parquet(raw).filter(c("gsis_id").is_not_null() & c("apy_cap_pct").is_not_null() & (c("year_signed") != c("draft_year")) & c("year_signed").is_between(2019, 2024))
    k = k.group_by("gsis_id", "year_signed").agg(c("apy_cap_pct").max(), c("date_of_birth").first(), c("draft_overall").first())
    played = x.filter(c("played"))
    ps = x.group_by("gsis_id", "season").agg(
        snap=c("snap_share").mean(), games=c("played").sum(), rost=pl.len(), lev=c("lev_share").mean(), hi=c("hi_share").mean(),
        yexp=c("years_exp").max(), g=c("g").first(),
    ).join(played.group_by("gsis_id", "season").agg(c("trust_gap").mean(), c("trust_oe").mean()), on=["gsis_id", "season"], how="left")
    d = k.join(ps.with_columns(year_signed=c("season") + 1), on=["gsis_id", "year_signed"]).with_columns(
        age=(pl.date(c("year_signed"), 3, 15) - c("date_of_birth").str.to_date("%B %d, %Y", strict=False)).dt.total_days() / 365.25,
        pick=c("draft_overall").fill_null(260).cast(pl.Float64),
    )
    say(f"1. Contracts: {d.height:,} veteran contracts signed 2019-2024 with the season before in our rows; mean {d['apy_cap_pct'].mean():.2%} of the cap")
    plain = ["snap", "games", "rost", "age", "pick", "yexp", "g"]
    sets = {"plain": plain, "+ leverage share": plain + ["lev"], "+ high-stakes share": plain + ["hi"],
            "+ trust gap (raw)": plain + ["trust_gap"], "+ trust over expected": plain + ["trust_oe"], "+ all four": plain + ["lev", "hi", "trust_gap", "trust_oe"]}
    preds = {nm: [] for nm in sets}
    parts = []
    for y in range(2021, 2025):
        tr, te = d.filter(c("year_signed") < y), d.filter(c("year_signed") == y)
        for nm, cols in sets.items():
            m = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=40, random_state=0)
            m.fit(tr.select(cols).to_numpy().astype(float), tr["apy_cap_pct"].to_numpy())
            preds[nm].append(m.predict(te.select(cols).to_numpy().astype(float)))
        parts.append(te)
    sc = pl.concat(parts).with_columns(**{nm: pl.Series(np.concatenate(v)) for nm, v in preds.items()})
    y = sc["apy_cap_pct"].to_numpy()
    eb = (y - sc["plain"].to_numpy()) ** 2
    say(f"  scored 2021-2024: {sc.height:,} contracts; the plain model's r with pay {np.corrcoef(y, sc['plain'].to_numpy())[0, 1]:.2f}")
    for nm in list(sets)[1:]:
        say(f"    {nm:24s} {boot(eb, (y - sc[nm].to_numpy()) ** 2)}")
    big = sc.filter(c("apy_cap_pct") >= 0.01)
    yb = big["apy_cap_pct"].to_numpy()
    say(f"  contracts at 1%+ of the cap ({big.height:,}):")
    for nm in list(sets)[1:]:
        say(f"    {nm:24s} {boot((yb - big['plain'].to_numpy()) ** 2, (yb - big[nm].to_numpy()) ** 2)}")
    say("  correlation of each measure with what the plain model leaves over (pay - plain), by group:")
    sc = sc.with_columns(left=c("apy_cap_pct") - c("plain"))
    names = {0: None}
    gmap = x.select("g", "rgroup").unique()
    sc = sc.join(gmap, on="g", how="left")
    for g in ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB"]:
        a = sc.filter(c("rgroup") == g)
        rs = [f"{m} {a.select(pl.corr(m, 'left')).item():+.2f}" for m in ("lev", "hi", "trust_gap", "trust_oe")]
        say(f"    {g:2s} ({a.height}) " + ", ".join(rs))
    del names


def plus_minus(x: pl.DataFrame, say) -> None:
    k = ["gsis_id", "season"]
    x = x.sort("gsis_id", "season", "week").with_columns(
        prev=c("snap_share").shift(1).over(k),
        prev_std=c("snap_share_std").shift(1).over(k),
        prev_oe=c("trust_oe_std").shift(1).over(k),
        prev_gap=c("trust_gap_std").shift(1).over(k),
        prev_lev=c("lev_share_std").shift(1).over(k),
    )
    miss = x.filter((c("prev") >= 0.3) & ~c("played") & c("season").is_between(2017, 2024))
    agg = miss.group_by("game_id", "team", "side").agg(
        n_out=pl.len(), out_snap=c("prev_std").sum(), out_oe=c("prev_oe").fill_null(0).sum(),
        out_gap=c("prev_gap").fill_null(0).sum(), out_lev=c("prev_lev").sum(),
    )
    tg = S.load("team_game", parts=["schedule", "efficiency"])
    rows = []
    for side, v in (("off", "off_next3_change"), ("def", "def_next3_ridge")):
        y1 = F.targets(tg, side, "next3")  # only for the schedule of windows; the game's own value below
        del y1
        sched = tg.filter(c("game_type") == "REG").select("game_id", "team", "opponent", "season", "week", "eff_plays", "eff_epa")
        league = sched.group_by("season", "week").agg(lm=c("eff_epa").sum() / c("eff_plays").sum())
        g = sched.join(league, on=["season", "week"])
        if side == "off":
            g = g.with_columns(rel=c("eff_epa") / c("eff_plays") - c("lm"), n=c("eff_plays"))
        else:
            opp = g.select("game_id", opponent="team", rel_o=c("eff_epa") / c("eff_plays") - c("lm"), n_o="eff_plays")
            g = g.join(opp, on=["game_id", "opponent"]).with_columns(rel=c("rel_o"), n=c("n_o"))
        f = S.latest(v).select("game_id", "team", fc="mean")
        g = g.join(f, on=["game_id", "team"]).with_columns(
            worse=pl.when(pl.lit(side == "off")).then(c("fc") - c("rel")).otherwise(c("rel") - c("fc")),
            side=pl.lit("offense" if side == "off" else "defense"),
        )
        rows.append(g.select("game_id", "team", "season", "week", "side", "worse", "n"))
    g = pl.concat(rows).join(agg, on=["game_id", "team", "side"], how="left").with_columns(c("n_out", "out_snap", "out_oe", "out_gap", "out_lev").fill_null(0))
    g = g.filter(c("season").is_between(2017, 2024) & c("worse").is_not_null())
    say("")
    say(f"2. Plus-minus: {g.height:,} team-game sides, 2017-2024; {g.filter(c('n_out') > 0).height:,} with a newly missing player ({miss.height:,} absences)")
    say("   'worse' = how much worse than team-efficiency's forecast the side played, EPA per play (+ = worse)")
    say(f"   mean worse with nobody newly out {g.filter(c('n_out') == 0)['worse'].mean():+.4f}; with someone out {g.filter(c('n_out') > 0)['worse'].mean():+.4f}")
    for nm, cols in (("snap share only", ["out_snap"]), ("snap + trust over expected", ["out_snap", "out_oe"]),
                     ("snap + trust gap", ["out_snap", "out_gap"]), ("snap + leverage share", ["out_snap", "out_lev"])):
        for side in ("offense", "defense"):
            d = g.filter(c("side") == side).with_columns(blk=pl.concat_str("season", "week", separator="-"))
            X = np.column_stack([np.ones(d.height)] + [d[cc].to_numpy() for cc in cols])
            yv, w = d["worse"].to_numpy(), d["n"].to_numpy().astype(float)
            sw = np.sqrt(w)
            beta = np.linalg.lstsq(X * sw[:, None], yv * sw, rcond=None)[0]
            blks = d["blk"].to_numpy()
            ub = np.unique(blks)
            idx = {b: np.where(blks == b)[0] for b in ub}
            rng = np.random.default_rng(0)
            bs = []
            for _ in range(300):
                pick = np.concatenate([idx[b] for b in rng.choice(ub, len(ub))])
                bs.append(np.linalg.lstsq(X[pick] * sw[pick, None], yv[pick] * sw[pick], rcond=None)[0])
            bs = np.array(bs)
            terms = [f"{cc} {beta[j + 1]:+.4f} ({np.percentile(bs[:, j + 1], 5):+.4f} to {np.percentile(bs[:, j + 1], 95):+.4f})" for j, cc in enumerate(cols)]
            say(f"   {side:7s} {nm:28s} " + "; ".join(terms))


def main() -> None:
    lines: list[str] = []

    def say(t: str = "") -> None:
        print(t, flush=True)
        lines.append(t)

    x = PT.rows()
    contracts(x, say)
    plus_minus(x, say)
    (HERE / "secondary.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    _ = load
    main()
