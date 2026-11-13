"""Opponent-adjusted efficiency (`team-efficiency` project; brief:
projects/team-efficiency/BRIEF.md, agreed 2026-11-13). Each offense's and defense's EPA per play,
with the situation and the opponents taken out, rated after every week from every play, and
forecast over its next 3 games and the rest of the season. Variants are validated with
`pcf backtest team-efficiency --variant <side>_<horizon>_<rung>`.

The ladder (`model.LADDER`): `league` (rung 0), `usual` (the garbage-time rule), `ridge` (every
play, rung 1), `dml` (DML with the game state, rung 2), `combo` (DML with the gap-aware
representativeness weights, rung 3). `off_next3_combo` publishes the ratings for higher layers.

Modules: `ratings.py` (the walk), `features.py` (per moment, bulk, and the targets), `model.py`
(the variants). The per-game inputs are the `team_game.efficiency` part
(`pcf.data.tables.efficiency`).
"""
