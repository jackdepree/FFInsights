# Exploration: Participation inference (`participation-live`)

> Who was on the field on each play, from what's known by the morning after, and do the CEO's hunches H32–H35 hold? Run 2026-11-11 on regular seasons 2016–2024, with the true participation (`player_play.on_field`) as the answer key. The reconstruction is trained on 2019–2021 and scored on 2022–2024. The 2025 vault isn't read. Scripts and their full output: [`explore/`](explore/).

**Verdict (2026-11-11): GO.** The free clues already pin most of each play: snap counts are almost exact and named players are always right (F1). What's left (about 5 open places a play on offense, 7 on defense) is predictable. A first reconstruction of 2022–2024 places 74.6% of the offense's and 73.3% of the defense's open-slot players right, against 72.8% and 72.2% from the snap share alone and about 65% from the depth chart. Its chances are well calibrated (within a point in every tenth). The biggest lever is the sequence. Knowing who was on the snap before would lift open-slot accuracy to 79% and 82% and cut the log loss by a fifth (F8). So the build is a sequence model over each drive, with the CEO's patterns as its inputs.

| Hunch | Verdict | Size |
|---|---|---|
| H32 past participation tendencies | **held, small** | His own situational habits from earlier seasons and his team's from last season: log loss 0.460 on open cells, against 0.469 with the league's situational habits and 0.478 with the snap share (1.9% and 3.7% better); the shuffled version ties the league's exactly. Open-slot accuracy +1.8 points (offense) and +1.2 (defense) over the snap share; backs +7.6, receivers none (F7) |
| H33 team or coach substitution by situation | **held** | All 18 team measures are traits (offense: week to week 0.85, season to season 0.62; third down 0.85 and 0.53; fourth quarter 0.73 and 0.61). They follow the head coach: 0.74 season to season with the same coach, 0.23 with a new one. Teams differ by 0.22–0.34 players a snap on an average of 1.3 (F2, F3) |
| H34 fatigue on a drive and consecutive touches | **held in part** | The drive and his streak: held-out log loss 6.2% better for defensive backs, 4.4% for the line, 0.3–1.6% elsewhere, shuffled 0.0%. Linemen come off most after their second and third straight snaps. Consecutive touches: nothing (0.0–0.4%) (F4) |
| H35 a player's own consecutive-play patterns | **held in part** | His own rhythm repeats: each player's stay and return rates beyond his snap share are traits in every group (backs 0.55 and 0.46 season to season). The example didn't hold: after a reception, players are 2–6 points *less* likely to stay on two more snaps, and that isn't a player's habit (noise) (F5, F6) |

## Expectations, written before running
From the brief (2026-11-11, "Claude's assumptions, limits and expectations"):
- **H32:** holds, a player's situational shares beating the plain season share for part-timers.
- **H33:** holds, following the coach.
- **H34:** holds for defensive linemen and backs, small for receivers and linemen.
- **H35:** on-and-off runs repeat; the event part (after a reception) real but small.

- **Right:** H33 (and that it follows the coach), H34 for defensive linemen and backs, H35's runs repeating.
- **Wrong:** H32's size. I expected situational history to beat the snap share clearly for part-timers; it does, but by 1–2 points of accuracy. Within a game the snap count already says most of what history would.
- **Wrong the other way:** H35's event part. I expected "real but small" in the CEO's direction; it's real and the other way (players come off after a catch).
- **Not expected:** no-huddle doesn't lock the offense (23% of no-huddle snaps change someone), and the defensive backs' streak is the biggest fatigue-like signal (sub packages, not tiredness).

## Data and definitions
- **Plays:** every regular-season scrimmage snap 2016–2024 (pass, run, kneel, spike, and plays wiped out by a penalty) whose true lineup has 11 on each side: 287,864 plays in 2,366 games, 6.33 million player-play rows ([profile](explore/profile.txt)).
- **Known by the morning after:** each player's offensive and defensive snaps (`player_game.snaps`), the players the play-by-play names on each play (passer, rusher, targeted receiver, tacklers, pass defenders, sackers, hitters, penalised and fumbling players), the situation, the depth chart (`player_game.depth`), the head coach (`team_game.pregame`).
- **Snap share:** his snaps × 11 ÷ his team's snaps for that side, so a team's shares add to 11.
- **Part-timer:** on some but not all of his side's snaps in the game.
- **Open slot:** a place in a play's 11 not filled by a named player or an every-snap player.
- **Turnover (substitution):** how many of a side's 11 change from one snap to the next in the same drive.
- **Consistency:** [`pcf.validation.consistency`](../../src/pcf/validation/consistency.py): odd against even weeks, and one season against the next, with 90% intervals. Team measures per team-game; player measures per player-game.
- **Position groups:** QB, RB (with fullbacks), WR, TE, OL, DL, LB, DB.

