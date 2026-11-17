# Brief: the touchdown expert (`td-expert`)

> The CEO's pick, 2026-11-16, in the strategy chat. This file gets the kickoff, the hunches, the exploration's changes and the agreed brief; the build happens in its own session, from this file.

**Status:** agreed (2026-11-17, the CEO: "I approve the brief"; explored 2026-11-16, verdict GO; the CEO's calls and the second look are under "The CEO's calls" and "The CEO's ideas, and the second look"; the build runs in its own session, from this file and EXPLORATION.md) · **Layer:** expert · **Cadence:** in_season

## What the CEO asked for
*Word for word, 2026-11-16.*

"Ok let us start the touchdown expert"

The registry's one-line summary, written when the project was listed: "Red-zone and goal-line usage, giving touchdown probability. Feeds TD-scorer props."

## The usual way
*Claude, before any research.*

Analysts treat touchdowns as the noisiest part of a player's line and forecast them in two steps. First, how many touchdowns will the team score (from the betting total or the team's offense rating), split into passing and rushing. Second, what share of them each player gets, from his share of the valuable chances: carries inside the 5, targets inside the 10 and into the end zone. A player's own scoring rate is pulled hard toward the league rate for that kind of chance ("touchdown regression": a receiver with 12 touchdowns on 90 targets is expected to fall back). Anytime-scorer props are then priced from the expected count, as the chance of at least one.

## Analogies
*Claude. Ways to look at it, not answers.*

1. **Goals in soccer and hockey (expected goals).** Goals are rare and decide everything, so analysts stopped counting them and started valuing each shot by where and how it was taken. Shot quality and shot volume repeat from season to season; finishing (goals beyond what the shots were worth) barely does, except for a handful of elite players. What it suggests looking at: whether scoring beyond the worth of the chances is a lasting trait for anyone, and for whom (a goal-line back, a tall red-zone target, a running quarterback); and whether the team creating the chances matters more than the player finishing them.
2. **An insurer pricing rare claims.** One driver's claims in a year say almost nothing about him, so the price comes mostly from his class (age, car, postcode) and moves toward his own record only as years accumulate. The method is a credibility weight: how much to trust the individual's record against the group's. What it suggests looking at: how many chances it takes before a player's own touchdown rate should be believed over his role's rate, and whether that number differs by kind of chance.

## What PCF already knows
*From finished work and explorations; the build must use these.*

- **Goal-line chances are worth the most** (opportunity-quality F3): a target into the end zone from the 10 or closer is a touchdown 45% of the time; a carry inside the 2, 52%.
- **But the kind of chance added nothing to next game's fantasy forecast beyond the count of chances** (opportunity-quality F4). The touchdown expert has to show it is different for touchdowns alone, or over a longer horizon.
- **A play's touchdown chance is among the most explainable outcomes** (context-live F3): the situation alone removes 27.7% of the error for a run and 16.7% for a dropback, almost all from field position and distance. The play call adds nearly nothing.
- **Depends on** opportunity quality and team efficiency (registry); neither's build output exists yet for opportunity quality.

## What the CEO said
*2026-11-16, word for word.*

> Can we predict red zone efficiency based on past play outcome variance in the red zone? Can we build features that predict touchdowns rather that field goals? I would love to forecast touchdown regression. I would love to have an estimate on the noisiness of an observed touchdown. That would also be a very cool measure, how many chances does each player need to estimate greater than 0.5 touchdowns? I think touchdown allocation will be closely tied to scheme and play calling tendencies; I am about 40% confident. I think the combination of explosive play rate and red zone opportunities will be the strongest predictors of rest of season touchdown totals; I am 50% confident. Do you have any more questions for me?

## CEO hunches
*The CEO's words, before any result. Claude's expectations were written before the first run.*

