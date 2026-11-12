# Results: Participation inference (`participation-live`)

**Date:** 2026-11-12 · **Status:** validating (not merged; the CEO's calls below) · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** `participation-live` · **Technical calls:** [decision 0030](../../docs/decisions/0030-participation-live.md) · **Code:** `pcf.experts.participation_live`

## In short
**It maps every play.** For each scrimmage play of 2019–2024, with each season held out and trained on the three before, it gives:
- every possible player's chance of being on the field;
- two lineups built from those chances.

What it gets right:
- **The chances beat every simpler version, in every season.** Log loss is 7.1% (offense) and 6.3% (defense) lower than the snap share alone, and 5.7% and 5.0% lower than a shuffled version of itself (R1).
- **The chances are calibrated** within 1.2 points (R2).
- **The snap-matched lineup:**
  - gets 87% of each offensive play's 11 right, and 81% on defense;
  - keeps 99.3% of players within one play of their snap count;
  - substitutes as often as real teams do: 1.22 players a snap, against a true 1.24 (R3).
- **The likeliest lineup** gets more right per play (89% and 83%), but drifts 7.5 plays a player from his snap count and substitutes half as often.
- **The position mix fixed the personnel.** The right number of backs and tight ends is now on 60% of plays, against 35% before (R4).

**The weak spot is the use the brief named first.** A player's on/off plus-minus built from the map correlates only 0.35–0.49 with the true one (R6). In-season plus-minus from this map is a noisy feature, not a measurement.

**Scores:** [build/backtest.txt](build/backtest.txt) (every rung, pooled and by season, by position group) and [build/fit_for_use.txt](build/fit_for_use.txt) (plus-minus and personnel against the truth). MLflow run `956a289679864800af8292a429e2a23b` (4,387 s).

**Vault:** closed; 2025 is untouched. Confirmation is the walk-forward 2019–2024 (each season trained on the three before), plus 2026 live.

**Versions tried:**
- one model per rung (5 rungs);
- the best guess three ways: no position mix; a mix with a step either side; the mix rounded over the whole game (the final).

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal / no noise | Yes. The sequence model beats its shuffled self by 5.7% log loss on offense and 5.0% on defense, pooled. In every season the margin is 5.2–6.2% and 4.8–5.3%. Every rung beats the one below in every season (R1) |
| Calibration | Inside the 3-point bar. Offense: 1.21 points, slope 1.08. Defense: 0.79 points, slope 1.05. Every season: 1.10–1.39 and 0.71–0.93. The slopes are inside the 0.9–1.1 band. The error grows up the ladder, from 0.43 points for the snap share (R2) |
| Uncertainty | The chances are the uncertainty: each cell's chance of being on, calibrated as above. A lineup has no range of its own; draws of whole lineups are a next step (Could be improved 2) |
| Leakage | The inputs view can't read the answer key (`player_play` isn't declared). Sample games rebuilt from a view at each game's own morning match the season run exactly: gap 0.0 (0 = none). Each season is fitted only on earlier seasons' answer keys (R8) |
| Football sanity | Every play has 11 a side in both lineups (100%). The chances add to 11 within 0.002 a play, and to each player's target within 0.04. Named players are pinned at 1. In the snap-matched lineup, 99.3% of players are within a play of their snap count. Backs are on the field on all but 2.7% of plays (truly 1.1%). 11 personnel is under-called: 56% against 62% (R7). The CEO's review is pending |
| CEO spot-check | Pending: the CEO picks one finding or call |

## Hunch verdicts
The exploration's verdicts stand. The build adds the size of each idea as a model input: the log loss on open spots, pooled 2019–2024, offense / defense. Copied into [`HUNCHES.md`](../HUNCHES.md).

| # | Hunch | Verdict | Evidence, with its size |
|---|---|---|---|
| H32 | A player's past participation tendencies predict whether he's on each play | **held, small** | His own situational habits (from every earlier season) and his team's (from last season) beat the league's habits by 1.9% offense and 1.8% defense, and by 1.7–2.1% in every season. The biggest gain is at quarterback, where history beats the snap share by 5.8%: backups come in blocks |
| H33 | Each team or coach has its own substitution habits in certain situations | **held** | The team's habits enter with the player's (above). The team's third-down habit is the largest team weight for defensive backs (+2.8) and linebackers (+1.7) in the 2024 fit |
| H34 | Fatigue on a drive and consecutive touches predict who comes off | **held in part** | Inside the sequence rung, the snap number in the drive lowers the chance of staying on in every group, most for the defensive line (−0.62 against −0.14 to −0.41 elsewhere). The build doesn't separate it from the memory: the whole sequence rung adds 3.8% / 3.3% over history. Consecutive touches stay out (F4) |
| H35 | Players have their own patterns across consecutive plays | **held in part** | Each player's return rate (on again after a snap off) carries weight on defense and for backs, receivers and quarterbacks (defensive backs +1.3, backs +0.8, the defensive line +0.7), not for tight ends or the offensive line. It's part of the sequence rung's 3.8% / 3.3%, every season 2.9–4.2%. "Two more snaps after a reception" stays noise (F5) |

