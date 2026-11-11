# Brief: Pace and play-calling (`pace`)

**Status:** draft (kickoff and hunches 2026-11-10; the CEO chose C, both; exploration done the same day, GO: [EXPLORATION.md](EXPLORATION.md), and its changes below wait for the CEO's agreement) · **Layer:** expert · **Cadence:** in_season

## The usual way
*Claude, 2026-11-10, before any research.* Pace analysts (Football Outsiders' pace stats, Sharp Football, the fantasy sites' team-volume projections) work in three steps:
- **Measure tendencies in neutral situations.** Seconds per play, no-huddle rate and pass rate are measured only when the game is close: score within about 7 points, outside the last two minutes of each half (or win probability between 20% and 80%). Outside those situations, the score sets the pace instead of the coach. Pass rate over expected (nflverse's `xpass`) is the usual play-calling measure.
- **Project each team's plays.** A team's plays next game come from its own neutral pace, the opponent's pace, and the game script the betting line implies: favorites run more and slow down late, underdogs pass more and hurry. Both teams share one 60-minute clock, so the two teams' plays are projected together, usually around 125–130 in all.
- **Split the plays into passes and runs.** The split uses the team's pass rate over expected and the same game script. The fantasy sites then share those passes and runs out to players by target and carry share.
- **What's known:** neutral pace follows the play caller and repeats season to season. Game script moves a single game's plays and pass rate more than any team trait does. The market's totals already reflect most of this.

## Analogies
1. **Possessions in basketball.** NBA analysts don't project points, they project possessions times points per possession. A game's possessions are a blend of both teams' paces, roughly *my pace × your pace ÷ league pace*, because both teams share the clock. Football has the same shared clock with a twist: drives alternate, so drives are close to equal, but plays per drive aren't. A team that converts third downs runs more plays and leaves the other team fewer. So this analogy asks: is pace really the snap clock, or is it drives times plays per drive, where plays per drive is mostly efficiency?
2. **Climate and weather.** A team's pace and pass rate are its climate; the score is the weather that pushes each game around. The usual neutral-situation filter measures climate only on calm days, and throws away most of the data to do it. A climate scientist would instead model how much the weather moves things and adjust it out, keeping every day. That's what pass rate over expected already does for pass rate. So this analogy asks: is an adjusted-for-script measure, on every play, steadier than the neutral-only one? (The CEO's H22 is this bet.)

## What it builds on
- **schemes-v2** already forecasts four team tendencies for the next game, from the shrunk season, the last 4 games, last season and the head coach's history: pass rate over expected, shotgun rate, **tempo** (game seconds from an in-bounds run to the next snap) and throw depth. They beat every simple average and hold on the 2025 vault except throw depth (schemes-v2#R1, R12). Tempo and the no-huddle rate follow the head coach (schemes-v2#F3, H10). **Both its pass rate and its tempo are measured in neutral situations only** (win chance 20–80%, `tables/tendencies.py`), the usual way that H22 bets against. What's new here is the **volume**: how many plays and passes each team runs in a game.
- **Elo** forecasts each game's margin and total, 0.27 and 0.30 points behind the close (elo#F2); its ratings and win chances are saved for higher layers, so the pre-game win chance H20 needs is already there.
- **participation** forecasts who plays; player opportunity will multiply its shares by this project's volume.
- **tag-tables#F4:** nflverse's expected pass rate (`xpass`), win probability and expected points were fit on seasons through 2019, so they're in-sample before 2020.

## CEO hunches
*The CEO's words, recorded as said on 2026-11-10, before Claude's research.* Each gets a verdict in [`projects/HUNCHES.md`](../HUNCHES.md).

| # | Hunch, in short | What the usual way says | How the exploration will test it |
|---|---|---|---|
| H19 | A team's pass rate over expected (pass rate against the average of nflverse's expected pass chance) is the same across situations: down, score, win chance, field position, the clock | Pass rate over expected is measured in neutral situations; early downs are often studied apart, as their own tendency | Each team-season's pass rate over expected in situation slices (each down, score bands, win-chance bands, field position bands, quarter). How well a team's number in one slice matches its number in another, against how well two random halves of the same slice match (the most it could) |
| H20 | Pass rate follows the odds of winning: a team likely to lose passes more | Agrees: game script is the biggest driver | Two levels. In a game: does the pre-game win chance (Elo's, and the close's) forecast a team's passes and pass rate beyond its own trait? On a play: after the expected pass chance, is win chance left over? |
| H21 | A team's recent pass success raises its future pass rate | Pass rate is the play caller's; analysts rarely say teams chase recent success | Recent pass success (success rate and EPA per dropback, last 4 games and season to date) against the next game's pass rate over expected, beyond schemes' own pass rate forecast |
| H22 | Close-game-only pace throws away the sample. Build an expected pace on every play from win chance and expected points, and measure each team's pace over expected on every play | Neutral situations only (as schemes-v2's tempo does) | Build it, then race it against the neutral-only measure on the two tests for every new measure: does it repeat week to week and season to season, and does it forecast the next game's plays and seconds per play better? |
| H23 | Our features are always consistent from game to game | Neutral pace and pass rate repeat; most per-game numbers are noisy | Every measure this project makes goes through `pcf.validation.consistency` and into CONSISTENCY.md, with a verdict per measure |
| H24 | High pace early in a game means more injuries later in it | Injury risk comes from season workload (snap counts), not one game's pace | In-game injuries from the play descriptions ("was injured during the play"). Does first-half pace forecast second-half injuries, per game and per play, beyond how many plays there were? |
| H25 | High pace early in a game tires the defense later | Commentators' lore; studies of time of possession find little | A defense's first-half plays faced and the opponent's early pace, against its EPA allowed per play in the fourth quarter, beyond both teams' strength |

**H19, H20, H21.**
> "I want to utilize the expected pass chance that is defined in nflverse play by play data. If we measure pass rate against the average of pass chance per play then we will find a feature of pass rate over expected. I would assume that this pass rate over expected is consistent across game situations like play clock, down, score differential, winning chance, and field position. I would definitely assume that pass rate follows odds of winning and the teams recent pass success rate. If a team is likely to lose, then they will pass more. If a team has a high pass success rate then I would assume that future pass rate will be relatively high."

**H22.**
> "I think pace features generally get it wrong when they limit their sample to close games. I think that close games serve as a valid measure of pace, but I think we can build an expected pace feature that regresses the pace at any point in a game; the inputs would be odds of winning and expected points on a given play within a drive. Therefore the pace expectation accounts for field position and score differential and so on. We can then measure the difference in pace for each team relative to the expectation. Then we will have a full sample of pace over expected for each team and each play."

**H23.**
> "I would expect our features to always be consistent from game to game."

**H24, H25.**
> "I would also be interested to see if pace earlier within a game can predict injuries later in the game. If pace is high then I would assume that injuries would also be high later in the game. If pace is high at the beginning of the game then I would also expect the defense to get tired later in the game."

### Claude's assumptions, limits and expectations, per hunch
*Stated before the exploration, so its results mean something.*
- **H19:**
  - *nflverse has no play clock.* Its `play_clock` column is 0 on every play, 2006–2024 (checked 2026-11-10), so "the clock" is the game clock: quarter and time left in the half.
  - *Some situations leave no room.* When the expected pass chance is 95% (3rd and 12, down 20 late), every team passes, so no team can differ. Slices are weighted by how much room they leave (expected × (1 − expected)).
  - *Advantage:* if it holds, pass rate over expected on every play is one trait, and the full sample measures it far better than neutral plays alone.
  - *My expectation:* holds across downs 1–2, score and field position; weaker on 3rd down and in the last minutes, where the situation dictates the call.
- **H20:**
  - *nflverse's expected pass chance probably already uses win chance* (it's fit with the score, time and the pre-game line). If so, at the play level the hunch is built into "expected", and what's left is near zero. The game level is where it matters: an underdog throws more passes in all.
  - *Simpler alternative:* the pre-game spread alone. Elo's win chance is tested beside it.
  - *My expectation:* held, and large at the game level; near zero at the play level. The usual way agrees, so on the scoreboard it counts as confirming the usual way, not beating it.
