"""context-live: what should have happened on each play, from the situation and both sides' calls,
with nothing known about who the players or teams are (projects/context-live/BRIEF.md).

- `plays`: the play table (situation, call fields, schemes traits, outcomes) from gateway views.
- `outcomes`: the outcomes, each with its population (runs, dropbacks, pass attempts, snaps).
- `models`: one model per outcome and rung (base rate, linear, trees), means and ranges.
- `run`: the walk-forward backtest by season, the nulls, the history and MLflow (decision 0036).
- `context`: each player's and team's average context per game.
"""
