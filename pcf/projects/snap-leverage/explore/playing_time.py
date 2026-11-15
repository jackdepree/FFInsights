"""snap-leverage exploration (2026-11-14), step 3: the main test (H45) and H47's comparison.

Does a player's high-stakes use predict his future playing time beyond his plain snap share?

Rows: every rostered player-game, regular season 2016-2024, QB through S (kickers, punters and
long snappers left out). His snap share is 0 in a game he didn't play. After each game, features
from his games so far that season (season to date and the last 3):
- plain: last game's snap share, the last 3's mean, season to date, games so far, position group;
- leverage: the same windows of leverage share, high-stakes share, trust gap, trust over expected
  (step 2; part of the plain model plus each, and all together).
Targets: (1) his mean snap share over his next 3 games that season; (2) his mean snap share next
season (rows from the last game of a season).
Walk-forward by season: each season 2018-2024 scored by models fitted on 2016 to the season
before (gradient-boosted trees, as participation's champion; a linear check beside it). Gain =
the share of the plain model's squared error removed, 90% interval from resampling weeks (target
2: resampling teams). Groups: everyone; part-timers (last 3 at 10-90%); first-year players.
Writes playing_time.txt. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/snap-leverage/explore/playing_time.py
"""

# ruff: noqa: E501
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge

from pcf.config import get_config
from pcf.data.tables.store import read_part

c = pl.col
HERE = Path(__file__).parent
SEASONS = list(range(2016, 2025))
SCORED = list(range(2018, 2025))
ROSTER_GROUP = {"QB": "QB", "RB": "RB", "WR": "WR", "TE": "TE", "OL": "OL", "DL": "DL", "LB": "LB", "DB": "DB"}
SIDE = {"QB": "offense", "RB": "offense", "WR": "offense", "TE": "offense", "OL": "offense", "DL": "defense", "LB": "defense", "DB": "defense"}
LEV = ["lev_share", "hi_share", "trust_gap", "trust_oe"]


def rows() -> pl.DataFrame:
    zone = get_config().zone("interim") / "snap-leverage"
    pg = pl.read_parquet(zone / "player_game.parquet")
    sched = read_part("team_game", "schedule", seasons=SEASONS).select("game_id", "team", "game_type").collect()
    r = (
        read_part("player_game", "roster", seasons=SEASONS)
        .select("gsis_id", "game_id", "season", "week", "team", "position", "years_exp", "rookie_year")
        .collect()
        .join(sched, on=["game_id", "team"])
        .filter(c("game_type") == "REG")
        .with_columns(rgroup=c("position").replace_strict(ROSTER_GROUP, default=None))
        .filter(c("rgroup").is_not_null())
        .unique(["gsis_id", "game_id"])
    )
    r = r.with_columns(side=c("rgroup").replace_strict(SIDE))
    x = r.join(pg.select("gsis_id", "game_id", "side", "group", "snap_share", "t_hi", *LEV), on=["gsis_id", "game_id", "side"], how="left")
    # a game he didn't play: no snaps, no high-stakes snaps; the trust measures stay empty
    x = x.with_columns(
        c("snap_share", "lev_share", "hi_share").fill_null(0.0),
        played=c("group").is_not_null(),
        first_year=(c("season") == c("rookie_year")).fill_null(False),
        g=c("rgroup").cast(pl.Categorical).to_physical(),
    ).sort("gsis_id", "season", "week")
    k = ["gsis_id", "season"]
    feats = []
    for m in ["snap_share", *LEV]:
        x = x.with_columns(
            c(m).alias(f"{m}_last"),
            c(m).rolling_mean(3, min_samples=1).over(k).alias(f"{m}_l3"),
            (c(m).cum_sum().over(k) / c(m).cum_count().over(k)).alias(f"{m}_std") if m in ("snap_share", "lev_share", "hi_share")
            else c(m).fill_null(strategy="forward").over(k).alias(f"{m}_ffill"),
        )
        feats += [f"{m}_last", f"{m}_l3"]
        feats += [f"{m}_std"] if m in ("snap_share", "lev_share", "hi_share") else []
    # trust measures: season-to-date means over games he played (nulls skipped)
    for m in ("trust_gap", "trust_oe"):
        x = x.with_columns((c(m).fill_null(0).cum_sum().over(k) / c(m).is_not_null().cum_sum().over(k).clip(1, None)).alias(f"{m}_std"))
    x = x.with_columns(n_games=pl.int_range(1, pl.len() + 1).over(k))
    x = x.with_columns(
        y3=pl.mean_horizontal(*[c("snap_share").shift(-i).over(k) for i in (1, 2, 3)]),
    )
    return x


