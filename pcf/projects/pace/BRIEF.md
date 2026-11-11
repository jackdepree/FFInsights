# Brief: Pace and play-calling (`pace`)

**Status:** draft (kickoff 2026-11-10; waiting for the CEO's hunches) · **Layer:** expert · **Cadence:** in_season

## The usual way
*Claude, 2026-11-10, before any research.* Pace analysts (Football Outsiders' pace stats, Sharp Football, the fantasy sites' team-volume projections) work in three steps:
- **Measure tendencies in neutral situations.** Seconds per play, no-huddle rate and pass rate are measured only when the game is close: score within about 7 points, outside the last two minutes of each half (or win probability between 20% and 80%). Outside those situations, the score sets the pace instead of the coach. Pass rate over expected (nflverse's `xpass`) is the usual play-calling measure.
- **Project each team's plays.** A team's plays next game come from its own neutral pace, the opponent's pace, and the game script the betting line implies: favorites run more and slow down late, underdogs pass more and hurry. Both teams share one 60-minute clock, so the two teams' plays are projected together, usually around 125–130 in all.
- **Split the plays into passes and runs.** The split uses the team's pass rate over expected and the same game script. The fantasy sites then share those passes and runs out to players by target and carry share.
- **What's known:** neutral pace follows the play caller and repeats season to season. Game script moves a single game's plays and pass rate more than any team trait does. The market's totals already reflect most of this.

## Analogies
1. **Possessions in basketball.** NBA analysts don't project points, they project possessions times points per possession. A game's possessions are a blend of both teams' paces, roughly *my pace × your pace ÷ league pace*, because both teams share the clock. Football has the same shared clock with a twist: drives alternate, so drives are close to equal, but plays per drive aren't. A team that converts third downs runs more plays and leaves the other team fewer. So this analogy asks: is pace really the snap clock, or is it drives times plays per drive, where plays per drive is mostly efficiency?
2. **Climate and weather.** A team's pace and pass rate are its climate; the score is the weather that pushes each game around. The usual neutral-situation filter measures climate only on calm days, and throws away most of the data to do it. A climate scientist would instead model how much the weather moves things and adjust it out, keeping every day. That's what pass rate over expected already does for pass rate. So this analogy asks: is an adjusted-for-script measure, on every play, steadier than the neutral-only one?

## What it builds on
- **schemes-v2** already forecasts four team tendencies for the next game, from the shrunk season, the last 4 games, last season and the head coach's history: pass rate over expected, shotgun rate, **tempo** (game seconds from an in-bounds run to the next snap) and throw depth. They beat every simple average and hold on the 2025 vault except throw depth (schemes-v2#R1, R12). Tempo and the no-huddle rate follow the head coach (schemes-v2#F3, H10). What's new here is the **volume**: how many plays and passes each team runs in a game.
- **Elo** forecasts each game's margin and total, 0.27 and 0.30 points behind the close (elo#F2); its ratings are saved for higher layers.
- **participation** forecasts who plays; player opportunity will multiply its shares by this project's volume.

## CEO hunches
*The CEO's words, recorded as said, before Claude's research.* Each hunch gets the next id on the scoreboard (H19, H20, ...), is tested in the exploration, and gets a verdict in [`projects/HUNCHES.md`](../HUNCHES.md).

| # | Hunch | What the usual way says | How the exploration will test it |
|---|---|---|---|
| | *waiting for the CEO* | | |

*The rest of the brief (the question, why it matters, terms, assumptions, goals, success tests, inputs and outputs) is drafted with the CEO after the hunches.*