| # | Hunch | CEO's confidence and expected size | Claude expects | What the usual way says | How the exploration will test it |
|---|---|---|---|---|---|
| H67 | "touchdown allocation will be closely tied to scheme and play calling tendencies" | "about 40% confident"; no size given | 65% that a team's tendencies (how often it passes near the goal line, shotgun rate, pass rate overall) repeat and forecast how its touchdowns split between rushing and passing, removing 2 to 5% of that split's error. 20% that they add 0.3+ points to a player's touchdown forecast once his own share of the chances is known: expected under 0.3 | Allocation follows each player's share of goal-line carries and end-zone targets; the scheme is behind those shares, not beside them | (a) Does the team's past pass share inside the 10 and its other tendencies forecast the rushing share of its later touchdowns? (b) Do they add to a player's rest-of-season touchdowns beyond his own chances? |
| H68 | "the combination of explosive play rate and red zone opportunities will be the strongest predictors of rest of season touchdown totals" | "50% confident"; no size given | 80% that red-zone chances are in the top three single predictors. 25% that explosive-play rate is in the top five; expected to add under 0.3 points beside volume. 15% that this pair is the strongest pair: expected winner is plain volume (chances or yards a game) with red-zone chances | Volume first (touches, targets, yards), then red-zone share; explosive plays are treated as luck | Rank each single predictor and each pair of predictors of a player's rest-of-season rushing and receiving touchdowns, held out |

## The CEO's questions
*Asked as questions, so they aren't scored as hunches. Claude's expectation beside each, written before the first run.*

| # | The question | Claude's reading | Claude expects |
|---|---|---|---|
| Q1 | "Can we predict red zone efficiency based on past play outcome variance in the red zone?" | Does the spread of a team's past red-zone plays (boom or bust against steady) forecast its later touchdown rate per red-zone trip, beyond its past average? | Red-zone touchdown rate repeats weakly (half season to half season about 0.15). 85% that the spread of outcomes adds nothing beyond the average |
| Q2 | "Can we build features that predict touchdowns rather that field goals?" | For drives that reach the red zone: touchdown or field goal? Which team traits forecast it | 75% that the offense's plain efficiency everywhere on the field forecasts it better than its own red-zone history. All features together remove 1 to 3% of the error |
| Q3 | "I would love to forecast touchdown regression" | A player's touchdowns beyond what his chances were worth: how much of it carries forward | 90% that expected touchdowns forecast later touchdowns better than past touchdowns do. A player keeps 5 to 20% of his touchdowns over expected the next season |
| Q4 | "an estimate on the noisiness of an observed touchdown" | How likely was the average scored touchdown before the snap, and what is one observed touchdown worth as evidence about later ones, against one expected touchdown | The average touchdown came on a chance worth 20 to 30%. One observed touchdown is worth a quarter to a half of one expected touchdown as evidence |
| Q5 | "how many chances does each player need to estimate greater than 0.5 touchdowns?" | Two readings, both measured: (a) how many chances of each kind add up to half an expected touchdown; (b) how many chances before a player's own touchdown rate is worth as much as the league's | (a) About 1 carry inside the 2, 1 to 2 end-zone targets from close, 10 to 12 ordinary targets, 15 to 20 ordinary carries. (b) Several hundred targets or carries: more than a season |

## What the exploration found
*[EXPLORATION.md](EXPLORATION.md), 2026-11-16. Verdict: GO, with a narrower job than the hunches hoped.*

