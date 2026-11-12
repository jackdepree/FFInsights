"""participation-live: who was on the field on every scrimmage play of each completed game, both
sides, from free data known by the morning after (projects/participation-live/BRIEF.md).

- `grid`: the snaps by the candidates, with the pins (named, every-snap) and the answer key.
- `history`: earlier seasons' habits per player and team (H32, H33, H35).
- `model`: the on-field model per position group, by rung (share → league → history → sequence).
- `chain`: the chances along each team's snaps (a two-snap-memory chain balanced to 11 a play
  and each snap count) and the snap-matched best guess.
- `reconstruct`: a season through the gateway, walk-forward, scored and saved.
"""
