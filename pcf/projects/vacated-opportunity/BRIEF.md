# Vacated opportunity: who absorbs an absent player's targets and carries

> **Status:** kickoff, 2026-11-24 (the CEO: "Ok, let's start vacated opportunity"). The usual way and two analogies are below. The CEO's direction and hunches H109 to H112 are in, all with odds (2026-11-24). The exploration ran methods 1 and 2 (the CEO's choice) the same day, pre-registered and with results in [EXPLORATION.md](EXPLORATION.md): go. H109 held by its pass rule; H110, H111 and H112 failed (H112's stayers side bet held); I125 held. The CEO closed H109 (held) and H110-H112 (failed) and split the project into two experts, `vacated-offseason` (between seasons) and `vacated-live` (within seasons). The CEO answered the brief's three questions (the bar is no change; a preseason intake flag; all three shares). The brief is drafted below, for the CEO to agree.

## Why now

- **The pieces it needs are built or agreed:**
  - participation (who plays, and his snap share);
  - availability (whether he'll play, brief agreed);
  - roles (what each player is asked to do; brief agreed, with its positionless spaces);
  - opportunity-quality (expected points per chance, and next game's opportunity).
- **It's the link to products:** `player-opportunity`, the composite that fantasy projections read, depends on it.
- **The record says there's room:**
  - a same-position teammate Out is information box-score models lack (+0.61 fantasy points, miss-lenses#F4), though experts' consensus rankings (ECR) already have it;
  - a newly missing full-time player costs his offense +0.021 EPA a play (snap-leverage#F11);
  - only 32% of real starter changes are visible by the Saturday run (player-pace#R5).

## The usual way

Fantasy analysts sum a departed or injured player's targets, air yards and carries ("vacated targets") and hand them out. They split them in proportion to the remaining players' current shares, or give the bulk to the depth chart's next man up. The sharper version is a with-or-without split (WOWY): each teammate's target share in past games with and without the star, read off the same season. Betting and projection sites do the same for props, usually assuming the team's total volume holds while the shares shift. In the offseason the same sum, "vacated targets" from players who left in free agency, is a staple of draft-season articles.

## Two analogies

- **Economics: diversion ratios in merger analysis.** When a product leaves the market, competition authorities ask where its customers go: what share switches to each rival, and what share stops buying altogether. The answer comes from how close the products are (customers move to the nearest substitute) and from past exits. This suggests three things to look at:
  - **the pie isn't fixed:** when the star is out, the team may throw less, so part of his targets disappears rather than moves;
  - **closeness decides who gains:** a teammate's distance from the missing player in role space (the roles project's coordinates) may predict his share of the diversion better than his current share does;
  - **past exits are data:** each team's earlier absences show its own diversion pattern.
- **Ecology: competitive release.** When a dominant species is removed, its competitors expand into its niche, and the one whose niche overlapped most expands most. Sometimes a species that was absent moves in from outside. Two questions follow:
  - Is absorption mostly by the closest teammate (overlap), or spread across the room?
  - How often does the gain go to someone outside the usual rotation (a call-up, a practice-squad player), whom no share-based method can see?

## What we already have

- **Findings:**
  - Target share and target depth travel with a receiver (F1); a back's carry share belongs mostly to his backfield (F2).
  - Substitutes are roughly like for like in role, clearest for backs (H101: rank 0.44, backs 0.30).
  - Pairs who swap for each other repeat at r 0.83 (H36), and a coach's role-pair habit (TE2 for WR3) is a trait of the coach (H37).
  - Participation already reads teammates' absences: they're among its next-game lasso's top inputs (participation#F20). The competition on the snap and pair habits add 1.8–2.2% on offense (participation-live#R10).
  - Movers are over-projected in evenly shared rooms (participation#F21). A mover's new slot adds more to his first 4 games than his own old share does (F57).
- **Data (free):**
  - snap counts per game (in season);
  - targets, air yards and carries per play (play-by-play, in season);
  - the injury report and rosters (in season);
  - who was on the field each play (participation, after the season);
  - routes for the targeted receiver.
- **Models and outputs:**
  - participation's snap-share forecasts and `active`;
  - opportunity-quality's next-game opportunity forecast (the incumbent for targets and carries);
  - the roles spaces (once built);
  - availability's chance he plays (once built).

## The backlog that fits

- **I49:** swap pairs say who inherits an absent player's snaps.
- **I9:** players new to a team are over-projected; the role they walk into might fix it.
- **I122:** a shrunk vacancy forecast, the average moved part-way toward the departed player's role.
- **I55:** the first game back from injury is under-forecast.
- **I53:** which usage rates travel with a player.

## The CEO's direction and hunches (word for word, before any test)

The CEO's message, 2026-11-24, in full:

> "Yes I would love to explore a plus minus approach but for all players, this way we can attempt to estimate a stable snap share to apply to the players that stayed with a team when a top player has left. I think it would be interesting to measure the variance between teams that intake a top player at the position group and teams that simply leave that position group void. I am 30% confident that if we find teams that suffered efficiency gains when a top player is injured then they will be more likely to intake more players at that position group. We can look at overall offense and defense efficiency and we can look at position group's respective outcome like pressures for offensive lines. I would be 60% confident that our roles project coordinates predicts recipients better than plain position labels. I think offseason departures and immigrations matter more than weekly injuries, but both are good for this expert. I think anything we find to be predictable counts as opportunity, but targets and carries should be the bedrock."

**Direction (not bets):**
- **Offseason first, weekly second:** "I think offseason departures and immigrations matter more than weekly injuries, but both are good for this expert." The offseason case (a player leaves in free agency, by trade or by release, and players arrive by free agency, trade or the draft) leads; the weekly case (a player Out on Sunday) follows. By rule m these are two cadences: **offseason_events** (between seasons, at free agency and the draft) and **in_season**. When the brief is agreed, they register as two experts (proposed: `vacated-offseason` and `vacated-live`, one project folder).
- **What counts as opportunity:** "anything we find to be predictable counts as opportunity, but targets and carries should be the bedrock." So targets and carries come first. Snaps, air yards, red-zone and goal-line chances are added where they prove predictable (the two tests for every new measure).
- **Every position group is in scope for the plus-minus** ("a plus minus approach but for all players"), not only skill players. For the line and the defense, the outcome is the group's own result (pressures allowed for an offensive line), since they have no targets or carries.
- **A measurement the CEO asked for** ("it would be interesting to measure the variance between teams that intake a top player at the position group and teams that simply leave that position group void"): after a top player leaves, the teams that bring in a top player at his position group against the teams that don't. What happens to the stayers' shares, to the spread of outcomes, and to the team's efficiency. It's a comparison, not a bet; it becomes a hunch if the CEO gives it odds.

**What the free data has, for these questions** (assumptions first):
- **Departures and arrivals:** weekly and season rosters, trades, draft picks and contracts (all in the data layer). A player who leaves is identifiable; *why* he left (cut, not re-signed, traded) is mostly identifiable from trades and contracts.
- **A "top player":** needs a definition. The usual one is by snaps or targets in his position group (his team's top 2 WRs, top TE, top RB, as roles' H104 used), or by value (VOE's plus-minus, which is mostly the team's for non-QBs).
- **Pressures for an offensive line:** pressure is charted per play, so **per team, not per lineman**. The free data doesn't say which lineman allowed it. A line's result is a team-level outcome, and a lineman's plus-minus is the only way to split it.
- **Injured top players' efficiency effects:** the "newly missing" estimate exists (snap-leverage#F11: +0.021 EPA a play on offense), but per team-season it rests on a handful of games.

**The hunches** (also in `HUNCHES.md`; the CEO's odds where given):

| # | Hunch | The CEO's odds | Claude's odds |
|---|---|---|---|
| H109 | A plus-minus across all players estimates a stable snap share for the players who stay when a top player leaves: "Yes I would love to explore a plus minus approach but for all players, this way we can attempt to estimate a stable snap share to apply to the players that stayed with a team when a top player has left." | 75% (2026-11-24, before any test: "H109; 75%.") | For the claim as worded (on offseason departures, stayers' next-season snap share from a plus-minus of every player's share on which teammates are present beats the usual way, his share plus a split of the departed player's share in proportion to the room, held out): 35%. Side bets: it beats the usual way for target and carry share too, 30%; it beats the usual way on weekly absences (a player Out), 50% (there are more with-and-without games there) |
| H110 | Teams whose efficiency moved when a top player was injured bring in more players at that position group: "I am 30% confident that if we find teams that suffered efficiency gains when a top player is injured then they will be more likely to intake more players at that position group. We can look at overall offense and defense efficiency and we can look at position group's respective outcome like pressures for offensive lines." | 30% (given with the hunch, 2026-11-24); efficiency *losses* (the CEO, 2026-11-24: "Yes, sorry efficiency losses is the correct terminology") | For the claim (the bigger a team's efficiency drop in the games its top player at a group missed, the more players it adds at that group the next offseason, through free agency, trades and the draft, beyond the group's age and contracts): 25%. Side bet: teams that lose a top player for good (he leaves) add more at that group than teams that don't, 85%. The drop per team rests on a few games, and intake follows contracts and age first |
| H111 | The roles project's coordinates predict who receives a departed or absent player's opportunity better than plain position labels: "I would be 60% confident that our roles project coordinates predicts recipients better than plain position labels." | 60% (given with the hunch, 2026-11-24) | For the claim as worded (each stayer's share of the vacated targets and carries is forecast better from his distance to the departed player in role space than from whether he plays the same position, held out): 55%. Side bet: it still adds once his current share is in, 35% (roles' H107 and I124 found the coordinates add nothing beyond a player's own rates) |
| H112 | After a top player leaves, the teams that bring in a top player at his position group and the teams that leave it empty differ in what happens next: "I think it would be interesting to measure the variance between teams that intake a top player at the position group and teams that simply leave that position group void." | 30% (2026-11-24: "Yes I'll give 30% odds for being in a top player or leave it empty comparison.") | For the claim as read (teams that bring in a top player recover more of the side's efficiency the next season than teams that leave the group empty): 25%. Side bets: the spread of the efficiency change differs, 20%; the stayers' shares grow less on teams that bring someone in, 90% |


### The CEO's answers after the exploration, 2026-11-24 (word for word)

> "Yes you can close those hunches and h109 should be held. 2; yes. 3; yes maybe we should have two experts one for between and the other for within seasons."

- **The closes:** H109 held; H110, H111 and H112 failed, as their pass rules read.
- **Question 2** asked whether the results match the CEO's sense that offseason departures matter more than weekly injuries, though the weekly side came out strongest. The CEO: "yes". The offseason expert keeps its priority for the CEO; the weekly one is where the forecast is strongest.
- **Question 3:** two experts by rule m.
  - **`vacated-offseason`, between seasons:** after departures, free agency and the draft. Cadence `offseason_events`. Its gate is I125: did the team bring in a top player at the group?
  - **`vacated-live`, within seasons:** after each game, for a player Out this week. Cadence `in_season`. The weekly plus-minus.

  `vacated-opportunity` stays the parent project, holding the shared exploration and one brief for both.

## Methods

Three ways to estimate who absorbs a departed or absent player's opportunity. One of them is exploratory. Each is scored against the others, and **the simpler side wins a tie** (rule k).

| | Method | What it assumes | Cost |
|---|---|---|---|
| 1 | **The usual way, and the simpler side:** split the vacated share among the stayers in proportion to their current shares, or use with-or-without splits (each teammate's share in past games with and without the player) | Shares scale up evenly, or a pair's past splits repeat | Cheap |
| 2 | **The CEO's plus-minus for all players:** a ridge regression of every player's game share (snaps, targets, carries) on which teammates are present, with team-season effects, across all teams' games. A player's coefficient on a teammate's absence is his "share when that teammate is gone". Pooling all players borrows strength where a pair has few games apart. For the line and the defense, the outcome is the group's result (pressures allowed, EPA allowed) | A teammate's absence shifts a player's share by a stable amount, the same in every game. The absences we see (injuries) teach us about departures | A session. Injury absences are the data; they're few per pair, so the penalty matters |
| 3 | **Exploratory: diversion ratios from a choice model.** Each target (or carry) is a choice among the players on the field that play (participation, after the season). The model is a nested logit: players in the same role nest (from roles' spaces) are closer substitutes. Removing a player diverts his share mostly within his nest, and a separate volume part says how much of it disappears (the team throws less) | The choice on a play depends on who is on the field and each player's pull; closer substitutes take more of a missing player's share | A session or two. It's how antitrust estimates where a departed product's customers go, and it gives the CEO's "who receives" and H111's role test in one model |

The CEO's second message, 2026-11-24, in full:

> "H109; 75%. Yes, sorry efficiency losses is the correct terminology. Yes I'll give 30% odds for being in a top player or leave it empty comparison. Yes I think the oline and dline can be incorporated in this project. Try the first two methods in this exploration, thank you!"

**Direction (not bets):**
- **Methods 1 and 2 in this exploration** ("Try the first two methods in this exploration"). The choice model (method 3) waits.
- **The offensive and defensive lines are in** ("Yes I think the oline and dline can be incorporated in this project"): their snap shares in H109, and their group outcomes (pressures allowed by the line, pressures made by the defensive line) in H110 and H112.

### The CEO's answers on the brief's three questions, 2026-11-24 (word for word)

> "The bar to beat should be no change, yes. Yes a preseason flag is good enough. Yes both experts should forecast snapshare, target share, and carry share."

- **The bar to beat is "no change"** (his own share in games where the absent or departed player played), not the proportional split, which lost to no change in every cell of the exploration.
- **The offseason's intake gate uses a flag known before the season** (a newcomer at the group who was a top player at his group elsewhere last season, or a pick 1–64 rookie). Contracts stay out of the tables for now.
- **Both experts forecast all three shares:** snap share, target share and carry share. For the lines, snap share only.

---

# The brief (draft, 2026-11-24, for the CEO to agree)

**Status:** draft (for the CEO to agree) · **Layer:** expert (1), two experts sharing this brief · **Cadence:** `vacated-live` in_season (the Saturday run, 12:00 Eastern, like participation and availability); `vacated-offseason` offseason_events (after free agency's first wave, after the draft, and at the week-1 roster)

## Methods

The exploration ran methods 1 and 2 (the CEO's choice); method 3 waits.

| | Method | Where it stands | In the build |
|---|---|---|---|
| 1 | **The proportional split** and with-or-without | Lost to no change in every cell (H109, I125). With-or-without adds nothing over it (+2.4%) | Scored as a reference only. **It doesn't ship** |
| 2 | **The CEO's plus-minus for all players:** a ridge on every player-game's share, demeaned within his player-season, on each absent top teammate's share. A pooled part per pair of groups (the transfer rates), plus a pair part per same-group pair (I49) | Weekly: +31% of no change's error, clear in all five groups. Offseason: +17% where the group was left empty, a loss where a top player came in | **The method both experts build**, climbing the ladder below |
| 3 | **Exploratory: diversion ratios from a choice model** (a nested logit over the players on the field, per target and carry) | Not run | Waits for the CEO's call (a question below). It's the only method that models the team's lost volume and who receives in one model |

## The noise ceiling (from the exploration)

- **A stayer's share repeats:** split-half r of next season's snap share is 0.78 (OL) to 0.95 (TE).
- **It moves a lot:** a stayer's change in snap share has an SD of 0.25. The proportional split explains 0–8% of that change.
- **In season, the room is large:** the plus-minus removes 31% of no change's squared error on the absent player's group-mates.
- **The fitting noise is small:** across 40 bootstrap refits, no same-group transfer rate flips sign (WR's 90% range is +0.15 to +0.17).

## The question

**Within a season:** when a top player is Out this week, how much of his snap, target and carry share goes to each teammate?

**Between seasons:** when a top player has left, what is each stayer's snap, target and carry share next season, given who the team brought in?

## Why it matters

- **It's the biggest clear in-season result in this project:** a third of no change's error on the absent player's group-mates.
- **It's the link to products:** `player-opportunity`, the composite fantasy projections read, depends on it. Start/sit for the backup when a starter is Out is a weekly fantasy decision.
- **It stops a common mistake:** "vacated targets" handed to stayers in proportion to their shares, the usual draft-season article, loses to doing nothing, because teams restock 72% of the time.
- **Users notice it:** a backup's projection the week a starter is Out; a stayer's projection in drafts after free agency and the draft.

## Terms

- **Standard terms used:** snap share, target share, carry share, ridge regression, squared error ([`docs/GLOSSARY.md`](../../docs/GLOSSARY.md)).
- **New terms:**
  - **Group:** WR; TE; RB (with FB); OL; DL (the roster's DL; edge rushers listed as LB aren't in it).
  - **Top player:** among his team's top k by snaps in his group: WR 2, TE 1, RB 1, OL 5, DL 3. In season, by snaps to date; between seasons, by last season's.
  - **Absence:** a team game, after his first game for the team that season, in which a top player has no snap. Live, it's read from the Saturday run's report (assumption 1).
  - **Departure:** a top player on the team in season s who isn't on its week-1 roster in s + 1.
  - **Stayer:** a player in that group who played for the team in s and is on its week-1 roster in s + 1.
  - **With share ("no change"):** his share in the games where every absent or departed group-mate played. It's the bar to beat.
  - **Transfer rate:** the plus-minus's pooled part. How much a player's share rises per unit of an absent top teammate's share, per pair of groups (WR +0.16, TE +0.28, RB +0.24, OL +0.08, DL +0.09; across groups about 0).
  - **Pair part:** a stayer's own extra rise when a particular group-mate is gone (I49's swap pairs).
  - **Intake flag:** the team brought in a top player at the group: a newcomer who was a top player at his group elsewhere last season, or a pick 1–64 rookie. Known at the event (the CEO: "a preseason flag is good enough").
  - **Unclaimed share:** the absent or departed players' share that the stayers' forecasts don't absorb. It's what newcomers, call-ups and the team's lost volume take.

## Builds on

| Project | What we use | Why |
|---|---|---|
| `participation` | snap shares per game; its saved next-game and season forecasts; F20, F21 | The shares, and the obvious-input check: participation already reads teammates' absences (F20) |
| `availability` | the chance each player plays next game (once built) | `vacated-live`'s absence input, as an expected absence. Until it's built, the report's Out and Doubtful |
| `opportunity-quality` | its next-game opportunity forecast | The incumbent for targets and carries; checked beside |
| `crude-forecaster` | the yardstick's next-game and season boards | The downstream score |
| `roles-archetypes` | the pooled coordinates | Only for I126 (H111 retried where the group was left empty). H111 failed, so coordinates aren't inputs |
| `snap-leverage`, `miss-lenses`, `player-pace` | F11, F4, R5 | The room (a missing full-timer costs +0.021 EPA a play; a teammate Out is +0.61 fantasy points box scores miss) and the warning (only 32% of starter changes are visible by Saturday) |

**Already tried (don't redo):**
- The proportional split and with-or-without lose to no change everywhere (H109, I125).
- Role distance doesn't beat position labels for who receives (H111); among stayers, who receives is a small slice, because newcomers take most of it.
- An absence's efficiency cost is noise and doesn't forecast intake (H110). Intake doesn't clearly change efficiency (H112).

## Assumptions

1. **Live absences are known by the Saturday run only in part.** The exploration knew who sat (hindsight). The build reads the report: an expected absence of (1 − his chance of playing) × his share, with availability's chance once built and the report's Out and Doubtful until then. The hindsight version is reported beside it as the ceiling.
2. **Absences teach us about departures.** The transfer rates are learned from in-season absences and applied to departures where the group was left empty (I125 held this).
3. **The transfer rates are a trait of the league** (CONSISTENCY.md): one value per pair of groups, refit after every completed season. Teams and coaches may differ (the coach's role-pair habit, H37), which the structured rung tests.
4. **The team's volume is someone else's.** The experts forecast shares. How many targets and carries the team gets is pace's and opportunity-quality's.
5. **The offseason backtest uses the week-1 roster.** Historical rosters from March and April aren't in the free data, so the runs after free agency and the draft are live only, on that day's roster. Only the week-1 run is backtested.
6. **Newcomers' shares are out of scope.** The experts forecast stayers. The unclaimed share is handed on for participation and roles (I9, I122).

## Goals

- **`vacated-live`:** each player's snap, target and carry share for next game when a top teammate is expected to miss it, with an interval.
- **`vacated-offseason`:** each stayer's next-season snap, target and carry share after a departure, gated on intake, with an interval.
- **Both:** the transfer rates as a standing table (per pair of groups, per season), and the unclaimed share per team-group.

## Tests

- **Success looks like** (walk-forward, 2017–2024; intervals are 90% team bootstraps):
  1. **`vacated-live`:** beats no change on squared error for the absent player's group-mates, on snap share in each of the five groups, and on target and carry share for the skill groups, with the Saturday run's knowledge (assumption 1). The weekly target and carry result is new: the exploration tested only snap share in season.
  2. **`vacated-offseason`:** where the group was left empty (the intake flag), beats no change on snap, target and carry share for the skill groups, and on snap share for the lines. The gated forecast (the plus-minus where the group was left empty and for the lines, no change where a top player came in) beats no change over all stayers.
  3. **No noise:** each beats 19 shuffled copies of itself (absences shuffled across games within the team-season; departures shuffled across team-seasons).
  4. **The obvious-input check:** beside participation's saved forecast (and opportunity-quality's for targets and carries), the expert's forecast still lowers squared error. If it doesn't, participation already has it, and the transfer rates go to participation as an input instead.
  5. **Calibration and ranges:** the slope of the actual change on the forecast change is 0.85–1.15; q10–q90 coverage is 75–85%.
  6. **The yardstick** (reported): next-game receiving and rushing yards (`vacated-live`) and season yards (`vacated-offseason`), beside the crude forecaster and participation.
- **Ties (CLAUDE.md rule k):** a tie is an interval that includes zero, and the simpler side wins it. The simpler side, named now:
  - no change over any plus-minus;
  - the pooled part alone over the pooled part plus the pair part;
  - one rate per pair of groups over team or coach rates;
  - the ridge over trees;
  - the plus-minus over the choice model (if it's built).
- **Failure looks like:** it doesn't beat no change, or it adds nothing beside participation. Then no change ships, and the transfer rates are kept as a description and as participation's input.
- **No-noise target (for the CEO to approve):** next game's snap, target and carry share for the absent player's group-mates (`vacated-live`), and next season's for stayers (`vacated-offseason`), each against no change.
- **Seasons:** shares from 2013 (snaps begin then), the lines' pressure from 2016; scored 2017–2024; **the 2025 vault untouched until the end**.

## Inputs and outputs

- **Inputs** (known-at in brackets):
  - snap shares, targets and carries per player-game [after each game];
  - the injury report and availability's chance he plays [the Saturday run];
  - weekly rosters, and the week-1 roster for the offseason backtest [that week's file];
  - draft picks [the draft];
  - last season's top players by team and group [after the season].
- **Outputs:**
  - **`vacated-live`** (player-game, the Saturday run): the forecast snap, target and carry share next game, its change from no change, q10 and q90, and which absent teammates drive it;
  - **`vacated-offseason`** (player-season, at each event): the forecast next-season shares for stayers, the intake flag, q10 and q90;
  - **both:** the transfer rates table (versioned, per completed season) and the unclaimed share per team-group.

## How it will be used

- In `player-opportunity` and fantasy projections: a backup's projection the week a starter is Out; a stayer's projection in drafts.
- As an input to participation's next-game forecast, if the obvious-input check says participation lacks it.
- In the yardstick's next-game and season boards.

## Plan

- **Order:** `vacated-live` first (`vacated-offseason` reads its transfer rates), each in its own build session.
- **The ladder:**
  1. no change (the bar);
  2. the pooled ridge (one rate per pair of groups);
  3. plus the pair part (I49);
  4. structured: transfer rates partly pooled by team and by coach (H37's habit);
  5. trees on the residual (the absent player's size, the stayer's rank, the depth chart);
  6. the choice model (method 3), if the CEO wants it.

  Each rung must beat the one below (rule k).
- **Time box:** three build sessions. `vacated-live`: two (the tables and the walk-forward with the Saturday run's knowledge; then scoring, the ranges and the yardstick). `vacated-offseason`: one (the week-1 backtest, the gate and the live event runs).
- **The backlog it carries:** I49 (the pair part), I126 (H111 retried where the group was left empty), I55 (the first game back) as a check in `vacated-live`.
- **Technical calls (for veto; logged in [decision 0046](../../docs/decisions/0046-vacated-opportunity-exploration.md)):**
  - the groups and top k, and the roster's DL only;
  - the ridge's penalty grid extended below 1 (the exploration chose the grid's edge), chosen by cross-validation within the training seasons;
  - the expected absence as (1 − chance he plays) × his share;
  - the offseason backtest on the week-1 roster only;
  - forecasts clipped to [0, 1].
