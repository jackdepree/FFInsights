# 0026: A `team_season` table of charted traits, measured and dated, with no model

**Date:** 2026-11-10 · **Decided by:** the CEO chose a table over a second expert ("Yes, can you please build the retrospective traits table? The table should obviously include as_of or timestamp columns that help downstream models utilize the charters without leakage"). The calls below are Claude's technical calls, listed for veto at merge. · **Project:** `schemes-v2`

**Decision:**
- **New table `team_season`:**
  - keys are team and season; one part, `charted` (the spine), from participation and play-by-play (`pcf.data.tables.team_season`);
  - one row per team and season, 2016–2025;
  - built with `pcf tables build team_season`.
- **Its timing columns:**
  - `known_at`: the day after the season's Super Bowl (participation's rule). It's the column the gateway filters on.
  - `first_kickoff` and `last_kickoff`: the regular-season games the row sums up.
  - `prior_for`: the first season whose in-season models may use the row, the season plus one.
  - The part is marked post-season, so an in-season view sees a row only once its season has finished, whatever `known_at` says (rule m, leakage check 5).
  - It's also marked as about results, so leakage check 2 fails any row known before its last game.
- **The measures:**
  - The offense's choices: personnel 11, 12 and 21, heavy, the pistol, and time to throw.
  - What the offense faced: box, man, two-high and blitz.
  - The defense's choices: box, man, two-high, blitz, pass rushers, nickel and dime.
  - Each comes raw and over expected (`_oe`), with play counts.

**The calls:**
1. **A table, not an expert** (the CEO's call). Nothing is forecast: a row describes a finished season. A model that wants a forecast uses last season's row as a prior, through `prior_for`.
2. **Regular season only.** Every team has 16–17 games, and the playoffs are played differently (schemes-v2, where it misses). `known_at` still waits for the Super Bowl, because participation is published then.
3. **Neutral situations, as in `tendencies` and `charted`.** Outside them, the score and clock choose the plays.
4. **The cells that set "over expected":**
   - offense choices: season, down and distance;
   - defense choices and what the offense faced: season, down, distance, shotgun and the offense's personnel group, meaning what defenses usually do against that look.
   - `team_game.charted` uses heavy or not in place of the group. The group is finer, and it matters for nickel and dime.
5. **Use the `_oe` columns across seasons, not the raw rates.** The charting's level shifts by season: the league's man rate is 0.41 in 2023, 0.49 in 2024 and 0.30 in 2025, and the pistol is 0.044, 0.105 and 0.057. Over expected takes each season's league level out.
6. **Personnel is parsed once** (`pcf.data.clean.personnel`), in both of participation's formats:
   - backs include fullbacks;
   - defensive backs are CB, S, FS, SS or DB.
   - This fixes `team_game.charted`, whose heavy look missed the fullback from 2023 on. That changed 5–7% of plays' look in 2023–2025 and moved the heavy share from 28–34% to 34–40%. The part is rebuilt.
7. **A dropback with 0 pass rushers is uncharted** (0.1–0.4% a season), in both tables. `team_game.charted` used to count it as "not a blitz".
8. **The tables' code takes a season key.** `assemble` keeps `season` when it's a key, and leakage checks 2 and 8 handle a part with no `game_id`:
   - check 2: not known before the last game;
   - check 8: scramble rows not yet known.

**Alternatives:**
- *A second expert, `schemes-v2-retro`, with its own forecasts:* needs sign-off. Not chosen.
- *Season totals of `team_game.charted` alone:* only three defensive choices, and no personnel, box or offense side.
- *A column per season for whether the row is usable (`usable_in_season`):* the gateway already enforces it. `prior_for` says it once, as data.
