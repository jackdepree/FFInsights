# Availability: who plays, and for how many games

> **Status:** kickoff, 2026-11-23 (the CEO: "Ok, let's start the availability expert"). The CEO's hunches H93 to H98 are in, all with the CEO's odds (2026-11-23: "H93; 60%. H96; 70%. h97; 70%. H98; 50%. Please proceed with the exploration and any more questions that you have, thank you"). **The exploration is done: GO** ([EXPLORATION.md](EXPLORATION.md)). By the pass rules: H93 held, H94 held, H95 held in part, H96 failed, H97 held, H98 held (small); the CEO closes them. The brief is drafted after the CEO's direction. Nothing has been tested for this project yet.

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
