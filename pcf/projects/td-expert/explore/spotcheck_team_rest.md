# Spot-check 3: teams' rest of season, B (volume) shipped over A (chances): the rules, before the numbers

The CEO, 2026-11-24 (through the strategy chat): "Please spot check the rest of season, 3." Written before any number below is computed; the script is `spotcheck_team_rest.py`, its output `spotcheck_team_rest.txt`.

## What the brief says
The no-noise rule (BRIEF.md, approved 2026-11-17): "method A must do at least as well as the plain count model from volume (method B) on held-out games ... where it doesn't, B ships". Read literally, a tie is A doing as well, so A ships. Decision 0043 call 21 shipped B on the tie because only B beats rung 0 clearly (rule k: simple first).

## What is checked (2016-2024, the saved walks; Poisson log loss, 90% by week blocks)
1. A against B, B against rung 0 and A against rung 0, overall and **by season** (9 seasons).
2. **By how far into the season the window starts** (weeks 1-6, 7-12, 13+): is A's loss a long-window story?
3. **The "keeps playing" story for a team:** whether the team changes its starting QB during the window (the team's QB who started the window's first game against the QBs who started the rest). A team always plays its games; its story would be who plays QB.
4. **Teams with an outlying start** (the top and bottom fifth of xtd a game so far): does A, built on chances, over-trust a hot or cold start?
5. Each method's calibration of the mean (average said against average scored, by fifths of the forecast).

## What would change the verdict
- **A ships instead** if A beats B in 6 or more of the 9 seasons, or if A beats rung 0 with its interval clear of 0 while B's gain over A is within noise in every lens.
- **B stays, as shipped,** if A doesn't clearly beat rung 0 overall, and B is at least as good as A in at least 5 of 9 seasons.
- **Unclear** otherwise; then the brief's letter (A) and the simplicity rule (B) point apart, and the CEO's "no vetoes" keeps B, written as such.
- A lens is a "story" if A against B in it is clear of 0 in one direction and the opposite lens is not.
