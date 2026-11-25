"""The availability expert (`availability` project): who plays, and for how many games, for
players and teams (brief: projects/availability/BRIEF.md; plan: BUILD.md; decision 0047).

- **The tables** (`pcf.data.tables.availability`): `roster_week` (the 53-man roster and the
  health reserve lists, per team-game) and `player_game.injured` (named in-game injuries).
- **The record** (`common`): each player's game-by-game health, with the health absence and the
  state (healthy, listed, out, reserve, off).
- **The forecasts** (`experts`, `models`): the chance of a health absence next game; games of
  health absence over the next 3 and the rest of the season by three methods (two models, a
  health-state chain, a hidden health state) beside rung 0; the chance he's active beside
  participation's; his share when he plays listed.
- **The measures** (`measures`): proneness and the snap-weighted adjusted games lost.
- `checks` and `run` hold the build's own checks and its runner.
"""
