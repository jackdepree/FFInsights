# Availability: who plays, and for how many games

> **Status:** kickoff, 2026-11-23 (the CEO: "Ok, let's start the availability expert"). The CEO's hunches H93 to H98 are in, all with the CEO's odds (2026-11-23: "H93; 60%. H96; 70%. h97; 70%. H98; 50%. Please proceed with the exploration and any more questions that you have, thank you"). **The exploration is done: GO** ([EXPLORATION.md](EXPLORATION.md)). The CEO closed H93, H94, H95, H97 and H98 as the pass rules read (2026-11-23), and H96 as failed after the follow-up test against H97 (2026-11-24: "Failed"). The CEO's direction after the exploration is below, with the CEO's answers on the line between availability and participation (2026-11-24). **The brief is drafted (2026-11-24) for the CEO to agree.**

## Why now

- **The yardstick batch (I60, 2026-11-23):** over the rest of a season, knowing the share of games a player goes on to play would remove 70.2% of the crude forecast's error for passing yards, 26.8% for rushing, 23.8% for receiving and 4.2% for team yards. A crude games-played forecast (games so far, shrunk to last season's rate, plus this week's report) gets 1.3% for receivers and nothing for QBs and backs. It's the biggest gap between hindsight and forecast we've measured.
- **Teams (I115):** a starters' games-played forecast adds +2.84% to team yards over the rest of the season beside Elo. That's an Elo repair, not a stand-alone signal yet.
- **The line's late news (I114's spot-check):** the kickoff line adds about 5.5% to team yards next game beyond all our team inputs, and most of its lead over the opener sits in games where the line moved 2.5+ points: injuries, weather, sharp money.

## The usual way

Teams' medical and sports-science staff forecast availability from workload tracking (GPS load, the acute-to-chronic workload ratio), screening and medical history, and none of that is public. Public analysts and fantasy and betting desks split it in two: **will he get hurt** (a rate per game or per snap by position and age, with past injuries as a flag), and **once he's hurt, how long is he out** (recovery times by injury type, read through the injury report, practice participation and beat reporters). The first part is usually found to be close to random beyond position, age and volume, so most of the skill sits in the second. For teams, the standard public tally is Football Outsiders' adjusted games lost, which weights starters more than backups.

## Two analogies

- **Insurance: frequency and severity.** An insurer prices a policy as how often claims come (frequency) times how big each one is (severity), and models the two apart because different things drive each. Its credibility theory then says how far to trust one driver's own record against the class average. That's the "injury-prone" question in numbers: how many past injuries before a player's own history outweighs his position and age?
- **Reliability engineering: the bathtub curve and repairs.** Machines fail often when new, rarely in mid-life, and more as they wear out, and a part that was just repaired fails again more often soon after. For players, the curve maps to rookies, the prime and age, and the repair to re-injury in the weeks after a return (the hamstring that comes back).

## What we already have

- **Participation's `active`:** the chance of being active next game. AUC 0.932 and close to calibrated (participation#F12), but it overstates Out and Doubtful players about twofold, and Questionable players are its weakest (slope 0.70, F27). Its next-3 and rest-of-season shares have no spike for a window that collapses through injury or release, so their q10 is too high (F14), and most misses there are a few games lost, not the whole window (F24).
- **Free data:**
  - injury reports from 2009, with Wednesday to Friday practice status and the body part (`report_primary_injury`, `practice_primary_injury`);
  - real game statuses from 2019, and the game-day inactive list (known an hour before kickoff, so never an input);
  - weekly rosters' status;
  - snap counts and depth charts;
  - participation's who-was-on-the-field, from 2016.
- **Not free:** workload tracking, medical detail, and most reporting. News is the weakest free source.

## The backlog that fits (W4's read)

