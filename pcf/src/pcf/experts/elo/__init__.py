"""Team Elo (`elo` project): each team's strength in points before every game, and the game's
margin, total and win chance from it (brief: projects/elo/BRIEF.md; exploration rung 3).
Variants are validated with `pcf backtest elo --variant <name>`.

| Variant | Quantity | What |
|---|---|---|
| `margin` | `home_margin` | Margin Elo (step 0.06, half pull), home field, QB out, same team |
| `total` | `total_points` | Offense and defense ratings (step 0.05, one-third pull), plus H1 |
| `win` | `home_win` | A logistic curve on the margin's features |
| `*_simple` | the same | Rung 1, the yardstick: no QB or same-team adjustment |

Modules: `ratings.py` (the walk), `same_team.py` (H1), `features.py` (per moment and bulk),
`model.py` (the variants).
"""