## Findings

**F1. The snap counts and the play-by-play already pin most of each play** ([profile](explore/profile.txt)).
- **Snap counts are nearly exact:** a player's snap share against his true share of the plays: r 0.991, off by 1.2 points on average, 85% within 2 points. 99.9% of the true player-games have a snap count.
- **Every-snap players** fill 44.9% of offensive slots (linemen, the QB) and 25.8% of defensive ones.
- **Named players are always right:** all 752,535 named player-plays are in the true lineup. About 1.5 a play on offense and 1.3 on defense; they pin 17% of offensive part-timers' snaps and 9.5% of defensive ones.
- **What's left:** about 5.0 open slots a play on offense (90th percentile 7) and 7.4 on defense (10), chosen from about 13.5 and 16.4 part-timers per team-game.
- Part-timers by group: backs, tight ends, receivers and the defensive line are almost all part-time (97–100% of their on-field rows), corners 66%, safeties about half, linemen and QBs about a fifth.

**F2. Substitution follows the situation, league-wide** ([h33](explore/h33.txt), first table). Players changed between consecutive snaps of a drive, 238,223 pairs a side:

| Second snap | Offense changes | Any change | Defense changes | Any change |
|---|---|---|---|---|
| All | 1.27 | 70% | 1.29 | 61% |
| Third down | 1.37 | 75% | **1.79** | 77% |
| Fourth quarter | 1.06 | 61% | 1.15 | 56% |
| Red zone | 1.34 | 72% | 1.40 | 65% |
| Last two minutes of a half | 0.67 | 43% | 0.84 | 44% |
| Margin 17+ | 1.05 | 59% | 1.13 | 55% |
| After a 20+ yard play | 1.31 | 69% | 1.51 | 66% |
| No-huddle | **0.35** | 23% | 0.62 | 33% |

- No-huddle cuts the offense's changes to a quarter but not to zero: 23% of no-huddle snaps still have a change (an injury, a flag on the no-huddle marker, or a change the defense forces). The brief's "no-huddle locks the offense" is a strong lean, not a constraint.

**F3. Each team has its own substitution habits, and they follow the coach (H33)** ([h33](explore/h33.txt)). Each team-game's changes per snap above the league's in the same situation and season:
- **Every one of the 18 measures is a trait.** Offense, all snaps: week to week 0.85 (90% from 0.82), season to season 0.62. Third down 0.85 and 0.53; fourth quarter 0.73 and 0.61. Defense, all snaps 0.79 and 0.44; third down 0.81 and 0.47; fourth quarter 0.59 and 0.37. The weakest: defense in blowouts (season 0.15) and in the no-huddle (week 0.12).
- **How big:** the spread between team-seasons is 0.22–0.34 players a snap, on a league average of about 1.3: a quarter of the average either way.
- **It follows the coach:** a team's season repeats into the next at 0.74 (offense, all snaps) with the same head coach and 0.23 with a new one; third down 0.63 against 0.21; defense 0.49 against 0.37. Only 3 coaches moved straight to another head job with full seasons on both sides, too few to follow one.
- **Football sanity:** McVay's Rams change the fewest offensive players on third down (2021 and 2023, about 0.9 a snap under the league); the most are Vrabel's Titans 2021 and Allen's Saints 2022. On defense Tomlin's 2016 Steelers change the fewest; Reich's 2019 Colts and Belichick's 2020 Patriots the most.
- **A caution:** some of the week-to-week repeat is the roster (a team with three receivers it trusts rotates less), not only the coach's choice.

