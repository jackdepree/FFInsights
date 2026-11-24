"""The touchdown expert (`td-expert` project): how many touchdowns a player or a team should
expect, how sure that is, and how much of what was scored so far was the chances and how much was
luck (brief: projects/td-expert/BRIEF.md; plan: BUILD.md; decision 0043).

- **The facts** are table parts, built with the tables (`pcf.data.tables.touchdowns`): `play.xtd`
  (each chance's expected touchdowns, thrown ones by their passer), `drive.td_chance` (the drive
  model's chances and near misses), `player_game.touchdowns` and `team_game.touchdowns` (sums,
  the dice's spread, the luck measure, the drive-aware hindsight).
- **The forecasts** (`model`, `horizons`): touchdowns next game and over the rest of the regular
  season, for players (rushing and receiving: QB, RB, WR, TE), quarterbacks' thrown touchdowns,
  and teams; each by method B (`volume`: a count model on volume) and method A (`chances`: next
  game's expected touchdowns forecast from his chances, times small corrections), beside rung 0
  (`rate`: the season touchdown rate). They are count forecasts (the harness's `count` kind):
  the chance of 0, 1, 2+ is a Poisson count around the mean.
- **The regression measure** (`regression`): touchdowns over expected so far and the share kept
  afterwards, by position, against keeping all and keeping none.
- `checks` and `run` hold the build's own checks (calibration of the facts, the ceilings,
  consistency, the CEO's hunches, I58, I61, A against B).
"""