## Terms
New in `docs/GLOSSARY.md`: **known spots** and **open spots**, **on-field chance**, **snap-matched best guess**, **likeliest lineup**, **position mix**.

## Findings
Numbered R1–R8 so they don't clash with the exploration's F1–F8. Cite as `participation-live#R1`.

**R1. The sequence model has real signal, and every rung adds to it in every season.**
- **The sizes, pooled, offense / defense:**
  - situation over the snap share: 1.6% / 1.3%;
  - history over situation: 1.9% / 1.8%;
  - the sequence over history: 3.8% / 3.3% (every season 2.9–4.2%);
  - in all, 7.1% / 6.3% over the snap share.
- **The shuffled version** scores exactly what the situation rung scores (0.437 and 0.492). So history and the sequence are the whole gain beyond situation, and none of it is chance.
- **The sequence is the big lever, as F8 said.** It gets about a fifth of what an oracle that knew the snap before would gain, because here the snap before is itself an estimate.
- **By group, the sequence helps most:**
  - at quarterback: log loss 0.27 to 0.14;
  - for backs: 0.425 to 0.384 (10%);
  - for defensive backs (5%) and linebackers (3%).
- It helps least for receivers and tight ends (about 1%).

**R2. The chances are calibrated, and slightly under-confident at the top rung.**
- The calibration error is 1.21 points on offense and 0.79 on defense, against a bar of 3.
- The slopes are 1.08 and 1.05: actual rates spread a little wider than the chances. That's inside the 0.9–1.1 band.
- The error grows up the ladder (snap share 0.43 points), because sharper chances have more room to miss.
- No recalibration was applied.

**R3. The two lineups trade per-play accuracy against faithfulness to the game.** The sequence model, pooled 2019–2024:

| | Snap-matched (`best`) | Likeliest (`likeliest`) |
|---|---|---|
| Of each play's 11 right, offense / defense | 87.1% / 80.8% | 88.8% / 83.5% |
| Open spots right, offense / defense | 71.5% / 70.8% | 75.3% / 74.8% |
| Plays with all 11 right, offense / defense | 16.5% / 5.4% | 22.6% / 10.8% |
| Players within a play of their snap count | 99.3% | 25.8% |
| Plays off the true snap count, per player | 0.7 | 6.8 |
| Substitutions a snap (truly 1.24) | 1.22 | 0.64 |
| Team-game substitution rate, r with the truth | 0.48 | 0.49 |

- The snap-matched lineup gives up about 4 points of open spots to keep the totals and the rhythm of substitution.
- On open spots alone, it is behind even the snap share's likeliest lineup (72.0% / 71.9%).
- The exploration's comparable number (top picks with history: 74.6% / 73.3% on 2022–2024) matches this build's history rung (74.0% / 73.5% on 2019–2024).

**R4. Without the position mix, the lineups weren't football; with it, they are.**

| Snap-matched lineup | Without the mix | With the mix |
|---|---|---|
| Plays with the right personnel (backs and tight ends) | 35% | 60% |
| Plays with no running back (truly 1.1%) | 13.2% | 2.7% |
| 11 personnel (truly 62%) | 33% | 56% |
| Team-game 11 rate, r with the truth | 0.55 | 0.87 |
| Open spots right, offense | 71.5% | 71.5% (−0.1 point) |
| Plus-minus (pass rate over expected), r with the truth | 0.38 | 0.46 |

- The mix costs the likeliest lineup 0.6 points of open spots, and lifts its personnel from 52% to 60%.
- Per-player chances don't know a play needs about one back. The count per group does.

**R5. The hardest players are the rotations: the defensive line, backs and tight ends.** Open spots right in the snap-matched lineup:
- quarterbacks 93%;
- defensive backs 81%;
- the offensive line 79%;
- receivers 73%;
- linebackers 72%;
- tight ends 66%;
- backs 63%;
- the defensive line 62%.

The likeliest lineup lifts most groups by 1–6 points; quarterbacks drop 0.8.

