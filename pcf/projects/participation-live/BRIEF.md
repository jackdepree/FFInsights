# Brief: Participation inference (`participation-live`)

**Status:** agreed 2026-11-11 (the CEO: "Yes we can start the build as long as our goal is to map every play’s participation"), with the exploration's changes below; kickoff 2026-11-11 (the CEO: "the next expert we build is the participation inference expert") · **Layer:** expert · **Cadence:** in_season (each completed game, by the morning after)

## The usual way
*Claude, 2026-11-11, before any research.*
- **Charting companies** (FTN, PFF, SIS) record who was on the field by hand from the All-22 film. The NFL has it exactly from the tracking chips in the shoulder pads. Both are paid or post-season only (DATA_SOURCES.md; FTN's commercial licence is on hold, ROADMAP 2026-11-11).
- **Without film or chips, analysts reconstruct it from partial clues:**
  - every play has 11 per side;
  - some players are named in the play-by-play (passer, rusher, targeted receiver, tacklers, pass defenders, sackers, penalised players);
  - each player's snap total per game is known the next morning;
  - depth charts say who's in line.
- **The modern version** trains on seasons where the true answer is known, then fills in each new game so that every play has 11 and every player's total matches his snap count.

## Analogies
1. **Gene imputation.** Cheap DNA tests read a sample of your genetic markers, and the rest are filled in from a reference panel of fully sequenced genomes, because markers come in blocks that travel together. The standard tool walks along the genome with a hidden Markov model, guessing which reference block each stretch copies. Here the 2016–2025 participation is the reference panel, a new game is the cheap test, personnel packages and rotation series are the blocks, and the walk is along the plays of a drive. This is also the shape of H35: a player's sequences on and off are the blocks.
2. **Balancing a table when only the totals are known.** Economists fill in a table of who sold to whom from the row and column totals plus a few known cells, adjusting until everything adds up (iterative proportional fitting). Our table has plays as rows (each adds to 11 per side) and players as columns (each adds to his snap count), with the named players as known cells. Any chance per player per play must respect both totals.

## What it builds on
- **The answer key:** `player_play.on_field` (participation): who was on the field on every play, both sides, 2016–2025, known after each season. The exploration uses 2016–2024; the 2025 vault stays closed.
- **Known by the morning after:**
  - play-by-play's named players on every play;
  - weekly snap counts (offense, defense and special teams per player-game, 2013 on);
  - daily depth charts;
  - rosters and the injury report.
  - FTN charting's counts per play (backfield, box, pass rushers, blitzers) arrive 1–2 weeks later, so they could refine a game after the fact, not by the next morning.
- **participation (done):** forecasts each player's snap share before a game. It's a prior here, not the same job.
- **player-pace:** the in-season expert was a dead end because in-season participation doesn't exist (player-pace#R2–R5). Between seasons, skill players' plus-minus on pass rate repeats and forecasts next season's 15% better than the group average (player-pace#R1). An in-season plus-minus needs this expert.
- **schemes-v2#F3:** personnel use follows the head coach when coaches move: the team's habits are a coach's habits (H33).

## The CEO's answers (2026-11-11, word for word)
1. **What it's for:** "this new expert is mainly for live forecasting of our models that could deal with play by play predictions. We will want to estimate the importance and value of each player within a live season to augment our forecasts and bets. So, I’d say all of the above."
2. **Outputs:** "yes it will output two main data sets a chance for every possible player on that play and one best guess for each play. So, both."
3. **Sides:** "we will want to estimate both offense and defense."
4. **Timing:** "we will want to reconstruct each completed game. We will not need to forecast each play for the next game."
5. **Success:** "both, we can measure success in many different ways."
6. **Paid data:** "we only want free data unless we discover that the data is absolutely necessary to beat the betting lines. So for now we will put a hold on this paid api option."

## CEO hunches
*The CEO's words, recorded as said, before Claude's research.* Each gets a verdict in [`projects/HUNCHES.md`](../HUNCHES.md).

**The CEO's direction** (2026-11-11): "we will want to use as many patterns as possible for the inputs of this model." And: "We can test a bunch of different charters and conditions to see what predicts the player turnover per play."

> "We want to see the player’s past participation tendencies and the team’s own variance on certain situations, alike maybe this coach or this team has been switching out a bunch of players on third down or maybe in the fourth quarter. Yes we will definitely want to estimate fatigue on a drive and consecutive touches."
>
> "It is also helpful to see a player’s individual chance of consecutive or multi-sequential plays, maybe one player often will play two more snaps after they make a reception and so on."

| # | Hunch, in short | What the usual way says | How the exploration will test it |
|---|---|---|---|
| H32 | A player's past participation tendencies predict whether he's on each play | Who plays is the depth chart and the season's snap share | His earlier on-field rates by situation (down, distance, quarter, score, field position, the offense's personnel) against a depth-chart and snap-share baseline, on held-out games |
| H33 | Each team or coach has its own substitution habits in certain situations (third down, the fourth quarter) | Packages follow league-wide down-and-distance norms | Per team and per coach, how many players change between plays by situation, against the league's rate in the same situations; through the consistency test (does it repeat week to week and season to season?) |
| H34 | Fatigue on a drive and consecutive touches predict who comes off | Fatigue matters for defensive line rotation, little else | The chance a player is off on the next play by plays in the drive so far, his consecutive snaps and his consecutive touches, by position, against the same situation without them |
| H35 | Players have their own patterns across consecutive plays (stays on two more snaps after a reception) | Substitutions happen between series and with personnel calls, not after a player's own plays | Each player's chance of staying on for 1, 2, 3 more plays after an event (a reception, a carry, a long play) against his usual rate, and whether it repeats season to season |

