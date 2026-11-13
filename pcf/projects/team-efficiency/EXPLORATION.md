# Exploration: Opponent-adjusted efficiency (`team-efficiency`)

**Date:** 2026-11-12, round two 2026-11-13 · **Verdict:** GO · **Brief:** [BRIEF.md](BRIEF.md) · **Scripts:** [explore/](explore/) (each writes a `.txt` beside it)

**The question.** Which way of measuring a team's efficiency, once the opponents and the situation are taken out, best predicts that team's own future? The CEO's main test (2026-11-12, "its own future is the main test") is each team's EPA per play over its next 3 games and over the rest of the season, for its offense and its defense, all plays, with those games' opponents taken into account. The CEO's hunches H40–H44 were each set against it.

**How every variant was scored.** One pipeline, so variants differ only in what they feed it ([explore/common.py](explore/common.py)):
- **A rating:** before each week, a ridge regression on the games already played that season: value = league + home + offense + defense. Each game counts by its plays times a recency weight, pulled toward last season's final ratings. Nothing from that week on reaches it.
- **A forecast:** the team's rating, its coming opponents' mean rating (the schedule is known) and its home share. The map from rating to forecast, and each variant's settings (memory, pull, carryover), were fitted on 2007–2015.
- **The score:** squared error on 2016–2024, as "skill" (the share of a reference's error removed), with a 90% interval from resampling whole weeks. 2020–2024 is shown apart, because nflverse's EPA was fitted on the seasons before 2020 (tag-tables#F4). The 2025 vault wasn't read.
- **Data:** 615,666 regular-season passes and runs, 2006–2024 ([build_plays.py](explore/build_plays.py)). Kneels, spikes and two-point tries are left out.

## Findings
Cite as `team-efficiency#F1`.

**F1. The usual garbage-time rule costs accuracy. Counting every play equally beats it** ([rung1.txt](explore/rung1.txt), [checks.txt](explore/checks.txt)). The rule keeps win chance 10–90% and drops the last two minutes of each half.

| All plays, equal, against the usual rule | Next 3 games | Rest of season |
|---|---|---|
| 2016–2024 | +4.6% (90% +3.9 to +5.4) | +7.1% (+6.0 to +8.1) |
| 2020–2024 | +4.2% (+3.4 to +5.1) | +7.4% (+6.2 to +8.7) |
| Garbage time left out of the target too | +2.4% (+1.8 to +3.1) | +3.6% (+2.9 to +4.7) |

- It wins on offense and on defense.
- It also makes the measure **more consistent**. Offense repeats week to week at 0.61 with all plays, against 0.52 with the rule; defense at 0.33 against 0.22.
- It's the same lesson as pace H22: the plays the rule throws away still say something about the team.

**F2. The ratings carry real signal.** The usual-rule ratings remove 15.7% (offense) and 9.9% (defense) of the league average's error over the next 3 games, and 19.5% and 12.5% over the rest of the season. A version with EPA shuffled within each week removes 0.0%.

**F3. A play-by-play learned weight fits noise** ([h41_first_build_gbm.txt](explore/h41_first_build_gbm.txt)). The first build of H41 used gradient boosting to learn a weight for every play from its situation. It came out 15–30% *worse* than equal weights, with football nonsense: first- and third-quarter plays weighted near 0, passes near 0, garbage time weighted 3×. One play's link to a team's future is far smaller than the play's own spread, so a play-level model chases noise. Kept as a record (a pitfall).

**F4. Learned across teams and shrunk toward equal, the representativeness weights (H41) tie equal weights** ([h41_h44.txt](explore/h41_h44.txt)).
- **How they were learned:** each play gets a kind (win-chance band × pass or run, plus the last two minutes of a half). A regression across 2006–2015 team-seasons measures how much one play of each kind moves the team's EPA per play in its other games (odd weeks against even weeks). The weights are shrunk toward equal by a strength picked by leaving one season out.
- **Offense:** the best shrinkage is nearly all the way to equal (it cuts the left-out error by only 0.04%). Every kind of offensive play is about equally representative.
- **Defense:** runs count more than passes (1.0–1.55 against 0.4–0.8), and the left-out error falls 1.05%. What a defense allows on runs says more about its other games than what it allows on passes. This matches CONSISTENCY.md: run defense repeats more than pass defense.
- **On the main test:** +0.0% (−0.2 to +0.2) over the next 3 games and −0.2% (−0.5 to +0.1) over the rest of the season, against equal weights.

**F5. The EPA–WPA gap helps the weights (H44)** ([h41_h44.txt](explore/h41_h44.txt)).
- **The gap:** a play's WPA less what its EPA is usually worth in win chance at that moment, from a model fitted on 2006–2015. EPA and the moment explain 90% of WPA, so the gap is the other 10%.
- **What was tested:** the plays at either extreme (top and bottom 5% of the gap) get kinds of their own in F4's weights.
- **The result against equal weights:** +0.3% (−0.0 to +0.6) over the next 3 games, +0.6% (+0.2 to +1.1) over the rest of the season. On defense over the rest of the season it's +1.0%; 2020–2024 gives +0.3% and +0.5%.
- **What it learned:** gap-extreme plays count a little less on offense (0.86–0.97), and gap-extreme passes count 0.6 on defense. These are plays where a team traded points for win chance, or the reverse, so they say less about its ability.
- **Consistency:** the weighted measure is the most consistent EPA measure we've built: 0.65 week to week on offense and 0.42 on defense, opponent-adjusted.

**F6. WPA as a measure of its own loses, and adds nothing beside EPA.** WPA per play is 4.7% (next 3) and 6.7% (rest) worse than EPA per play. Put into the same forecast, the two together are +0.0% over EPA alone. WPA is consistent (0.51 week to week on offense), but a few late plays in close games carry most of it.

**F7. Double machine learning with game state helps a little (H42), and the situation propensity is the part that does it** ([h42_dml.log.txt](explore/h42_dml.log.txt)).

| Against all plays, equal (plain ridge) | Next 3 games | Rest of season | 2020–2024 (next 3 / rest) |
|---|---|---|---|
| DML, with game state (score, win chance) | +0.2% (+0.0 to +0.4) | +0.4% (+0.2 to +0.6) | +0.3% / +0.5% |
| DML, without game state | −0.0% | +0.0% | +0.0% / +0.1% |
| The outcome model alone (no propensity), with game state | −0.2% | −0.1% | −0.2% / −0.1% |

- **The outcome model** (a play's expected EPA from its situation, fitted on 2006–2015) explains only 0.5% of EPA's spread. EPA already accounts for down, distance, field and clock.
- **The situation propensity** (the chance a play in this kind of situation belongs to each team, cross-fitted within the season so far) is what helps. It compares teams on equal footing when some spend more time leading or trailing.
- **It moves the ratings very little** (r 0.998 with plain ridge): the gain is fine-tuning.
- **The score is partly the team's own doing (a mediator), but leaving the game state in still helped.** The propensity only rebalances where teams play; it doesn't credit the score itself.

**F8. The two small gains add up, to more than their sum** ([combo.txt](explore/combo.txt)). DML with game state, with each play counted by F5's weights (offense weights for offense ratings, defense weights for defense ratings):

| Against all plays, equal | Next 3 games | Rest of season |
|---|---|---|
| 2016–2024 | **+0.6%** (+0.3 to +0.9) | **+1.4%** (+1.0 to +1.8) |
| Offense / defense | +0.7% / +0.4% | +1.0% / +1.9% |
| 2020–2024 | +0.7% (+0.3 to +1.1) | +1.5% (+1.0 to +2.1) |

Against the usual garbage-time rule, that's about +5% over the next 3 games and +8½% over the rest of the season.

**F9. Per series (H40): EPA per series ties EPA per play; series success rate is the most consistent measure, but a different one** ([h40_h43.txt](explore/h40_h43.txt), [h40_own_future.txt](explore/h40_own_future.txt), [checks.txt](explore/checks.txt)).
- **EPA per series ties EPA per play** on the main test (−0.0% and −0.1%). It also ties when the future is counted per series, its own unit. A series' EPA is its plays' EPA added up, so it mostly reweights the same plays.
- **WPA per series loses:** −4.7% and −6.8%.
- **Series success rate** (the share of series that make a first down or a touchdown):
  - it's 2.4% and 4.3% worse at forecasting EPA per play;
  - it's the **most consistent team measure in the project:** 0.69 week to week on offense and 0.47 on defense, opponent-adjusted, and 0.52 / 0.42 season to season;
  - it forecasts its own future 0.8% (+0.1 to +1.6) better than EPA per play does, and with EPA per play beside it, 1.4% better.
- **So it's a real trait of its own, not a better EPA:** steadiness at moving the chains. A feature candidate for game script, pace and drive-level models.

**F10. Other grains add nothing beyond plays (H43)** ([h40_h43.txt](explore/h40_h43.txt)).
- **EPA per drive and per quarter tie EPA per play** (±0.1%). Points per drive is 2.5% and 3.2% worse.
- **The representativeness weights by kind of drive** (its starting win chance and half) tie: −0.1% and −0.2%.
- **By kind of quarter** (the quarter and the score at its start): +0.1% and +0.2% (+0.3% on defense over the rest of the season). The offense weights shrink all the way to equal.
- **Putting any second grain beside EPA per play makes the forecast worse** (−0.4% to −0.7%): the extra terms fit noise.
- Points per drive is consistent (0.64 / 0.37 week to week, offense / defense, adjusted), so it goes in CONSISTENCY.md.

**F11. Taking the opponents out makes every measure more consistent,** and defense repeats much less than offense:
- **EPA per play:** offense 0.61 → 0.63 week to week, defense 0.33 → 0.38;
- **Success rate:** 0.62 → 0.64 and 0.39 → 0.45.

Every measure here is a trait. Over a whole season the adjustment is small, because schedules differ little (elo#F10). The rating's settings say the same: it remembers a season-long window (half-life 16 weeks) and keeps 0.5–0.7 of last season's rating.

**F12. Side targets** ([checks.txt](explore/checks.txt)):
- **Next game's points:** all-plays ratings beat the usual rule's by 2.0% (+1.5 to +2.6), and remove 9.0% of the league average's error. The DML and weighted versions tie equal there.
- **Dropbacks and runs:** efficiency ratings alone don't forecast them (dropbacks −1.2% against the league average, runs +0.1%). The play mix needs pace's inputs (pace#R3), with efficiency as one feature.
- **Not looked at:** the team's fantasy points, and Elo's margin with efficiency added. Both are for the build.

## Round two (2026-11-13): four more ideas
*Claude's ideas I33–I36, chosen by the CEO on 2026-11-13 ("Yes please start with those ideas"), with the tempting but bad ones left out (the pregame spread or the score as confounders, more causal machinery, a sequence neural net). Same pipeline, settings and seasons as round one. Each idea was set against F8's combination (DML with game state + gap-aware weights), the best so far.*

**F13. How much is left to find: late in the season, almost nothing; early in the season and over the rest of the season, a lot, but not from the plays** ([r2_ceiling.txt](explore/r2_ceiling.txt)). The target is itself noisy (about 180 plays over three games), so no rating can remove all of the league average's error. Three ceilings, from generous to strict:

| Skill against the league average, 2016–2024 | Now (F8's combination) | Hindsight oracle | Play-noise bound | Split-half reliability |
|---|---|---|---|---|
| Next 3 games | 17.5% | 22.8% | 35.1% | not possible (3 games) |
| Next 3, weeks 1–4 / 5–9 / 10+ | 12.3% / 15.5% / 20.3% | 22.7% / 26.7% / 21.1% | 36% / 36% / 34% | |
| Rest of season | 23.5% | not a ceiling there | 47.9% | 50.9% |
| Rest, weeks 1–4 / 5–9 / 10+ | 18.1% / 25.7% / 23.9% | | 68% / 61% / 41% | 65% / 54% / 43% |

- **What the ceilings are:**
  - **The hindsight oracle** rates every team on the whole season except the target team's next 3 games: its earlier *and later* games. It's a realistic ceiling for any rating that treats a team's season as one ability.
  - **The play-noise bound** removes only the plays' own scatter. It's generous, because whole games swing too: weather, game plans, injuries.
  - **Split-half reliability** steps the agreement between the odd and even games of the rest of the season up to its full length. It's strict, because it counts the opponents as noise.
- **Late in the season we're at the ceiling.** From week 10 on, F8's combination reaches 20.3% against the oracle's 21.1%. Overall it takes 76% of the oracle's skill over the next 3 games.
- **The room is early in the season** (12.3% against 22.7% in weeks 1–4) **and over the rest of the season** (23.5% against about 50%). That's room for knowing who a team is *before* its plays show it: priors, and changes such as injuries. It isn't room for squeezing more from the plays, which is what F14 and F15 confirm.

**F14. Stripping luck out of EPA makes it a little more consistent, but it doesn't forecast better** ([r2_luck.txt](explore/r2_luck.txt)). This is baseball's FIP idea, applied to the rating's input only; the target stays every play's real EPA.
- **What was changed:**
  - **Fumbles:** a fumble play's EPA was replaced by the average over who recovers. Fumbles are 1.6% of plays and 12% of EPA's squared spread.
  - **Interceptions:** a pick's EPA was blended with what an incompletion would have cost there. They're 1.3% of plays and 16% of the spread.
  - **Huge plays:** EPA was capped at ±k. Plays beyond ±3 are 4% of plays and 48% of the spread.
- **What the tuning on 2007–2015 chose:** keep 75% of an interception's EPA, and cap only at ±6, which barely touches anything. Picks are mostly the quarterback's doing, and the big plays are signal.
- **On the main test,** all three together: −0.0% and −0.0% against all plays equal. Run through F8's combination: −0.0% (−0.3 to +0.3) and +0.0% (−0.4 to +0.4) against the combination. Fumbles alone: −0.1% and −0.1%.
- **More consistent:** 0.66 against 0.63 week to week on offense, and 0.39 against 0.38 on defense (opponent-adjusted). A trait, kept in CONSISTENCY.md. But the future being forecast has its own fumble bounces, and the ridge already averages most of this luck away.

**F15. Combining the steady measures, with a gate by week: no gain that holds up; efficiency is mostly one trait** ([r2_stack.txt](explore/r2_stack.txt), [r2_gate.txt](explore/r2_gate.txt)).
- **What was stacked:** EPA (F8's combination), series success rate, success rate, passing and rushing EPA, this season alone and the prior alone. Each measure's own rating and its opponents' mean went into a ridge regression, its strength picked by leaving one season out within 2007–2015.
- **The gate:** every coefficient may differ by part of the season (weeks 1–4, 5–9, 10+).
- **2016–2024:**
  - the stack with the gate ties F8's combination (+0.1% and −0.2%);
  - it's better in weeks 1–4 (+1.1%, +0.2 to +2.0, on both horizons) and worse later;
  - without the gate, the rest of season is −0.6%.
- **That early gain doesn't hold on 2007–2015's left-out seasons.** A hard gate that picks, per part of the season and side, whichever was better on 2007–2015 picked "EPA alone" in all 12 cells. So it's +0.0%: the weeks 1–4 gain on 2016–2024 is luck or a change of era, not a gate to trust.
- **Compression:** one principal component carries 77% of the measures' spread on offense and 70% on defense, loading almost equally on all of them (runs least). One component alone forecasts 0.4–0.9% worse, and two or three components get closer. So **team efficiency is basically one trait**, which the EPA rating already holds. The others are small pieces that don't pay their way in the forecast.
- Series success rate still earns its place as a published trait of its own (F9), just not as a booster for EPA.

**F16. Season-start priors: a new quarterback or coach should weaken last season's carryover on offense. It's small, and series success makes a worse prior** ([r2_prior.txt](explore/r2_prior.txt), [r2_prior_pull.txt](explore/r2_prior_pull.txt)).
- **The flags, both known before week 1:**
  - **A new starting QB:** the week-1 depth chart's QB1 isn't last season's main passer. That's 31% of team-seasons.
  - **A new head coach:** 21% of team-seasons.
- **A side model (fitted on 2007–2015) of this season's final rating from last season's:**
  - **Offense:** carryover from last season's EPA is 0.42. With a new QB it falls to 0.17, and with a new coach to 0.23.
  - **Defense:** last season's EPA carries almost nothing (0.03) once last season's series success rate is known (0.63).
  - Football-sensible, but it's fitted on 288 team-seasons.
- **As priors in the rating:**
  - **P1** (last season's EPA + series success): −0.3% and −0.3%.
  - **P2** (P1 + new QB + new coach): +0.1% and −0.0%. Offense +0.4%, defense −0.3% to −0.4%; 2020–2024 +0.7% and +1.1%.
  - **Picked per side on 2007–2015** (that picked the usual prior for offense and P2 for defense): −0.1% and −0.1%.
- **P3, the direct version.** The usual prior, but a team's pull is weakened by a × new QB and b × new coach. a and b were tuned on the main test on 2007–2015 (768 versions); it chose a 0.25 and b 0.25 on offense, and no change on defense.
  - Offense +0.3% (+0.0 to +0.5) and +0.4% (+0.2 to +0.6). Defense −0.1% and −0.3%; overall +0.1% and +0.1%; 2020–2024 +0.1%.
  - Offenses with a new QB, weeks 1–4: +0.8% (−1.2 to +2.8).
- **Week 1 on its own,** where the rating is only the prior: every richer prior is worse than pull × last season's EPA (−2.0% to −3.3%).

**Round two in one line:** F8's combination stands. None of the four ideas adds a gain that holds on both the tuning and the scored seasons. The ceiling (F13) says why: the plays are nearly used up, and the room left is in what a team is before its plays show it.

**Versions tried in round two:**
- **Scored on 2016–2024:** 24 (luck 7, priors 4, stacks 12, gate 1).
- **Tuned only on 2007–2015:** about 830 settings (mostly P3's 768).
- **Both rounds together:** about 49 scored versions.

### Round two verdicts
These were Claude's ideas, chosen by the CEO, so they're logged in IDEAS.md (I33–I36), not HUNCHES.md.

| # | Idea | Verdict | Evidence | Claude expected |
|---|---|---|---|---|
| I33 | Estimate the noise ceiling first | **done** | At the ceiling late in the season; the room is early in the season and in the rest-of-season target (F13) | Near the ceiling for next 3: right late in the season, wrong early |
| I34 | Strip luck out of EPA (fumbles, interceptions, huge plays) | **failed** (more consistent, no better forecast) | −0.0% / +0.0% through F8's combination; week r 0.66 vs 0.63 (F14) | **The biggest new gain: wrong.** Picks are mostly skill, big plays are signal, and the ridge already averages the fumble bounce |
| I35 | Stack the steady measures with a week gate (mixture of experts; compression) | **failed** | Ties overall; the weeks 1–4 gain on 2016–2024 doesn't hold on 2007–2015, so the hard gate picks EPA alone everywhere. One trait carries 70–77% (F15) | A gain from series success beside EPA: wrong for the EPA target |
| I36 | Better season-start priors (QB and coach changes, steadier measures) | **unclear** (small, offense only) | P3 offense +0.3% / +0.4%, overall +0.1%; series success as a prior hurts (F16) | A gain in weeks 1–4: mostly wrong, though the QB and coach effects are real in the carryover |

### What round two changes in the brief
- **The ladder stays as round one left it** (F8's combination).
- **One optional rung on offense:** P3's weaker pull after a new QB or a new head coach. It's small (+0.3–0.4% on offense); the vault decides.
- **Report the ceiling in the results** (F13), so later work knows where the room is: early in the season, and in who a team is before its plays show it.
- **Not to build:** luck-stripped EPA as the forecast input (it's kept only as a consistent trait), the measure stack, and series success as a prior.

## Round three (2026-11-13): a stronger pull for teams with no change (IDEAS I40, the CEO's pick)
**F17. Teams that kept their QB and coach don't deserve a stronger pull** ([r3_keep_pull.txt](explore/r3_keep_pull.txt)). P3 in the build cost teams with neither change 0.8% early in the rest-of-season forecast (RESULTS R13). This tried two fixes, each tuned on 2007–2015 and scored on 2016–2024 against P3:
- **A keep factor:** the offense pull for unchanged teams = K × 0.7 (capped at 1), tuned with the two cuts. The next-3 error picks K = 1.10 with a = b = 0.25 (P3's cuts). Against P3: +0.0% (−0.1 to +0.1) next 3 games, −0.1% (−0.1 to −0.0) rest of season. Unchanged teams, weeks 1–4 of the rest of season: −0.2% (−0.7 to +0.3).
- **A separate forecast slope** for unchanged teams (own rating × neither, in the map): −0.0% next 3, −0.2% (−0.4 to −0.1) rest of season; unchanged teams −0.4% early.

The error surface is flat: across all 45 versions, the 2007–2015 next-3 error moves only in the fourth digit. Verdict: **failed** (a tie). R13's loss is P3's price, not a gap in it.

## Hunch verdicts (round one)
| # | Hunch | Verdict | Evidence | Claude expected |
|---|---|---|---|---|
| H40 | Efficiency is "EPA and Winning Percent Added per series" | **unclear** | EPA per series ties EPA per play (−0.0%, −0.1%; also in its own unit). WPA per series loses (−4.7%, −6.8%). Series success rate loses on EPA (−2.4%, −4.3%) but is the most consistent measure (0.69 / 0.47), forecasts its own future 0.8% better, and adds 1.4% beside EPA (F9) | A tie for EPA per series; WPA repeating less. Both right |
| H41 | A model decides which plays count, not "arbitrary sampling" | **held against the usual rule, by the full sample; the model itself ties equal** | The usual rule loses to all plays by 4.6% and 7.1% (F1). Learned weights tie equal on their own (+0.0%, −0.2%, F4), help with the gap (F5) and add up with DML (F8). Like pace H22, the principle held; the CEO calls it | A modest win over the fixed rule: right, but the win comes from using every play, not from the weighting |
| H42 | Causal inference (DML) separates situation from ability | **held, small** | With game state: +0.2% (+0.0 to +0.4) and +0.4% (+0.2 to +0.6), 2020–2024 +0.3% and +0.5%. The situation propensity carries it; the outcome model alone doesn't help (F7). With F5's weights: +0.6% and +1.4% (F8) | A small gain at most, from the score and the matchup: right |
| H43 | The model applied at several grains (plays, drives, quarters, situations) | **failed** | Nothing adds beyond plays more than 0.2%; a second grain beside plays makes it worse (−0.4% to −0.7%) (F10) | Plays carry most of it: right |
| H44 | Mesh EPA and WPA; the gap as a feature for the propensity model | **held, small (the gap as a feature); WPA itself failed** | The gap's extremes as their own kinds: +0.3% (−0.0 to +0.6) and +0.6% (+0.2 to +1.1) over equal (F5). WPA as a measure loses 4.7–6.7%, and adds 0.0% beside EPA (F6) | The gap a useful flag, a blend not beating EPA: right |

The CEO's two meanings of "propensity" (2c) both earned a place, kept apart by name. The **representativeness weight** (H41, H44) is which plays count. The **situation propensity** (H42) is which team tends to be in which situation, used to compare teams on equal footing. They help in different places, and together they add up (F8).

## Go / no-go
**GO.** Efficiency is a real, consistent trait with clear held-out signal (F2), and the CEO's ideas improve on the usual way twice over. Every play counts (F1: about 5–7%). On top of that, DML with the situation propensity and the gap-aware weights adds 0.6–1.4% (F8). The gains past F1 are small and need the vault to confirm them.

## What this changes in the brief
- **The bar becomes "all plays, equal".** The usual rule loses, so it can't be the simple alternative that ships if nothing else wins.
- **The ladder for the build:**
  - rung 1: ridge on all plays;
  - rung 2: DML with game state (the situation propensity);
  - rung 3: plus the representativeness weights with the EPA–WPA gap (F8's combination);
  - passing and rushing parts for each.
- **A second published measure: series success rate**, opponent-adjusted (F9). It's the most consistent trait here and adds beside EPA on its own target.
- **The build adds:** an interval for each rating, calibration of the forecasts, the 2025 vault, Elo's margin with efficiency added, and the team's fantasy points as a side target.
- **Dropped:** grains past plays (H43) and WPA as a measure of its own (H44's mesh). The gap stays, as a weight feature.

## The case against (so far)
- **The gains past F1 are small.** 0.6% and 1.4% clear zero on 2016–2024 and 2020–2024, but about 49 versions have now been scored over two rounds, and the combination (F8) was picked after seeing its parts. The vault is the real test.
- **The ceiling (F13) depends on how it's built.** The hindsight oracle uses no recency weight and a fixed light pull, so a better-tuned oracle could sit a little higher. "At the ceiling late in the season" is about this oracle.
- **Not every setting was tuned on the earlier seasons.** The kinds of plays and the propensity bins were chosen by Claude, not tuned. A different binning could do better or worse.
- **The defense weights (runs over passes)** could partly be the spread of pass outcomes rather than representativeness. Either way, the weight is the right one for forecasting, but the football reading should be held loosely.
- **EPA and win chance come from nflverse's models**, fitted on the seasons before 2020. The scored results hold in 2020–2024, though.

## What not to redo
- **A per-play gradient-boosted weight (F3):** it fits noise. Learn weights across teams.
- **The usual garbage-time rule as a bar (F1).**
- **WPA as a measure of its own (F6), and grains past plays stacked beside EPA (F10).**
- **Luck-stripped EPA as the forecast input (F14), stacking the steady measures onto EPA (F15), and series success as a season-start prior (F16). A stronger pull or a separate slope for teams with no change (F17).**
