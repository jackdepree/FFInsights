# Exploration: Opportunity quality (`opportunity-quality`)

> A first look at splitting a player's fantasy points into **expected points** (what his targets and carries were worth from where they happened) and **points over expected** (what he did with them), and at the CEO's hunches H56–H62: which chances are worth the most, whether opportunity follows a player to a new team, whether efficiency lasts, and whether it earns a player more work.
> Run on 2026-11-16 with [`explore/first_look.py`](explore/first_look.py) (output: [`explore/first_look.txt`](explore/first_look.txt)). Chances: every target and carry by a RB, WR or TE, regular seasons, 438,090 with expected points (2010–2024). Player-games: every game with a snap, 66,626 (2012–2024). Forecast tests are scored on 2019–2024, each season from models fit on earlier seasons. The vault (2025) wasn't read.

**How to read it.** Points are PPR on targets and carries only (1 a catch, 0.1 a yard, 6 a touchdown; no passing, fumbles or two-point tries). Expected points come from boosted trees on the situation (yard line, down, distance, throw depth, side, formation, clock, score), fit only on earlier seasons. "Removes X%" is the share of squared error removed. Intervals are 90%. Discovery only: one rough version, not through the gateway or the harness.

**Verdict: GO.** Opportunity is where the room is: knowing the chances a player actually got would remove 74% of the error in his points, against 40% from his past points. Expected points repeat (0.84 week to week); points over expected barely do (0.14), but a small lasting part exists, enough for the CEO's regression measure. Efficiency does earn opportunity (H61). **One result the CEO should weigh before the brief is agreed:** the *quality* of chances adds nothing to next game's forecast beyond plain counts of targets, carries and snaps (F4). Quality is needed to define efficiency; it doesn't pay as a forecast input by itself.

## The noise ceiling (measured first)

Next game's points, players with a snap, 2019–2024 (34,920 player-games; average 6.3 points, spread 7.5):

| What is known | Share of squared error removed |
|---|---|
| His past points (season so far, last 4 games, last season) | 40.3% |
| Hindsight: his average over the season's other games | 42.5% |
| **The chances he actually got in that game** (their expected points) | **73.6%** |

- **The room is in the opportunity, not the efficiency.** Between what past points know (40%) and what the game's own chances would tell (74%) sit 33 points of error. The remaining 26% is what a player does with his chances on the day, and nothing forecasts it: past points over expected remove 0.1% of next game's.
- **Next game's expected points are themselves 52.5% predictable** from past expected points. Closing the rest is mostly participation's job (who plays, how much) and the share of the ball once on the field.
- **Fitting noise: not measured** (these trees have no randomness as set up). The build measures it before any gain under 0.5% is read.

## Findings