### Claude's assumptions, limits and expectations
*Stated before the exploration, so its results mean something.*
- **For every hunch:**
  - *Training on past seasons' participation is point-in-time.* A season's participation is known the day after its Super Bowl, so a model for 2026 games may learn from 2016–2025. What it may not use is participation of the season it's estimating (rule m). Each game's inputs are known by the morning after: named players, snap counts, depth charts.
  - *In season, "past tendencies" have two sources:* earlier seasons' true participation, and this season's earlier games as this expert estimated them. Learning from its own estimates can compound its errors. The exploration measures how much this season's estimated games add, against earlier seasons' truth alone.
  - *Snap counts are the strongest clue.* A player with 60 of 60 offensive snaps was on every play, and one with 0 on none. The hard cases are the part-timers: rotating backs, tight ends, receivers 3 to 5, the defensive line, sub-package defensive backs.
  - *A no-huddle play locks the personnel:* the offense can't substitute, and the defense usually doesn't. That's a free constraint.
  - *Special teams are out of scope*, read from "both offense and defense". Their snap counts help only to rule players in or out of the game.
- **H32:** *My expectation:* holds. A player's share of snaps in a situation (third down, inside the 10, two-minute) repeats, and beats the plain season share for part-timers. Limit: rookies and players new to a team have no history.
- **H33:** *My expectation:* holds. Personnel is the coach's (schemes-v2#F3), so substitution by situation should repeat within a coach's stint and follow him to a new team. Limit: "switching out a bunch of players" needs both plays' lineups, so it's measured on the 2016–2024 answer key, where both are known.
- **H34:** *My expectation:* holds for defensive linemen and backs (rotations by snaps played), small for receivers and offensive linemen. Limit: consecutive touches are rare outside backs, so the samples outside backs are thin.
- **H35:** *My expectation:* a player's on-and-off runs repeat (rotation in blocks, like a back who plays two series and sits one). The event-specific part (after a reception) is real but small. Limit: in season, the previous play's lineup is itself an estimate, so this enters as a sequence model over the whole drive, not as a known input.

## The question
On each play of a completed game this season, who was on the field for each side, and how sure are we, from free data known by the morning after?

**The goal is the map of every play** (the CEO, 2026-11-11): for each play in order, each side's 11. Game totals are not the target: each player's snap count is known the next morning and is used only as a fact the play-by-play map must add up to.

## Why it matters
PCF's live play-by-play models and each player's in-season value need to know who was on the field on every play. That's only available after the season (free) or with a paid licence (on hold). With it, PCF can measure in-season plus-minus (which the in-season player pace expert needed), live context and value over expected, routes and roles per play, and how a team's play changes with a player in or out. Those feed forecasts and bets.

