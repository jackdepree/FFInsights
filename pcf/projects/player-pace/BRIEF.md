# Brief: Player pace and play-calling (`player-pace`)

**Status:** draft (kickoff 2026-11-11, the CEO: "Start player pace"; waiting for the CEO's hunches) · **Layer:** expert · **Cadence:** in_season (see "What it builds on": who was on the field per play is post-season only)

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

*(waiting for the CEO)*
