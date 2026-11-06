"""Participation (`participation` project): each rostered skill player's share of their team's
offensive snaps, predicted before kickoff (brief: projects/participation/BRIEF.md). Variants are
validated with `pcf backtest participation --variant <name>`.

| Variant | What | Rung |
|---|---|---|
| `last_game` | Last game's share, 0 if inactive | 0 |
| `last3` | The last 3 games' average, an absence counting as 0 | 0 |
| `last3_active` | The last 3 games the player was active (F9) | 0 |
| `lasso` | Two parts: a logistic model for taking a snap, a lasso for the share | 1 |
| `trees`, `trees_career` | Two parts with boosted trees, without and with career share | 2 |
| `trees_status` | `trees`, with separate residuals for players on the injury report | 2 |
| `trees_spikes` | `trees_status`, plus the chance of every snap where that's common (QBs) | 2 |
| `trees_top` | `trees_spikes`, non-every-snap games kept below 100%, that chance recalibrated | 2 |
| `trees_week` | `trees_top`, plus the week of the season and the last week times win rate | 2 |
| `active` | The chance of being on the active list (trees) | n/a |
| `season_h3`, `lasso_h3`, `trees_h3` | Average share over the next 3 team games | 0, 1, 2 |
| `season_rest`, `lasso_rest`, `trees_rest` | Average share over the rest of the season | 0, 1, 2 |
"""