**R6. A player's plus-minus from the map is a noisy copy of the true one.** This is a player's team pass rate over expected with him on minus with him off, per player-season, for players with 20 or more weight in the truth.

| | Pass rate over expected, r | Mean miss | Pace over expected, r |
|---|---|---|---|
| Sequence chances (soft: 60% counts 0.6) | 0.35 | 6.1 points | 0.49 |
| Snap-matched lineup | 0.46 | 6.8 points | 0.41 |
| Likeliest lineup (294 players can't be computed) | 0.29 | 11.4 points | 0.30 |
| Snap share's snap-matched lineup | 0.29 | 7.2 points | 0.14 |

- The true plus-minus spreads 7.7 points (SD), so the mean miss is nearly as big as the spread.
- **The chances are better within a group:** tight ends 0.60, receivers 0.56, linebackers 0.48. The snap-matched lineup is better for backs (0.55).
- Pooled across groups, the chances lose, because soft weights shrink every plus-minus toward 0.
- The sequence model roughly doubles the snap share's fidelity, but it isn't a measurement.

**R7. Team personnel rates come out well; single plays less so.**
- **Per play:**
  - exact personnel on 60% of plays;
  - the right number of backs on 82.5%;
  - the right number of tight ends on 70%.
- **Per team-game,** the 11 rate correlates 0.87 with the truth and the 12 rate 0.78.
- **11 is under-called:** 56% against 62%.
- The personnel comes from the mix, so the history rung gets the same (60.6%) and the snap share less (54.2%).

**R8. Point in time holds.**
- The inputs view refuses `player_play`.
- Sample games rebuilt from a view at each game's own morning match the season run: gap 0.0.
- Each test season is fitted on the three seasons before it, and history uses only earlier seasons' answer keys.

## The ladder
Each rung is fitted per position group on the three seasons before the test season, then balanced along the game (decision 0030, calls 4 and 5). The scores are pooled 2019–2024, offense / defense; "open right" counts only the cells the model fills.

| Rung | Adds | Log loss | Open right, snap-matched | Open right, likeliest | Calibration (points) |
|---|---|---|---|---|---|
| share | his snap share in the game | 0.444 / 0.499 | 64.9% / 64.5% | 72.0% / 71.9% | 0.43 / 0.16 |
| league | the situation (down, distance, field, clock, score, shotgun, no-huddle, pass) | 0.437 / 0.492 | — | 73.3% / 72.8% | 0.66 / 0.30 |
| history | his habits by situation (every earlier season) and his team's (last season, same coach) | 0.429 / 0.483 | 69.1% / 68.2% | 74.0% / 73.5% | 0.87 / 0.56 |
| **sequence** | the two snaps before, same drive or not, no-huddle, his stay and return rates, the snap number in the drive | **0.412 / 0.468** | **71.5% / 70.8%** | **75.3% / 74.8%** | 1.21 / 0.79 |
| shuffled | the sequence model with history and memory shuffled | 0.437 / 0.492 | — | 73.3% / 72.8% | 0.66 / 0.30 |

- **Takeaways each rung applied:**
  - The snap share stays the strongest single input in every group (weights +0.55 to +0.87 a unit).
  - History and memory enter as interactions with it.
  - Consecutive touches and "after a reception" were left out (F4, F5).
  - The no-huddle flag is a feature, not a lock (F2).
- **The ladder stops at the sequence rung.** A tree rung wasn't tried (Could be improved 5).

## Where it misses
The miss lenses run on player-game amount models. This is a play-level probability model, so its misses are read by position group and by the kind of measure built from it.
- **By group (R5):** the rotations. The defensive line (62% of open spots), backs (63%) and tight ends (66%) are the hard cells; quarterbacks and defensive backs are easy. The defensive line also has the highest log loss (0.55).
- **Personnel (R7):** 11 is under-called by 6 points. The mix's counts come from summed chances, which likely lean toward a second tight end or back when two are each partly likely.
- **Substitution:** the snap-matched lineup's per-game substitution rate correlates only 0.48 with the truth. The average is right (1.22 against 1.24), but which games are busy isn't.
- **Plus-minus (R6):** weakest for the defensive line (r 0.18–0.36) and receivers in the lineups (0.44).
- **Not scored:** the 9% of play-sides whose true lineup isn't a complete 11.

## The case against (2026-11-12, written before asking to merge)
1. **The use the brief named first is weak.**
   - In-season plus-minus from the map correlates 0.35–0.49 with the true plus-minus, and misses by nearly the true spread.
   - If the point of the expert is a player's on/off effect this season, it doesn't deliver that yet.
   - Part of the gap may be that a season's true plus-minus is itself noisy (a small difference of two means), so a correlation against it understates usefulness. That wasn't tested.
2. **The snap-matched lineup is not the most accurate lineup.**
   - On open spots it trails even the snap share's top picks (71.5% against 72.0%).
   - Calling it the headline rests on a taste call: that the totals and the rhythm of substitution are what the map should be faithful to.
3. **The gain over the snap counts is modest.**
   - The snap counts do most of the work (F1).
   - The full model takes 7% off the snap share's log loss, and lifts the likeliest lineup's open spots by 3.3 points.
   - It also takes 5 rungs, an optimizer and two linear programs.
4. **The truth is nflverse's participation data, unchecked.** Its own errors are baked into every score.
5. **Only clean plays are scored:** play-sides with a complete true 11 (91%). The rest are likely worse.
6. **Calibration gets worse as the model gets sharper** (0.43 to 1.21 points). It's still inside the bar, and recalibration wasn't tried.
7. **Live use depends on the snap counts arriving by the morning after.** A late upload delays the whole map. 2026 and the 2025 vault aren't scored yet.
8. **Versions tried:** 5 rungs and 3 versions of the best guess, chosen on these same seasons. The position mix was designed after seeing R4's failure. The vault is the clean test.

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
- **H34 and H35 apart from the memory.** The sequence rung adds them together.

## Could be improved
1. **Let the play's own events shift unnamed players** (an emission model). A deep pass makes the third receiver likelier; a goal-line run makes the second tight end likelier. Today only named players are evidence.
2. **Draws of whole lineups** from the chains, under the totals. These give a causal model honest uncertainty, and a plus-minus a range.
3. **A personnel model from each team's habits** (its 11 and 12 rates by situation), feeding the mix instead of summed chances, to fix the 11 under-call (R7).
4. **Depth charts and the injury report** as inputs: a backup's chance when the starter is limited.
5. **A tree rung** (rule k's next step), especially for the defensive line.
6. **Recalibration** inside the training folds (R2).
7. **This season's estimated games as history,** measured against truth-only history.
8. **A post-game moment kind in the shared harness,** once a second post-game expert exists (decision 0030, alternatives).

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
| **Outputs** | `outputs/participation-live/<run_id>/history.parquet`: one row per candidate and scrimmage snap, with `quantity` `on_field_chance`, `mean` = the chance (q10–q90 equal it), `best` (snap-matched best guess), `likeliest`, `side`, `team`, `n` (the team's snap number), `as_of`, `train_end` |
| **Level of detail** | player-play, both sides |
| **Interval** | every completed game, 2019–2024 walk-forward (2016–2018 train only) |
| **Cadence** | in_season |
| **Known at** | the first weekly run at least a day after kickoff (snap counts are in the morning after) |
| **How to use it** | Use `mean`, the chance, wherever a measure can take weights: a player 60% likely counts 0.6 on and 0.4 off. Use `best` when a model needs whole lineups that agree with the snap counts (snaps by situation, substitution, personnel rates). Use `likeliest` only to look up one play's most likely 11. Don't treat either lineup as observed: for effects per player, carry the chance or draw lineups, and compare plus-minus within a position group (R6). In training, read only the walk-forward history (rule e) |
| **Feeds** | in-season player plus-minus and value, context-live and voe-live (who was on), routes and roles per play, fantasy usage, the game simulator; later, causal effects per player and play |

## Open questions for the CEO
1. **Which lineup should the map be faithful to?** (a taste call: your instinct first)
   - Higher layers will use one by default; both stay in the output.
   - **Snap-matched:** every player's snap count and how often teams substitute, at 87% of each play's 11.
   - **Likeliest:** the most players right on each play (89%), with totals 7 plays a player off and half the substitution.
2. **Any veto on the technical calls?** These are decision 0030's calls 1–10:
   - its own runner;
   - the snaps from play-by-play;
   - pins and targets;
   - a logistic regression per group with two snaps of memory;
   - the balancing;
   - the best guess with the position mix;
   - two lineups;
   - history shrinkage;
   - the 2019–2024 test seasons;
   - the output schema.
3. **Which finding or call should I spot-check** in depth before the merge?
4. **Plus-minus is weak (R6). Merge now, or one more round first?**
   - Why it matters: plus-minus was the first use named in the brief.
   - **Merge now** with plus-minus marked "noisy", and improve later with lineup draws and play events (Could be improved 1–2).
   - **Or hold the merge** for that round.