PLAIN = ["snap_share_last", "snap_share_l3", "snap_share_std", "n_games", "g", "first_year"]
SETS = {
    "plain": PLAIN,
    "+ leverage share": PLAIN + ["lev_share_last", "lev_share_l3", "lev_share_std"],
    "+ high-stakes share": PLAIN + ["hi_share_last", "hi_share_l3", "hi_share_std"],
    "+ trust gap (raw)": PLAIN + ["trust_gap_last", "trust_gap_l3", "trust_gap_std"],
    "+ trust over expected": PLAIN + ["trust_oe_last", "trust_oe_l3", "trust_oe_std"],
    "+ all four": PLAIN + [f"{m}_{w}" for m in LEV for w in ("last", "l3", "std")],
}


def fit_predict(tr: pl.DataFrame, te: pl.DataFrame, cols: list[str], y: str, kind: str) -> np.ndarray:
    a = tr.select(cols).to_numpy().astype(float)
    b = te.select(cols).to_numpy().astype(float)
    if kind == "trees":
        m = HistGradientBoostingRegressor(max_iter=250, learning_rate=0.06, max_leaf_nodes=31, min_samples_leaf=100, random_state=0)
        m.fit(a, tr[y].to_numpy())
        return np.clip(m.predict(b), 0, 1)
    a, b = np.nan_to_num(a), np.nan_to_num(b)
    mu, sd = a.mean(0), a.std(0) + 1e-9
    m = Ridge(alpha=1.0).fit((a - mu) / sd, tr[y].to_numpy())
    return np.clip(m.predict((b - mu) / sd), 0, 1)


def gain(d: pl.DataFrame, base: str, alt: str, y: str, block: str, n: int = 500) -> str:
    e = d.with_columns(eb=(c(y) - c(base)) ** 2, ea=(c(y) - c(alt)) ** 2).group_by(block).agg(c("eb").sum(), c("ea").sum())
    eb, ea = e["eb"].to_numpy(), e["ea"].to_numpy()
    rng = np.random.default_rng(0)
    i = rng.integers(0, len(eb), size=(n, len(eb)))
    g = 1 - ea[i].sum(1) / eb[i].sum(1)
    lo, hi = np.percentile(g, [5, 95])
    return f"{1 - ea.sum() / eb.sum():+.2%} ({lo:+.2%} to {hi:+.2%})"


