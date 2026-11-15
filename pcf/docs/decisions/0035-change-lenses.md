# 0035: The lens list of 2026-11-15: two change lenses

**Date:** 2026-11-15 · **Decided by:** the CEO ("yes please add the change lens to the miss report", 2026-11-15), after IDEAS I47's check at retro 1. The calls below are Claude's technical calls, listed for veto at merge. · **Project:** `miss-lenses` (the lens list), from `projects/RETRO.md`

**Decision:**
- **A new dated lens list, `2026-11-15`:** the list of 2026-11-03 plus two lenses, both known before the game. A new list is a new date, never an edit: reports saved under the old list keep its date.
  - **`player_change`:** games since something changed for the player. Groups, the most recent change first: first game back from injury; games 2–4 back; rookie, weeks 1–4; rookie, weeks 5+; new to the team, weeks 1–4; new to the team, weeks 5+; none.
  - **`team_change`:** games since something changed for his team. Groups, the first games after a change first: QB changed in season, games 1–4; new head coach, games 1–4; new QB at season start, games 1–4; QB changed in season, games 5+; new head coach, games 5+; first game after a bye; none.
- The scoring method keeps its date (2026-11-03): nothing about how a lens is scored changed.

**Claude's technical calls:**
1. **Two lenses, not eight.** I47 looked at eight kinds of change one at a time. On a scorecard that would double the fixed list, so they are grouped into one lens for the player and one for his team. The cost: a row with two changes shows under one of them (the order above).
2. **"Just after" is 4 games** (`CHANGE_GAMES`), the window I47 used and the one I9 and the new-coach prior found.
3. **A player's weeks are his weeks on the team's roster that season**, not his games played: the roster is the spine every player-game model shares.
4. **The team's changes come from who actually started and coached** (`team_game.pregame`), compared with last season's most-started QB and final coach. That makes it a lens for diagnosis only. The point-in-time version of the season-start flags, for models, stays in `pcf.experts.team_efficiency.changes`.
5. **A known duplication (rule j):** `team_changes` in `pcf.validation.misses` and `season_changes` in `team_efficiency.changes` both work out a new QB and a new coach, from different inputs (the actual starter against the week-1 depth chart with its known-at). Left apart for now: merging them means touching a champion's inputs. A shared `pcf.data` function is the fix when a third user appears (I54 would be one).
6. **Seasons with no season before them in the data** call nothing new (the flags are empty), rather than guessing.
7. **Mid-season head-coach changes are left out:** too few rows to clear the lens's 200-row floor in most histories.

**What it shows on the saved histories (2016–2024, discovery):** the top group for participation's champion is the first game back from injury (+4.3 points of snap share, 90% +3.4 to +5.3, 1,376 rows); for the lasso's fantasy points it is the same group (−0.62 points). Both lenses' bias share is about 0.0%: the biases are real, and correcting them would move the overall error very little, as miss-lenses#F11 found for every pre-game lens.

**Why:** I47 found clear biases just after a change in three experts, one expert at a time before that (I9, I11, I41). A lens on every scorecard finds the next one without a special study.
