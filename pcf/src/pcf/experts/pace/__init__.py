"""Pace and play-calling (`pace` project; brief: projects/pace/BRIEF.md, agreed 2026-11-10). Each
team's habits and volume in its next game, predicted before kickoff from its own earlier games,
measured on every play against PCF's own expected pass chance and expected pace
(`team_game.pace`, decision 0028). Variants are validated with
`pcf backtest pace --variant <name>`.

| Variants | What | Rung |
|---|---|---|
| `<habit>_league`, `_last4`, `_season` | One average of the habit | 0 |
| `<habit>_shrunk` | schemes-v2's blend: shrunk season, last 4, last season, coach | 1 |
| `<volume>_league`, `_season`, `_last_season` | One average of the team's volume | 0 |
| `<volume>_neutral` | The usual way: history, the line, efficiency, neutral habits | 1 |
| `<volume>_full` | The same with the full-sample habits | 1 |

Habits: `pace_oe`, `proe`, `proe_1st`, `proe_2nd`, `proe_3rd`, `no_huddle`. Volume: `plays`,
`dropbacks`, `runs`. The per-play measures are the `play.pace` part, for the later `player-pace`.
"""