def main() -> None:
    lines: list[str] = []

    def say(t: str = "") -> None:
        print(t, flush=True)
        lines.append(t)

    x = rows()
    say(f"Rostered player-games, 2016-2024 regular season: {x.height:,}; played {x['played'].mean():.1%}")
    # target 1: next 3 games
    d = x.filter(c("y3").is_not_null())
    say("")
    say("1. Next 3 games' snap share. Share of the plain model's squared error removed (+ = better), 2018-2024, 90% interval")
    for kind in ("trees", "linear"):
        preds = {nm: [] for nm in SETS}
        parts = []
        for s in SCORED:
            tr, te = d.filter(c("season") < s), d.filter(c("season") == s)
            for nm, cols in SETS.items():
                preds[nm].append(fit_predict(tr, te, cols, "y3", kind))
            parts.append(te.select("season", "week", "team", "gsis_id", "rgroup", "y3", "snap_share_l3", "first_year", "n_games"))
        sc = pl.concat(parts).with_columns(**{nm: pl.Series(np.concatenate(v)) for nm, v in preds.items()}).with_columns(blk=pl.concat_str("season", "week", separator="-"))
        base_mse = sc.select(((c("y3") - c("plain")) ** 2).mean()).item()
        say(f"  {kind}: plain model's mean squared miss {base_mse:.4f} ({sc.height:,} rows)")
        groups = [("everyone", pl.lit(True)), ("part-timers (last 3 at 10-90%)", c("snap_share_l3").is_between(0.1, 0.9)),
                  ("first-year players", c("first_year")), ("weeks 1-4 of his season", c("n_games") <= 4)]
        for gn, gx in groups:
            sub = sc.filter(gx)
            say(f"    {gn} ({sub.height:,}):")
            for nm in list(SETS)[1:]:
                say(f"      {nm:24s} {gain(sub, 'plain', nm, 'y3', 'blk')}")
        if kind == "trees":
            say("    by position group (trees, + all four):")
            for g in ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB"]:
                sub = sc.filter(c("rgroup") == g)
                pt = sub.filter(c("snap_share_l3").is_between(0.1, 0.9))
                say(f"      {g:2s} everyone {gain(sub, 'plain', '+ all four', 'y3', 'blk')} | part-timers {gain(pt, 'plain', '+ all four', 'y3', 'blk')}")
    # target 2: next season
    say("")
    say("2. Next season's snap share, from the season so far (last game's row). Same comparisons, trees, resampling teams")
    last = x.filter(c("n_games") == c("n_games").max().over("gsis_id", "season"))
    nxt = x.group_by("gsis_id", "season").agg(y_next=c("snap_share").mean()).with_columns(c("season") - 1)
    d2 = last.join(nxt, on=["gsis_id", "season"])
    say(f"  rows {d2.height:,} (players rostered in both seasons; a player who leaves the league drops out)")
    preds = {nm: [] for nm in SETS}
    parts = []
    for s in [t - 1 for t in SCORED if t - 1 >= 2017]:
        tr, te = d2.filter(c("season") < s), d2.filter(c("season") == s)
        for nm, cols in SETS.items():
            preds[nm].append(fit_predict(tr, te, cols, "y_next", "trees"))
        parts.append(te.select("season", "team", "gsis_id", "rgroup", "y_next", "snap_share_l3", "first_year"))
    sc = pl.concat(parts).with_columns(**{nm: pl.Series(np.concatenate(v)) for nm, v in preds.items()})
    for gn, gx in (("everyone", pl.lit(True)), ("part-timers", c("snap_share_l3").is_between(0.1, 0.9)), ("first-year players", c("first_year"))):
        sub = sc.filter(gx)
        say(f"    {gn} ({sub.height:,}):")
        for nm in list(SETS)[1:]:
            say(f"      {nm:24s} {gain(sub, 'plain', nm, 'y_next', 'team')}")
    # H47: how far the situation moves the rankings
    say("")
    say("H47. Raw trust gap against trust over expected, player-seasons with 8+ games at 10-90% snap share:")
    ps = x.filter(c("played") & c("snap_share").is_between(0.1, 0.9)).group_by("gsis_id", "season", "rgroup").agg(
        c("trust_gap").mean(), c("trust_oe").mean(), n=pl.len()).filter(c("n") >= 8)
    for g in ["RB", "WR", "TE", "DL", "LB", "DB"]:
        a = ps.filter(c("rgroup") == g)
        rho = a.select(pl.corr("trust_gap", "trust_oe", method="spearman")).item()
        say(f"  {g:2s} {a.height:5,} player-seasons: rank correlation {rho:.2f}")
    (HERE / "playing_time.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
