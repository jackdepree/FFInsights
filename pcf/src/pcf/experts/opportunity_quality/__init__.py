"""Opportunity quality (`opportunity-quality` project): what a player's targets and carries were
worth from where they happened, how much of what he did with them lasts, and a forecast of the work
he'll get (brief: projects/opportunity-quality/BRIEF.md; decision 0041).

- **The facts** are table parts, built with the tables: `play.xfp` (each chance's expected catch,
  yards and touchdown, from models fit on earlier seasons) and `player_game.opportunity` (each
  player-game's chances summed). `common` turns them into points in any scoring.
- **The forecast of opportunity** (`model`, `horizons`): next game's expected points (a spike
  forecast), and the average over the next 3 games and the rest of the season. Validated with
  `pcf backtest opportunity-quality --variant <name>`.
- **The regression measure** (`regression`): each player's points over expected per chance, how
  much of it is kept (method A: one rate per position; method B: a rate per player from how many
  chances he's had), the range for his true level, and the chance the gap closes by half.
- `run` holds the build's own checks: the comparison with nflverse's expected points, the
  consistency entries, the regression measure's backtest, the no-noise test and the yardstick.
"""