- **H67 held in part:** a team's tendencies forecast how its touchdowns split between rushing and passing (7.5% of the error, better than the split's own history) and add 1.3% to a player's forecast (WR +2.1%, TE +2.8%), most of it shared with how good the offense is.
- **H68 failed:** yards and chances are the strongest predictors of rest-of-season touchdowns (32% and 30%); chances inside the 20 rank 6th of 14, explosive-play rate 13th, and neither adds to volume. The exception: red-zone carries for quarterbacks (+4.7%).
- **Q1 no:** the spread of past red-zone plays doesn't repeat (0.06) or forecast. **Q2 barely:** touchdown or field goal on a trip is 0.8% forecastable, all from the whole offense.
- **Q3 yes:** a player keeps about a tenth of his touchdowns over expected (WRs none). But expected touchdowns forecast no better than past touchdowns; volume beats both.
- **Q4:** the average touchdown came on a chance worth 28.5%; in one game 64% of the spread in a player's touchdowns is luck; one touchdown is worth half an expected touchdown as evidence.
- **Q5:** half an expected touchdown is one carry inside the 2, two end-zone targets, 9 ordinary targets (WR, TE) or 17 carries (RB). To trust a player's own scoring rate takes hundreds of chances; his finishing beyond the chances' worth, thousands (for WRs and RBs).
- **The ceiling:** a forecast from his games so far removes 32% of the error; knowing every chance he then gets, 72%; the last 28% is dice. The room is in forecasting chances, not in valuing them.
- **Data:** targets before 2009 are unusable (EXPLORATION F1).

*Second look, 2026-11-17 (EXPLORATION F17 to F23):*
- **Next game, players:** games so far remove 7.9%; knowing that game's chances, 35.8%; 64% is dice (F17).
- **I-a ahead:** a plain Poisson count around the forecast gives a calibrated chance of 0, 1, 2+ (says 23.9% score, 23.9% did); how concentrated a player's chances are adds nothing (F18).
- **I-a looking back:** a season's touchdowns over expected are almost exactly dice (1.07 dice spreads wide); luck is 78% of the spread for players expecting 2 to 4, 46% at 7 or more (F19).
- **I-b:** the average red-zone field goal came after the drive peaked at a 55% chance of a touchdown; 73% had passed 50%. But a team's near misses don't repeat (0.08 half to half, 0.03 season to season) and add nothing to a forecast: a description, not an input (F20).
- **Teams:** next game 9.0% (the opponent adds 1.9%), rest of season 23.9%; a team's touchdowns so far and its EPA do as well as anything. The team's ceiling is still unmeasured (F21).
- **Thrown touchdowns:** next game 7.2%, rest of season 43.3%; a quarterback keeps about 9% of his thrown touchdowns over expected, and past thrown touchdowns add to expected ones (+5.5%), unlike receivers' (F22).
- **Method C:** a player's share of his team's chances inside the 10 repeats (RB 0.63, QB 0.57, TE 0.49, WR 0.44): the allocation side is stable (F23).

## Methods
*Claude. Two usual, one exploratory, and a tempting one that is wrong.*

