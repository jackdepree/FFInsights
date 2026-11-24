# Roles and archetypes: what each player is asked to do

> **Status:** kickoff, 2026-11-24 (the CEO: "i would like to start roles and archetypes, please"). The CEO's hunches H99 to H108 are in, all with the CEO's odds. **The exploration is done: GO** ([EXPLORATION.md](EXPLORATION.md), three looks), and the CEO closed H99 to H108 as their pass rules read (2026-11-24: "Yes h99-h108 can be closed"). The CEO's direction after each look is below, word for word. **The brief proper is drafted at the end (2026-11-24) and waits for the CEO's agreement,** with its no-noise target.

## Why now

- **Much of what repeats and travels is role** (retro 3, P11). Target share and target depth belong to the receiver (F1). A running back's carry share belongs mostly to his backfield (F2). An outside linebacker's rusher-or-dropper role is his own, and an inside linebacker's is the scheme's (F18). Next season's sacks come from the role, not from pressures within it (F49).
- **Other projects are waiting for a role table:**
  - I113 (skill-over-expected's 14 measures read within role);
  - I79 (the per-position map of what to use and ignore);
  - `vacated-opportunity` (who's like the missing player);
  - availability (deep-target receivers get hurt more, H95).
- **Movers:** a mover's new slot adds more to his first 4 games than his own old share does (F57). A role says what slot he's walking into.

## The usual way

Charting services (PFF, FTN, Sports Info Solutions) label every snap by hand: where each player lined up (wide, slot, inline, backfield, box, edge) and what he did (route, block, rush, coverage). Analysts then sum each player-season into a usage vector (alignment shares, route mix, target depth, carries by down) and cluster it, usually k-means or a Gaussian mixture. That gives archetypes such as the slot receiver, the X receiver, the satellite back, the move tight end, the box safety and the slot corner. The labels are used for comparables ("players like him"), for matchups, and as inputs in projection models, often with a similarity score to find a player's nearest past seasons.

## Two analogies

- **Ecology: niches and guilds.** Ecologists define a species by what it does (what it eats, where, when), not by what it looks like. Species that do the same job form a guild. When one is removed, the closest member of its guild takes over its niche. A role is a player's niche, and an archetype a guild. The analogy suggests two things to look at:
  - Roles are continuous, and guilds are a convenient cut. How many archetypes are real, and do the cuts repeat?
  - The empty-niche question is `vacated-opportunity`'s: who fills it is whoever's most alike.
- **Basketball's positionless era.** NBA analysts found the five listed positions hid a dozen or so playing styles. Topological data analysis on box-score profiles found 13, and lineup analysis now uses style, not position. In football the listed position is "WR", but a slot receiver and an X receiver are asked to do different jobs. The analogy suggests asking whether style beats listed position as the bin every other measure is read within.

## What we already have

- **Findings:**
  - Target share and depth travel with the player (F1). Carry share is mostly the backfield's (F2).
  - Outside linebackers split into rushers and droppers (F18, 82% of seasons outside the middle third). Inside linebackers' role is the scheme's.
  - Schemes-v2 split what moves with a play caller (scheme) from what moves with a player (role), and found throw depth is a QB and roster trait (R3).
  - The passing-down role is paid in contracts (I43, snap-leverage F10).
- **Free data:**
  - **In season:**
    - play-by-play: targets, air yards, pass location, run gap and direction, carries by down and distance;
    - weekly snap counts (offense, defense, special teams);
    - depth-chart labels on every play (the cleaning port's `slot_labels`, from 2016);
    - Next Gen Stats weekly: target depth, separation, cushion, share of team air yards, rushing against 8+ in the box;
    - PFR advanced stats;
    - FTN charting from 2022 (motion, play action, blitzers; about 1–2 weeks behind).
  - **After the season only** (retrospective; never a live input): participation from 2016. It says who was on the field, the offense and defense personnel, the targeted receiver's route (one route a play), coverage and pressure.
- **Not free:** per-snap alignment for every player (slot, wide, inline) and every receiver's route. The free route is only the targeted receiver's.

## The backlog that fits

- **I113,** a role table for every player-season (slot, wide or inline share and depth for receivers; a back's share of his backfield). It's open, for skill-over-expected's build (group E). It's this project's first deliverable, or a shared one.
- **I57,** forecasting a receiver's route mix from his past routes. It repeats as a role; the routes arrive only after the season.
- **I79,** the per-position map of what to use and what to ignore.
- **I23,** receiver depth fit: deep threats moving to short-passing offenses.
- **I9 and I49,** movers over-projected for snaps, and swap pairs inheriting an absent player's snaps (role-alike substitutes).
- **I91,** how much of the outside linebackers' sack forecast is only knowing who rushes.
- **Answered and reusable:** I53 and I84, which usage rates travel with a mover.

## The CEO's direction and hunches (word for word, before any test)

The CEO's message, 2026-11-24, in full:

> "So for this project, I would want it to be both traditional and I would love to make something like experimental. So I would love for this project to kind of branch out and use a latent space to describe each player. So when I think of roles and archetypes, obviously I think of like the traditional, oh, you're a wide receiver, you're, maybe your A dot, your average depth of target is really high, so you're catching balls all downfield, or maybe you're a tight end and you're number one tight end and you get a lot of catches. And maybe you have this other tight end on the team that is tight end number 2. They play less and they only play on running plays, so clearly they're a blocker, So I think we can learn a lot from roles and positions based on the context where they are not on the field just as much as when they are on the field. I would say like 50, I would give like 60% odds that that we can find like a meaningful amount of players, or that at least like error prediction in terms of consistency and autocorrelation improves when we take into account the plays that a player plays on and the snaps that they are not on that play. So observed and like disobserved or anti-observed patterns will inform us on their role. And obviously it's within teams, so you can basically say like it's within the same context, but we can also still account for pass play expected rate or pace. I think that's really important to account for that. And so basically, to me, the inputs of this expert are going to be a lot of measurables. So it's like, how tall are they? How much do they weigh? Do we have a listed like 40-yard dash time? And then it's also going to be their other random characteristics, like do they play mostly on running plays? Do they play mostly on passing plays? Do they tend to catch the ball really far downfield? Do they tend to get tackles? Like if they're a defensive player, do they get tackles with someone, or are they usually a solo tackler? Things like that I'm trying to look for. I don't know what exactly the information we have. Like, do we have like where they lined up before the play? We also want to look at like the personnel that they're in. Like, do they only play this personnel, or maybe they only play 2 personnel, or maybe they just play any personnel. It doesn't even matter. They just play with everyone who's on the field. And basically, I don't think this is going to be the only output. I think we can have different kinds of outputs. Like we can have clusters. We can do almost like a cluster analysis and kind of say, okay, these people fit as like speedsters, or these people fit as like the satellite back or the slot receiver. I think those standard naming conventions are pretty smart. I think those work well. But I also still want to make like a latent space measurement, like almost convert their usage and their roles and their archetype into this latent space that describes some meaningful features. So maybe we can look at what are the most predictive or most consistent features, and then we can use maybe 4 or 5 or 6 of those features and say, okay, based on these features, this is their mapping. They're very high percentile in these 2 features, but they're very low percentile in these other features. Like maybe one of the features is the pace, and maybe another feature is personnel, and maybe another feature is I don't even know, but it's almost like positionless. It's like getting away from all the other descriptors and categories and putting it into this latent space. And now we can use this latent space that I would think the computers can use pretty well, because it's hopefully capturing some sort of consistent information. It's almost like a PCA. I mean, PCA obviously isn't exactly the correct. Well, maybe PCA would be good, because you're condensing the information to components that are supposed to be independent from each other. So we could try PCA, see if those are consistent from week to week, and if those predict roles. And I think there's going to be some overlap with some testing, because I think like you already mentioned it, one really good way of testing this would be like, okay, if there's a vacated position, or if someone moves out of a play, does someone else with the same kind of role step in, or is there a substitute, someone who has a similar kind of role? Do teams kind of switch out roles, or do teams not switch out roles? That would be a good question to look at. So that's my thoughts so far. Well, I think because of the timing question and because we need participation data, I think what we can do is we can say, like, okay, we have prior season participation data, and just based on that, what do we know? And then we can just label everyone just like that. And then for any future downstream expert, you can just use the most recent label or whatever. And then within season, I don't really know. Within season, we can try and make a metric or some sort of estimate or algorithm that says like, okay, before the season, we think they are this kind of role. We think they're a certain kind of role. And then without using participation data, in the next season, can we accurately predict if their role is the same or changed? And that's all we do. We don't have to figure out what their new role is. We just have to figure out, like, did their role change? So it would be, the inputs would basically be prior charting data, prior guess on their role, prior usage, prior pace, prior efficiency, prior, basically everything prior. And then also the next season things that we can get from each week. So like overall usage, we can get, I think we can get pace, we can get efficiency, we can get all those things, and we can say like, okay, if they change too much, do they have a different role? And if so, just flag it. It can be a flag, like, okay, or not even a flag, it can just be a probability. Like, what's the chance that they have the same role? And I think that would be a good within season feature or output."

**Direction (not bets):**
- **Both traditional and experimental** ("I would want it to be both traditional and I would love to make something like experimental"):
  - clusters with the standard names: speedster, satellite back, slot receiver ("I think those standard naming conventions are pretty smart");
  - a positionless latent space of 4 to 6 features, each player read by his percentile on each ("They're very high percentile in these 2 features, but they're very low percentile in these other features").
- **Inputs the CEO wants:**
  - measurables (height, weight, the 40);
  - the run and pass mix of his snaps;
  - target depth;
  - solo or assisted tackles;
  - where he lined up;
  - the personnel he plays in.
  - The team's context, pass rate over expected and pace, is held fixed.
- **Timing** ("because we need participation data"):
  - **Between seasons:** label everyone from the prior season's participation, and downstream experts use the latest label ("we can just label everyone just like that. And then for any future downstream expert, you can just use the most recent label").
  - **In season:** only the chance that his role is the same as last season's, from everything prior plus this season's weekly usage, pace and efficiency, without participation ("We don't have to figure out what their new role is. We just have to figure out, like, did their role change?").
  - The charter's rule m makes these two experts (proposed: `roles-retro` and `roles-live`, one project folder), registered when the brief is agreed.

**What the free data has, for the CEO's question** ("I don't know what exactly the information we have"):
- **Where he lined up:** not per player. We have:
  - the depth chart's position label (slot receiver where a team lists one);
  - the formation and the box count (after the season);
  - Next Gen Stats' cushion for receivers, a weekly stand-in.
- **Personnel:** yes, per play (participation), after the season only.
- **Measurables:**
  - height and weight for nearly everyone (`load_players`);
  - combine results from 2000 (40, vertical, broad, cone, shuttle, bench), missing for players who skipped drills.
- **Run or pass mix, target depth, solo or assisted tackles:** yes, from the play-by-play, in season.
- **The plays he's off:** who was on the field each play is participation (after the season). In season we have only each game's snap counts.

**The hunches** (also in `HUNCHES.md`):

| # | Hunch | The CEO's odds | Claude's odds |
|---|---|---|---|
| H99 | The plays a player is *not* on say as much about his role as the plays he is on (a second tight end who's on the field only for runs is a blocker), within his team's context and with its pass rate over expected and pace held fixed; taking both into account makes role measures more consistent (season to season, autocorrelation): "So I think we can learn a lot from roles and positions based on the context where they are not on the field just as much as when they are on the field. I would say like 50, I would give like 60% odds that that we can find like a meaningful amount of players, or that at least like error prediction in terms of consistency and autocorrelation improves when we take into account the plays that a player plays on and the snaps that they are not on that play. So observed and like disobserved or anti-observed patterns will inform us on their role. And obviously it's within teams, so you can basically say like it's within the same context, but we can also still account for pass play expected rate or pace. I think that's really important to account for that." | 60% (given with the hunch, 2026-11-24: "I would say like 50, I would give like 60% odds"); no size given | For the claim as worded (role measures built from the plays he's on *and* off, by play type and within team, repeat season to season more than the same measures built from his own snaps only): 65%. Side bets: the gain is for part-time players (second tight ends, second backs, sub-package defenders), season r up 0.05 or more, 55%; for every-down players (on 90%+ of snaps) nothing, 85%. Who's on the field each play comes from participation, so this is retrospective (after the season) |
| H100 | A latent space of a few features (4 to 6), positionless, made from usage, context and measurables (PCA, or something like it), describes each player by his percentile on each; the features are consistent week to week and predict roles: "But I also still want to make like a latent space measurement, like almost convert their usage and their roles and their archetype into this latent space that describes some meaningful features. So maybe we can look at what are the most predictive or most consistent features, and then we can use maybe 4 or 5 or 6 of those features and say, okay, based on these features, this is their mapping. They're very high percentile in these 2 features, but they're very low percentile in these other features. Like maybe one of the features is the pace, and maybe another feature is personnel, and maybe another feature is I don't even know, but it's almost like positionless. It's like getting away from all the other descriptors and categories and putting it into this latent space. And now we can use this latent space that I would think the computers can use pretty well, because it's hopefully capturing some sort of consistent information. It's almost like a PCA. I mean, PCA obviously isn't exactly the correct. Well, maybe PCA would be good, because you're condensing the information to components that are supposed to be independent from each other. So we could try PCA, see if those are consistent from week to week, and if those predict roles." | 50% (given 2026-11-24, before any test) | For the claim as worded (within a position, the first 4 to 6 components repeat week to week and recover the standard roles): 70%. Side bets: the top components repeat season to season at r 0.5+, 75%; one season's components match another's (stable loadings), 60%; as inputs downstream they beat a hand-built role table of the same size, 30% (the role table is the simpler side and wins a tie). Fixed measurables (height, weight, a 40 time) repeat by construction, so the consistency test is run with and without them |
| H101 | When a player leaves a play or the lineup, the one who replaces him has the same kind of role (a like-for-like substitute), or teams don't swap like for like; the test of the latent space is who steps in: "one really good way of testing this would be like, okay, if there's a vacated position, or if someone moves out of a play, does someone else with the same kind of role step in, or is there a substitute, someone who has a similar kind of role? Do teams kind of switch out roles, or do teams not switch out roles? That would be a good question to look at." | 40% (given 2026-11-24, before any test; read as like-for-like) | For like-for-like (the player who steps in is closer in role to the one who left than a random teammate at his position): 85%. Side bets: closer than the depth chart's next man would be, 45%; like-for-like holds more for tight ends and backs than for receivers, 55%. Joins I49 (swap pairs) and `vacated-opportunity` |
| H102 | In season, without participation, a player's chance of keeping last season's role can be estimated from his prior role, prior usage, pace and efficiency, and this season's weekly usage, pace and efficiency; the output is a chance, not a new label: "Within season, we can try and make a metric or some sort of estimate or algorithm that says like, okay, before the season, we think they are this kind of role. We think they're a certain kind of role. And then without using participation data, in the next season, can we accurately predict if their role is the same or changed? And that's all we do. We don't have to figure out what their new role is. We just have to figure out, like, did their role change? So it would be, the inputs would basically be prior charting data, prior guess on their role, prior usage, prior pace, prior efficiency, prior, basically everything prior. And then also the next season things that we can get from each week. So like overall usage, we can get, I think we can get pace, we can get efficiency, we can get all those things, and we can say like, okay, if they change too much, do they have a different role? And if so, just flag it. It can be a flag, like, okay, or not even a flag, it can just be a probability. Like, what's the chance that they have the same role? And I think that would be a good within season feature or output." | 60% (given 2026-11-24, before any test) | For the claim as worded (the chance is calibrated and beats each position's base rate on held-out seasons): 70%; already by week 4, 50%. The noise ceiling has to come first here: some "role changes" are a label flipping on noise, measured by how often labels differ between two halves of one season |
| H103 | Some roles gravitate to the schemes that use them well, and pairing roles with schemes shows combinations that work and ones that don't, to a predictive degree, even if only retroactively: "So I'd be very curious if there's any kind of correlation that we can see, like, okay, some roles and archetypes definitely gravitate towards those this kind of schemes that use them well. It would be very interesting if we could pair up roles and schemes and map out and say these combinations work and these combinations do not work, or are maybe more effective and less effective to like a predictive degree, like a significant amount. We can retroactively say like, hey, these are different. I would say there's a 75% chance that we will find that to be the case." | 75% (given with the hunch, 2026-11-24); no size given | For the claim as worded (role-by-scheme combinations change efficiency by a significant amount, on held-out rows): 30%. Side bets: roles and schemes are correlated (some roles cluster on some schemes), 80%; at least one combination differs clearly in-sample (retroactively), 50%. H12 (player-scheme fit) was unclear, leaning failed |
| H104 | Each head coach's scheme seeks certain roles: when a team loses a starter (its WR1), the player it brings in fits the role that works in its scheme or the role of the player who left, and knowing that reduces the error: "I would also be interested to see if different teams, like every team has their own scheme, or at least every head coach has their own scheme, and that they try to get certain players in certain roles to come to their team. So if you have a team with obviously a measured scheme that we measured, and they have a vacancy at wide receiver number 1, maybe we can expect them to get a different wide receiver that fits the role that works best in that team, or a role that is the same role or archetype as the wide receiver that just left. I think that'd be very interesting to see if that information reduces the loss or error, or increases the loss. I think that'd be very interesting to see. I would say that would be 30% chance for that." | 30% (given with the hunch, 2026-11-24); no size given | For the claim as worded (the departed player's role, or the scheme's role, reduces the error of forecasting the newcomer's role beyond his position's average): 55%. Side bet: newcomers are closer in role to the player who left than newcomers to other teams are, 60%. A newcomer's role is partly given to him by his new team, so this reads his role with the team; H105 reads his role before he arrived |
| H105 | Teams target players in free agency and trades by their roles: "I would be 30% confident for a team in free agency or trades to see if teams target certain players based off of their roles." | 30% (given with the hunch, 2026-11-24); no size given | For the claim as worded (a veteran mover's role *before* he joins is closer to the role his new team lost, or its scheme's usual role, than chance): 35% |
| H106 | An archetype does better or worse against an opposing defense's scheme (a loaded box, few blitzes, many in coverage, two high safeties may hurt speedsters); roles and schemes are behavioural patterns that only say who wins when read together, player and opponent: "I would also be mildly confident, probably a 30% chance that we could find this based off of the results of the schemes expert, but based on an archetype of maybe a wide receiver, we could estimate that they will perform less well against an opposing defense's scheme. So maybe like the opposing defense scheme is they like put a lot of people in the box, or maybe they don't blitz a lot, or maybe they have a lot of people in coverage, or they run two cover safeties, all the time, and maybe that hurts speedsters or something like that, and then I think that would be interesting. I would say probably 30% chance of that happening, but that would be cool if we could test it that way and see if we find anything interesting, because like the same thing that I always said with schemes, like to me, roles and archetypes and schemes are just behavioral patterns, but everyone's always trying their best. So a scheme or a behavior or a tendency doesn't tell you if they're good or not, or if they're going to perform well or not. The only thing that actually does tell you if they're going to do well is when you combine both player A and the opposition, and you look at both schemes conditionally, like in tandem. Then you can say, okay, with these two schemes opposing each other, like the defense will win or the offense has the advantage. And the same thing with schemes. That failed with schemes, but I still believe that to be somewhat true. And I would hope to see that in the roles and archetypes." | 30% (given with the hunch, 2026-11-24); no size given | For the claim as worded (archetype-by-defense-scheme interactions improve held-out efficiency forecasts): 15%. Side bet: at least one interaction is clear in-sample, 45%. Schemes' matchups failed before (H9 unclear, leaning failed; H13 failed); a player's role gives the matchup a sharper unit than a team's |

The CEO's second message, 2026-11-24, in full:

> "h100; 50%, h101; 40%, h102; 60%. I would also think that this expert is super closely related to the schemes expert. So I'd be very curious if there's any kind of correlation that we can see, like, okay, some roles and archetypes definitely gravitate towards those this kind of schemes that use them well. It would be very interesting if we could pair up roles and schemes and map out and say these combinations work and these combinations do not work, or are maybe more effective and less effective to like a predictive degree, like a significant amount. We can retroactively say like, hey, these are different. I would say there's a 75% chance that we will find that to be the case. I would also be interested to see if different teams, like every team has their own scheme, or at least every head coach has their own scheme, and that they try to get certain players in certain roles to come to their team. So if you have a team with obviously a measured scheme that we measured, and they have a vacancy at wide receiver number 1, maybe we can expect them to get a different wide receiver that fits the role that works best in that team, or a role that is the same role or archetype as the wide receiver that just left. I think that'd be very interesting to see if that information reduces the loss or error, or increases the loss. I think that'd be very interesting to see. I would say that would be 30% chance for that. I would be 30% confident for a team in free agency or trades to see if teams target certain players based off of their roles. I think the explanation should try all three methods. I don't see why we can't try a bunch. Basic, kind of on the same thing that I just said. I would also be mildly confident, probably a 30% chance that we could find this based off of the results of the schemes expert, but based on an archetype of maybe a wide receiver, we could estimate that they will perform less well against an opposing defense's scheme. So maybe like the opposing defense scheme is they like put a lot of people in the box, or maybe they don't blitz a lot, or maybe they have a lot of people in coverage, or they run two cover safeties, all the time, and maybe that hurts speedsters or something like that, and then I think that would be interesting. I would say probably 30% chance of that happening, but that would be cool if we could test it that way and see if we find anything interesting, because like the same thing that I always said with schemes, like to me, roles and archetypes and schemes are just behavioral patterns, but everyone's always trying their best. So a scheme or a behavior or a tendency doesn't tell you if they're good or not, or if they're going to perform well or not. The only thing that actually does tell you if they're going to do well is when you combine both player A and the opposition, and you look at both schemes conditionally, like in tandem. Then you can say, okay, with these two schemes opposing each other, like the defense will win or the offense has the advantage. And the same thing with schemes. That failed with schemes, but I still believe that to be somewhat true. And I would hope to see that in the roles and archetypes. So yeah, I would love to hear about all the methodology that you try with trying to create like a latent space, but also trying to have like very robust and traditional labels for players. So please proceed, thank you."

**Direction (not bets):**
- **The exploration tries all three methods** for the latent space ("I think the explanation should try all three methods. I don't see why we can't try a bunch"):
  - the hand-built role table with named clusters;
  - PCA and factor analysis;
  - the on- and off-field factorization.
- **Both kinds of output stay:** "trying to create like a latent space, but also trying to have like very robust and traditional labels for players".
- **"Please proceed":** the exploration runs, pre-registered in [EXPLORATION.md](EXPLORATION.md) before any number.

The CEO's third message, 2026-11-24, after the exploration's results, in full:

> "Yes it still does make sense, because it aligns with the "latent space" idea. Each play utilizes players differently in unique ways, a play still relies on roles and jobs that define a players role. Each play utilizes a support group and target group to accomplish an offensive or defensive stance and goal, so I assume we can place players into a latent space of responsibilities and possibly even attribute outcomes to different players based on their identity within the latent space. A latent space would simply be a better descriptor than simple position labels.yes roles retro can start with offense. Yes in season role changes can go to participation expert."

**Direction (not bets):**
- **The results make sense to the CEO** (teams give a newcomer his role after he arrives; the defense's roles barely repeat in this data), "because it aligns with the "latent space" idea".
- **`roles-retro` starts with offense** ("yes roles retro can start with offense"): WR, TE and RB first. The defense waits for data that sees a defender's job (alignment, coverage), or stays at its one or two components that repeat.
- **The in-season role-change chance goes to the participation expert** ("Yes in season role changes can go to participation expert"). H102 showed it is mostly the snap-share change, which participation already forecasts, so there's no `roles-live`; this project is retrospective only (rule m), and its labels reach in-season models as a prior from completed seasons.
- **The latent space is one of responsibilities:** each play has a *target group* (the players the play is designed to go through: the targeted receiver, the ball carrier, the pass rusher) and a *support group* (the blockers, the decoys, the coverage that holds); a player's place in the space is the mix of jobs he's given.

**What the free data can see of a responsibility** (assumptions first, before odds):
- **The target group, yes:** every target, carry, sack, hit and tackle names its player.
- **The support group, mostly not:** who was on the field (participation, after the season), but not his job on the play. Routes exist only for the targeted receiver before 2023 (all routes 2023–2024); blocking assignments, alignment and coverage assignments aren't free. A support job is read from *when* he's on the field (H99, M3) and from what he's never targeted for.
- **So the advantage** is that the target group is measured well and the support group is inferred; **the limitation** is that attributing a play's outcome to support players rests on that inference. **The simpler alternative** is credit by the box score (the target and the carrier) plus plain plus-minus for everyone else, which VOE already tried (a non-QB player's plus-minus is mostly the team's: it repeats at 0.08 for movers; FINDINGS.md's VOE row, F46–F48).

**The hunches from this message** (also in `HUNCHES.md`; the CEO's odds, 2026-11-24: "H107; 75%, h108; 50% please proceed with the exploration"):

| # | Hunch | The CEO's odds | Claude's odds |
|---|---|---|---|
| H107 | A latent space of responsibilities describes players better than position labels: "Each play utilizes players differently in unique ways, a play still relies on roles and jobs that define a players role. ... A latent space would simply be a better descriptor than simple position labels." | 75% (the CEO, 2026-11-24, before any test: "H107; 75%, h108; 50% please proceed with the exploration"); no size given | For the claim as worded (offense pooled across WR, TE and RB, positionless coordinates forecast next season's targets and carries per snap better than the three position labels, held out): 80%. Side bets: beyond the position label *and* last season's volume (the obvious input), the coordinates still add on the crude yardstick (receiving and rushing yards), 45%; they beat a hand-built role table of the same size, 30% (H100's side bet; the table is the simpler side) |
| H108 | A play's outcome can be attributed to the players on it by their identity in the latent space (their responsibility: target group or support group): "Each play utilizes a support group and target group to accomplish an offensive or defensive stance and goal, so I assume we can place players into a latent space of responsibilities and possibly even attribute outcomes to different players based on their identity within the latent space." | 50% (the CEO, 2026-11-24, before any test: "H107; 75%, h108; 50% please proceed with the exploration"); no size given | For the claim as worded (credit by responsibility repeats season to season for players who change teams more than plain plus-minus does, with a clear interval): 25%. Side bet: for the target group alone (credit to the targeted receiver and the ball carrier, weighted by his role), the credit repeats for movers at r 0.2+, 50%. VOE's non-QB plus-minus was mostly the team's (movers repeat 0.08; FINDINGS.md's VOE row), and the support group's jobs aren't seen in free data |

The CEO's fourth message, 2026-11-24, after the second look and Claude's options for widening the space, in full:

> "I think what you mocked up is great. I think we can still treat the latent space coordinates as a forecasting input so that we appropriately stress test the idea and we can always revert to a shared map approach later on. Yes h99-h108 can be closed. Yes please run the pooled defense check now"

**Direction (not bets):**
- **The expansion plan is agreed** ("I think what you mocked up is great"):
  - defense pooled across its positions next;
  - players under 200 snaps, shrunk toward their group, with rookies started from measurables and draft slot;
  - quarterbacks later, as their own space;
  - no offensive line (the free data can't place them);
  - no single space for all 22.
- **The coordinates are judged as a forecasting input,** not only as a shared map ("we can still treat the latent space coordinates as a forecasting input so that we appropriately stress test the idea and we can always revert to a shared map approach later on"). The brief's success tests score them downstream, against position labels and the role table, with the table winning ties.
- **H99 to H108 closed** as their pass rules read.
- **The pooled defense check runs now** (EXPLORATION.md, the third look).

## The CEO's fifth message, 2026-11-24 (word for word)

> "Yes please proceed and draft the brief, these are great findings! After the brief we can start another project"

---

*The brief proper starts here (drafted 2026-11-24, after three looks; **not yet agreed**).*

**Status:** draft (2026-11-24) · **Layer:** expert (layer 1) · **Cadence:** retrospective (rule m: the in-season role-change chance went to participation, the CEO, 2026-11-24)

## Methods

The ladder (rule k) runs them in order, and each rung must beat the one below.

| | Method | What it assumes | Cost |
|---|---|---|---|
| 1 | **The usual way, and the simpler side: a role table plus named roles.** Six hand-picked features per side, plus explicit rules that name roles from them (below) | A few features carry the role; named cuts are stable enough | Cheap. Version 1 is in the exploration (I113, H107's table) |
| 2 | **The CEO's latent space: one pooled PCA per side.** Offense: WR, TE and RB together. Defense: DL, OLB, ILB, CB and S together. 6 components each, no position label, no measurables | Roles lie along a few straight directions, and the stable ones are those that separate positions (the third look) | A session. The exploration's version passed on both sides |
| 3 | **Exploratory: a small nonlinear embedding.** An autoencoder, fit on the same features per side, with a 6-number middle layer | Roles bend: a receiving back and a move tight end may be close in a way no straight axis shows. It also catches H107's carries step, which the straight-line model missed | A session, plus seeds (its fitting noise must be measured). It must beat PCA clearly or PCA ships |

## The noise ceiling (from the exploration)

- **How much a role repeats:**
  - **Playing time** repeats most: snap share 0.90 within a season.
  - **When he's on the field:** team-adjusted own-snap shares 0.69–0.88; the red zone only 0.29.
  - **What he does:** targets per pass snap 0.69, target depth 0.52, rushes per pass snap 0.42, passes defensed only 0.12.
- **The pooled spaces:**
  - offense: 5 of 6 components at split-half 0.5+;
  - defense: 5 of 6, and 4 of 6 centred within position;
  - movers keep most of it (the defense's rusher-or-dropper axis repeats 0.80 for movers).
- **Label noise:** a 2-cluster mixture's label flips between a season's halves 14% of the time. Any named role must beat that.
- **Efficiency barely repeats** (EPA per target 0.11–0.12 within a season, per touch 0.29). So the role is the input, not a performance score.

## The question

What is each player asked to do? Described as coordinates in a positionless space (one for offense, one for defense) and as named roles, published after each season. Do those beat position labels as forecasting inputs?

## Why it matters

- **Other experts are waiting for it:**
  - skill-over-expected reads its measures within role (I113);
  - VOE could credit value by role, which traveled with movers (H108);
  - `vacated-opportunity` asks who's like the missing player (H101);
  - availability reads deep-target receivers' risk (H95).
- **The depth chart's labels are wrong where the roles blur.** Half the listed outside linebackers are edge rushers indistinguishable from defensive linemen. A quarter of safeties play like corners.
- **Users would notice it** in player comparisons ("players like him"), in a role column on every player page, and in role-aware projections for movers and backups.

## Terms

- **Standard terms used:** snap share, personnel, target depth (aDOT), EPA ([`docs/GLOSSARY.md`](../../docs/GLOSSARY.md)).
- **New terms:**
  - **Pooled role space:** one PCA per side of the ball, fit across its positions together, with no position label. Offense's 6 axes:
    - in tight or split out;
    - the ball carrier;
    - red zone and middle;
    - 12 personnel;
    - the featured player;
    - targets in heavy sets.

    Defense's 6 axes:
    - box or coverage;
    - rusher or dropper;
    - red zone;
    - the tackler;
    - 3rd down;
    - playing time.

    The build re-reads and renames them after its refits.
  - **Role coordinates:** a player-season's 6 numbers in his side's space, with an interval.
  - **Named role:** a region of the space with an explicit rule, for example "edge" (rushes per pass snap above a cut, DL or OLB alike) or "slot defender" (CB or S on the field mostly against 11 personnel). The rules are set in the build and logged as technical calls.
  - **Team-adjusted own-snap share:** the share of his snaps that are, say, runs, minus his team's share of runs (the better role measure in H99).
  - **Role credit:** the part of a play's EPA credited to the roles on the field (H108's role part), offered to VOE.

## Builds on

| Project | What we use | Why |
|---|---|---|
| `participation` | `player_play.on_field` (who's on the field, after the season) | The on-field counts every feature comes from |
| `schemes-v2` | `team_season.charted` | The scheme traits roles cluster on (H103's side bet) |
| `skill-over-expected` | I113, its 14 measures | The first user, reading measures within role |
| `voe` | plain plus-minus (FINDINGS' VOE row) | H108's role credit is offered to it, and plain plus-minus is the bar |
| `crude-forecaster` | the yardstick (`score_input`) | The downstream score |
| `opportunity-quality` | F-rows on target depth and deep share | Usage measures already known to repeat |

**Already tried (the exploration; don't redo):**
- **On/off tilts** as a general role measure repeat less than own-snap shares (H99 failed); they stay only as inputs inside the space.
- **One PCA per position** repeats worse than the pooled space.
- **A mixture by BIC** gives playing-time tiers, not roles.
- **Role × scheme effects on efficiency** (H103, H106) and role targeting in free agency (H105) failed.
- **The in-season role-change chance** reduces to the snap-share change (H102) and moved to participation.

## Assumptions

1. **Participation's on-field lists are complete** for the players we place. The back seven's weak on/off tilts (H99) may partly be recording noise, flagged.
2. **A role is a season-level trait** of the player with his team. It's published after the season and used next season as a prior (rule m).
3. **Free data sees the target group, not the support group's job:** no alignment, blocking or coverage assignment. Slot against outside, and man against zone roles, rest on proxies (personnel faced, the middle-target share, the depth chart's slot label where a team lists one). Each named role states its proxy.
4. **Players under 200 snaps** are placed in the same space and shrunk toward their position's mean, by his snaps over his snaps plus 200.
5. **Measurables stay outside the space** (they repeat by construction); they're separate fixed inputs.
6. **Depth-chart positions** are used only to report and to compare, never inside the space.

## Goals

- Two pooled role spaces (offense, defense), refit after each completed season, with coordinates and intervals for every player-season since 2016.
- Named roles that are stable, with flips between halves below 14%, and that read as football.
- The coordinates scored as a forecasting input (the CEO, 2026-11-24: "we can still treat the latent space coordinates as a forecasting input so that we appropriately stress test the idea and we can always revert to a shared map approach later on").
- The role table (I113's next version) for skill-over-expected.

## Tests

- **Success looks like:**
  1. **Consistency, held out:** fit on 2016–2020; on 2021–2024, 4 or more of each side's 6 components repeat at split-half 0.5+, centred within position, and movers keep at least half of each component's season r.
  2. **Against position labels:** next season's per-snap rates (targets and carries; tackles and rushes per pass snap) from the coordinates beat the position labels (the exploration: +44% for targets, +26–28% for defense, carries not clear).
  3. **Beyond his own rates (the stricter test):** the coordinates add to position labels plus his own last-season rates and snap share. **The exploration found nothing here on either side**, so this is the test most likely to fail.
  4. **The yardstick:** through `score_input`, beside participation, on the receiving and rushing rest-of-season boards. The gain clears its interval and the 19 shuffled copies (coordinates shuffled within position).
  5. **Named roles:** flip between halves under 14%. Like-for-like substitutes on the pooled space rank under 0.5 (H101's test).
- **Ties (rule k):** a tie is an interval that includes zero, and the simpler side wins it. The simpler side, named now:
  - position labels plus his own rates over the coordinates;
  - the role table over the pooled PCA;
  - the pooled PCA over the nonlinear embedding;
  - the lasso over trees.
- **Failure looks like:** tests 3 and 4 fail, which the exploration expects. The coordinates then ship as a **shared map**: description, comparables, the bin other measures are read within. They're not a forecasting input, as the CEO allowed. If test 1 fails too, the role table ships alone.
- **No-noise target (the CEO approves):** next season's per-snap usage rates (targets and carries per snap; tackles and rushes per pass snap), against position labels plus his own last-season rates. Downstream: the yardstick's rest-of-season receiving and rushing boards.
- **Seasons:** 2016–2024 (participation's span), fit 2016–2020, scored 2021–2024 walk-forward; the vault is 2025, untouched.

## Inputs and outputs

- **Inputs** (known-at in brackets):
  - `player_play.on_field` [after the season];
  - play-by-play: targets, air yards, pass location, carries, run direction, tacklers, sacks and hits, passes defensed [after each game];
  - `team_season.charted` [after the season];
  - measurables from `players` and the combine [offseason], beside the space, not in it.
- **Outputs** (player-team-season, published after each season, known-at the season's last game plus participation's release):
  - offense or defense coordinates (6), each with a split-half interval;
  - named role and how sure the rule is (distance to its cut);
  - the role table's six features;
  - the shrinkage weight (for players under 200 snaps);
  - the PCA version (axes aligned to the last fit).

## How it will be used

- **As a prior in next season's in-season models,** from completed seasons only (rule m):
  - skill-over-expected (within-role measures);
  - participation (its role-change chance reads last season's role);
  - `vacated-opportunity`;
  - VOE (role credit);
  - availability.
- **In the yardstick,** as a candidate input (test 4).
- **In products:** player pages (role and comparables), and mover and backup projections.

## Plan

- **Ladder:** position labels (baseline) → the role table and named roles, lasso (method 1) → the pooled PCA per side (method 2) → trees on the coordinates (for H107's carries step) → the nonlinear embedding (method 3). Each rung must beat the one below; the ladder stops when one doesn't.
- **Time box:** three build sessions:
  1. package code, the on-field counts and both pooled spaces with refits, consistency and shrinkage;
  2. named roles, the forecasting tests and the yardstick;
  3. the nonlinear embedding and the scorecard.
- **Later, by the expansion plan the CEO agreed:**
  - quarterbacks as their own space;
  - rookies started from measurables and draft slot. That's an offseason event, so by rule m it registers as its own small expert when built.
- **The backlog it carries:**
  - I57 (route mix; the forecast itself);
  - I113 (the role table);
  - I122 (a shrunk vacancy forecast);
  - I123 (labels that aren't playing time);
  - I49 (swap pairs, with participation).
- **Technical calls (for veto):**
  - **Refits:** each side's PCA is refit after every completed season on all completed seasons. The new axes are rotated to match the last fit (Procrustes), so a coordinate keeps its meaning across versions. Walk-forward history: season s's coordinates come from a fit on seasons up to s.
  - **Inputs inside the space:** the team-adjusted own-snap shares and the on/off tilts both stay in. PCA weights them, and H99's failure was as a stand-alone measure.
  - **Placement and shrinkage:** players are fit on 200+ snaps; those under 200 are placed and shrunk by snaps / (snaps + 200).
  - **Measurables:** outside the space.
  - **Named-role rules:** set on the 2016–2020 fit, frozen for scoring.
  - **Trees:** added as a rung (not in the exploration) to answer the carries step.