**F4. Who comes off next: the drive and his streak matter for defenders, touches don't (H34)** ([h34_35](explore/h34_35.txt), [h34b](explore/h34b.txt)). For a part-timer on the field now, the chance he's off on the next snap of the same drive (3.2 million cases, 18.8% off):
- **By plays in the drive:** 15% after the first two snaps of a drive, about 21% after that, flat from snap 5. For defensive linemen who have played every snap of the drive so far: 7% off after the first snap, 22% after the second, 24% after the third, then falling to 7% by the twelfth (the ones still on are the starters). That's the rotation the usual way describes.
- **By his consecutive snaps:** the longer he's been on, the less likely he comes off (defensive backs 27% after one snap, 3% after 13+), except linemen, who come off most after two to four.
- **Consecutive touches:** no pattern. A back with one carry or target on this snap is a little *less* likely to come off (25% against 31%); after two or three in a row, the same as without (33%, 32%).
- **Held-out test** (train 2016–2021, test 2022–2024), log loss of "off next snap" against a baseline of his game snap share and the next snap's situation:

| Group | Off rate | All fatigue features | Drive alone | Streak alone | Touches alone | Shuffled |
|---|---|---|---|---|---|---|
| DB | 8.7% | **6.2%** better | 3.5% | 5.0% | 0.1% | 0.0% |
| DL | 22.0% | **4.4%** | 3.7% | 2.2% | 0.0% | 0.0% |
| RB | 27.8% | 1.6% | 0.7% | 0.1% | 0.4% | 0.0% |
| LB | 16.4% | 1.0% | 0.7% | 0.2% | 0.0% | 0.0% |
| WR | 21.3% | 0.8% | 0.4% | 0.1% | 0.3% | 0.0% |
| TE | 31.8% | 0.3% | 0.2% | 0.0% | 0.1% | 0.0% |

- Part-time linemen and QBs show 12% gains, but they're few (19,000 and 23,000 test rows) and mostly injury replacements and blowouts.
- The shuffled versions equal the baseline: the gains are signal.

