# Vacated opportunity: who absorbs an absent player's targets and carries

> **Status:** kickoff, 2026-11-24 (the CEO: "Ok, let's start vacated opportunity"). The usual way and two analogies are below. The CEO's direction and hunches H109 to H112 are in, all with odds (2026-11-24). The exploration ran methods 1 and 2 (the CEO's choice) the same day, pre-registered and with results in [EXPLORATION.md](EXPLORATION.md): go. H109 held by its pass rule; H110, H111 and H112 failed (H112's stayers side bet held); I125 held. Waiting for the CEO's direction and closes.

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