- **I60** (graduated in the batch: the room is real, and the crude forecast of it is weak) and **I115** (inside Elo's next build).
- **I51,** a probable starting QB from the practice lines, and **I49,** swap pairs inheriting an absent player's snaps.
- **I9,** movers over-projected for snaps. Who absorbs a missing player's chances belongs to `vacated-opportunity`.
- **Fatigue (bucket F): I29, I30, I50.** The registry's `injury-fatigue` idea covers workload, risk tiers and recovery, so it overlaps this project.

## The CEO's direction and hunches (word for word, before any test)

The CEO's message, 2026-11-23, in full:

> "I would definitely want to try to replicate football outsider's idea. I would also want to predict the dichotomy of chance of injury and conditional of the chance of injury and past injuries how long would they be out for? If we assumed a player is going to get hurt on their next play, based on their past injuries and recovery rate and age, what would we expect their missed time to become? I would definitely want to measure how prone an injury is, I would be 30% confident that some injuries repeat and other injuries are unlikely to repeat or random. I would also be 50% confident that different roles of players are more or less likely to get hurt; maybe speedsters are more likely to get an injury rather than players who have low yardage variance per play. I would also expect that weighted snaps will predict injuries better than simple counts of snaps played. We can create a propensity model to estimate the chance of an injury for each position type (offensive line or wide receiver) on a given play; maybe plays that include more than one tackler or a tackle behind line is scrimmage or a play that ran for more than 5 seconds are more likely on average to observe an injury. Then if we cumulatively sum the risky play for each player we can measure the fatigue for each player and we can even include a recency bias to explain high and recent rates of injury-prone plays. The overlap with injury and fatigue idea can be overwritten by this availability expert. The touchdown expert can wait for my go-ahead later tonight."

**Direction (not bets):**
- **Replicate Football Outsiders' adjusted games lost** ("I would definitely want to try to replicate football outsider's idea."). It's a deliverable: a free rebuild of the team tally, from the injury reports, snap counts and depth charts.
- **Scope:** this expert replaces the registry's `injury-fatigue` idea ("The overlap with injury and fatigue idea can be overwritten by this availability expert."). Its fatigue leads come here: I29, I30 and I50, and pace's F10 to F12.
- **td-expert's build waits** for the CEO's go-ahead ("The touchdown expert can wait for my go-ahead later tonight.").

**The hunches** (also in `HUNCHES.md`):

| # | Hunch | The CEO's odds | Claude's odds |
|---|---|---|---|
| H93 | Two parts, the chance of an injury and, given one, how long he's out; if he were hurt on his next play, his past injuries, his recovery rate and his age say how much time he'd miss: "I would also want to predict the dichotomy of chance of injury and conditional of the chance of injury and past injuries how long would they be out for? If we assumed a player is going to get hurt on their next play, based on their past injuries and recovery rate and age, what would we expect their missed time to become?" | 60% (given 2026-11-23, before any test) | For the claim as worded (given an injury, past injuries, recovery rate and age forecast games missed better than his position's average): 70%. Side bet: they add anything clear beyond the injury's body part and his first report status, 35%; if so, under 5% of the squared error in games missed |
| H94 | Proneness depends on the injury: some repeat, others don't or are random: "I would definitely want to measure how prone an injury is, I would be 30% confident that some injuries repeat and other injuries are unlikely to repeat or random." | 30% (given with the hunch, 2026-11-23); no size given | For the claim as worded (the same body part's repeat rate is well above the base rate for some injuries and near it for others): 70%. Side bet: a hamstring's repeat rate in the same season is 2x the base rate or more, 40%. The report's body-part field may be too coarse to see it |
| H95 | Within a position, roles differ in injury risk; speedsters get hurt more than players whose yards per play vary little: "I would also be 50% confident that different roles of players are more or less likely to get hurt; maybe speedsters are more likely to get an injury rather than players who have low yardage variance per play." | 50% (given with the hunch, 2026-11-23); no size given | For the claim as worded: 45%. Side bets, beside position, snaps and touches (the obvious-input check): roles differ within a position, 60%; high variance in yards per play means more injuries, 30% |
| H96 | Snaps weighted by each play's injury risk forecast injuries better than plain snap counts: "I would also expect that weighted snaps will predict injuries better than simple counts of snaps played." | 70% (given 2026-11-23, before any test) | For the claim as worded (weighted snaps beat counts on held-out injuries, beyond the clear interval): 45%; if so, small, under 1% of the log loss |
| H97 | A propensity model gives each position group's chance of an injury on each play; plays with more than one tackler, a tackle behind the line, or over 5 seconds long have higher rates: "We can create a propensity model to estimate the chance of an injury for each position type (offensive line or wide receiver) on a given play; maybe plays that include more than one tackler or a tackle behind line is scrimmage or a play that ran for more than 5 seconds are more likely on average to observe an injury." | 70% (given 2026-11-23, before any test) | For the claim as worded (at least two of the three features raise the play's injury rate, beside position and play type): 75%; all three, 45%. The play-by-play names in-game injuries ("was injured during the play", about 800 in 2024; pace exploration). A play's length isn't in the free data, so it needs a proxy |
| H98 | Each player's running total of risky plays, weighted toward recent ones, measures his fatigue and explains high recent injury rates: "Then if we cumulatively sum the risky play for each player we can measure the fatigue for each player and we can even include a recency bias to explain high and recent rates of injury-prone plays." | 50% (given 2026-11-23, before any test) | For the claim as worded (the recency-weighted total forecasts his next injury beyond position, snaps and plain season totals): 30%; if so, under 1% of the log loss. Fatigue failed on performance before (H24, H25) and held on substitution (H34); I29 is the lead |