- **H21:**
  - *Two stories give the same sign.* A team may pass more because passing worked (the hunch), or because its QB is good, which made passing work and makes the play caller trust it (a lasting reason). Schemes' pass rate forecast already carries the last 4 games of pass rate over expected, so the test is what success adds beyond it.
  - *Opponents matter:* passing works against bad pass defenses, and teams pass more against them. Success is measured against each opponent's average.
  - *My expectation:* a small positive effect, mostly the QB story.
- **H22:**
  - *The clock stops.* Most of the time between snaps is set by whether the clock stopped (an incompletion, out of bounds, a timeout, a penalty, the two-minute warning), not by the team. Schemes' tempo avoids that by using only the gap after an in-bounds run. So the exploration tests the CEO's version (win chance and expected points) on every play, and beside it a version that also knows whether the clock stopped (Claude's addition, labelled as such). The hunch's verdict is the CEO's version.
  - *Pace is seconds between snaps while the clock runs, plus the no-huddle rate.* Without a play clock, a team that snaps with 2 seconds left and one that snaps with 20 differ only in game seconds.
  - *nflverse's win chance and expected points are in-sample before 2020* (tag-tables#F4), so confirmation uses 2020–2024, or our own expected pace fit only on earlier seasons.
  - *My expectation:* steadier week to week than neutral-only (two to three times the plays), a modest gain on next-game plays.
- **H23:** *My expectation:* fails as "always". Pace and pass rate over expected repeat (schemes found tempo repeats at 0.77 week to week and 0.53 season to season), but recent pass success (H21) repeats much less.
- **H24:**
  - *More plays is more exposure.* A fast game has more snaps, so more injuries in total is close to certain. The hunch is about fatigue: more injuries per play. Both are reported.
  - *The data:* about 430 in-game injuries a season in 2006 and 870 in 2024, about 3 a game. The rise is partly the scorers writing more down, so comparisons stay within a season.
  - *My expectation:* yes per game (exposure), faint or nothing per play.
  - *Where it goes:* a held result feeds `injury-fatigue`, not this expert's forecast.
- **H25:**
  - *Fast offenses are good offenses.* A defense that faced many early plays also faced a good offense, which scores late too. Both teams' strength is held fixed.
  - *My expectation:* a small effect at most. It also goes to `injury-fatigue`.

## The question
Before each game, how many plays will each team run, how many of them passes, and how fast, and which parts of that are the team's own lasting habits rather than the game script?

## Why it matters
Fantasy points are volume times efficiency, and volume is the half PCF can forecast best. Player opportunity multiplies participation's shares by this project's plays and passes; game script and the game simulator need each team's pace and pass lean. A user would notice it as better projections for every player on fast, pass-heavy teams and on teams expected to trail.

## Terms
- **Standard terms used:** [EPA, expected points, win probability, pass rate over expected, neutral situation, no-huddle, success rate](../../docs/GLOSSARY.md); schemes-v2's [trait and tempo](../../docs/GLOSSARY.md).
- **New terms this project introduces:**
  - **Expected pass chance:** nflverse's `xpass`, the chance an average team passes in this exact situation (down, distance, field position, score, time, the pre-game line).
  - **Expected pace:** the seconds an average team takes between snaps in this exact situation, from win chance and expected points (H22), fit on every play.
  - **Pace over expected:** a team's seconds between snaps minus its expected pace, averaged over its plays. Negative is fast.
  - **Volume:** a team's plays in a game (passes plus runs, with scrambles and sacks counted as passes), and its passes and runs apart.
  - **In-game injury:** a play whose description says a player "was injured during the play".

## Assumptions
- Pace and pass rate over expected are mostly the play caller's (schemes-v2#F3, H10), so a coach change resets them toward the coach's history.
- Volume is the two teams' shared clock: plays forecasts are made for both teams of a game together, so they can't add up to an impossible game.
- Everything is known before kickoff: season to date, last season, the coach's history, and the pre-game line and Elo's win chance (rule c). A game's own plays never describe that game.

## Goals
1. **The measures:** pass rate over expected and pace over expected on every play (H19, H22), each through the two tests (does it help the target; is it consistent).
2. **The forecasts (the CEO's call C, 2026-11-10: both):** each team's habits, pace over expected and pass rate over expected on every play, as features; and its volume for the next game (plays, passes, runs) as the forecast, with q10, q50 and q90.
3. **Discovery for injury & fatigue:** H24 and H25, handed on with numbers.

## Success and failure, as tests
*Thresholds from `docs/VALIDATION.md`.*
- **Signal:** each final forecast beats its shuffled, signal-free self (rule k).
- **Beats the usual way:** the full-sample measures (H22) against the neutral-only ones, and the volume forecast against the usual projection (neutral pace plus the line's game script), both by a 90% week-block interval above zero.
- **Beats simple averages:** the season-to-date and last-season averages of each team's plays and passes.
- **Calibrated:** 80% ranges hold about 80% of games.
- **Football sanity:** a game's plays stay between about 110 and 150; favorites run more and pass less; coach changes move pace.
- **Vault:** the 2025 vault is spent for schemes, so the confirmation is 2016–2024 walk-forward plus 2026 live, as the ledger's other models are judged.
- **Failure looks like:** the full-sample measures no steadier than neutral-only, and volume no better than the line's game script; then the usual way ships.

## Inputs and outputs
- **Inputs:** the play table (pass, expected pass chance, win chance, expected points, game clock, no-huddle, clock stops), team-game tables, schemes-v2's trait forecasts, Elo's win chances, the schedule's line, in-game injuries from play descriptions. All free, all already in PCF; nothing new to sign off.
- **Outputs:** per team-game, at each weekly run: next-game plays, passes and runs (q10, q50, q90, in the standard schema), and the habits (pace over expected, pass rate over expected) as forecasts for the next game; the per-play measures as a table for higher layers.

## How it will be used
Player opportunity (volume × shares), game script, the game simulator, totals, and the injury & fatigue expert (H24, H25).

## CEO decisions
1. **What pace forecasts for each team's next game** (taste call, 2026-11-10): **C, both.** The habits (pace over expected and pass rate over expected, on every play) as features, and volume (plays, passes, runs) as the forecast. The other options were A, volume only, and B, habits only, leaving volume to game script and the simulator.

## What the exploration changed (proposed, 2026-11-10; for the CEO to agree)
*From [EXPLORATION.md](EXPLORATION.md).* Verdicts: H19 unclear (mixed), H20 held, H21 held small, H22 unclear (mixed), H23 held, H24 failed, H25 failed.
1. **The habits are measured on every play** (F1, F5, F6): PROE on every play, with early downs and 3rd down as separate habits; pace over expected on every snap, from an expected pace that knows when the clock stopped; and the no-huddle rate. The neutral versions remain as yardsticks.
2. **Volume is drives times plays per drive, for both teams together** (F9): the line (favorites run more, F2), both teams' habits, and both offenses' and defenses' efficiency (Elo's offense and defense ratings or EPA). Ranges come first: a single game's plays are hard to forecast (F8).
3. **H24 and H25 leave this project:** reported to `injury-fatigue` with the long-drive lead (F10–F12, I29).
4. **Goal 3 is replaced** by a stronger success test for the habits: the full-sample measures against the neutral ones, on consistency and on next-game volume.

