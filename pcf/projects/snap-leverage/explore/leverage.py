"""snap-leverage exploration (2026-11-14), step 1: leverage for every scrimmage play.

Leverage (the CEO's "variance of winning percent added per play based on conditions/
situations") is how much the win chance can swing on a play, from the situation before the snap
alone: quarter, clock, score margin, down, distance, field position, both teams' timeouts and the
win chance going in. It's the spread of WPA among plays like it: a gradient-boosted model of WPA
squared, its square root, fitted walk-forward (each season 2016-2024 on 2006 to the season before).
The leverage index (li) divides by the training plays' mean, so 1.0 is an average snap.

Rung 0, the simple version: 4th quarter with the score within 8 points (one score).

Regular-season passes, runs, kneels and spikes (2-point tries left out); never the 2025 vault.
Writes `<interim>/snap-leverage/plays.parquet` and leverage.txt. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/snap-leverage/explore/leverage.py
"""

# ruff: noqa: E501
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingRegressor

from pcf.config import get_config
from pcf.data.clean import standard
from pcf.data.tables.store import read_part

c = pl.col
HERE = Path(__file__).parent
SEASONS = range(2006, 2025)
SCORED = range(2016, 2025)
COLS = [
    "game_id", "play_id", "season", "week", "season_type", "posteam", "defteam", "home_team",
    "away_team", "down", "ydstogo", "yardline_100", "qtr", "half_seconds_remaining",
    "game_seconds_remaining", "score_differential", "posteam_timeouts_remaining",
    "defteam_timeouts_remaining", "wp", "epa", "wpa", "pass", "rush", "play_type",
    "two_point_attempt", "passer_player_id", "rusher_player_id", "receiver_player_id",
    "pass_defense_1_player_id", "pass_defense_2_player_id", "interception_player_id",
    "sack_player_id", "half_sack_1_player_id", "solo_tackle_1_player_id",
    "assist_tackle_1_player_id", "tackle_with_assist_1_player_id", "qb_hit_1_player_id",
]
X = ["qtr", "game_seconds_remaining", "half_seconds_remaining", "score_differential", "down",
     "ydstogo", "yardline_100", "posteam_timeouts_remaining", "defteam_timeouts_remaining", "wp"]