## The CEO's direction after the exploration (word for word)

The CEO's message, 2026-11-23, in full:

> "Can you please explain or test the possible incongruity between the results of h96 and h97? I think availability should forecast games played for any reason and even the estimate or chance of decreased participation or snap share. I think healthy scratches and benches are participation expert domain, respectively. I think adjusted games lost should be weighted by snaps played. I will close all hunches except for h96, for now."

**What it decides:**
- **The main output is games played, for any reason.** Availability forecasts whether each player plays, not only whether he's injured ("I think availability should forecast games played for any reason").
- **A second output: reduced participation.** The chance he plays with a reduced snap share, and by how much ("and even the estimate or chance of decreased participation or snap share").
- **Healthy scratches and benchings belong to `participation`, not here** ("I think healthy scratches and benches are participation expert domain, respectively"). The line between the two experts is drafted in the brief, for the CEO to confirm.
- **Adjusted games lost is weighted by snaps played** ("I think adjusted games lost should be weighted by snaps played"), not FO's equal weights per starter.
- **Hunches:** H93, H94, H95, H97 and H98 closed as the pass rules read; H96 stays open ("I will close all hunches except for h96, for now"), with the follow-up test of H96 against H97 in [EXPLORATION.md](EXPLORATION.md). After the follow-up, the CEO closed H96 as failed (2026-11-24: "Failed").

## The CEO's answers on the line between experts (word for word)

The CEO, 2026-11-24: "1; yes, availability. 2; yes, only what was known before the game to weight by their share."

- **Playing hurt belongs to availability** ("1; yes, availability"). When a player plays with fewer snaps because he's hurt, availability forecasts the drop. Participation keeps his healthy share.
- **Adjusted games lost weights each game lost by the player's snap share, using only what was known before that game** ("2; yes, only what was known before the game to weight by their share").

---

# The brief (draft, 2026-11-24, for the CEO to agree)

**Status:** draft · **Layer:** expert (1) · **Cadence:** in_season (the Saturday run, 12:00 Eastern, like participation)

## Methods

Three ways to build it. The ladder (rule k) runs them in order, and each rung must beat the one below. **The CEO chose all three** (2026-11-24: "All three").

