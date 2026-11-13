# Exploration: Opponent-adjusted efficiency (`team-efficiency`)

**Date:** 2026-11-12 · **Verdict:** GO · **Brief:** [BRIEF.md](BRIEF.md) · **Scripts:** [explore/](explore/) (each writes a `.txt` beside it)

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

## Hunch verdicts
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
- **The gains past F1 are small.** 0.6% and 1.4% clear zero on 2016–2024 and 2020–2024, but about 25 versions were tried, and the combination (F8) was picked after seeing its parts. The vault is the real test.
- **Not every setting was tuned on the earlier seasons.** The kinds of plays and the propensity bins were chosen by Claude, not tuned. A different binning could do better or worse.
- **The defense weights (runs over passes)** could partly be the spread of pass outcomes rather than representativeness. Either way, the weight is the right one for forecasting, but the football reading should be held loosely.
- **EPA and win chance come from nflverse's models**, fitted on the seasons before 2020. The scored results hold in 2020–2024, though.

## What not to redo
- **A per-play gradient-boosted weight (F3):** it fits noise. Learn weights across teams.
- **The usual garbage-time rule as a bar (F1).**
- **WPA as a measure of its own (F6), and grains past plays stacked beside EPA (F10).**