**F5. After a reception, players come off more, not less (H35, the CEO's example)** ([h34_35](explore/h34_35.txt), H35 tables).
- **Still on for the next two snaps of the drive, after an event on this one, against the same player-game's other snaps:** reception, backs −4.0 points (90% about −4.7 to −3.3), receivers −6.3, tight ends −2.4; a back's carry −3.6; a receiver's carry (jet sweeps) −11.
- **Not a player's habit:** a player's reception effect doesn't repeat (backs and receivers: noise week to week; tight ends a weak state).
- **The one that repeats:** after a 20+ yard play, the defense's front stays on more (linemen +3.9, linebackers +3.6, trait at about 0.16–0.21), likely because the offense hurries; defensive backs come off more (−3.7).

**F6. Each player has his own on-and-off rhythm, beyond his snap share (H35, broader)** ([h34b](explore/h34b.txt), last table, and [h34_35](explore/h34_35.txt), sequence tables).
- **Sequences are strong:** within a drive, a part-timer on now is on next 69–97% of the time; one off now is on next 3–24%. Across a drive break the memory is much weaker (defensive linemen 57% against 42%, against 79% and 17% within a drive): lines rotate by series.
- **The snap before last matters too:** a defensive back on two snaps ago but off now is back on next 42% of the time, against 11% if he was off both (one-play sub packages). The same for receivers (48% against 18%) and tight ends (38% against 18%). So a model needs at least two snaps of memory.
- **It's the player's:** each player-game's stay rate (on next given on now) and return rate (on next given off now), minus his position's average at the same snap share, repeat for every group. Backs: stay 0.65 week to week and 0.55 season to season; return 0.68 and 0.46. Defensive line 0.56/0.34 and 0.65/0.38; tight ends 0.45/0.31 and 0.67/0.43; receivers the weakest, 0.43/0.19 and 0.50/0.32. All traits.

**F7. Past tendencies help, a little (H32)** ([h32](explore/h32.txt)). The first reconstruction, 2022–2024 (3.8 million player-plays, 202,218 play-sides):
- **How it works:**
  - Each team-game-side is a table: plays by the players with snaps. Each play adds to 11, and each player to his snap count (scaled to the plays we have). Named and every-snap players are fixed at 1.
  - Each method gives a prior chance for the open cells. The same balancing (logit raking, a smooth form of the brief's iterative proportional fitting) then makes both totals hold.
  - The best guess takes each play's most likely open players.
  - Priors are fitted per position group on 2019–2021; history comes only from seasons before the one estimated.

| Method | Offense open slots right | Defense open slots right | Offense, all 11 right | Defense, all 11 right | Log loss, open cells |
|---|---|---|---|---|---|
| Depth chart (same lineup every play, named players in) | 64.1% | 65.7% | 8.9% | 4.6% | |
| Snap share | 72.8% | 72.2% | 18.5% | 9.4% | 0.478 |
| + the league's situational habits by group | 74.1% | 72.6% | 20.3% | 9.5% | 0.469 |
| **+ his and his team's history (H32, H33)** | **74.6%** | **73.3%** | **21.2%** | **10.0%** | **0.460** |
| History shuffled (rule k's null) | 74.1% | 72.6% | 20.3% | 9.5% | 0.469 |
| Oracle: + his true on or off on the snap before | 79.0% | 81.6% | 29.5% | 31.2% | 0.382 |

- **By group (open-slot players right, snap share against history):** backs 43.9% → 51.5%, QBs 76.1% → 83.5%, tight ends 65.9% → 69.3%, defensive line 63.1% → 64.9%, linebackers 74.1% → 74.7%, defensive backs 82.1% → 82.9%, receivers 81.8% → 81.5%. Backs are the hardest place, and where history helps most.
- **Calibration:** in every tenth, the history method's average chance is within 1 point of how often the player was on (for example 0.75 against 0.76, 0.95 against 0.95).
- **Sanity:**
  - every play's chances add to 11 and every best guess has 11;
  - each player's chances add to his snap count within 0.04 plays, and to his true total within 0.57;
  - **but the best guess doesn't keep the totals:** a player's best-guess plays are off his true total by 7.8 on average. Taking each play's top players always picks the same ones. The build's best guess must be matched to the snap counts as a whole (an assignment across the game), not play by play.

**F8. The sequence is the big lever.**
- Knowing who was on the snap before cuts the log loss by a fifth (0.460 to 0.382) and lifts the defense's open-slot accuracy by 8 points. That's the ceiling for what memory along the drive can add (F6), not a result: in season the snap before is itself an estimate.
- A sequence model gets part of it. Each play's chances and the plays around it are estimated together (forward and backward along the drive), with the snap totals and named players as anchors. The named players act as fixed points the sequence carries forward: a receiver who catches a pass on third down was probably on for second down too.
- The gene-imputation analogy fits here: the named players and snap counts are the markers, and the drive is the stretch of genome the reference panel fills in.

## What this changes in the brief
- **The model is a sequence model over each drive**, at least two snaps of memory (F6, F8), with the CEO's patterns as inputs to each snap's chance:
  - the snap share;
  - the league's situational habits by position group;
  - his own history (H32) and his team's under the same coach (H33);
  - the drive and his streak, for defenders above all (H34);
  - his own stay and return rates (H35).
  - Touches and receptions enter as small features, not a pillar (F4, F5).
- **Constraints stay:** 11 a play, snap totals per player, named players fixed. Logit raking keeps the totals (F7).
- **The best guess must keep each player's snap total** (an assignment over the game, not each play's top picks; F7 sanity).
- **No-huddle becomes a feature, not a constraint** (F2: 23% of no-huddle snaps change someone; 97% of players stay put).
- **The baselines are now measured:** snap share 72.8% (offense) and 72.2% (defense) of open-slot players right, log loss 0.478; depth chart about 65%. The bar for the build is the history model without sequence: 74.6%, 73.3%, 0.460. The oracle (79.0%, 81.6%, 0.382) is the ceiling to report against.
- **A new sanity test:** best-guess totals within one play of each player's snap count.
- **The depth chart is the weaker baseline:** worse than the snap share everywhere but backs. It stays as a reported baseline and as an input for backs.

## Not looked at
- **Personnel groupings as an input.** They come from participation itself (post-season) or FTN's counts (1–2 weeks late), so none is known by the morning after. Left out of every prior here.
- **The 2023 change of source** (Next Gen Stats to FTN's charting) in the answer key: test seasons weren't split by source.
- **Players with no history** (rookies, new signings) apart from the rest.
- **Fit for use:** plus-minus and personnel rates built from the estimates against the truth. That's the build's test once there's a sequence model.
- **The injury report** as a reason for a part-timer's snaps.
- **Special teams**, as the brief scoped.

## What not to redo
- **Don't treat no-huddle as a lock** (F2).
- **Don't take each play's top players as the best guess:** it breaks the snap totals (F7).
- **Don't chase the reception effect as a player trait:** it's the other way and noise (F5).
- **Don't use the depth chart as the main baseline:** the snap share beats it (F7).