| | Method | What it assumes | Cost |
|---|---|---|---|
| 1 | **The usual way: two separate models.** A classifier for "plays next game" and, for players who are out, a model of games missed. Each horizon (next game, next 3, rest of season) is fitted on its own | Each horizon can be learned apart, and the pieces add up | Cheap. Participation's `active` and the exploration's H93 model are already this |
| 2 | **Structured: a weekly health-state chain.** Each player is in one state each week: healthy, listed (Questionable, Doubtful), Out, or on a reserve list. The model learns the chance of each move from his report, history, proneness, age and exposure, then rolls forward week by week. Next-3 and rest-of-season ranges come out of the same chain | A week's move depends on this week's state and his traits, not on the whole path (with "weeks in this state" added to soften that) | A session. It gives the spike at 0 games and the "a few games lost" misses (participation#F14, F24) by construction |
| 3 | **Exploratory: a hidden health state.** The report, practice status and snap share are noisy readings of a health state nobody sees. A hidden Markov model infers the state, so "listed Questionable but full practice Friday" and "played 60% of his usual snaps" are read as evidence about the same hidden health | The readings are conditionally independent given the state; three or four states are enough | Expensive: identifiability, and fitting on about 2 million player-weeks. It's the only method that gives playing hurt and missing games from one model |

## The noise ceiling (from the exploration)

- **Next game:** players' injury rates differ beyond position (a fragile player at +1 SD gets hurt about 1.7x as often). Per game, it's barely forecastable: 1–2% of the log loss.
- **How long he's out:** the next report removes 62% of the error, and history adds 1.6%.
- **Rest of season:** regular skill players miss about 20% of their team's games. Three-quarters of those are new absences, and a fifth of all absences start with a named in-game injury.
- **The room on the yardstick (I60):** 24–70% of a rest-of-season forecast's error is availability. A crude games-played forecast gets about 1%.

## The question

Will each player be available next game, and over the next three games and the rest of the season? When he plays hurt, how much of his usual role does he keep? And how much is each team losing to absences?

## Why it matters

- **It's the biggest measured gap between hindsight and forecast** in PCF: 24–70% of a rest-of-season forecast's error is who plays, and we capture about 1% of it.
- **It repairs what participation gets wrong:** Out and Doubtful players overstated about twofold (F27), and rest-of-season ranges with no spike at 0 (F14).
- **It feeds teams:** a starters' availability forecast adds +2.84% to Elo's rest-of-season team yards (I115).
- **Users notice it** in rest-of-season and dynasty values, weekly start/sit on Questionable players, and futures.

## Terms

- **Standard terms used:** snap share, injury report status, log loss, credibility ([`docs/GLOSSARY.md`](../../docs/GLOSSARY.md)).
- **New terms:**
  - **Health absence:** a game he doesn't play while he's on the injury report (any status) or on a reserve list for injury, illness or NFI. Absences while he's healthy and on the active roster (healthy scratches, benchings) are participation's.
  - **Games played (any reason):** what availability reports at the top. It's the health part from this expert, times participation's chance of playing when healthy. Availability owns the health part; the composite is scored on the yardstick.
  - **Playing hurt:** a game he plays while listed. His **kept share** is his snap share that game over participation's healthy-share forecast.
  - **Proneness:** his in-game injuries per scrimmage snap over his position's rate, shrunk toward 1 by credibility (half weight at about 2 expected injuries), with body-part repeat factors for calf, back, foot, groin, hip, hamstring and knee (H94).
  - **Snap-weighted adjusted games lost:** per team, the sum over players of games lost to health absence, each weighted by his snap share on his side in his earlier games that season (known before the game). It's the CEO's version of Football Outsiders' adjusted games lost.
  - **Exposure:** snaps, touches and (for defenders) tackles made, entered as logs, plus a recency-weighted sum of snaps (the H96 follow-up).

## Builds on

| Project | What we use | Why |
|---|---|---|
| `participation` | `active`, the next-game share (trees_week) and the horizons' shares, from saved histories; F12, F14, F24, F27 | The incumbent to beat, the healthy share that kept share is read against, and the misses to fix |
| `timeline` | known-at timestamps | The report's known-at rule (`date_modified`, else noon on the final report's day) |
| `crude-forecaster` | the yardstick, and I60's crude games-played forecast | The downstream score and the baseline to beat |
| `pace` | F10–F12 and I29's long-drive fatigue | The fatigue leads this expert takes over from `injury-fatigue` |
| `elo` | I115 | Where the team output goes first |

**Already tried:**
- Fatigue on performance failed (H24, H25); fatigue on substitution held (H34).
- **H96 failed:** weighting snaps by the play's risk is a count in disguise (correlation 0.997), so H97's play model is a description, not a workload weight.
- H98's recency is workload, not risk.
- A player's career mix of risky plays adds nothing (the follow-up, F).

## Assumptions

