"""Vacated opportunity (decision 0050; brief in projects/vacated-opportunity/BRIEF.md): who absorbs
a missing top player's snap, target and carry share.

Two experts by rule m share this package:

- `vacated-live` (in season, the Saturday run): when a top player is expected to miss next game,
  each teammate's share that game, from the CEO's plus-minus for all players (`rates`, `live`).
- `vacated-offseason` (offseason events, the week-1 roster): each stayer's next-season share after
  a top player has left, gated on intake (`offseason`).

`choice` holds method 3, the nested-logit choice model, fit on completed seasons only.
"""
