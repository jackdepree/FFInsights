# Brief: Snap leverage (`snap-leverage`)

**Status:** draft (kickoff 2026-11-14; the CEO signed off on the new expert and its name: "I sign off on this new expert, but can we rename it to snap leverage"). Agreed after the exploration · **Layer:** expert · **Cadence:** in_season (to be settled: see Assumptions 4)

## The usual way
*Claude, 2026-11-14, before any research.*
- Baseball's **leverage index** scores each moment by how much the win chance can swing on it (1.0 is an average moment). Who a manager brings in at high leverage shows which relievers he trusts.
- Football analysts copy it with win-probability models: "high-leverage snaps" are the ones where a play can move the win chance most (late, close, short of the sticks or near the goal line).
- Basketball tracks "clutch minutes" and closing lineups, the five a coach trusts at the end of close games.
- Most of this is descriptive: snap counts in situations. It is rarely tested against an outcome, which is where this project can be different.

## Analogies
1. **The hardest operations.** Which surgeon a hospital gives its hardest cases says more about trust than who works the most hours. Here: who is on the field when the game hangs on the snap.
2. **Revealed preference (economics).** A choice made when it costs the most shows what someone really values. A coach can rest anyone in a blowout; who he keeps on the field when the season is on the line is the costly choice.

## CEO hunches
*The CEO, 2026-11-14, word for word.*

First message: "Opportunity quality sounds like a very interesting expert. I want to build something similar to expected fantasy points but instead a measure that can apply to all players. The goal of the expert would be to attempt to weight the snaps that each player participated in. The expert attempts to measure the importance of snaps and shows which players a team relies on in high stakes situations. The only issue I foresee is a good test. How should we estimate the success of the measure, or a better question would be what outcome is the most appropriate? I think one good outcome could be salary on new contracts or future playing time."

Second message: "I think that it is true that starters will offer no signal, because they necessarily carry zero variance to learn from. However, I do believe that the starters are trusted more than nonstarters, this is simply an interpretation of the results rather that a description of the methodology. I think that the situation trap will not cause too much trouble in our expert, this is because I assume there will be other plays of winning teams that need to run the ball to drain the clock and win a close game. I think situation will definitely play a part and could skew the interpretation of the results. I think playing time should be the main test; contracts and plus minus should be the secondary tests. I sign off on this new expert, but can we rename it to snap leverage instead, or does that interfere with another expert? I want to make this expert to essentially measure the variance of winning percent added per play based on conditions/situations. I would assume to find that some positions carry larger variance in leveraged (high stakes) plays, like wide receiver and cornerback. I would also be curious to see if schemes that a team deploys interacts with which players or positions have the highest variance in leveraged plays."