| # | Finding | Confidence |
|---|---|---|
| F1 | **The expected-points model matches nflverse's.** Per player-game, r 0.988 with `ff_opportunity`'s expected points (53,607 player-games), from a model fit only on earlier seasons. The situation explains 6.9% of one target's points and 13.5% of one carry's. | strong |
| F2 | **H59: expected points repeat, points over expected barely do.** By `pcf.validation.consistency`, week to week and season to season: expected points per game 0.84 and 0.75; points per game 0.76 and 0.72; points over expected per game 0.14 and 0.17; per chance 0.03 and 0.04. | strong |
| F3 | **H56: goal-line chances are worth the most.** Points per chance, 2019–2024: a target into the end zone from the 10 or closer 3.36 (a touchdown 45% of the time); a carry inside the 2, 3.18 (52%); a target inside the 10 short of the goal line 2.74; a target into the end zone from further out 2.70; a deep target (20+ yards downfield) 2.05. An average target is worth 1.69 and an average carry 0.63, so a goal-line carry is worth five ordinary carries. These four kinds are 6.4% of all chances. | strong |
| F4 | **But the kind of chance adds nothing to next game's forecast beyond the count.** Added to past points: past targets, carries and snaps +1.47% (1.18 to 1.77). Then, beyond those counts: expected points −0.19% (−0.29 to −0.08); counts by kind (inside the 5, end zone, deep, air yards) −0.07%; the goal-line kinds alone −0.10% (−0.18 to −0.02). For next game's touchdowns, the goal-line kinds beside past touchdowns and points: −0.03%. Goal-line work is too rare a game to be told from luck over a few weeks, and past touchdowns already carry it. | medium: one model, next game only; longer horizons (rest of season) weren't run and are where rare events add up |
| F5 | **Expected points do help beside past points when counts are left out:** +0.73% (0.49 to 0.99); TE +1.32%, WR +0.73%, RB +0.44%. Used alone, in place of past points, they are worse: −1.20%. So the soccer result ("expected predicts better than actual") doesn't hold here: past points keep information that expected points drop. | strong |
| F6 | **H61: efficiency earns opportunity.** Past points over expected improve the forecast of next game's expected points by 0.94% (0.74 to 1.12), beside past expected points, targets, carries and snaps. Players in their first two seasons +1.37%; later +0.76%; RB +1.17%, WR +1.02%, TE +0.23% (not clear). At a similar level of work (about 10 expected points a game), the players furthest under expected over their last 4 games lose 0.96 expected points next game; the furthest over gain 0.17. Losing work for poor play shows more than gaining it for good play. | medium: the by-group table mixes in ordinary drift back to average |
| F7 | **H57: opportunity follows a player in part.** Season to next season, 50+ chances in both: expected points per game repeat at 0.67 for stayers (n 1,147) and 0.52 for movers (0.43 to 0.59, n 234); per snap 0.76 and 0.68. Running backs lose the most by moving (−1.02 expected points a game, stayers −0.12); receivers lose nothing (+0.03). | medium: only players with real roles in both seasons are in it, which flatters both groups |
| F8 | **A mover's next role is about half his and half the seat's.** Next season's expected points per game for movers: 0.40 × his own last season + 0.33 × what the new team gave the player who held the same depth rank the year before. | weak: the rank is the one he ended up with, known only in hindsight |
| F9 | **"Quality" per chance is almost a label.** Expected points per chance repeat at 0.96 odd against even weeks and 0.97 season to season, 0.96 for movers. It mostly says whether a player is a back or a receiver, and what kind. | strong, and positions are pooled, which inflates it |
| F10 | **H60: splitting by formation doesn't follow movers better.** Last season's expected points re-weighted to the new team's shotgun rate: r 0.489 against 0.516 for the plain number; among movers to a team at least 10 points of shotgun rate different, 0.451 against 0.503. The fit term is +5.6 with a standard error of 5.5. A player's shotgun share of his work is his own in part: it repeats at 0.80 for stayers and 0.49 for movers. | medium: one split (shotgun or under center), 234 movers |
| F11 | **H58: yards after the catch over expected are a trait; they pay for tight ends, not for wide receivers.** Season to season: WR 0.35 (0.29 to 0.41), TE 0.39, RB 0.14. For tight ends they predict next season's points over expected (r 0.30) and add beside last season's (+0.042 points per chance per yard, standard error 0.017); the top quarter average +0.126 a chance the next season, 67% above zero. For wide receivers: r 0.12, nothing beside last season's points over expected, and the top quarter averages +0.001, 47% above zero. | medium |
| F12 | **H62: everyone regresses, at about the same rate.** Share of one season's points over expected per chance kept the next: everyone 26% (21 to 31); stayers 25%; movers 22%; RB 21%, WR 23%, TE 37%. Above or below zero two seasons running: 29% (21 to 37), against 17% (7 to 27) for players who switched sides. Moved and stayed on the same side on the new team ("carried it"): 20% (4 to 34, n 73). No group clearly keeps more than a third. | medium; weak for the 73 |
| F13 | **A lasting part exists, and sample size is what sets the rate.** The spread of points over expected per chance across player-seasons is 0.216; the part that lasts is about 0.114 (roughly 0.7 points a game at 100 chances a season). Players with 150+ chances keep 35% (25 to 45). The gap closes by half or more the next season 57% of the time (61% for gaps of 0.10 a chance or more). | medium: the players are survivors with 50+ chances in both seasons |

