# 0022: Elo knows which teams have their playoff seed locked going into the final week

**Date:** 2026-11-07 · **Decided by:** the CEO chose the flag ("seed locked"); Claude made the technical calls below, listed for veto at merge · **Project:** `elo` (idea I19)

**Decision:**
- **New shared module `pcf.data.standings`:** standings and playoff seeds under the NFL's tiebreakers.
- **The flag:** for each team, whether its seed is fixed in every outcome of the final week's games, computed from the results known at the run.
- **How Elo uses it:**
  - The margin and win variants add `lock_diff`: away team locked minus home team locked. It's 0 in every other week.
  - The margin history publishes `h_lock` and `a_lock`.

**Evidence** ([`lock_flag.py`](../../projects/elo/explore/lock_flag.py), [`final_week.py`](../../projects/elo/explore/final_week.py)):
- **The cause:** 76% of Elo's final-week gap to the close is in the 31 games where a usual QB sat healthy.
- **The effect:** seed-locked teams score 6.8 points below Elo's rating-only forecast in the final week (90% interval −9.8 to −3.7; 67 team-games, 2002–2024).
- **The fix, out of sample:** with a size fitted on 2002–2015 (5.7 points) and applied to 2016–2024, the final-week gap to the close falls from 1.32 to 0.98 points.

**The calls:**
1. **Tiebreakers run through strength of schedule.** The points-based steps can't be known before the games. A tie that only they would break counts as unresolved, and an unresolved outcome counts as "the seed could differ". A lock is never claimed on a guess.
2. **The checks against reality:**
   - Seeds from every regular-season result match every real playoff field, 2002–2024: every wild-card game with the higher seed at home, every bye, and every 1 seed hosting the lowest seed left. That's 0 mismatches ([`seeds_check.py`](../../projects/elo/explore/seeds_check.py)).
   - A test re-checks 2016–2024 against the local tables.
3. **Every outcome is tried,** per conference: the final week's games involving that conference's teams, at most 2¹². Tied games are ignored.
   - Other-conference final-week results count as unplayed inside strength of victory and schedule. That's a rare, small approximation.
   - A cancelled game (2022 BUF–CIN) counts as never played.
4. **Final week only.** The second-to-last week also shows a gap (+0.54 points, 0.20 to 0.87), but trying every outcome of two weeks costs 2¹⁶ per conference. That's left for later.
5. **"Eliminated" is computed but not used.** Eliminated teams match Elo's forecast in the final week (+0.5 points, −0.6 to +1.6).
6. **The total doesn't use the flag (untested).** The gap was in margins. Rested starters may also lower totals, and that's a cheap check for later.
7. **Divisions are a fixed table** of today's team codes, valid since the 2002 realignment. The tables already rename relocated teams. Before 2002 there's no flag.

**Alternatives:**
- The record as a proxy (".800+ going into the final week", F11): cheap, but noisier. It misses teams locked into lower seeds and flags teams still playing for the 1 seed.
- **Tempting, rejected:** the market's line movement as a rest signal. It would leak the close into a model whose job is to be an independent feature next to the close.
- An exact two-week lock: later, if the second-to-last week's gap proves to be rest too.
