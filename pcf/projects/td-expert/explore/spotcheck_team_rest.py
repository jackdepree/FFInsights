"""Spot-check 3 (the CEO, 2026-11-24): teams' rest of season, B (volume) shipped over A (chances).
The rules are in spotcheck_team_rest.md, committed before this ran. Reads the saved walks
(2016-2024) and, for the QB lens, the player_game table through the gateway.

Run: python -m ... (from pcf/) .venv/Scripts/python.exe projects/td-expert/explore/spotcheck_team_rest.py
"""
from pathlib import Path

import numpy as np
import polars as pl

from pcf.data.gateway import END_OF_TIME, Gateway
from pcf.experts.td_expert.checks import gain, gain_line, pct
from pcf.experts.td_expert.run import cache_dir, saved_dir
from pcf.validation import backtest

c = pl.col
KEYS = ["game_id", "team"]
OUT = Path(__file__).with_suffix(".txt")

d = cache_dir()
rate, vol, ch = (pl.read_parquet(d / f"walk_team_rest_{r}.parquet") for r in ("rate", "volume", "chances"))
feats, _ = backtest.load_features(saved_dir("team", "rest", ""))
f = feats.select(*KEYS, "games_left", "games_played", "xtd_s", "td_s").unique(KEYS)

# the starting QB of every team-game (most throws), and whether the window's QBs differ from its first
view = Gateway().view(END_OF_TIME, "in_season", {"player_game": ("touchdowns",)})
pg = view.table("player_game", seasons=range(2016, 2025)).filter(c("tdx_throws").fill_null(0) > 0)
qb = (pg.filter(c("position") == "QB").sort("tdx_throws", descending=True)
      .unique(["game_id", "team"], keep="first").select("game_id", "team", "season", "week", qb="gsis_id"))


def windows(rows: pl.DataFrame) -> pl.DataFrame:
    """For each window (its first game, team): the share of its games started by another QB."""
    w = rows.select(*KEYS).with_columns(season=c("game_id").str.slice(0, 4).cast(pl.Int32),
                                        start=c("game_id").str.slice(5, 2).cast(pl.Int32))
    first = w.join(qb.select(*KEYS, first_qb="qb"), on=KEYS, how="left")
    games = first.join(qb.select("team", "season", "week", "qb"), on=["team", "season"])
    games = games.filter((c("week") >= c("start")) & (c("week") <= 18))
    return games.group_by(KEYS).agg(
        other=(c("qb") != c("first_qb")).mean(), start=c("start").first(), season=c("season").first()
    )


win = windows(vol)
lines = ["Spot-check 3: teams' rest of season, B (volume) against A (chances), 2016-2024",
         "(Poisson log loss share; positive: the first better; 90% by week blocks)", ""]
lines.append(gain_line("A against B", gain(ch, vol, KEYS)))
lines.append(gain_line("B against rung 0", gain(vol, rate, KEYS)))
lines.append(gain_line("A against rung 0", gain(ch, rate, KEYS)))

lines += ["", "By season (A against B; B against rung 0; A against rung 0):"]
a_wins = b_wins = 0
for s in range(2016, 2025):
    sel = lambda p: p.filter(c("season") == s)  # noqa: E731
    ab, br, ar = gain(sel(ch), sel(vol), KEYS), gain(sel(vol), sel(rate), KEYS), gain(sel(ch), sel(rate), KEYS)
    a_wins += ab["loss"][0] > 0
    b_wins += ab["loss"][0] <= 0
    lines.append(f"  {s}: A-B {pct(ab['loss'][0])} ({pct(ab['loss'][1])} to {pct(ab['loss'][2])}); "
                 f"B-rate {pct(br['loss'][0])}; A-rate {pct(ar['loss'][0])}; {ab['rows']} windows")
lines.append(f"  A ahead in {a_wins} of 9 seasons, B ahead or level in {b_wins}")


def lens(label, keep):
    ks = win.filter(keep).select(KEYS)
    a, b = ch.join(ks, on=KEYS, how="semi"), vol.join(ks, on=KEYS, how="semi")
    return gain_line(label, gain(a, b, KEYS))


lines += ["", "Lenses (A against B):"]
lines.append(lens("window starts weeks 1-6", c("start") <= 6))
lines.append(lens("window starts weeks 7-12", (c("start") >= 7) & (c("start") <= 12)))
lines.append(lens("window starts week 13+", c("start") >= 13))
lines.append(lens("same QB starts every game", c("other") == 0))
lines.append(lens("another QB starts some games", c("other") > 0))
lines.append(lens("another QB starts a quarter or more", c("other") >= 0.25))
lines.append(f"  (windows with another QB starting some games: {win.filter(c('other') > 0).height:,} "
             f"of {win.height:,})")
fx = f.with_columns(xtd_g=c("xtd_s") / c("games_played").clip(1))
for name, p in (("hot start (top fifth of xtd a game so far)", 0.8), ("cold start (bottom fifth)", 0.2)):
    q = fx.filter(c("games_played") >= 3)["xtd_g"].quantile(p)
    keep = (c("xtd_g") >= q) if p > 0.5 else (c("xtd_g") <= q)
    ks = fx.filter((c("games_played") >= 3) & keep).select(KEYS)
    a, b = ch.join(ks, on=KEYS, how="semi"), vol.join(ks, on=KEYS, how="semi")
    lines.append(gain_line(name, gain(a, b, KEYS)))

lines += ["", "Calibration of the mean, by fifths of each forecast (said, scored, touchdowns over the window):"]
for name, p in (("B", vol), ("A", ch)):
    q = p.with_columns(fifth=(c("mean").rank("ordinal") * 5 / (pl.len() + 1)).floor().cast(pl.Int32))
    g = q.group_by("fifth").agg(said=c("mean").mean(), got=c("y").mean()).sort("fifth")
    lines.append(f"  {name}: " + "; ".join(f"{r['said']:.1f}/{r['got']:.1f}" for r in g.iter_rows(named=True)))
    lines.append(f"     overall said {p['mean'].mean():.2f}, scored {p['y'].mean():.2f}")

# per-window difference, where it comes from: the share of A's extra loss from the 10% worst windows
j = ch.select(*KEYS, la="loss").join(vol.select(*KEYS, lb="loss"), on=KEYS)
diff = (j["la"] - j["lb"]).to_numpy()
top = np.sort(diff)[::-1]
lines += ["", f"Per window, A's loss minus B's: mean {diff.mean():+.4f}; A worse in {np.mean(diff > 0):.0%} of windows; "
          f"the worst 10% for A carry {top[: len(top) // 10].sum() / max(diff.sum(), 1e-9):.0%} of the net (net {diff.sum():+.2f})"]

OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
