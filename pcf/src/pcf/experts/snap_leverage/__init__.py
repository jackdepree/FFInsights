"""Snap leverage (`snap-leverage`; brief: projects/snap-leverage/BRIEF.md, agreed 2026-11-14;
decision 0033). Every snap a player was on, weighted by its leverage before the snap (the CEO's
"variance of winning percent added per play based on conditions/situations", `play.leverage`),
from participation-live's morning-after map, so it runs in season.

- `usage`: per player-game leverage share, the passing-down role gap and trust over expected.
- `features`: the rows at a moment (plain snap share, then the leverage measures) and the targets.
- `model`: nine variants, {`lev_next3`, `lev_rest`, `snap_next3`} × {`plain`, `lev`, `full`}.

Validated with `pcf backtest snap-leverage --variant <name> --refit season --shuffles 20`.
"""
