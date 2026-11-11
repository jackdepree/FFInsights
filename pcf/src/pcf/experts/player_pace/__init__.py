"""Player pace, in season (`player-pace`; brief: projects/player-pace/BRIEF.md, agreed
2026-11-11; decision 0029). Each team's next-game pass rate over expected, pace over expected
and volume, from team pace's features plus the players expected to play: the expected starting
QB's own history, a change of starter, a rookie, and the pass lean of skill players ruled out.
Its retrospective twin is `player-pace-retro`. Validated with
`pcf backtest player-pace --variant <name>`.

| Variants | What | Rung |
|---|---|---|
| `<habit>_team` | The team's own history only (the like-for-like yardstick) | 1 |
| `<habit>_qb` | Plus the expected starting QB | 1 |
| `proe_lineup` | `proe_qb` plus who's ruled out | 1 |
| `<volume>_qb` | Team pace's `<volume>_full` plus the expected QB | 1 |

Habits: `proe`, `pace_oe`. Volume: `plays`, `dropbacks`, `runs`. The QB columns are published
with the walk-forward history for higher layers.
"""
