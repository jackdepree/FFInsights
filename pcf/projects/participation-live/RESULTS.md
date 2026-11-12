# Results: Participation inference (`participation-live`)

**Date:** 2026-11-12 · **Status:** validating (not merged; the CEO's calls below) · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** `participation-live` · **Technical calls:** [decision 0030](../../docs/decisions/0030-participation-live.md) · **Code:** `pcf.experts.participation_live`

## In short
**It maps every play.** For each scrimmage play of 2019–2024, with each season held out and trained on the three before, it gives:
- every possible player's chance of being on the field;
- two lineups built from those chances.

What it gets right:
- **The chances beat every simpler version, in every season.** Log loss is 9.0% (offense) and 6.4% (defense) lower than the snap share alone, and 5.5% and 5.1% lower than a shuffled version of itself (R1).
- **The chances are calibrated** within 1.1 points (R2).
- **The snap-matched lineup:**
  - gets 87% of each offensive play's 11 right, and 81% on defense;
  - keeps 99.3% of players within one play of their snap count;
  - substitutes as often as real teams do: 1.24 players a snap, against a true 1.24 (R3).
- **The likeliest lineup, the headline** (the CEO, 2026-11-12), gets more right per play (89% and 83%), but drifts 7.3 plays a player from his snap count and substitutes half as often.
- **The position mix fixed the personnel.** The right number of backs and tight ends is now on 63% of plays, against 40% without it (R4).
- **Each play has a certainty:** the likeliest lineup's expected share right. It's honest to within 1 point and sorts plays from 81% right to 96% on offense (R12).
- **The CEO's spot-check of the inputs added two** (R9, R10): the competition in a player's position group on the snap, and his pair habits with the teammates named on it (the CEO's tandems, H36). Together: 2.0% better on offense and 0.13% on defense, in every season, including the four that played no part in choosing them.

**The weak spot is the use the brief named first.** A player's on/off plus-minus built from the map correlates only 0.42–0.50 with the true one (R6). In-season plus-minus from this map is a noisy feature, not a measurement.

**Scores:** [build/backtest.txt](build/backtest.txt) (every rung, pooled and by season, by position group) and [build/fit_for_use.txt](build/fit_for_use.txt) (plus-minus and personnel against the truth). MLflow run `6f13a56965644245a9c06384f0959448` (4,653 s); the run before the spot-check's two inputs was `956a289679864800af8292a429e2a23b`.

**Vault:** closed; 2025 is untouched. Confirmation is the walk-forward 2019–2024 (each season trained on the three before), plus 2026 live.

**Versions tried:**
- one model per rung (5 rungs);
- the best guess three ways: no position mix; a mix with a step either side; the mix rounded over the whole game (the final);
- the inputs (the CEO's spot-check): 10 variants in round 1, 7 in round 2, on 2023–2024.

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal / no noise | Yes. The sequence model beats its shuffled self by 5.5% log loss on offense and 5.1% on defense, pooled. In every season the margin is 5.2–5.9% and 4.8–5.4%. Every rung beats the one below in every season (R1) |
| Calibration | Inside the 3-point bar. Offense: 1.10 points, slope 1.07. Defense: 0.82 points, slope 1.05. Every season: 1.01–1.25 and 0.75–0.99. The slopes are inside the 0.9–1.1 band. The error grows up the ladder, from 0.43 points for the snap share (R2) |
| Uncertainty | The chances are the uncertainty: each cell's chance of being on, calibrated as above. Each play's `certainty` (the likeliest lineup's expected share right) is honest within 1 point: 88.2% expected against 89.1% right on offense, 82.8% against 83.5% on defense (R12). Draws of whole lineups are a next step (Could be improved 2) |
| Leakage | The inputs view can't read the answer key (`player_play` isn't declared). Sample games rebuilt from a view at each game's own morning match the season run exactly: gap 0.0 (0 = none). Each season is fitted only on earlier seasons' answer keys (R8) |
| Football sanity | Every play has 11 a side in both lineups (100%). The chances add to 11 within 0.002 a play, and to each player's target within 0.04. Named players are pinned at 1. In the snap-matched lineup, 99.3% of players are within a play of their snap count. Backs are on the field on all but 0.7% of plays (truly 1.1%). 11 personnel is under-called a little: 60% against 62% (R7). The CEO reviewed the results on 2026-11-12 |
| CEO spot-check | Done (2026-11-12): the inputs' logic, family by family, and two new inputs (The CEO's spot-check: the inputs; R9, R10) |

## Hunch verdicts
The exploration's verdicts stand for H32–H35, and H36–H38 (the CEO's review, 2026-11-12) were tested after the build ([explore/h36_38.py](explore/h36_38.py) → [h36_38.txt](explore/h36_38.txt)). The build adds the size of each idea as a model input: the log loss on open spots, pooled 2019–2024, offense / defense. Copied into [`HUNCHES.md`](../HUNCHES.md).

| # | Hunch | Verdict | Evidence, with its size |
|---|---|---|---|
| H32 | A player's past participation tendencies predict whether he's on each play | **held, small** | His own situational habits (from every earlier season) and his team's (from last season) beat the league's habits by 1.9% offense and 1.8% defense, and by 1.7–2.1% in every season. The biggest gain is at quarterback, where history beats the snap share by 5.8%: backups come in blocks |
| H33 | Each team or coach has its own substitution habits in certain situations | **held** | The team's habits enter with the player's (above). The team's third-down habit is the largest team weight for defensive backs (+2.8) and linebackers (+1.7) in the 2024 fit. **But held out, it adds nothing on top of the players' own habits** (+0.03% / +0.01%, R9): what a team does is mostly what its players do. The coach's habit shows up in pairs instead (H37) |
| H34 | Fatigue on a drive and consecutive touches predict who comes off | **held in part** | Inside the sequence rung, the snap number in the drive lowers the chance of staying on in every group, most for the defensive line (−0.62 against −0.14 to −0.41 elsewhere). The build doesn't separate it from the memory: the whole sequence rung adds 3.8% / 3.3% over history. Consecutive touches stay out (F4) |
| H35 | Players have their own patterns across consecutive plays | **held in part** | Each player's return rate (on again after a snap off) carries weight on defense and for backs, receivers and quarterbacks (defensive backs +1.3, backs +0.8, the defensive line +0.7), not for tight ends or the offensive line. It's part of the sequence rung's 3.8% / 3.3%, every season 2.9–4.2%. "Two more snaps after a reception" stays noise (F5). **Held out, the stay and return rates add nothing on top of the two snaps of memory** (+0.02% / +0.02%, R9) |
| H36 | Certain players act as tandems ("maybe Steve and Jerry both tend to leave the field at the same intervals or same time") | **held** | Per pair of part-timers in a game (619,000 pair-games, 2019–2024), the correlation of their changes between snaps. 9.9% of pairs move together strongly (above +0.5) against 0.3% by chance (time-shifted), and 2.8% swap strongly (below −0.5) against 0.2%. The strongest tandems are whole units (a backup quarterback with backup linemen, +0.49) and defensive backs (+0.24, packages); the strongest swaps are two backs (−0.23) and two tight ends (−0.08). **A pair's habit repeats:** odd weeks against even weeks r 0.83 (offense) and 0.81 (defense), the same pair on the same team next season 0.69 and 0.56. **The model misses pairs together, and those misses repeat too** (r 0.82 / 0.80): the pairs aren't in the model. **As an input** (`pn`: his pair habit with each teammate named on the snap), held out 2023–2024: **0.47% better log loss on offense and 0.12% on defense**, in both seasons; now in the model (decision 0030, call 11). Claude expected swaps more than tandems and tandems on the defensive line: wrong on both counts (the defensive line's pairs are the weakest, +0.03) |
| H37 | A coach switches two positions at once ("substitute the tight end at the same time as substituting the second string wide receiver") | **held** | The CEO's example is the league's third-strongest swap: the second tight end for the third receiver (−0.18, 11 ↔ 12 personnel), after the two backs (−0.43) and the two tight ends (−0.19). On defense the strongest tandems are the top two pass rushers (+0.36) and the fifth defensive back with the top pass rusher (+0.31): the passing-down package. **Teams differ from the league** (spread 0.12 for TE2–WR3), and a team's role-pair habits repeat: odd/even weeks r 0.62 offense, 0.65 defense; next season with the same head coach 0.45 / 0.50, with a new one 0.13 / 0.20. **The habit is the coach's.** For defense predictions (the CEO's "might be powerful"): the offense's personnel adds nothing to the defense's chances (0.00% expected, 0.46% even if known exactly); the defense's own pairs are where its tandems live. Claude expected this: the league swap strong, team versions modest and following the coach |
| H38 | Schemes influence which players or positions a coach substitutes | **held, moderate** | Over 192 team-seasons, teams heavy in two-tight-end and two-back sets substitute more (r 0.33), teams living in 11 personnel less (−0.38); dime-heavy (0.36) and man-heavy (0.31) defenses more, nickel-heavy and two-high defenses less (−0.28). Beyond last season's habit, a change in scheme moves substitution: more 11, fewer subs (−0.32); more nickel, fewer (−0.28); more dime, more (+0.21). Claude expected weak to moderate. Not an input: the charted scheme traits are known only after the season |

## Terms
New in `docs/GLOSSARY.md`: **known spots** and **open spots**, **on-field chance**, **snap-matched best guess**, **likeliest lineup**, **position mix**.

## Findings
Numbered R1–R12 so they don't clash with the exploration's F1–F8. R9–R12 come from the CEO's review (2026-11-12). Cite as `participation-live#R1`.

**R1. The sequence model has real signal, and every rung adds to it in every season.**
- **The sizes, pooled, offense / defense:**
  - situation and the competition in his group over the snap share: 3.7% / 1.4%;
  - history (his, his team's, his pair habits) over situation: 2.3% / 2.0%;
  - the sequence over history: 3.3% / 3.2% (every season 2.8–3.5%);
  - in all, 9.0% / 6.4% over the snap share (every season 8.6–9.4% and 6.2–6.7%).
- **The shuffled version** scores exactly what the situation rung scores (0.427 and 0.492). So history and the sequence are the whole gain beyond situation, and none of it is chance.
- **The sequence is the big lever, as F8 said.** It gets about a fifth of what an oracle that knew the snap before would gain, because here the snap before is itself an estimate.
- **By group, the sequence helps most:**
  - at quarterback: log loss 0.21 to 0.13;
  - for backs: 0.390 to 0.356 (9%);
  - for defensive backs (5%) and linebackers (3%).
- It helps least for receivers and tight ends (about 1%).

**R2. The chances are calibrated, and slightly under-confident at the top rung.**
- The calibration error is 1.10 points on offense and 0.82 on defense, against a bar of 3.
- The slopes are 1.07 and 1.05: actual rates spread a little wider than the chances. That's inside the 0.9–1.1 band.
- The error grows up the ladder (snap share 0.43 points), because sharper chances have more room to miss.
- No recalibration was applied.

**R3. The two lineups trade per-play accuracy against faithfulness to the game.** The sequence model, pooled 2019–2024:

| | Snap-matched (`best`) | Likeliest (`likeliest`) |
|---|---|---|
| Of each play's 11 right, offense / defense | 87.4% / 80.9% | 89.1% / 83.5% |
| Open spots right, offense / defense | 72.1% / 70.9% | 76.0% / 74.9% |
| Plays with all 11 right, offense / defense | 17.3% / 5.4% | 23.9% / 10.9% |
| Players within a play of their snap count | 99.3% | 25.8% |
| Plays off the true snap count, per player | 0.7 | 6.7 |
| Substitutions a snap (truly 1.24) | 1.24 | 0.66 |
| Team-game substitution rate, r with the truth | 0.51 | 0.52 |

- The snap-matched lineup gives up about 4 points of open spots to keep the totals and the rhythm of substitution.
- On open spots alone, it only ties the snap share's likeliest lineup on offense (72.0%) and trails it on defense (71.9%).
- The exploration's comparable number (top picks with history: 74.6% / 73.3% on 2022–2024) is close to this build's history rung (74.8% / 73.6% on 2019–2024).

**R4. Without the position mix, the lineups weren't football; with it, they are.**

| Snap-matched lineup | Without the mix | With the mix |
|---|---|---|
| Plays with the right personnel (backs and tight ends) | 40% | 63% |
| Plays with no running back (truly 1.1%) | 8.9% | 0.7% |
| 11 personnel (truly 62%) | 39% | 60% |
| Team-game 11 rate, r with the truth | 0.58 | 0.88 |
| Open spots right, offense | 72.6% | 72.1% (−0.4 point) |
| Plus-minus (pass rate over expected), r with the truth | 0.38 | 0.45 |

- The mix costs the likeliest lineup 0.4 points of open spots, and lifts its personnel from 56% to 63%.
- Before the spot-check's two inputs it was 35% → 60%; the competition input helped the no-mix lineup most (plays with no back 13.2% → 8.9%).
- Per-player chances don't know a play needs about one back. The count per group does.

**R5. The hardest players are the rotations: the defensive line, backs and tight ends.** Open spots right in the snap-matched lineup:
- quarterbacks 94%;
- defensive backs 81%;
- the offensive line 80%;
- receivers 74%;
- linebackers 72%;
- tight ends 66%;
- backs 64%;
- the defensive line 62%.

The likeliest lineup lifts most groups by 1–6 points (backs 66%, tight ends 71%, the defensive line 68%); quarterbacks drop 1.9. The spot-check's inputs lifted backs by 1.4 points and quarterbacks by 1.0.

**R6. A player's plus-minus from the map is a noisy copy of the true one.** This is a player's team pass rate over expected with him on minus with him off, per player-season, for players with 20 or more weight in the truth.

| | Pass rate over expected, r | Mean miss | Pace over expected, r |
|---|---|---|---|
| Sequence chances (soft: 60% counts 0.6) | 0.42 | 5.5 points | 0.50 |
| Snap-matched lineup | 0.45 | 6.7 points | 0.41 |
| Likeliest lineup (190 players can't be computed) | 0.31 | 11.0 points | 0.28 |
| Snap share's snap-matched lineup | 0.29 | 7.2 points | 0.14 |

- The true plus-minus spreads 7.7 points (SD), so the mean miss is nearly as big as the spread.
- **The chances are better within a group:** tight ends 0.61, receivers 0.58, linebackers 0.49. The snap-matched lineup is better for backs (0.49 against 0.39).
- The spot-check's inputs lifted the chances' plus-minus most (0.35 → 0.42).
- Pooled across groups, the chances lose, because soft weights shrink every plus-minus toward 0.
- The sequence model roughly doubles the snap share's fidelity, but it isn't a measurement.

**R7. Team personnel rates come out well; single plays less so.**
- **Per play:**
  - exact personnel on 63% of plays;
  - the right number of backs on 86%;
  - the right number of tight ends on 71%.
- **Per team-game,** the 11 rate correlates 0.88 with the truth and the 12 rate 0.77.
- **11 is under-called a little:** 60% against 62% (56% before the spot-check's inputs).
- The personnel comes from the mix, so the history rung gets the same (63.1%) and the snap share less (54.2%).

**R8. Point in time holds.**
- The inputs view refuses `player_play`.
- Sample games rebuilt from a view at each game's own morning match the season run: gap 0.0.
- Each test season is fitted on the three seasons before it, and history uses only earlier seasons' answer keys.

**R9. Three families carry the model; two of the CEO's earlier ideas add nothing on top of the rest** (the CEO's spot-check, 2026-11-12). Each family zeroed in training and test, held-out 2023–2024, offense / defense, change in log loss on open spots:
- **his own habits by situation** (H32): +1.9% / +1.8%, the most valuable after the memory;
- **the situation:** +1.5% / +0.8%;
- **the snap in the drive** (H34): +0.03–0.07% / +0.12%, small but in both seasons, and on defense;
- **his team's habits** (H33): +0.03% / +0.01%, nothing on top of the players' own;
- **his stay and return rates** (H35): +0.02% / +0.02%, nothing on top of the two snaps of memory.

The last two aren't noise (removing them is slightly worse in both seasons), so they stay. Both were consistent traits in the exploration; the model already gets them from the players' habits and the memory.

**R10. The competition in a player's group and his pair habits were missing, and add 2% on offense** (decision 0030, call 11).
- **The competition** (his group's teammates named on the snap, its every-snap players): +1.1% offense, 0.0% defense, almost all for backs (log loss 0.373 → 0.356) and tight ends. A second back named on the snap pushes the first off.
- **His pair habits** (`pn`, the CEO's tandems): +0.5% offense, +0.1% defense, for backs, linebackers and the defensive line.
- **In the rerun** the sequence rung improves by 1.8–2.2% on offense and 0.10–0.16% on defense in every season 2019–2024. That includes 2019–2022, which played no part in choosing them. The likeliest lineup's open spots right go from 75.3% to 76.0% on offense (74.8% to 74.9% on defense), and exact personnel from 60% to 63%.

**R11. Knowing each play's personnel would be worth 4–6 points of open spots, but it isn't known by the morning after.**
- Per-play personnel is only in nflverse participation, after the season. FTN's free charting (1–2 weeks after a game) has the backfield, box and pass-rusher counts but no personnel.
- An oracle with each play's true count per position group lifts the likeliest lineup's open spots from 75.3% to 81.5% on offense and from 74.8% to 78.5% on defense (the model before R10).
- The offense's personnel adds almost nothing to the defense's chances: 0.00% from the offense's expected counts, 0.46% even from its true ones.

**R12. Each play's certainty is honest.** `certainty` is the likeliest lineup's expected share right: (known spots + the chances of the open players it picked) / 11.
- **On average,** offense 88.2% expected against 89.1% right, defense 82.8% against 83.5%: under-confident by under 1 point, inside the 3-point bar. It isn't recalibrated.
- **It sorts plays.** By tenths of plays, the share right climbs steadily from 81% to 96% on offense and from 75% to 91% on defense, with each tenth's certainty within 1.2 points of its share right.
- An expected count needs no independence between players, so the correlated misses within a pair (H36) don't bias it. It has no range of its own.

## The CEO's spot-check: the inputs (2026-11-12)
The CEO: "can you please spot check the meta logic of the inputs into the model? I want to make sure we are selecting the right features for the model to learn to correctly predict who was on the field for each play."

**How it was checked.** Held-out 2023 and 2024, each trained on the three seasons before (as in the backtest), sequence rung, scored on open spots (log loss, and open spots right in the likeliest lineup). Each family of inputs was zeroed in training and test to measure what it adds; candidate inputs the model didn't have were added to measure what they would. Scripts and numbers: [build/spot_inputs_round1.py](build/spot_inputs_round1.py) → [round1.txt](build/spot_inputs_round1.txt), [build/spot_inputs.py](build/spot_inputs.py) → [spot_inputs.txt](build/spot_inputs.txt).

**What the model is told, why, and what each is worth.** Change in log loss when the family is removed (mean of 2023–2024, offense / defense; positive = the family helps). Round 1 is the model before this check; round 2 the model with the two new inputs.

| Family | What it is | Known by the morning after? | Why it's there | Worth |
|---|---|---|---|---|
| Snap counts | Each player's snaps → his share (`ls`) and his target; every-snap players pinned | Yes (next-morning snap counts) | The strongest single fact: how much he played (F1) | The base: the snap share alone is the bottom rung; R1's ladder is measured from it |
| Named players | Passer, rusher, receivers, tacklers... pinned on their snaps, and evidence for the snaps around them through the memory | Yes (play-by-play) | Certain facts about the play | Pinned on their snaps; the memory spreads them to the snaps around |
| Two snaps of memory | Was he on the snap before and the one before that, same drive or not, no-huddle | Yes (inferred along the game) | Substitutions happen between series, not every snap (F6, F8) | 3.8% / 3.3% (the sequence rung over history, R1) |
| The situation | Down, distance, field, clock, score, shotgun, no-huddle, pass | Yes (play-by-play) | Packages follow the situation | **+1.5% / +0.8%** |
| His own habits (H32) | His on-field beyond his share, by situation, every earlier season | Yes (earlier seasons' answer key) | Third-down backs, red-zone tight ends | **+1.9% / +1.8%**: the most valuable family after the memory |
| His team's habits (H33) | The team's, last season, same head coach | Yes | Coaches' packages | **+0.03% / +0.01%** (round 2: +0.04% / +0.01%): nothing on top of the players' own habits |
| His stay and return rates (H35) | How often he stays on, or comes back, beyond his share | Yes | Players' own rhythm | **+0.02% / +0.02%** (round 2: +0.03% / +0.01%): nothing on top of the memory |
| Snap in the drive (H34) | Fatigue | Yes | Linemen rotate as a drive goes on | **+0.07% / +0.12%** (round 2: +0.03% / +0.12%), both seasons: small, real on defense |
| Competition in his group (new) | His group's teammates named on the snap; his group's every-snap players | Yes (play-by-play, snap counts) | A second named back pushes the first off | Round 2: **+1.14% / −0.02%** |
| Pair habits (new, H36, H37) | How often he was on with each teammate named on the snap, beyond his share, from earlier seasons | Yes (earlier seasons' answer key) | Tandems and swaps | Round 2: **+0.47% / +0.12%** |

**What it wasn't told, and now is** (decision 0030, call 11). Together, round 2: **2.16% better on offense and 0.13% on defense** than the model without them (2.28% / 0.15% in 2023, 2.04% / 0.11% in 2024); open spots right in the likeliest lineup 75.2% → 75.8% on offense.
- **The competition in his group on the snap.** The chances were balanced to 11 a play, but a player's own chance didn't know that a second back named on the snap pushes the first one off. Round 1 added `gn` (his group's teammates named on the snap) and `gfull` (his group's every-snap players): **−1.65% offense** (backs 0.386 → 0.360, tight ends 0.488 → 0.485), −0.08% defense, open spots right +0.6 points on offense, in both seasons. Round 1's version had a flaw (its training rows didn't see full-timers, so `gfull` was always 0 there and `gn` counted fewer players than in test). The model now computes both over every candidate. **Round 2, the fixed version: removing it costs 1.14% on offense (1.24% and 1.05% by season) and nothing on defense (−0.02%).** It's a backfield and tight-end input: backs' log loss 0.373 → 0.356.
- **Pair habits with the teammates named on the snap** (`pn`, from H36 and H37 below). Round 2: **removing it costs 0.47% on offense and 0.12% on defense** (0.53% / 0.15% in 2023, 0.42% / 0.10% in 2024), most for backs (0.360 → 0.356), linebackers and the defensive line. The CEO's tandems help both sides, defense included.

**Tried and left out.**
- **The offense's personnel, for the defense** (the CEO: "this input pattern might be powerful for defense predictions"). The offense's expected backs, tight ends and receivers on the snap (from its own chances): **0.00%**. Even the offense's *true* counts (an oracle) take only 0.46% off the defense's log loss, mostly for defensive backs. The defense's own named players and snap counts already carry it.

**The CEO's question: are the chances conditioned on each play's known personnel?**
- **No, because it isn't known by the morning after.** Per-play personnel (`offense_personnel`, `defense_personnel`) is only in nflverse participation, published after the season. FTN's free charting arrives 1–2 weeks after a game and has the backfield count, the box count and pass rushers, but no personnel.
- **What the model is conditioned on:** the named players, every player's snap count, 11 a side, and (for the lineups) each play's position mix, which comes from the summed chances.
- **What personnel would be worth** (an oracle on 2019–2024): with each play's true count per position group, the likeliest lineup's open spots right would go from **75.3% to 81.5%** on offense and **74.8% to 78.5%** on defense (the model before the two new inputs). That's the prize if a free source of per-play personnel ever arrives by the morning after.

**Are we selecting the right inputs?**
- The inputs were chosen by football logic and the exploration's hunch tests, then each family's worth measured on held-out seasons. The two big ones (his own habits, the memory) and the situation carry the model; the snap counts and named players are its facts.
- Two families add nothing measurable on top of the others: the team's habits (H33) and the stay and return rates (H35). They aren't noise (removing them is slightly worse in both seasons), so they stay (decision 0030, call 11).
- **A caveat on rule k** (feature selection inside the folds): adding the competition and pair inputs was decided on 2023–2024, which are also test seasons. 2019–2022 played no part in the choice, so the rerun's numbers for those seasons are the clean check; the 2025 vault stays closed.

## The ladder
Each rung is fitted per position group on the three seasons before the test season, then balanced along the game (decision 0030, calls 4 and 5). The scores are pooled 2019–2024, offense / defense; "open right" counts only the cells the model fills.

| Rung | Adds | Log loss | Open right, snap-matched | Open right, likeliest | Calibration (points) |
|---|---|---|---|---|---|
| share | his snap share in the game | 0.444 / 0.499 | 64.9% / 64.5% | 72.0% / 71.9% | 0.43 / 0.16 |
| league | the situation (down, distance, field, clock, score, shotgun, no-huddle, pass), the snap in the drive, the competition in his group on the snap | 0.427 / 0.492 | — | 74.0% / 72.8% | 0.46 / 0.31 |
| history | his habits by situation (every earlier season), his team's (last season, same coach), his pair habits with the teammates named on the snap | 0.418 / 0.482 | 69.9% / 68.3% | 74.8% / 73.6% | 0.67 / 0.58 |
| **sequence** | the two snaps before, same drive or not, no-huddle, his stay and return rates | **0.404 / 0.467** | **72.1% / 70.9%** | **76.0% / 74.9%** | 1.10 / 0.82 |
| shuffled | the sequence model with history and memory shuffled | 0.427 / 0.492 | — | 74.0% / 72.8% | 0.45 / 0.31 |

- **Takeaways each rung applied:**
  - The snap share stays the strongest single input in every group (weights +0.55 to +0.87 a unit).
  - History and memory enter as interactions with it.
  - Consecutive touches and "after a reception" were left out (F4, F5).
  - The no-huddle flag is a feature, not a lock (F2).
  - The spot-check's ablations (R9): the situation, his own habits and the memory carry the model; his team's habits and his stay and return rates add almost nothing on top.
- **The ladder stops at the sequence rung.** A tree rung wasn't tried (Could be improved 5).

## Where it misses
The miss lenses run on player-game amount models. This is a play-level probability model, so its misses are read by position group and by the kind of measure built from it.
- **By group (R5):** the rotations. The defensive line (62% of open spots), backs (63%) and tight ends (66%) are the hard cells; quarterbacks and defensive backs are easy. The defensive line also has the highest log loss (0.55).
- **Personnel (R7):** 11 is under-called by 2 points (6 before the spot-check's inputs). The mix's counts come from summed chances, which likely lean toward a second tight end or back when two are each partly likely.
- **Substitution:** the snap-matched lineup's per-game substitution rate correlates only 0.51 with the truth. The average is right (1.24 against 1.24), but which games are busy isn't.
- **Plus-minus (R6):** weakest for the defensive line (r 0.20–0.37).
- **Not scored:** the 9% of play-sides whose true lineup isn't a complete 11.

## The case against (2026-11-12, written before asking to merge)
1. **The use the brief named first is weak.**
   - In-season plus-minus from the map correlates 0.42–0.50 with the true plus-minus (the chances), and misses by most of the true spread.
   - If the point of the expert is a player's on/off effect this season, it doesn't deliver that yet.
   - Part of the gap may be that a season's true plus-minus is itself noisy (a small difference of two means), so a correlation against it understates usefulness. That wasn't tested.
2. **The headline lineup breaks the snap counts.** The likeliest lineup (the CEO's call) is the most accurate per play, but drifts 7 plays a player from his snap count and substitutes half as often as real teams. A higher layer that counts snaps or substitutions from it will be wrong; those need `best`.
3. **The gain over the snap counts is modest.**
   - The snap counts do most of the work (F1).
   - The full model takes 9% off the snap share's log loss, and lifts the likeliest lineup's open spots by 4.0 points on offense and 3.0 on defense.
   - It also takes 5 rungs, an optimizer and two linear programs.
4. **The truth is nflverse's participation data, unchecked.** Its own errors are baked into every score.
5. **Only clean plays are scored:** play-sides with a complete true 11 (91%). The rest are likely worse.
6. **Calibration gets worse as the model gets sharper** (0.43 to 1.10 points). It's still inside the bar, and recalibration wasn't tried.
7. **Live use depends on the snap counts arriving by the morning after.** A late upload delays the whole map. 2026 and the 2025 vault aren't scored yet.
8. **Versions tried:** 5 rungs and 3 versions of the best guess, chosen on these same seasons. The position mix was designed after seeing R4's failure. The vault is the clean test.
9. **The two new inputs were chosen on test seasons** (2023–2024, the spot-check). Rule k wants selection inside the folds. 2019–2022 had no part in the choice, and they gained the same (offense 1.8–2.1%, defense 0.10–0.16%, R10); the vault is the cleaner check.
10. **The pair habits are partly a model artifact.** The chances treat players one at a time, so any two players who swap get misses that move together whatever their habit. The misses' repeat (R10) overstates how much pair structure is left to find.

## Pitfalls
- **Newton raking didn't settle on sticky chains.** Plays added to 4.5–8 instead of 5 on a synthetic game. The convex dual with L-BFGS-B fixed it, with an exact gradient (decision 0030, call 5).
- **The best guess's chances were right but its lineups weren't football** (R4). The per-player chances and totals don't know that a play needs about one back. Check the position mix of any lineup built from per-player chances.
- **Rounding each play's counts alone breaks the totals.** A team's only tight end at 60% rounded up on every snap. Round over the whole game (decision 0030, call 6).
- **The gateway loaded every season for every view.** Building one season's grid ran out of memory until each season used `TableSource(seasons=[s-1, s])`.
- **A plus-minus from the likeliest lineup can't be computed for many players.** The likeliest lineup puts some part-timers on every snap or none, so they have no "off" (or "on") snaps. The fit-for-use script reports how many are missing rather than dropping them silently.
- **Soft plus-minus shrinks toward 0.** Weighting by the chance pulls every player's plus-minus in, which hurts a correlation pooled across groups (R6). Compare within a group.

## Not looked at
- **The 2025 vault.** It opens once, at the final check.
- **Special teams.** The grid is scrimmage plays only; kicks and returns aren't reconstructed.
- **Players with no snap-count row.** A player who was on the field but missing from the snap counts can't be a candidate. The truth's lineups with 11 cover 91% of play-sides; the rest aren't scored.
- **Depth charts and the injury report as inputs.** The brief listed them, but the snap counts already say who played and how much, so they were left for a later rung.
- **Routes per play** (the brief's third fit-for-use measure): needs the route data, which is retrospective only.
- **This season's estimated games as history** (the brief's in-season "two sources"): the build uses earlier seasons' true participation only, so its errors can't compound.
- **H34 apart from the memory** beyond the spot-check's ablation of the snap in the drive (R9).

## Could be improved
1. **Let the play's own events shift unnamed players** (an emission model). A deep pass makes the third receiver likelier; a goal-line run makes the second tight end likelier. Today only named players are evidence.
2. **Draws of whole lineups** from the chains, under the totals. These give a causal model honest uncertainty, and a plus-minus a range.
3. **A personnel model from each team's habits** (its 11 and 12 rates by situation), feeding the mix instead of summed chances, to fix the 11 under-call (R7).
4. **Depth charts and the injury report** as inputs: a backup's chance when the starter is limited.
5. **A tree rung** (rule k's next step), especially for the defensive line.
6. **Recalibration** inside the training folds (R2).
7. **This season's estimated games as history,** measured against truth-only history.
8. **A post-game moment kind in the shared harness,** once a second post-game expert exists (decision 0030, alternatives).
9. **Pairs inside the chain** (H36): today a pair habit enters only when one of the pair is named. Moving pairs together along the game (joint transitions for the strongest tandems and swaps) would use the habit on every snap.
10. **Schemes as a prior** (H38): the team's scheme from the map itself (its 11 and 12 rates so far this season) or from completed seasons, to set how much it substitutes.
11. **Per-play personnel** would lift the likeliest lineup's open spots by 4–6 points (R11), if a free source arrives by the morning after.

## Don't redo
- **Each play's top picks as the only lineup.** It breaks the snap totals by about 7 plays a player (F7, R3).
- **A best guess without the position mix** (R4), or a mix rounded play by play (Pitfalls).
- **Newton raking for the balancing** (Pitfalls).
- **Depth charts as the baseline to beat.** About 65% right in the exploration, far below the snap share (72–73%).

## Interface card
Also in this project's `interface` block in `registry.yaml`.

| | |
|---|---|
| **Inputs** | `play.pbp` (situation, named players, no-huddle, drive), `player_game` (roster, snaps), `team_game.pregame` (head coach), and earlier seasons' `player_play.on_field` as the answer key (retrospective view, history and training only) |
| **Outputs** | `outputs/participation-live/<run_id>/history.parquet`: one row per candidate and scrimmage snap, with `quantity` `on_field_chance`, `mean` = the chance (q10–q90 equal it), `best` (snap-matched best guess), `likeliest`, `certainty` (the play's expected share of the likeliest 11 right: a weight or propensity for downstream models), `side`, `team`, `n` (the team's snap number), `as_of`, `train_end` |
| **Level of detail** | player-play, both sides |
| **Interval** | every completed game, 2019–2024 walk-forward (2016–2018 train only) |
| **Cadence** | in_season |
| **Known at** | the first weekly run at least a day after kickoff (snap counts are in the morning after) |
| **How to use it** | **The lineup to use is `likeliest`** (the CEO, 2026-11-12): each play's likeliest 11. Use `mean`, the chance, wherever a measure can take weights: a player 60% likely counts 0.6 on and 0.4 off. Use `best` only when a model needs lineups whose totals agree with the snap counts (snaps by situation, substitution rates). Don't treat either lineup as observed: for effects per player, carry the chance or draw lineups, and compare plus-minus within a position group (R6). In training, read only the walk-forward history (rule e) |
| **Feeds** | in-season player plus-minus and value, context-live and voe-live (who was on), routes and roles per play, fantasy usage, the game simulator; later, causal effects per player and play |

## Open questions for the CEO
Answered 2026-11-12 (the CEO, word for word in [BRIEF.md](BRIEF.md)):
1. **Which lineup?** "higher layers should use the likeliest 11 players on each play": `likeliest` is the headline (decision 0030, call 7).
2. **Vetoes on the technical calls?** "no vetos" (calls 1–10). Call 11 (the two new inputs) came after, from the spot-check: open for veto.
3. **The spot-check:** "the meta logic of the inputs into the model", plus "an estimate of certainty for each play": done above (The CEO's spot-check: the inputs; R9–R12).
4. **Merge?** "do not merge now, but very soon."

Still open:
1. **A second edition of the map, 1–2 weeks after each game?** (a product call)
   - **Why it matters:** each play's personnel would be worth 4–6 points of open spots (R11). FTN's free charting arrives 1–2 weeks after a game with the backfield, box and pass-rusher counts. It has no personnel, but those counts would pin some of it.
   - **Options:** (a) keep the morning-after map only; (b) add a second, later edition that re-runs each game once FTN arrives, for uses that can wait (season plus-minus, value, the retrospective models). FTN is already a listed free source, so no new data.
2. **Merge now?** Call 11 (the two new inputs) is open for veto; everything else is answered.