| | Method | What it assumes | Cost | For and against |
|---|---|---|---|---|
| A | **Chances times their worth.** Forecast each player's chances by kind (from `participation` and `opportunity-quality`), multiply by the calibrated worth of each kind, then add the small corrections the exploration found (the offense's quality, the team's tendencies, a tenth of his touchdowns over expected). The count's spread comes from the chances themselves, which gives the chance of zero, one, two | That the worth of a kind of chance is the same for everyone, bar the small corrections | Medium; leans on two experts whose builds haven't run | For: it is where the ceiling says the room is, and it explains itself. Against: until those builds exist it has to forecast chances crudely |
| B | **A count model straight from volume.** A model built for counts (touchdowns from yards, chances, snaps, the team's offense), with the spread fitted | Nothing about why; that volume carries it | Low | For: the exploration says this is already as good as anything (32%). It is the plain version every other method must beat. Against: says nothing about regression or luck |
| C | **Exploratory: play the red zone out.** Forecast a team's red-zone trips, then simulate each one play by play: who gets the ball at each yard line and down, and whether it scores, from the team's own calling there. Touchdowns for every player on a team come out together, so they add up to the team's, and a back's and a receiver's are tied | That calling near the goal line is stable enough to simulate, and that a team's trips can be forecast | High | For: gives joint outcomes (two players' touchdowns in the same game), which props and best ball need. Against: H67 says the tie to calling is modest, and a fifth of touchdowns come from chances worth under 10% (F7), mostly outside the red zone |
| X | **Tempting and wrong: each player's own touchdown rate.** Treat scoring rate as a skill and project it | That finishing is a trait | Low | Wrong because touchdowns over expected repeat at 0.05 (F5, F10) |

*Claude's recommendation was* B first as the plain version, then A beside it; C waits for the game simulator. **The CEO's call (2026-11-17): "The method should be an and b, we can explore c."** So the build makes B (the plain version) and A, for players and teams, and C stays an exploration: its allocation side repeats (EXPLORATION F23); forecasting trips and calling is for the game simulator.

## The question
For each player and each team, in the next game and over the rest of the season, how many touchdowns (rushing, receiving and thrown) should we expect, how sure is that (the chance of 0, 1, 2+), and how much of what was scored so far was the chances and how much was luck?

## Terms
- **Chance:** a target or a carry. **Expected touchdowns:** the share of chances like this one that score, from where it happened, known before the snap. **Touchdowns over expected:** touchdowns minus expected touchdowns.
- **Touchdown regression:** the share of a player's touchdowns over expected that he keeps afterwards (about a tenth).
- **Red-zone trip:** a drive with a play inside the 20.
- **Tendencies:** how a team calls plays (pass share, pass share inside the 10, pass rate over expected), not how well it plays.
- **Thrown touchdowns:** a quarterback's touchdowns on the targets he threw; a throw's expected touchdowns are its target's.
- **Drive model:** the chance that a drive ends in a touchdown, from the situation before each snap.
- **Near miss:** for a drive that ended in a field-goal try, the closest it came: its highest chance of a touchdown (drive model) before any snap. Not a sum of its chances' expected touchdowns, which counts a failed goal-line series four times (EXPLORATION F20).
- **Luck measure (looking back):** touchdowns minus expected, in units of the dice's spread on those chances (the square root of the sum of p × (1 − p)), with the chance of scoring at least that many.

## Assumptions
- A chance's worth depends on where it happened, not on who got it (true to within a tenth; EXPLORATION F5).
- Rushing, receiving and thrown touchdowns (the CEO, 2026-11-17); defensive and return touchdowns are out.
- The next-game forecast assumes the player plays; the chance he doesn't is `participation`'s, and a prop price combines the two.
- Play-by-play from 2009 for targets (F1); player-games from 2012 (snap counts).

## Goals
1. **Expected touchdowns** per chance (targets, carries, throws), per player-game (rushing, receiving, thrown) and per team-game, calibrated, saved with walk-forward history.
2. **A regression measure:** touchdowns over expected so far, and the share to keep by position (about a tenth for RBs and TEs, none for WRs, about 9% for a quarterback's thrown touchdowns).
3. **A forecast** for players and teams, next game and rest of season, by method B (the plain count model) and method A (chances times their worth), with the chance of 0, 1, 2+ from a Poisson count around the forecast (EXPLORATION F18). For teams, the opponent's touchdowns allowed go in (F21).
4. **The luck measure, looking back** (the CEO's idea): for every touchdown, player-game, team-game and stretch of games, how surprising it was: the chance before the snap, the luck measure, the chance of at least that many (F19).
5. **Near misses** (the CEO's idea): for every field-goal drive, how close it came to a touchdown, and a team's near misses per game. A description for reports and stories; not a forecasting input (F20).

## Tests
- **Signal:** expected touchdowns are calibrated by tenth on held-out seasons, and beat a shuffled version.
- **No noise (approved by the CEO, 2026-11-17):** method A must do at least as well as the plain count model from volume (method B) on held-out games, for each horizon and for players and teams; where it doesn't, B ships as the forecast and the expert ships its measures.
- **The ceiling first:** before reading any team gain, the build measures the team's room with a drive-aware hindsight (each drive's chances, stopping at its first touchdown); summing every chance's expected touchdowns isn't a fair one (EXPLORATION F21).
- **The regression measure** must beat both "keeps all of it" and "keeps none of it" on held-out touchdowns over expected, for rushing and receiving and for thrown.
- **Ranges:** the chance of at least one and of two or more is calibrated by tenth (when it says 30%, about 30% score), checked separately for thrown touchdowns, where Poisson may be too narrow.
- **Consistency:** each new measure gets its entry in `CONSISTENCY.md` in the build (the explorations' repeats: expected touchdowns 0.60; touchdowns over expected 0.05; thrown touchdowns over expected 0.12 and 0.09; a team's red-zone touchdown rate 0.20; the spread of its red-zone plays 0.06; near misses 0.08 and 0.03, marked noise; a player's share of his team's chances inside the 10, 0.44 to 0.63).
- **Yardstick:** the crude forecaster scores yards only, so touchdowns have no yardstick yet; fantasy points can be added to it later (the CEO, 2026-11-15).

## The CEO's calls
*2026-11-17, word for word.*

> I think it should predict both next game and rest of season. Plus, I think it should predict players and teams. I think we can include passing touchdowns. The method should be an and b, we can explore c. Your pass-fail test is approved. I think we could add a forecasting and retroactive element that measures the noisiness of a touchdown? I think we could try and measure how close a touchdown was after a field goal. Just ideas

What that settles:
1. **Horizons:** next game and rest of season, both.
2. **Who:** players and teams.
3. **Passing touchdowns:** in this expert (a quarterback's thrown touchdowns, beside every player's rushing and receiving ones).
4. **Method:** A and B are built; C is explored, not built.
5. **The no-noise test:** approved.
6. **The team side:** the team's touchdowns are forecast; the spread of red-zone plays (Q1) is dropped; touchdown-or-field-goal (Q2) comes back through the CEO's near-miss idea below.
7. **Late sizes for H67 and H68:** none recorded (the scoreboard rows stay as they were).

## The CEO's ideas, and the second look
*The CEO called these "just ideas", so they are measures to build, not hunches; they aren't on the scoreboard. The added scope (next game, teams, passing touchdowns) and the ideas were explored in a second look before the brief is agreed. Claude's expectations, written before the second run:*

| # | What | Claude's reading | Claude expects |
|---|---|---|---|
| I-a | "a forecasting and retroactive element that measures the noisiness of a touchdown" | **Looking back:** for every touchdown, player-game and stretch of games, how surprising it was (the chance before the snap; how likely that many touchdowns were from those chances). **Looking ahead:** the forecast's chance of 0, 1, 2+ touchdowns, and whether anything beyond the forecast's average tells how noisy a player's touchdowns will be (a goal-line back's few high-value chances against a receiver's many low-value ones) | 60% that a plain Poisson count around the forecast average gives a chance of at least one that is calibrated within 2 points. 70% that knowing how concentrated a player's chances are improves the chance of 0/1/2+ by under 0.5% |
| I-b | "measure how close a touchdown was after a field goal" | For each drive that ended in a field-goal try: how likely a touchdown was from the chances it had (the chance that at least one of them scores). Summed by team, it is "touchdowns nearly scored" | The average field-goal drive that reached the red zone had about a 35 to 45% chance of a touchdown. Its rate repeats weakly for a team (about 0.1). 30% that a team's near misses so far add 0.5%+ to its later touchdowns beyond its touchdowns and expected touchdowns so far |
| S-1 | Next game, players | The noise ceiling for one game | Games so far remove 8 to 12% of the error; knowing that game's chances, about 40%; the rest is dice |
| S-2 | Teams | A team's touchdowns, next game and rest of season | Next game 5 to 8%; rest of season 25 to 35%; knowing that game's chances about 55% |
| S-3 | Passing touchdowns | A quarterback's thrown touchdowns: ceiling, best predictors, regression | Rest of season about 30%, next game about 8%; thrown touchdowns over expected repeat more than receivers' (keeps 10 to 20%) |
| S-4 | Method C, can it work | Does a player's share of his team's chances inside the 10 repeat half to half | RB about 0.55, WR and TE about 0.4 |