def main() -> None:
    lines: list[str] = []

    def say(t: str = "") -> None:
        print(t, flush=True)
        lines.append(t)

    p = (
        read_part("play", "pbp", seasons=list(SEASONS))
        .select(COLS)
        .filter(
            (c("season_type") == "REG")
            & c("play_type").is_in(["pass", "run", "qb_kneel", "qb_spike"])
            & (c("two_point_attempt").fill_null(0) == 0)
            & c("wpa").is_not_null() & ~c("wpa").is_nan()
            & c("wp").is_not_null() & ~c("wp").is_nan()
        )
        .collect()
    )
    for t in ("posteam", "defteam", "home_team", "away_team"):
        p = standard.standard_teams(p, t)
    p = p.with_columns(c("down").fill_null(0), rung0=((c("qtr") >= 4) & (c("score_differential").abs() <= 8)).cast(pl.Int8))
    parts = []
    say("Leverage: the spread of WPA a play's situation allows, before the snap, walk-forward.")
    say("Held-out season | train | corr(leverage, |WPA|) | corr(rung 0, |WPA|) | WPA^2 explained: leverage, rung 0")
    for s in SCORED:
        tr = p.filter(c("season") < s)
        te = p.filter(c("season") == s)
        m = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.08, max_leaf_nodes=63, min_samples_leaf=200, random_state=0)
        m.fit(tr.select(X).to_numpy().astype(float), (tr["wpa"] ** 2).to_numpy())
        base = float(np.sqrt(np.clip(m.predict(tr.select(X).to_numpy().astype(float)), 1e-8, None)).mean())
        lev = np.sqrt(np.clip(m.predict(te.select(X).to_numpy().astype(float)), 1e-8, None))
        te = te.with_columns(lev=pl.Series(lev), li=pl.Series(lev / base))
        a = te["wpa"].abs().to_numpy()
        y2 = (te["wpa"] ** 2).to_numpy()
        r_l = np.corrcoef(lev, a)[0, 1]
        r_0 = np.corrcoef(te["rung0"].to_numpy(), a)[0, 1]
        e_l = 1 - np.mean((y2 - lev**2) ** 2) / np.var(y2)
        g0 = te.group_by("rung0").agg(m2=(c("wpa") ** 2).mean())
        f0 = te.join(g0, on="rung0")["m2"].to_numpy()
        e_0 = 1 - np.mean((y2 - f0) ** 2) / np.var(y2)
        say(f"  {s} | {tr['season'].min()}-{s - 1} | {r_l:.3f} | {r_0:.3f} | {e_l:.3f}, {e_0:.3f}")
        parts.append(te)
    q = pl.concat(parts)
    q = q.with_columns(
        hi=(c("li") >= c("li").quantile(0.8).over("season")).cast(pl.Int8),
        decile=(c("li").rank("ordinal").over("season") * 10 / (pl.len().over("season") + 1)).floor().cast(pl.Int8) + 1,
    )
    say("")
    say("Calibration, 2016-2024: by leverage decile, the predicted spread of WPA against the realised one")
    say("decile | mean li | predicted sd | realised rms WPA | share 4th qtr | share one-score | pass share")
    t = q.group_by("decile").agg(
        c("li").mean(), c("lev").mean(), rms=(c("wpa") ** 2).mean().sqrt(), q4=(c("qtr") >= 4).mean(),
        close=(c("score_differential").abs() <= 8).mean(), pas=c("pass").mean(),
    ).sort("decile")
    for r in t.iter_rows(named=True):
        say(f"  {r['decile']:2d} | {r['li']:.2f} | {r['lev']:.4f} | {r['rms']:.4f} | {r['q4']:.2f} | {r['close']:.2f} | {r['pas']:.2f}")
    hi = q.filter(c("hi") == 1)
    say("")
    say(f"High stakes = the top fifth of each season's plays by leverage (li >= {q.filter(c('hi') == 1)['li'].min():.2f}).")
    say(f"  They hold {hi.select((c('wpa') ** 2).sum()).item() / q.select((c('wpa') ** 2).sum()).item():.1%} of all WPA^2 (the swing), and are")
    say(f"  {hi['qtr'].ge(4).mean():.1%} 4th-quarter, {(hi['score_differential'].abs() <= 8).mean():.1%} one-score, {hi['pass'].mean():.1%} passes; rung 0 agrees on {(hi['rung0'] == 1).mean():.1%} of them.")
    lead = hi.filter(c("score_differential") > 0)
    say(f"  Leading offenses run {lead['rush'].mean():.1%} of their high-stakes plays; trailing ones {hi.filter(c('score_differential') < 0)['rush'].mean():.1%}; tied {hi.filter(c('score_differential') == 0)['rush'].mean():.1%}.")
    say(f"  Share of high-stakes plays that are a leading team's runs (H47's clock-draining runs): {((hi['score_differential'] > 0) & (hi['rush'] == 1)).mean():.1%}")
    xp = read_part("play", "pace", seasons=list(SCORED)).select("game_id", "play_id", "pcf_xpass").collect()
    q = q.join(xp, on=["game_id", "play_id"], how="left")
    say(f"  Expected pass chance (pace's pcf_xpass) known on {q['pcf_xpass'].is_not_null().mean():.1%} of plays.")
    out = get_config().zone("interim") / "snap-leverage"
    out.mkdir(parents=True, exist_ok=True)
    q.write_parquet(out / "plays.parquet")
    say(f"Plays written: {q.height:,} (2016-2024).")
    (HERE / "leverage.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
