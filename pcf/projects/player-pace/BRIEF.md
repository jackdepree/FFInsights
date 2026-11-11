# Brief: Player pace and play-calling (`player-pace`)

**Status:** draft (kickoff 2026-11-11, the CEO: "Start player pace"; hunches H26–H31 recorded 2026-11-11; one CEO call open) · **Layer:** expert · **Cadence:** in_season, retrospective, or one of each (the CEO's call, "Open for the CEO"; who was on the field per play is post-season only)

## The usual way
*Claude, 2026-11-11, before any research.* Analysts mostly treat pace and pass rate as the play caller's, and move them for players only at the edges:
- **Starting QB changes.** When a starter is hurt or benched, the fantasy sites and the betting market cut the team's pass volume and total for a weak backup, and raise designed runs for a mobile one. The size of the cut is judgment, or a "with and without" split: the team's numbers in games with QB A against games with QB B.
- **With-and-without splits for everyone else.** The same split is done for a star receiver or back ("pass rate is 4 points higher when he plays"). The samples are small, and the splits mix in the schedule, the score and the season, so careful analysts treat them as hints.
- **Plus-minus, from other sports.** Basketball and hockey solve this with regularized adjusted plus-minus: one regression on every stint with an indicator for each player on the floor, ridge-shrunk because teammates are almost always on together. In football it's been tried for player value (EPA), rarely for pace or pass rate.
- **What's known:** PROE and tempo follow the head coach when coaches move (schemes-v2#F3, pace#R4); a new QB moves season PROE about as much as a new coach (season-to-season r 0.26 against 0.32, schemes-v2#F3).

## Analogies
1. **Hockey's linemates.** Hockey plus-minus struggles because linemates share almost every shift: you can't tell the centre's effect from his wingers' until injuries and line changes split them. Football's QB and play caller are the extreme case: a starter shares nearly every snap with one coordinator for a whole season. So this analogy asks: where do the splits come from? Backup QBs, mid-season injuries, coordinator changes, players changing teams. Those are the only rows that can tell a player's pace from his coach's, and how many there are decides how much shrinkage it needs.
2. **A conductor and a soloist.** The conductor sets the tempo; a strong soloist can push it or drag it, and an orchestra plays a concerto differently for a soloist it trusts. So this analogy asks: does a player change the tempo *itself*, or change what the conductor chooses (a coach who trusts his QB lets him pass on 3rd and 2)? The first would show on every play; the second only in some situations, like PROE by down.

## What it builds on
- **pace (done 2026-11-11):** `play.pace` has every snap's PCF expected pass chance, pass rate over expected, expected gap and pace over expected; `team_game.pace` sums them per team-game. Pace over expected repeats at 0.84 week to week and PROE at 0.77 (pace#B1); coach changes move both (pace#R4). The team expert forecasts next-game plays, dropbacks and runs (pace#R1). A player effect would be a feature for that forecast.
- **schemes-v2#F3:** shotgun, no-huddle, tempo and personnel follow the coach when coaches change teams; scrambling and efficiency follow the QB.
- **Who was on the field.** In season, PCF knows the passer, rusher and receiver of every play (play-by-play) and each player's snap count per game (weekly, the morning after; 2013→). Who was on the field on each play (participation) is known only after the season, 2016–2025. So an in-season expert sees the QB on every dropback and each player's share of the snaps, not the full lineup per play; a lineup-per-play version would be retrospective (rule m: two experts if both are needed).
- **cleaning-port#F14, tag-tables#F17:** the starting QB isn't the team's usual starter in 11–25% of team-games: the splits the hockey analogy needs.
- **participation** forecasts who plays; a player effect only helps a forecast if PCF knows before the game who'll be on the field.

## CEO hunches
*The CEO's words, recorded as said, before Claude's research.* Each gets a verdict in [`projects/HUNCHES.md`](../HUNCHES.md).

**The CEO's direction** (2026-11-11): "I want to treat this expert ver similarly to our previous team pace expert except for the obvious fact that the granularity is different." The same measures (pace over expected, pass rate over expected on every play, against PCF's own expected values from `play.pace`), the same two tests per measure, the same harness; the grain is the player.

