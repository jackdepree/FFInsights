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

Second build: **anti-traits** (CEO, 2026-11-09; `anti_model.py`, decision 0024). Each team's gain
from an option in its next game (EPA per play with it less without), for `pass` and `shotgun`
(live) and `man`, `two_high` and `blitz` (defenses, from finished seasons):
`<option>_gain_league`, `_season` (defenses `_last_season`), `_avoid` (the anti-trait: the
league's gain plus a weight on the team's use) and `_blend` (plus its past gains). **Retired**
(the CEO, 2026-11-10) after failing the vault: kept only so the findings can be rerun.

The retrospective traits (each team's charted traits per season) are a table, not a variant:
`team_season.charted` (decision 0026).
"""
