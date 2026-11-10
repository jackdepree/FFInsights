"""H9's real test, first look (2026-11-08, discovery only): do style pairings predict margins
beyond the ratings and the market?

From `conditions.py`: each side (offense O against defense D) gets the summed offense × defense
interaction prediction for its EPA per play, fitted on the other half of the seasons (even
seasons predict odd, and the reverse), with every tendency known before the game. A game's
matchup term is the home offense's prediction less the away offense's (EPA per play).

1. The matchup term against the margin's miss: the close (result less `spread_line`), and
   Elo's validated margin forecast (2016-2024, its last forecast before kickoff).
2. Against shuffled opponents (each offense gets a random defense from the same week), 200 times.
3. The size in points, and whether the term does better where the two styles differ most.
The vault (2025) isn't read.

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/margins.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from conditions import DEF, OFF, SHUFFLES, ols_t, shuffled, sides

from pcf.config import get_config
from pcf.data.tables.store import read_part

c = pl.col
MARGIN_RUN = "21082e26cec94ea1920081554197d201"


def held_preds(s: pl.DataFrame, dz: dict[str, np.ndarray]) -> np.ndarray:
    y = s["resid"].to_numpy()
    season = s["season"].to_numpy()
    preds = np.zeros(s.height)
    for fold in (0, 1):
        tr, te = season % 2 == fold, season % 2 != fold
        for a in OFF:
            za = s[f"z_{a}"].to_numpy()
            for d in DEF:
                zd = dz[d]
                ok = tr & ~(np.isnan(za) | np.isnan(zd) | np.isnan(y))
                if ok.sum() < 500:
                    continue
                b, _ = ols_t(y[ok], [za[ok], zd[ok], za[ok] * zd[ok]])
                preds[te] += np.nan_to_num(b[3] * za[te] * zd[te])
    return preds


def games() -> pl.DataFrame:
    sch = read_part("game", "schedule").select("game_id", "season", "home_team", "away_team").collect()
    res = read_part("game", "result").select("game_id", "home_score", "away_score").collect()
    pre = read_part("game", "pregame").select("game_id", "spread_line").collect()
    elo = (pl.read_parquet(get_config().zone("outputs") / "elo" / "margin" / MARGIN_RUN / "history.parquet")
           .sort("as_of").group_by("game_id").last().select("game_id", elo=c("mean")))
    return (sch.join(res, on="game_id").join(pre, on="game_id", how="left").join(elo, on="game_id", how="left")
            .with_columns(margin=c("home_score") - c("away_score"))
            .with_columns(miss_close=c("margin") - c("spread_line"), miss_elo=c("margin") - c("elo")))


def game_terms(s: pl.DataFrame, preds: np.ndarray, g: pl.DataFrame) -> pl.DataFrame:
    sp = s.select("game_id", "team").with_columns(p=pl.Series(preds))
    return (g.join(sp.rename({"team": "home_team", "p": "p_home"}), on=["game_id", "home_team"])
            .join(sp.rename({"team": "away_team", "p": "p_away"}), on=["game_id", "away_team"])
            .with_columns(term=c("p_home") - c("p_away")))


def r(x, y) -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = ~(np.isnan(x) | np.isnan(y))
    return float(np.corrcoef(x[ok], y[ok])[0, 1])


def main() -> None:
    s = sides()
    g = games()
    real = game_terms(s, held_preds(s, {d: s[f"z_{d}"].to_numpy() for d in DEF}), g)
    nulls = [game_terms(s, held_preds(s, shuffled(s)), g) for _ in range(SHUFFLES)]
    print(f"\ngames with both sides' terms: {real.height} (weeks 4+, 2006-2024); with Elo's forecast: {real['miss_elo'].is_not_null().sum()} (2016-2024)")
    print("\n== 1-2. The matchup term (home offense's interaction prediction less the away offense's) against the margin's miss")
    for miss, label in (("miss_close", "the close"), ("miss_elo", "Elo")):
        rr = r(real["term"], real[miss])
        nn = np.array([r(n["term"], n[miss]) for n in nulls])
        q = real.drop_nulls([miss, "term"])
        b, t = ols_t(q[miss].to_numpy(), [q["term"].to_numpy()])
        print(f"   against {label:<9}: r {rr:+.3f}; shuffled opponents mean {nn.mean():+.3f}, 95th {np.quantile(nn, 0.95):+.3f}; at or above the real r {np.mean(nn >= rr):.1%}. "
              f"Slope {b[1]:+.1f} points per EPA per play of term (t {t[1]:.1f}); the term's sd {q['term'].std():.4f}, so 1 sd = {b[1] * q['term'].std():+.2f} points")
    both = (c("p_home") != 0) & (c("p_away") != 0)
    q = real.filter(both)
    nn = np.array([r(n.filter(both)["term"], n.filter(both)["miss_close"]) for n in nulls])
    rr = r(q["term"], q["miss_close"])
    print(f"   only games where both sides have 3+ earlier regime games ({q.height}): against the close r {rr:+.3f}, shuffled 95th {np.quantile(nn, 0.95):+.3f}, at or above {np.mean(nn >= rr):.1%}")
    print("\n   by era (against the close):")
    for lo, hi in ((2006, 2017), (2018, 2024)):
        q = real.filter(c("season").is_between(lo, hi))
        nn = np.array([r(n.filter(c("season").is_between(lo, hi))["term"], n.filter(c("season").is_between(lo, hi))["miss_close"]) for n in nulls])
        rr = r(q["term"], q["miss_close"])
        print(f"   {lo}-{hi} ({q.height} games{', with coverage' if lo == 2018 else ', play-by-play tendencies only'}): r {rr:+.3f}, shuffled 95th {np.quantile(nn, 0.95):+.3f}, at or above {np.mean(nn >= rr):.1%}")

    print("\n== 3. Where the term is largest: mean miss against the close by the term's quintile (points)")
    q = real.drop_nulls(["miss_close"]).with_columns(band=(c("term").rank("ordinal") * 5 // (pl.len() + 1)).cast(pl.Int32))
    print(q.group_by("band").agg(n=pl.len(), term=c("term").mean(), miss_close=c("miss_close").mean(), home_cover=(c("miss_close") > 0).mean()).sort("term"))


if __name__ == "__main__":
    main()
