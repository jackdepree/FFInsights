"""Player pace, between seasons (`player-pace-retro`; brief: projects/player-pace/BRIEF.md, agreed
2026-11-11; decision 0029). Each player's plus-minus on his team's pass rate over expected and
pace over expected next season, forecast at the start of the season from his earlier seasons
(`player_season.on_field_pace`, from who was on the field on every play: post-season only).
Validated with `pcf backtest player-pace-retro --variant <name>`.

| Variants | What | Rung |
|---|---|---|
| `<m>_group` | His position group's average | 0 |
| `<m>_last` | His plus-minus last season | 0 |
| `<m>_shrunk` | Earlier seasons, decayed, shrunk toward his group, a slope per group | 1 |

Measures `<m>`: `proe` (on minus off the field, PCF's pass rate over expected), `proe_pers` (the
same within personnel groupings: exploration F4) and `pace` (pace over expected).
"""
