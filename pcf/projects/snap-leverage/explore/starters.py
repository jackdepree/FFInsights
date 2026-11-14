"""snap-leverage exploration (2026-11-14): H46, "the starters are trusted more than nonstarters".

Among player-games with a similar snap share, do depth-chart starters (listed first at their spot
that week) play a larger share of the high-stakes snaps than their snap share, and non-starters a
smaller one? Both the raw trust gap and trust over expected (step 2), by snap-share band and by
position group, with 90% intervals from resampling weeks. 2016-2024 regular season, games with 5+
high-stakes plays on the player's side.
Writes starters.txt. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/snap-leverage/explore/starters.py
"""

# ruff: noqa: E501
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

from pcf.config import get_config

c = pl.col
HERE = Path(__file__).parent
BANDS = [(0.1, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.01)]


def diff(d: pl.DataFrame, m: str, n: int = 500) -> str:
    """Starters' mean minus non-starters', resampling weeks."""
    w = d.with_columns(blk=pl.concat_str("season", "week", separator="-")).group_by("blk", "starter").agg(s=c(m).sum(), k=pl.len())
    blks = w["blk"].unique().to_list()
    idx = {b: i for i, b in enumerate(blks)}
    S = np.zeros((len(blks), 2))
    K = np.zeros((len(blks), 2))
    for r in w.iter_rows(named=True):
        S[idx[r["blk"]], int(r["starter"])] = r["s"]
        K[idx[r["blk"]], int(r["starter"])] = r["k"]
    rng = np.random.default_rng(0)
    i = rng.integers(0, len(blks), size=(n, len(blks)))
    est = S[:, 1].sum() / K[:, 1].sum() - S[:, 0].sum() / K[:, 0].sum()
    bs = S[i, 1].sum(1) / K[i, 1].sum(1) - S[i, 0].sum(1) / K[i, 0].sum(1)
    lo, hi = np.percentile(bs, [5, 95])
    return f"{est:+.4f} ({lo:+.4f} to {hi:+.4f})"


def main() -> None:
    lines: list[str] = []

    def say(t: str = "") -> None:
        print(t, flush=True)
        lines.append(t)

    pg = pl.read_parquet(get_config().zone("interim") / "snap-leverage" / "player_game.parquet")
    pg = pg.filter(c("group").is_not_null() & (c("t_hi") >= 5))
    say("H46: starters against non-starters with a similar snap share. Mean trust gap (high-stakes share")
    say("minus snap share) and trust over expected, starters minus non-starters, 90% interval (weeks).")
    say("band | starters | non-starters | starters' gap | non-starters' gap | difference in gap | difference in trust over expected")
    for lo, hi in BANDS:
        b = pg.filter(c("snap_share").is_between(lo, hi, closed="left"))
        s, n = b.filter(c("starter")), b.filter(~c("starter"))
        say(f"  {lo:.1f}-{min(hi, 1):.1f} | {s.height:,} | {n.height:,} | {s['trust_gap'].mean():+.4f} | {n['trust_gap'].mean():+.4f} | {diff(b, 'trust_gap')} | {diff(b, 'trust_oe')}")
    say("")
    say("By position group, snap share 30-90% (where both kinds are common): difference in gap | in trust over expected")
    for g in ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "CB", "S"]:
        b = pg.filter((c("group") == g) & c("snap_share").is_between(0.3, 0.9))
        if b.filter(c("starter")).height < 100 or b.filter(~c("starter")).height < 100:
            say(f"  {g:2s} too few of one kind ({b.filter(c('starter')).height} starters, {b.filter(~c('starter')).height} others)")
            continue
        say(f"  {g:2s} ({b.filter(c('starter')).height:,} / {b.filter(~c('starter')).height:,}) {diff(b, 'trust_gap')} | {diff(b, 'trust_oe')}")
    say("")
    say("All player-games: starters' and non-starters' share of the high-stakes snaps against their snap share")
    for k, nm in ((True, "starters"), (False, "non-starters")):
        a = pg.filter(c("starter") == k)
        say(f"  {nm}: snap share {a['snap_share'].mean():.3f}, high-stakes share {a['hi_share'].mean():.3f}, trust over expected {a['trust_oe'].mean():+.4f}")
    (HERE / "starters.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
