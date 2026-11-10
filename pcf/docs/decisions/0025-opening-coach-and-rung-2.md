# 0025: A head coach is known from the start of week 1; the traits' rung 2 adds early-season weights and the opponent's bend

**Date:** 2026-11-10 · **Decided by:** Claude (technical calls, listed for veto at merge), finishing `schemes-v2` at the CEO's request ("Can you please finish schemes-v2?") · **Project:** `schemes-v2`

**Decision:**
- **New part `team_game.opening_coach`:** each team's head coach for its first regular-season game, on that game's row only, known at the start of week 1 (the schedule facts' known-at).
- **The trait features use it:** before a team's first game of a season, its coach is the opening coach once known (else last season's last, as before). From game 1 on, it's the coach of the team's latest known game, unchanged. So a new coach's history counts from week 1, not week 2.
- **Rung 2** (`<trait>_rung2` in `pcf.experts.schemes_v2.model`): the blend, plus each of its four gaps times an early-season weight, 4 ÷ (4 + games played), plus the opponent's bend (`<trait>_opp`: what offenses do against the opposing defense, as a shrunk season gap from the league, known by the moment). Tempo has no defensive column, so it gets the early weights only. Judged against the blend; kept only if it beats it.

**The calls:**
1. **Week 1's start, not the hire date.** Head coaches are hired and announced in January and February, months earlier, so this leans late. There is no free, dated source of hires, and week 1's start is already a known-at in the calendar.
2. **Only the first game gets a row.** A row for every game until a firing would tell an early view when the firing comes. A mid-season coach still counts from their first game (`pregame`, known at kickoff), even though interim coaches are usually named a few days earlier.
3. **The early weight is 4 ÷ (4 + games):** the same 4 games the shrunk season uses, so the weight is 1 before game 1 and a half after 4. One interaction per gap, not a weight per week, to keep it at 9 numbers.
4. **The opponent's bend is the exploration's average bend (F10),** taken as the opponent defense's shrunk gap from the league, with the same 4 games of prior as the team's own season. It's 0 where nothing is known.

**Alternatives:**
- *Dated hires from news:* a new data source (needs sign-off) for about 6 to 8 coaches a year.
- *Weights per week of the season:* closer to "weights that change with games played", but 18 sets of weights for a gain R4 put at half the late-season edge.
- *A coach's bend (H13):* failed in exploration (F11), so it isn't in the model.
