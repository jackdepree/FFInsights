# 0051: skills over expected's build, its technical calls

**Date:** 2026-11-25 · **Decided by:** Claude (technical calls, for the CEO's veto) · **Project:** `skill-over-expected` (the build of the agreed brief, `projects/skill-over-expected/BRIEF.md`, agreed 2026-11-20: "1; yes I approve") · **Vetoes:** none (the CEO, 2026-11-26: "No vetoes from me, we should record the thought process and the exception for call 30 so we can always revert that decision in the future"). Calls 31-34 came after that answer, from the CEO's other answers the same day and the spot-check.

## What ships, and how it's read

1. **A saved history, not a forecasting expert** (decision 0048's way, call 1): one row per player-season and trait, walk-forward, in the standard output columns (`as_of`, `train_end`, `cadence` = retrospective), under `outputs/skill-over-expected/<run_id>/history.parquet`, pinned in the registry's `history_runs`. A season's row is known once its participation is out (the day after the Super Bowl); an in-season model reads it only for finished seasons (rule m).
2. **Read through the gateway,** a retrospective view at the end of time, one season at a time (`play.pbp`, `play.participation`, `player_play.on_field`, `player_game.roster` and `pfr`), regular season, 2016-2024 (PFR's charting 2018-2024). Cached in `<interim>/skill_over_expected/`. **The 2025 vault stays closed** (the CEO, 2026-11-25: "No keep 2025 closed please").
3. **A sack counts as a pressure** in every pressure rate from participation (QB pressures, the line's pressure over expected, a lineman's on-field rate). Before 2023 participation's pressure flag is empty on every sack (I90's trap, context-v2's fourth look); the exploration's first look counted sacks out.
4. **Main team and position** as `pcf.validation.owners.main_team` (most roster games, ties alphabetical; most on-field snaps, ties alphabetical), computed on snap counts instead of one row per snap (`data.main_teams`, the same answer with far fewer rows). "Moved" means the main team changed.
5. **Groups** from the main position: DL (DE, DT, NT), OLB, ILB (ILB, MLB, LB; and since call 31 an OLB player-season in an off-ball role), DB (CB, FS, SS, S, DB), WR, RB, QB, OL. Each trait is fit per group, but its k is pooled over its groups (call 24).
6. **Traits and floors** are the exploration's: pressures per on-field dropback (DL, OLB, ILB; 150 dropbacks); rush share (OLB, ILB; 150 dropbacks and 10 pressures or targets); WR plain catch rate (40 targets); QB sacks per dropback, throw depth, time to throw (150 dropbacks); RB yards after contact and broken tackles per PFR carry, and the share of after-the-line tackles needing two or more tacklers (80 carries); DB catch rate allowed, interceptions per target, throw depth against (30 targets). Beside them, not shipped (the "ignore" column's evidence): pass rushers' sacks per on-field dropback, QB pressures per dropback and sacks per pressure, a lineman's team's pressure and sacks on his dropbacks (300 dropbacks). The line's pressure over expected is a team-game row (`line_poe`), as the exploration built it.

## The ladder

7. **Centred rates.** Every rate is read less its group's mean that season (over the rows that pass the floor), the brief's "plain rates with each season's level taken out" and stabilization's centring. The target is next season's rate less next season's group mean, so every rung is scored on the same level-free scale; the level itself is not this table's forecast.
8. **Rung 2, the shrink (M1),** is stabilization's method 1 (its `components`): k = sigma2 / tau2, the noise per chance from each player's games around his season rate, over the true spread of centred season rates. One k per trait (over its groups, call 24), fit on seasons up to the input season. The shrunk rate is n / (n + k) of the way from the group's mean to his rate.
9. **Rung 2b, the second pull** (I156, stabilization's): M1 times one slope fit by weighted least squares on earlier season pairs only. It's in the ladder because stabilization's exploration found it beats M1 for 12 of 18 rates and its agreed brief makes it the base; using it here follows stabilization rather than inventing a second method.
10. **Rung 3, the owner split:** one weighted fit, on earlier pairs, of next season's rate on his own M1 and the **team part**, the shrunk centred rate last season of his next team's other players in his group (k for the team part from the spread of team-group rates). For a mover it's the team he joins, for a stayer his teammates. **His next team is his main team next season**, which for almost everyone is the team he starts the season with (known before week 1 after free agency); a player traded in season is the exception, a small look-ahead stated in the case against.
11. **Fits are weighted by next season's chances, with no intercept** (centred rates). The slopes need 30 earlier pairs, so a trait's first season pair is never scored: every rung is scored on the same rows (rung 3's fittable ones).
12. **Ties go to the simpler rung** (rule k): the ladder stops when a rung doesn't clear the one below. The champion per trait is the highest rung that cleared.

## The tests

13. **Gain** = the share of the base's weighted squared error removed; 90% interval from resampling players, 2,000 draws.
14. **Counts** = the interval clears zero **and** the gain beats all 20 shuffled copies, each the walk rerun with **the piece the rung adds** moved to another player of the same season and group: for M1 against the raw rate, his chances (shrinking by someone else's sample size); for the split against the rung below it, the team part. **The second pull has no added input** (it's one slope), so it's judged on its interval alone. The **signal test** (VALIDATION §5, retrospective: within season and position) moves every input together (rate, chances, team part) and scores against the position's average: the champion must beat all 20.
15. **Ranges:** normal 80% ranges for next season's rate, mean the champion, variance v + sigma2 / w, where v is the true rate's spread left around the forecast (fit on earlier pairs) and w next season's chances. Coverage (75-85%), coverage by thirds of chances, and the range score against the position average's range made the same way.
16. **Owner labels** from the share kept (`pcf.validation.owners.kept`, each season's level out) with its 90% interval (`kept_interval`): player when movers keep half or more, else team.
17. **Seasons won** (I147's count) is reported beside every champion's gain.
18. **The yardstick:** each offensive champion's shrunk value as last season's prior on the crude forecaster's rest-of-season boards (WR catch rate on receiving, the RB traits on rushing, the QB traits on passing), beside participation, `score_input`, with 19 copies shuffled within season and position (decision 0048, call 21's way).

## Odds written before the full run

A code-check run of the ladder (every trait's rungs 1 to 3 on all rows) was seen before these were written, so the brief's own success test (the shrunk trait beats the raw rate and the position's average) has no scored odds here; it was already visible. Nothing below had been run:
- **The yardstick:** 45% the shrunk WR catch rate counts on the receiving board beside participation; 30% at least one RB trait counts on rushing; 35% at least one QB trait counts on passing. Size: +0.1% to +0.5% of the squared error where they count.
- **I90's halves** (Claude's odds from 2026-11-20 in `IDEAS.md`, never scored): 55% QB movers keep under half of sacks per pressure in both providers' halves; 70% sacks per dropback still follows the QB more than the line.
- **I170, I171, I172** (new, in `IDEAS.md`), **I156** on the yardstick (its odds from 2026-11-25), **I79**'s three bets (2026-11-20), **I76** and **I112** where they run.

## Calls made during the build (after the odds above)

19. **The table's interval for his true rate this season** is 90%, normal, sd sqrt(sigma2 / (n + k)) around the shrunk rate: the spread left once the season's chances and the position's spread are combined. It describes this season, not next.
20. **The table's range for next season** is the champion's 80% range made as in call 15 and call 25, fit on pairs whose target season is the row's season or earlier, at **this** season's chances (next season's aren't known when the row is made). The first seasons, with fewer than 30 earlier pairs, have no range (null).
21. **The history's rung** is each trait's champion. Where the split wins, the history carries the rung below it, because the split needs next season's team; no shipped trait's champion was the split in the first run (only the linemen's rows, which aren't shipped); since call 31 OLB pressures' is, and its rows carry M1. A `rung` column names it on every row.
22. **Rung 3 was redesigned after the first full run.** As first built (his M1 and his next team's part, call 10), the team part for stayers is his own teammates, which adds noise for everyone who stays. The shipped rung 3 is his M1 plus the **change** in team part (his new team's part less his old team's, him left out of both), which is zero for a stayer. The first design is kept as `split0` and is what I171's odds were written against, so I171 is scored on it.
23. **Shuffling his chances is a diagnostic, not the bar for M1.** The copies with chances moved between players keep the average pull (the copies land within a point of the real gain for every trait), so they can't tell M1 from one flat pull. A **flat rung** (one slope on the raw rate, no chances) was added to answer "do his chances matter?" head on. A rung that adds no input (M1 over the raw rate, the second pull over M1) counts on its interval; the signal test (every input moved, against the position's average) is the null every champion must beat.
24. **One k per trait, pooled over its groups.** The brief reads "one stabilization constant per trait"; the build first fit one per group, and I172 then found per-group k ties the pooled one for all three traits with groups. Rule k gives a tie to the simpler model, so the pooled k ships (each group is still centred on its own mean, and its slopes and owners stay per group). It changes pressures, rush share and the pass rushers' sacks only: inside linebackers' rush share now clears the raw rate (it tied before), and outside linebackers' rush share's champion becomes M1 (the second pull no longer clears it).
25. **Ranges are scaled to hold on earlier pairs** (a conformal step, VALIDATION §7): the first full run's normal ranges held only 55% to 74%, because the normal shape is too thin for next season's rate. The scale is the 80th percentile of earlier pairs' standardized misses over 1.2816, fit with no look at the target season.
26. **I76's movers model** uses two-way fixed effects (players and franchises, weighted by chances) on the largest set of teams and players linked by movers, and corrects the noise by **fitting on odd and even weeks apart** and reading each part's true spread as the covariance of the two halves' estimates. It's a cheaper stand-in for the leave-one-out correction the idea names (Kline, Saggio and Sølvsten): both remove the noise's share of the plain fit's variances; split halves loses half the data in each fit.
27. **I112 runs on input seasons 2017-2022 only,** from context-retro's walk-forward player-game rows (run 7ca46aa8), because its spot-check (context-retro#R13) found the after-pressure part is the QB's only on the old provider's pressures.
28. **I156 can't be scored on the yardstick here.** The crude forecaster refits a linear board on each input, so multiplying an input by one slope can't change its forecast. The second pull is scored on this project's own target (next season's rate) instead.
29. **The bootstrap sorts players first,** so an interval doesn't wobble with the order polars returns groups in (about 0.3 points between runs before the fix).
30. **The shrink (M1) ships over the flat pull although they tie: an exception to rule k, recorded so it can be reverted** (the CEO, 2026-11-26: "we should record the thought process and the exception for call 30 so we can always revert that decision in the future").
    - **The tie.** The flat pull is one slope on his raw rate, fit on earlier season pairs, the same for every player whatever his chances. Against M1 it spans zero for 13 of 15 shipped trait-groups in the first run (F111) and 14 of 15 after call 31's rerun (run 6ecfce2a). The point estimates lean to the flat pull for 12 of the 15 (by 0.3 to 7.5 points); it clears only for DB throw depth against (-4.4%, -8.7 to -0.2), whose champion is the second pull anyway, a rung above both.
    - **Why rule k doesn't settle it.** Rule k gives a tie to the simpler, faster, cheaper model. Here the two cost the same: one number per trait each (k, or a slope), fit in a second, from the same inputs (his rate and his chances, which the flat pull ignores). Neither is simpler in the sense rule k means.
    - **Why M1 was kept.**
      1. It is the brief's rung 2 ("shrunk toward the position (one stabilization constant per trait)") and stabilization's method 1, so the two projects share one method (call 32).
      2. **Each player gets his own interval** (call 19). A player with 600 dropbacks and one with 150 at the same rate get different shrunk values and different widths. The flat pull gives them the same value and no interval of its own, and downstream models that weight a trait by how sure it is need that interval.
      3. The flat pull's lean is inside the noise. And a player's chances must matter in the end: a two-snap season can't be read like a full one.
    - **What reverting looks like.** One line: change `SHRINK = "m1"` to `SHRINK = "flat"` in `pcf/src/pcf/experts/skill_over_expected/traits.py`. Then rerun `python -m pcf.experts.skill_over_expected.run` and pin the new run in the registry's `history_runs`. The flat rung it switches to is tested (`tests/experts/test_skill_over_expected.py`, `test_flat_rung_has_one_pull_and_no_interval`).
      - **What changes in the history:** `shrunk` becomes slope × his centred rate, plus the group's mean. `shrunk_lo` and `shrunk_hi` become null (no per-player interval). `next_c`, and the range around it, are built on the flat pull. The `rung` column reads `flat`.
      - **What doesn't change:** the raw rates, the owner labels, and k (still reported, and still used by the owner split). The second pull keeps its place above M1, so a trait whose champion is the second pull keeps it.
    - **What would trigger a revert.** Any one of these:
      - (a) the flat pull clears M1 for three or more shipped trait-groups on seasons this table hasn't scored (2025, when the vault opens, or 2026);
      - (b) the per-player interval fails its own check: on a split-half test, the true rate falls inside the 90% interval for under 80% of player-seasons;
      - (c) a downstream model that reads the table gains nothing from the interval, and gains from the flat pull's values.

31. **4-3 off-ball outside linebackers count as inside linebackers, by rule** (the CEO, 2026-11-26: "Yes we can count those linebackers as middle/inside linebackers"). An OLB player-season (roster or on-field position) moves to the ILB group when the role table (roles-archetypes run 696a3f0b, I113) gives it an off-ball fine role that season: `box linebacker` or `base defensive back` (`traits.regroup`, `OFF_BALL`). There is no list of names, and the old label stays as `roster_position`.
    - **Counts.** 472 of 1,280 OLB player-seasons move (148 of the 461 over a trait's floor). The OLB group keeps the role table's run defenders (133 seasons in the sacks rows) and pass rushers (51).
    - **The rule's misfiles, left in.** Among the 461 seasons over the floor:
      - 18 movers rush on more than half their pass snaps: edge players the role table calls off-ball.
      - 9 OLB seasons that stay rush on under 0.3 of them.
      - A certainty floor of 0.9 on the role call would cut the 18 to 2, but leave 28 off-ball seasons as OLB. The role table's rush-per-pass column doesn't separate them better.
      - So the plain role call ships. The misfiles are about 6% of the rows.
    - **Pairs.** A pair needs the same group in both seasons, so a player whose group flips between his two seasons leaves both groups' pairs. OLB pressures go from 234 to 126 pairs (target seasons 2021-2024), and ILB pressures from 249 to 303.
    - **What it changed** (rerun 6ecfce2a against 94e6bd0e):
      - **OLB pressures:** M1 now ties the average (+13.9%, -0.5 to +27.8; was +54.9%). The owner split clears and ships as champion (+8.0% over M1, beats the copies); the history carries M1.
      - **ILB pressures:** M1 now clears the average (+34.8%, +3.8 to +53.4).
      - **ILB rush share:** M1 ties raw (+5.6%, -8.4 to +16.8), so its champion is the raw rate.
      - **OLB sacks:** noise from season to season (r 0.03). OLB pressures no longer add to sacks for all OLBs (+3.8%, -1.5 to +9.0).
      - **k** is now 178 (pressures), 10 (rush share) and 483 (sacks). I172 still ties for every trait.

32. **The pull code is stabilization's, and stays the same across projects** (the CEO, 2026-11-26: "Yes stabilization should own the code for pulling rates toward the average, but that does not necessarily mean other experts can not use that code. The code should be consistent between projects unless there is a good football reason").
    - **Where the code is now.** Stabilization has no package code yet. This build's `traits.components`, `traits.pairs` and the second pull are the first in the package.
    - **The direction.** Stabilization's build moves them to a shared module it owns (for example `pcf.validation.stabilize`), and this table imports them from there.
    - **Until then,** this copy matches stabilization's exploration (`projects/stabilization/explore/stab_common.py`):
      - the same k (the noise from each player's games around his season rate; the spread from the den-weighted variance of centred rates, less the mean noise);
      - the same pooling over positions, around each position-season mean;
      - the same second pull.
    - **Where they differ, and why:**
      - **The pull target:** this table uses the same season's group mean, because a retrospective table reads a finished season. Stabilization uses last season's, because in-season the current mean isn't known yet. That is a timing reason, not a football one; a shared function takes the target as an argument.
      - **Floors:** this table uses the brief's floor per trait (150 dropbacks, 40 targets and so on); stabilization uses `min_den` 10. Each project's brief sets its floor, and a shared function takes it as an argument.
      - **The second pull:** stabilization's base. Here it is a rung that ships only where it clears M1 (rule k).
      - **The groups, the one football reason:** off-ball OLBs count as ILB here (call 31). Stabilization groups by roster position, and keeps that for now (the CEO, 2026-11-26).
    - A note for stabilization's build is in `docs/ROADMAP.md` and in the shared notes.

33. **The spot-check changes the advice for movers, not the table** (`projects/skill-over-expected/SPOT_CHECK.md`). The CEO picked the inside linebackers' movers result (I171, F115).
    - **It still clears after call 31:** pressures +9.4%, rush share +11.0%.
    - **But it isn't about the new team.** Shuffling the new team's rate among inside linebackers scores as well, and the second pull alone gives the same gain. A mover's team-owned trait falls back toward the average more than a stayer's, and his new team adds nothing beyond that. The same holds for WR catch rate and DB throw depth against.
    - **Where the new team does add,** beyond the harder pull:
      - offensive linemen's movers: pressure +19.6%, sacks +23.2%;
      - outside linebackers' pressures: +2.9% on all rows, +10.8% for movers (call 34).
    - **The interface card's advice:** for a mover, read `next_c` from the second pull. Add his new team's part only for linemen and for edge pressure.
    - The history doesn't change, because it has no split rung.

34. **OLB pressures' split is checked against the second pull.** This was added after the spot-check, because call 31 made the split the champion.
    - **It clears:** +2.9% (+0.7 to +5.6), beating 20 copies with the team change shuffled (best +1.8%). For movers, +10.8% (+3.0 to +18.4).
    - **OLB rush share's split doesn't** (-0.3%).
    - So for edge players, as for linemen, the new team's pressure part says something about next season's pressures.
    - This is one more test run after the result was seen, on 126 pairs. Read it as a lead, not a finding (I173).

## For the CEO's veto

Calls 1-30: **no vetoes** (the CEO, 2026-11-26). The calls that changed what ships after the odds were written:
- 22: rung 3 redesigned;
- 23: the flat rung, and shuffled chances as a diagnostic;
- 24: one k per trait;
- 25: scaled ranges;
- 30: M1 over the flat pull, an exception to rule k, with its revert written out.

Calls 31-34 came after the veto round. 31 and 32 carry out the CEO's own answers; 33 and 34 follow from the spot-check. The technical calls in them, for the CEO's veto before the merge:
- 31: the role-table rule, with its misfiles left in;
- 32: the pull target and the floors kept per project;
- 33 and 34: the advice for movers.

## At the merge (2026-11-26)

The CEO, word for word: "Yes please merge skills over expected into main. No vetoes from me. No stabilization's build does not need to count off ball linebackers as inside linebackers for now."

- No vetoes on calls 1-34, including call 30 (the recorded exception to rule k) and calls 31-34.
- Stabilization's build keeps its roster grouping of linebackers for now; off-ball OLBs count as ILB only in this table.