## Terms
- **Standard terms used:** [participation, snap count, personnel grouping, depth chart, no-huddle](../../docs/GLOSSARY.md).
- **New terms this project introduces:**
  - **On-field chance:** a player's estimated chance of being on the field for a play, for his side.
  - **Best-guess lineup:** the 11 per side per play that the on-field chances make most likely, with each player's snap total matched to his snap count.
  - **Named player:** a player the play-by-play lists on a play (passer, rusher, targeted receiver, tackler, and so on). He was on the field for certain.
  - **Turnover per play (substitution):** how many of a side's 11 change from one play to the next.

## Assumptions
- Everything an estimate uses is known by the morning after the game (rule c), except FTN's counts, which come 1–2 weeks later and are kept apart.
- Participation's answer key is right: nflverse's 2016–2022 come from Next Gen Stats tracking and 2023 on from FTN's charting. A change of source in 2023 may change its error.
- One season's estimates never learn from that season's true participation.

## Goals
1. **The patterns:** a verdict for each hunch (H32–H35), with numbers, and each new measure through the two tests (CONSISTENCY.md).
2. **The two outputs:** each possible player's on-field chance per play, both sides, and a best-guess lineup per play, for every scrimmage play of every completed game.
3. **Fit for use:** the measures built from the estimates match the ones built from the true participation (plus-minus, personnel rates, routes per play).

## Success and failure, as tests
*Thresholds from `docs/VALIDATION.md`; where it has none, the bar is beating the simpler version (rule k).*
- **Per play:**
  - **Accuracy:** the share of each play's true 11 that the best guess gets right, overall and by position, against two baselines: the snap-share-only estimate (each player's chance is his share of the game's snaps) and the depth chart (the top players at each spot).
  - **On-field chances:** a log loss that beats both baselines, and calibration inside VALIDATION.md's bands (a 70% chance is right about 70% of the time).
- **Fit for use:** player-season plus-minus and team personnel rates from the estimates against the same from the true participation, on held-out seasons: the closer the correlation is to 1, the better.
- **Signal:** the estimates beat a shuffled, signal-free version of themselves (rule k).
- **Football sanity:**
  - every play has 11 per side;
  - each player's total matches his snap count;
  - a named player has a chance of 1;
  - no-huddle plays keep the offense's 11.
- **Failure looks like:** for the part-timers, no better than the snap share. Then the snap share is the honest estimate, and the in-season plus-minus stays out of reach.

## Inputs and outputs
- **Inputs:** play-by-play (situation, named players, no-huddle, drive), snap counts, depth charts, rosters, the injury report, and earlier seasons' participation as the answer key. FTN's counts only as a later refinement. All already in PCF; nothing new to sign off.
- **Outputs:**
  - **On-field chances:** per game, play, side and player, his chance of being on.
  - **Best-guess lineups:** per game, play and side, 11 players.
  - Both for every completed game, by the morning after, in the standard schema, made walk-forward so higher layers can learn from them (rule e).

## How it will be used
Live play-by-play models, in-season player plus-minus and value, context and value over expected in season, routes and roles per play, fantasy usage, and the game simulator.

**The long-run aim** (the CEO, 2026-11-11): each player's causal effect on each play and its outcome. That needs the map play by play, not totals. The on-field chances let such a model carry the uncertainty (a player 60% likely on counts as 60%, or many possible lineups are drawn and the effect must hold across them); the best guess alone would make effects look more certain than they are.

## Agreed changes (2026-11-11)
The exploration ([EXPLORATION.md](EXPLORATION.md): GO) changed the brief, and the CEO agreed it: "Yes we can start the build as long as our goal is to map every play’s participation".
- **The model is a sequence model over the team's snaps** (two snaps of memory at least), because the snap before is the big lever (participation-live#F6, F8). The CEO's patterns are its inputs: snap share, the league's situational habits, his own and his team's history, the drive and his streak, and his own stay and return rates.
- **The best guess keeps each player's snap total** across the game. Each play's top picks are off by 7.8 plays a player (F7).
- **No-huddle is a feature, not a constraint** (F2).
- **The bar to beat** is the history model without sequence (74.6% offense and 73.3% defense of open-slot players right, log loss 0.460, 2022–2024). The snap share (72.8%, 72.2%, 0.478) and the depth chart (about 65%) are the baselines. The oracle (79.0%, 81.6%, 0.382) is the ceiling.
- **Terms in plain words:** *known spots* on a play are the players certain to be on it (on every snap by his snap count, or named by the play-by-play); *open spots* are the rest of the 11, which the model fills.