| # | Hunch | What the usual way says | How the exploration will test it | Claude's expectation, before testing |
|---|---|---|---|---|
| H45 | Weighting each player's snaps by "the importance of snaps" shows "which players a team relies on in high stakes situations", and that predicts "future playing time" (main test) and "salary on new contracts" and plus-minus (secondary) | Plain snap counts and snap share | A player's leveraged snaps and trust over expected (Terms) added to his plain snap share: next 3 games' and next season's snap share, every position, held-out seasons; then the secondary tests (Tests) | A small gain overall, because snap share already predicts itself well (R² 0.6–0.76, participation#F3). Larger where roles are changing: rookies, backups, mid-season promotions |
| H46 | "The starters are trusted more than nonstarters" (an interpretation of the results, not the method) | Starters are whoever the depth chart lists first | Among players with a similar overall snap share, do depth-chart starters play a larger share of the high-stakes snaps than their overall share, and non-starters a smaller one? | Held, and clearly: rotations shrink in late close games (the defensive line stops rotating, running-back committees narrow) |
| H47 | "The situation trap will not cause too much trouble", because "there will be other plays of winning teams that need to run the ball to drain the clock and win a close game"; situation "could skew the interpretation" | Adjust for situation and personnel: third-down backs and nickel corners play the passing downs because of their role | The measure raw and adjusted for situation type (down, distance, score, clock): how far the player rankings move, which version predicts future playing time better, and how much of the high-stakes snaps are clock-draining runs | Partly held. Little difference for everyday players; real differences for passing-down specialists, because a leading team's late runs swing the win chance less than a trailing team's passes |
| H48 | "Some positions carry larger variance in leveraged (high stakes) plays, like wide receiver and cornerback" | QBs carry most of a play's win-probability swing; position value as the salary market prices it (QB, edge, tackle, WR, CB) | By position: how much a play's WPA spread depends on the player in that spot, on high-stakes against ordinary plays (involvement: who was targeted, covering, carrying; and on-field plus-minus), against a shuffled-player null | QB first by far; WR and CB above the other positions on passing plays, since deep passes swing the win chance most |
| H49 | "Schemes that a team deploys" interact "with which players or positions have the highest variance in leveraged plays" | Position value is the same for every team | H48's position spreads split by schemes-v2's traits (pass rate over expected, shotgun, depth of target, tempo), against a shuffled-team null | Unclear. A pass-heavy team moves leverage toward WRs and CBs, but that is a main effect; schemes-v2's interaction hunches mostly failed (H13, H14, H16) |

## The question
Which players does each team put on the field when the game hangs on the snap, beyond how much they play overall, and does that show who the team relies on?

## Why it matters
- It covers all 22 players, including linemen and defenders, whom fantasy stats ignore.
- **Player opportunity** (volume for the coming game) gets a leading signal for role changes: a backup trusted late in close games may be next in line.
- **Vacated opportunity** and injuries: losing a trusted player should cost a team more than losing a player with the same snap share (the plus-minus test).
- **Contract value** (parked `contract-motivation`, `dynasty-values`): if the market pays for trust, the measure helps value players before their next deal.

## Terms
- **Standard terms used:** WPA (win probability added), win probability, snap share, depth chart, participation ([GLOSSARY](../../docs/GLOSSARY.md)).
- **New terms this project introduces** (names to settle in the brief):
  - **Leverage** (the CEO's "variance of winning percent added per play based on conditions/situations"): how much a play's win chance can swing **before the snap**, from its situation alone (quarter, clock, score margin, down, distance, field position, timeouts). Computed as the spread of WPA among plays in that situation, fitted only on earlier seasons. Different from the `high_leverage` tag, which marks plays that turned out to swing the win chance 5 points or more, after the fact: a coach picks the lineup before the snap, so trust has to be read from leverage before it.
  - **Leveraged snaps:** a player's snaps, each weighted by its leverage. Starters rank high here (H46).
  - **Leverage share:** his leveraged snaps as a share of his team's, the weighted version of snap share.
  - **Trust over expected:** his share of the high-stakes snaps minus the share his usage in that kind of situation predicts. This is where non-starters show signal; starters sit near zero (the CEO: "starters will offer no signal, because they necessarily carry zero variance to learn from").

## Builds on
| Project | What we use | Why |
|---|---|---|
| `grain-tables` | `play` (WPA, win probability, situation), `player_game.snaps`, `player_game.depth` | Plays, snap counts for every position (2012→), starters |
| `participation`, `participation-live` | nflverse participation (who was on the field, 2016–2025, after the season); the morning-after on-field map (2019–2024 walk-forward, live in 2026) | Which snaps each player was on. Participation's champions are the bar for skill-player playing time |
| `tag-tables` | Situation tags (two-minute, red zone, garbage time) and `high_leverage` | The simple rungs and the after-the-fact contrast |
| `schemes-v2` | Traits per team-game | H49 |
| `team-efficiency` | Findings on WPA | What WPA can and can't do |
| `validation-harness` | Walk-forward moments, consistency (`pcf.validation.consistency`) | The tests |

**Already tried:**
- **WPA is noisy as a team measure:** it forecasts team efficiency 4.7–6.7% worse than EPA and adds nothing beside it (team-efficiency#F6). Here WPA is used for the stakes of a snap, not as a player's quality.
- **nflverse's win probability and EPA are in-sample before 2020** (tag-tables#F4), so a leverage built on them looks sharper there than it was.
- **Snap share predicts itself well** (participation#F3) and past box-score stats add almost nothing beside it (#F7): the main test's bar is high.
- **2016 participation lists 11 a side on only 87% of plays** (cleaning-port#F5).

## Assumptions
1. Coaches choose who is on the field partly by trust, and that choice shows most when the stakes are high. Flagged: the same lineup may simply be the base package.
2. Leverage can be estimated before the snap from the situation alone, well enough to rank snaps.
3. Situation type (passing down, clock-draining runs) can be separated from trust (H47).
4. **Timing (rule m):** who was on the field is known for sure only after the season (nflverse participation). Live, it comes from participation-live's map (89% of offensive players and 83% of defensive players right per play). The exploration uses the true participation; whether the live version runs on the map, or the expert is retrospective, is settled in the brief.
5. Contracts: OverTheCap's data has only the year signed, no date, and is one snapshot (DATA_SOURCES.md). It serves as an outcome only, never as a feature.

## Goals
A per player-game measure of leveraged snaps, leverage share and trust over expected, for every position, that repeats and predicts future playing time beyond plain snap share.

## Tests
- **Success looks like:**
  - **Main (the CEO):** leveraged snaps or trust over expected improve the next 3 games' and next season's snap-share forecasts over plain snap share, with the 90% interval above zero, on held-out seasons.
  - **Secondary (the CEO):** a lighter bar, any signal with its interval clear of zero:
    - **Contracts:** the next veteran contract's pay as a share of the cap, within position, beyond age, draft slot and plain snaps.
    - **Plus-minus:** when a trusted player misses a game, the team plays worse than when a player with the same plain snap share misses one. Taken as the CEO's "plus minus"; to confirm.
  - **Consistency:** trust over expected repeats week to week and season to season, with intervals clear of zero.
- **Failure looks like:** no gain over plain snap share, and no consistency. Then leverage-weighted snaps are a description, not a signal.
- **No-noise target** (CEO approves): next 3 games' snap share; the baseline is plain snap share from the same model.
- **Seasons:** participation 2016–2024 (2016 thin, train only); held out season by season; the vault is 2025, unopened.

## Inputs and outputs
- **Inputs:** `play` (known after the game), nflverse participation (after the season) or participation-live's map (the morning after), `player_game.snaps` and `player_game.depth` (each at its known-at).
- **Outputs:** per player-game: leveraged snaps, leverage share, trust over expected; per play: leverage. Ranges to come with the build.

## How it will be used
Features for player opportunity and vacated opportunity; a lens for which players a team can least afford to lose; and possibly contract value.

## Plan
- **Exploration (time box: one session):** leverage per play (rung 0: 4th quarter in one-score games; rung 1: WPA spread by situation); the per-player measures; H45–H49 and the consistency test.
- **Then the brief is agreed** with what the exploration changed, and the build climbs the ladder.
