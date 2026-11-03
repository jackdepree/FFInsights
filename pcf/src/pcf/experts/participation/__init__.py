"""Participation (`participation` project): each rostered skill player's share of their team's
offensive snaps, predicted before kickoff (brief: projects/participation/BRIEF.md). Variants are
validated with `pcf backtest participation --variant <name>`.

| Variant | What | Rung |
|---|---|---|
| `last_game` | Last game's share, 0 if inactive | 0 |
| `last3` | The last 3 games' average, an absence counting as 0 | 0 |
| `last3_active` | The last 3 games the player was active (F9) | 0 |
"""