| # | Hunch, in short | What the usual way says | How the exploration will test it |
|---|---|---|---|
| H26 | Some conditions make a player's rates over expected inconsistent as forecasts of the future; find them | Player-level splits are noise, except the QB's | Each player's pace over expected and PROE (on the plays they were on the field) through `pcf.validation.consistency`, week to week and season to season, overall and split by condition (position, snap share, starter or backup, same or new coach, same or new team, sample size). Conditions where the interval reaches 0 are the inconsistent ones |
| H27 | Players carry their rates over expected to a new team | Pace and PROE follow the coach (schemes-v2#F3, pace#R4); the QB carries scrambling and efficiency, not the play-calling | Players who changed teams between or during seasons (trades, free agency, released and signed): their rate at the old team against their rate at the new one, beside the new team's rate the season before, and beside the same test for coaches who moved |
| H28 | Players carry a plus or minus relative to their team's pace or pass rate | With-and-without splits are hints; plus-minus is a basketball and hockey tool | Plus-minus: the team's pace over expected and PROE with the player on the field against without, shrunk toward 0 the way basketball's regularized plus-minus is, with the team-game's own level taken out |
| H29 | That plus or minus repeats game to game and season to season | Plus-minus needs years of data to settle | H28's plus-minus through `pcf.validation.consistency`: odd against even weeks, and one season against the next |
| H30 | Pace or pass rate is associated with the age of players at different positions | Aging curves are for efficiency and playing time; lore says teams "protect" rookie QBs with the run | Team-game pace over expected and PROE against the snap-weighted age at each position (QB, RB, WR, TE, offensive line; each defensive group), beyond the coach's own history |
| H31 | Defensive players carry the same features and consistencies as their offensive counterparts | Defenses barely set the other team's pace; what a team's defense allows barely repeats (pace#B1) | H26, H28 and H29 for defensive players, on the opponent's plays they were on the field for: does the opponent's pace over expected and PROE move with them, and does it repeat? |

**H26–H31** (the CEO, 2026-11-11, word for word, after the direction above).
> "I would want to discover the conditions that are inconsistent in terms of predicting future pass rate over expected or pace over expected. I want to test to see if players carry their rates over expected from team to team, so if a player is traded will they carry their rates to the new team? I’d also be interested to see if players carry a plus or minus value relative to their team's pace or pass rate. I’d be curious if plus or minus is auto-correlative from game to game or season to season. I’d also be curious if pace or pass rate is associated with age of players at different positions. I’d be curious too if defensive players carry the same features or consistencies as their offensive counterparts."

### Claude's assumptions, limits and expectations, per hunch
*Stated before the exploration, so its results mean something.*
- **For every hunch:**
  - *A player's rate is the team's rate on the plays they were on the field.* Never on the plays they touched: a receiver's targets are passes and a back's carries are runs by definition, so "PROE on his touches" is 1 or −1, not a habit. That's the tempting but bad version.
  - *Who was on the field on each play is post-season only* (participation, 2016–2024 for the exploration; the 2025 vault stays closed). In season PCF knows the passer and rusher of each play and each player's snap count per game. So the exploration measures on-field rates from participation, and checks how much of that survives with what's known in season: snap-share-weighted team-game rates, and the QB on dropbacks.
  - *Teammates and the coach are on together.* A starting QB shares nearly every snap with one play caller for a season (the hockey analogy), so a player's rate is mostly his coach's until something splits them. Every player number is set against the coach's own history.
- **H26:** *My expectation:* QBs are consistent season to season, weaker week to week; most other positions are noise, because they're on the field for nearly the team's every play and so their rate is the team's. Inconsistent conditions: small samples (backups, part-timers), a new coach, a new team.
- **H27:**
  - *Few movers, and they rarely move alone.* Starting QBs who change teams number a handful a season, and their new team often has a new coach too. Players who change teams mid-season are fewer still.
  - *Mobile QBs are the likeliest carriers:* designed QB runs count as runs, so a running QB lowers PROE wherever he goes.
  - *My expectation:* QBs carry a little PROE (mostly running QBs), nobody carries pace; skill players carry nothing measurable.
- **H28:**
  - *"Without" needs the player off the field.* Starters are on nearly every snap, so their "without" rows are their absences (injuries, rest), which come with a backup and often a different game script. Those are the only rows that measure them.
  - *Simpler alternative:* the with-and-without split by game (starter played or not), from snap counts, known in season. The plus-minus per play is the precise version, post-season only.
  - *My expectation:* a real plus-minus for QBs (backups pass less over expected), small or none elsewhere.
- **H29:** *My expectation:* QB plus-minus repeats season to season; others don't clear 0 week to week.
- **H30:**
  - *Age is tangled with who still plays.* A 35-year-old RB still starting is a good one; young rosters belong to rebuilding teams with new coaches. The coach's history and the team's strength are held fixed.
  - *My expectation:* a small rookie-QB effect toward the run (the lore), nothing clear elsewhere.
- **H31:**
  - *A defender changes the offense's plan only if the offense plans around him.* A shutdown corner or an elite pass rusher might move the opponent's pass rate; most defenders shouldn't.
  - *My expectation:* fails mostly: what a team's defense allows barely repeats (pace#B1), so its players' share of it should repeat less. A few stars may show up, too few to call it held.

## The question
How much does each player, starting with the QB, move his team's pace over expected and pass rate over expected, does that follow him (to a new team, from game to game, season to season), and under which conditions is it noise?

## Why it matters
Team pace forecasts each team's plays, dropbacks and runs from the coach's habits (pace#R1). When the QB changes, or a star is out, those habits change and the team forecast doesn't know it. A player effect fixes the forecast in exactly the weeks the market and the fantasy sites adjust by judgment: a backup QB starting, a star back out. A user would notice it as better volume projections the week a starter is hurt.

## Terms
- **Standard terms used:** [pass rate over expected, pace over expected, PCF expected pass chance, snap share, participation, plus-minus](../../docs/GLOSSARY.md) (pace's terms; plus-minus is new to the glossary).
- **New terms this project introduces:**
  - **On-field rate:** a team's pace over expected or PROE on the plays a player was on the field for (participation), or, in season, weighted by his snap share of each game.
  - **Player plus-minus:** the team's rate with the player on the field minus without, shrunk toward 0 by how many plays measure it, with the team-game's level taken out.
  - **Mover:** a player who played for one team and then another, between or within seasons.

## Assumptions
- Pace and PROE are mostly the play caller's (schemes-v2#F3, pace#R4); a player effect is what's left once the coach is held fixed.
- Everything a forecast uses is known before kickoff (rule c). A player effect helps a forecast only if PCF knows who'll play (participation's forecast, injury reports).
- Retrospective outputs reach in-season models only from completed seasons, as priors (rule m).

## Goals
1. **The measures:** on-field rates and plus-minus per player, each through the two tests (H26, H28, H29, H31).
2. **The verdicts:** movers (H27) and age (H30), with numbers.
3. **Discovery for team pace:** whether a player effect, known before the game, improves team pace's plays, dropbacks and runs forecasts (pace#R1) in the weeks a starter changes.

## Success and failure, as tests
*Thresholds from `docs/VALIDATION.md`.*
- **Consistent:** a measure is kept if its week-to-week or season-to-season interval stays above 0 (CONSISTENCY.md), and marked noise otherwise.
- **Signal:** each final forecast beats its shuffled, signal-free self (rule k).
- **Helps the target:** team pace's volume forecasts with the player effect beat the same model without it by a 90% week-block interval below zero on the range score, at least in the games where the starting QB changed.
- **Football sanity:** backup QBs move PROE the way the market assumes (down); running QBs lower PROE; a player's effect is smaller than the coach's.
- **Failure looks like:** no player effect beyond the coach's that repeats; then the team pace expert stands as it is, and the CEO's hunches get their verdicts.

## Inputs and outputs
- **Inputs:** `play.pace` (every snap's expected pass chance, PROE, pace over expected), play-by-play passer and rusher, weekly snap counts, participation (post-season, 2016→), rosters (age, position), team pace's forecasts, coaches. All already in PCF; nothing new to sign off.
- **Outputs:** depend on the CEO's call below: per player, the effect on his team's pace and PROE, with q10, q50 and q90, in the standard schema.

## How it will be used
Team pace's volume forecasts (in the weeks a starter changes), player opportunity, fantasy projections, and the game simulator.

## Open for the CEO
1. **What should player pace give the layers above, and when?** *(taste call; your instinct first)* It decides whether the expert runs in season, between seasons, or both (rule m: two experts if both).