1. **The report is known by the Saturday run.** We use the final report and practice through Friday. The game-day inactive list is never an input.
2. **Health absence can be told apart from scratches.** "On the report or a reserve list" marks health. A player released or traded lands "off every roster", which is participation's (flagged and counted in the build).
3. **In-game injury names in the play-by-play are logged unevenly** (660–960 a season, rising). They feed proneness as a rate per snap, read within season.
4. **Games missed means no snap.** A benching right after an injury counts as health time missed (the case against).
5. **Body parts exist only for listed players,** so injured-reserve stints are the least described.
6. **Participation's forecasts already read the report.** The overlap is handled by scoring availability's outputs beside participation's, never alone.

## Goals

- Forecast health availability at three horizons, with honest ranges, a spike at 0 and calibrated Questionable players.
- Forecast kept share when playing hurt.
- Build proneness and the snap-weighted adjusted games lost as standing measures, with their consistency tests.
- Hand the team output to Elo (I115) and the player outputs to the yardstick.

## Tests

- **Success looks like:**
  1. **Next game:** the chance he plays beats participation's `active` on held-out log loss (2017–2024 walk-forward, the interval above 0). The Questionable calibration slope comes out between 0.85 and 1.15 (participation's is 0.70), and Out or Doubtful is no longer overstated twofold.
  2. **Rest of season:** games played beats I60's crude forecast, with q10–q90 coverage of 75–85% and the q10 problem fixed (F14).
  3. **Playing hurt:** kept share beats participation's share alone on the squared error of listed players who play.
  4. **The yardstick:** beside I60's crude forecast and participation, it adds clearly on at least one rest-of-season board (receiving, rushing or passing yards) and beats its 19 shuffled copies.
  5. **Team:** the snap-weighted adjusted games lost repeats (season r with its interval) and tracks the change in net EPA. Its forecast adds beside Elo on the team rest-of-season board (I115's test).
- **Failure looks like:** it doesn't beat `active` or I60's crude forecast. Then availability ships as descriptions only (proneness, the severity table, snap-weighted adjusted games lost) and participation stays the forecast.
- **No-noise target (the CEO approves):** games played next game and over the rest of the season, against participation's `active` and I60's crude forecast. Downstream: the yardstick's rest-of-season boards.
- **Seasons:** training from 2013 (reports from 2009; in-game injury names from 2016 for proneness), scored 2017–2024, vault 2025.

## Inputs and outputs

- **Inputs** (known-at in brackets):
  - the injury report and practice status through Friday [`date_modified`, else noon on the final report's day];
  - weekly roster status and reserve lists [that week's file];
  - snaps, touches and tackles made from earlier games [after each game];
  - in-game injuries named in the play-by-play [after each game];
  - age;
  - participation's saved histories [the Saturday run].
- **Outputs** (player-game, Saturday run):
  - chance of a health absence next game, and expected games of health absence over the next 3 and the rest of the season, with q10, q50 and q90;
  - games played (any reason), composed with participation;
  - kept share when listed, with an interval;
  - proneness, with its credibility;
  - per team: snap-weighted adjusted games lost to date and its forecast for the next game and the rest of the season.

## How it will be used

- In rest-of-season and dynasty values, and weekly start/sit for listed players.
- In the yardstick and the crude forecaster's rest-of-season boards.
- In Elo's rest-of-season regression (I115), and later in team strength and futures.

## Plan

- **Ladder (the CEO, 2026-11-24: "All three"):** baseline (the position's rates plus a status-by-body-part table) → logistic and lasso (method 1, with proneness, log exposure and recency) → the health-state chain (method 2) → trees on the chain's moves → the hidden health state (method 3). All three methods are built and scored, whatever the rung below does; the champion is the one that wins on the tests, and the ladder's rule (rule k) still decides which ships.
- **Time box:** four build sessions (three before the CEO chose all three methods): the tables and baseline with method 1; the chain; the hidden health state; then scoring, the yardstick and the team output.
- **The backlog it carries:** I29, I30, I50 (fatigue) and I116 (proneness on the yardstick). I49 and I51 stay with participation and `vacated-opportunity`.
- **Technical calls (for veto):**
  - week 1 and a player's first game of a season weight adjusted games lost by last season's snap share (known before the game); with neither, his depth-chart rank's average share at his position that week;
  - a release or trade is not a health absence;
  - exposure enters as logs (the H96 follow-up's G).
