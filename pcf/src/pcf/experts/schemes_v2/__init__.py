"""Schemes v2 (`schemes-v2` project), first build: **traits** (brief: projects/schemes-v2/BRIEF.md,
CEO direction 2026-11-09). Each team's tendency in its next game, predicted before kickoff from
its own earlier games. Variants are validated with `pcf backtest schemes-v2 --variant <name>`.

One set of variants per trait (`pass_oe`, `shotgun`, `tempo`, `depth`):

| Variant | What | Rung |
|---|---|---|
| `<trait>_league` | The league's average over the last two seasons | 0 |
| `<trait>_last4` | The team's last 4 games | 0 |
| `<trait>_season` | The team's season to date (last season's before its first game) | 0 |
| `<trait>_shrunk` | A fitted blend: shrunk season, last 4 games, last season, coach history | 1 |
"""