## The hunches

| # | Hunch | Verdict | Real? | Pays? | CEO said | Claude said |
|---|---|---|---|---|---|---|
| H56 | Goal-line carries and targets are worth the most | **held** (F3) | yes | no, beyond counts (F4) | 80% | 90% they rank first: yes; "three times an average chance": 2 to 5 times; 40% it pays: it didn't |
| H57 | Expected points follow a player from team to team | **held in part**: 0.52 for movers against 0.67 for stayers (F7, F8) | partly | not a forecast yet | 25% | 60% that movers repeat at 0.5+: 0.52; stayers "about 0.75": 0.67 |
| H58 | Receivers strong after the catch consistently beat expected | **unclear**: the trait repeats; it pays for tight ends, not wide receivers (F11) | partly | partly: TE only | none | 65% it repeats at 0.25+ and predicts: yes for TE, half for WR |
| H59 | Expected points are more consistent than efficiency | **held** (F2) | yes | not a forecast | 80% | 97%; expected 0.7+ and over-expected under 0.15: 0.84 and 0.14 |
| H60 | Split by scheme, opportunity follows players better | **failed** (F10) | no | no | 30% | 20% |
| H61 | A player creates his own opportunity through efficiency | **held**, small (F6) | yes | yes: +0.94% of expected points' error | none | 65%, small, stronger for young players: all three |
| H62 | Players whose pattern holds across teams won't regress | **failed** (leaning: 73 such players) (F12) | no | no | none | 30% some keep more: no; 70% everyone keeps under a third: yes, bar tight ends (37%) |

Retro patterns: P1 (ownership holds) fits H57, H59 and H61. P2 (team fit fails) predicted H60. P4 (clever versions tie the plain one) fits F4: the expected-points model ties plain counts. P7 (real isn't the same as useful) fits H56.

## The case against this exploration

- **The quality result (F4) is a next-game result.** Rare, valuable chances can't show in one game's forecast. Over the rest of a season they might; that wasn't run.
- **Survivors.** Every season-to-season number uses players with 50+ chances in both seasons. Players who lost their role after a bad year or a move aren't there, so "opportunity follows" and "efficiency is kept" are both flattered.
- **Efficiency holds some opportunity and the other way round.** A receiver who gets open deep makes his own throw depth, which this counts as opportunity, not skill.
- **PPR on targets and carries only.** No passing, no fumbles; another scoring would shift the worth of each kind of chance (touchdowns weigh more in standard scoring).
- **Target rows before 2009 are thin** (about 10,000 a season against 16,000 later), which only touches the first seasons' training.
- **One version, looked at once**, and the counts-against-quality comparison used one setting of the models. Differences of 0.1 to 0.2% are within what another setting could move.

## What this means for the brief

- **Build the split:** expected points and points over expected per player-game, in the package, any scoring (F1, F2).
- **The CEO's regression measure is feasible** as a rate per player set by his number of chances (method B): the lasting part is small and real (F13), and no group is exempt (F12).
- **The efficiency-to-opportunity link is worth an input** in whatever forecasts opportunity: it is the clearest gain here (F6).
- **Forecast with counts first.** For next game's points the plain counts beat the expected-points model as inputs (F4), so the ladder's first rungs are counts, and expected points must beat them to be used.
- **Movers: own record and seat, about half each** (F8), with no scheme split (F10). Method C isn't worth building yet.
- **Open for the CEO:** what the expert's main output is, given F4; whether to test the rest-of-season horizon before agreeing; tight ends' yards after the catch (F11).
