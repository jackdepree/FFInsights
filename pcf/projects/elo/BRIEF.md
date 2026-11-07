# Brief: Team Elo (`elo`)

**Status:** draft, 2026-11-07 · **Layer:** expert · **Cadence:** in_season

## The usual way
*Claude, 2026-11-07, before any research.* The standard is FiveThirtyEight's NFL Elo:
- **Ratings:** each team has one rating. A rating gap becomes a win probability through a logistic curve, and a point spread at about 25 rating points per point.
- **Updates:** after each game, a team's rating moves by a fixed step size times how far the result beat or missed expectations. The step grows with the margin of victory, damped so favorites don't snowball.
- **Adjustments:** a home-field bonus, a quarterback adjustment when the starter changes, and a pull about a third of the way back toward average between seasons.
- **How good it gets:** the closing line is the yardstick, and good Elo models miss the final margin by roughly 1 to 1.5 points more than the line does.
- **Variants:** Glicko (each rating has its own uncertainty), least-squares power ratings, and ratings built from EPA instead of final scores.

## Analogies
1. **Tracking a moving car with GPS.** Each game is a noisy reading of a team's true strength, which drifts. A tracking filter (Kalman) asks how much to trust each new reading against the old belief, and how fast the truth can move. Elo's step size is that trust, frozen at one value. A car can also turn suddenly, like a quarterback going down or a coach being fired, and a good tracker trusts new readings more for a while after a turn.
2. **A stock index and its constituents.** A team is an index of its parts: QB, line, receivers, pass rush, secondary, coaching. Elo sees only the index. When a big constituent leaves, the index should drop by its weight at once, not over weeks of losses. And when two indexes trade against each other, the result depends partly on which parts meet which.

## CEO hunches
*The CEO's words as said on 2026-11-07, before Claude's research. Each gets a verdict in [`projects/HUNCHES.md`](../HUNCHES.md).*

| # | Hunch, in short | What the usual way says | How the exploration will test it |
|---|---|---|---|
| H1 | A team is its players that week: injury reports and week-to-week changes in snap share tell whether it's the same team | Only a QB adjustment; every other absence is ignored | A "same team" measure (the share of a team's usual snaps on the field this week, from participation and the injury report) moves the rating or the step size. Against the usual Elo with its QB adjustment, on next games' margins |
| H2 | Turnover makes a new team each season: weight recent games more, and regress toward the mean at the turn of the season | A fixed one-third pull toward average for every team | The pull toward average set by each team's measured turnover (the share of last season's snaps that return). Against the fixed one-third, on weeks 1–6 |
| H3 | Average win probability across a game's plays says more than the final margin; an underdog win that came late should count for less | Final margin, damped | Ratings updated from average win probability, against final margin. nflverse's win probability is fit on games through 2019 (tag-tables#F4), so it's judged on 2020–2024 only |
| H4 | Noise-cancelled scores: high-impact plays that are pure luck (a fumble returned for a touchdown) should count as if they didn't happen | Final score as it happened; some analysts discount fumble recoveries | First find plays with a big effect on the score that teams don't repeat week to week (return touchdowns, fumble recoveries, missed kicks, and any others the data shows). Then update ratings from the margin without them, against the real margin |
| H5 | Strength is conditional: at home, against a bad QB, against heavy zone coverage, when trailing at halftime | One rating plus a home bonus | Part 2, after H6 |
| H6 | First find which conditions are consistent and predict the future, and which are noise ("a fake variable") | Not part of Elo | Its own project, `stabilization`, started once this brief is agreed. H4's luck plays are its first slice |
| H7 | An overall rating for downstream models, plus parts: offense, defense, running, passing, winning and losing states | One rating, sometimes offense and defense | Offense and defense ratings (totals need them), then running and passing. Each part is kept only if it improves next games' forecasts over the overall rating |

**H1.**
> "a team isn't a real thing. It's really just like a bunch of players that sometimes play, sometimes don't play, play under different situations, you know, against different people."

> "teams are not homogenous. So I think a rating, like, looking at quarterbacks is good because, like, oh, if there's a quarterback change or if the quarterback gets hurt, like, oh, that's a big difference. But I think looking at the injury reports and maybe looking at the variance from week to week of, like, player participation and snap share, that tells a lot about, is this the same team that played last week or the week before or the week before?"

**H2.**
> "that same kind of idea applies to between seasons, where there's a ton of personnel turnover, where, like, so many people get traded, so many people get cut, so many people retire, so many people are drafted. And so it's really a new team every season, like a big, it's a really different team. And so I think one miss that ELO ratings usually have, or maybe they don't have this, but I think it's important to upweight recency and downweight things that happened a long time ago, and especially between seasons. So if you're going from one season to the other, every team should regress towards the mean when the season turns over."

**H3.**
> "I think it would also be important to not just look at the margin of victory, but also the percent of a team, like the percent a team actually was expected to win. So the winning at any given play within a game, is a certain amount, it's a value, and let's say you average all of the plays up, and so let's say a game finished and team A had an average win percent chance of 60% across all plays, and team B would have obviously the opposite, they'd have 40%. But team B actually won. Because maybe they had a 10% chance of losing the entire time, but then randomly at the very last second they get a touchdown and a field goal and they win the game. You know? So like maybe they're losing the whole game and maybe they're even expected to lose the whole game. And then they took the win out from under them. They got an underdog win. Like that's important. That's a good feature."

**H4.**
> "maybe we shouldn't even start with the ELO rating. Maybe we should start with noise canceled scores, which I think is interesting. So like essentially trying to find which plays are extremely unpredictable and carry very little predictive value."

> "if something is noise, did it have a really big impact on the game? And if it did have a really big impact on the game, that means we shouldn't care about it. We should exist almost as if it did not happen, because that information is essentially unpredictable, and there's no consistency."

> "if someone fumbles the ball and it gets returned for a touchdown, you can't expect that to happen every single game. That's not a thing that the team did. That's just a random fluke."

> "let's just say if you played the game and you added like 100 more minutes or 5 more quarters to the game for whatever reason, then the team that should have won will win. You know, if you just add more time to the game, you add more samples, it's just going to regress towards the mean, which is that team, the better team will win."

**H5.**
> "let's say one team has a really good ELO rating when they're playing at home, or maybe one team has a really good ELO rating when they're playing another team that has a bad quarterback, or maybe one team has a really bad ELO rating and otherwise they're average, but they have a really bad ELO rating when they have to play a team that uses a lot of zone coverage on defense, you know, things like that."

> "let's say a team is losing at halftime, you know, maybe they're really bad. Maybe they just aren't able to catch up. They're just not expected to catch up. Or maybe they're winning at halftime and it's not very consistent to whether they're going to keep winning in the second half and they might just lose the game, you know. Or maybe let's say like if they run the ball a lot, then they're just not doing that well, or maybe they are doing really well."

**H6.**
> "we need to find what things are consistent, so then we can really dive deep on those things."

> "under certain conditions, can we find conditions that reliably predict the future? So like, maybe a team, you know, when they're losing, they still perform well. And so when they're losing, we don't count that against them. And maybe we can figure out that this is a new feature that we should use in almost every downstream thing, that every downstream expert that we have, you know. Or maybe we find that, you know, it doesn't really matter if a team is losing or winning. It's just noise. It's like a fake variable that we track that doesn't really matter. But we need to find features that do matter, that cancel out the noise, that or not even cancel out the noise, but just like, they filter the noise so we can find the true image underneath."

**H7.**
> "I think it's good to have like an overall predictor, because that's, it's easy for downstream models to learn from that. But it's also good to have like, okay, yeah, there's an offense, and within an offense, there's, what are the consistent parts? Well, there's running, there's passing, there's when you're losing, there's when you're winning."

**On scope (CEO):**
> "Do we want this project to be really a really simple team ELO rating? Or do we want it to be like an expansive expert that is essentially trying to not necessarily create schemes, but trying to figure out like [conditional strength] ... So I think we might want to build the schemes layer before the ELO. Or what we could do is we could build a simple ELO rating system and then just caveat and say it's the project is half done."

**On what it predicts (CEO, 2026-11-07):**
> "I think the team ratings should predict all three. So who wins by how much and the total points. But I think it should also predict a fourth thing, which would be future wins. So maybe like next three games or next the rest of the season, or things like that, or like given how many wins they have now, the rest of the season. So some sort of long horizon."

**On order (CEO, 2026-11-07):** Elo in two parts. Part 1 is the rating, with H1–H4 and H7 as its experiments. Part 2, conditional strength (H5), comes after the consistency project (H6).

## The question
How strong is each team before each game? Strong enough to forecast who wins, by how much, the total points, and the wins still to come.

## Why it matters
- **PCF's first betting model:** sides and totals, set against the closing lines we collect.
- **The base for team strength:** opponent-adjusted efficiency, pace, game script and every product use it. Fantasy needs it for game script and the touchdowns available.
- **A clean test bed for the hunches:** one rating fed different inputs shows directly whether noise-cancelled scores or win probability predict the next game better than the real score.

## Terms
- **Standard terms used:** range score (pinball), log loss, MAE, closing line, coverage ([glossary](../../docs/GLOSSARY.md)).
- **New terms:**
  - **Rating:** a team's strength in points against an average team on a neutral field.
  - **Step size:** how far one game moves a rating. In the tracking analogy, how much a new reading is trusted.
  - **Pull toward average:** how far ratings move back toward the league average between seasons.
  - **Same-team share (H1):** the share of a team's usual snaps that are on the field this week.
  - **Luck plays (H4):** plays with a big effect on the score that teams don't repeat from week to week.
  - **Noise-cancelled margin (H4):** the final margin with the luck plays' points taken out.

## Builds on
| Project | What we use | Why |
|---|---|---|
| `grain-tables` | `game` (schedule, result), `team_game`, `play` (pbp) | Results, scores, and the plays behind them |
| `validation-harness` | The contract, gateway, walk-forward backtest, `compare`, signal test | The same rules as every model |
| `baselines` | `MarketMargin`, `MarketTotal`, `MarketWin` (the closing line) | The yardstick. Known only at kickoff, so a benchmark, never an input (validation-harness#F3) |
| `participation` | Snap shares and the injury report | H1's same-team share, H2's turnover |
| `tag-tables` | Garbage-time and game-state tags | Where luck plays and game states live (tag-tables#F3, #F4) |
| `prediction-ledger` | The live run | Elo joins the ledger with its closing line once validated |

**Already known:** the closing line misses margins by 9.8 points and totals by 10.4 on average, and favorites win 66.5% (baselines#F6). nflverse's win probability and EPA are fit on seasons through 2019 (tag-tables#F4).

## Assumptions
- **A rating is updated after each game and used at the next prediction moment.** Results are in by Tuesday, and the injury report by the Thursday and Saturday runs (decision 0016). The run time is a technical call, made in the exploration.
- **Past seasons look enough like this one.** The game has changed since 1999 (more passing, new kickoff rules), so the exploration checks whether old seasons help or hurt.
- **The close is about as good as forecasts get.** Matching it isn't expected. Getting near it says the rating is healthy, and any edge comes from the few places where we differ and are right.

## Goals
1. A team rating before every game that forecasts who wins, the margin and the total, each with a range, plus wins over the next 3 games and the rest of the season.
2. A verdict on each of H1–H4 and H7: does it beat the usual Elo?
3. Ratings and forecasts saved as a walk-forward history for higher layers.

## Tests
- **Success looks like (CEO, 2026-11-07):**
  > "if we have a super simple base ELO that is literally just looking at margin of victory or margin of defeat, and we just do, you know, the rolling sum or the rolling average and or rolling sum, and we use like very standard like how chess does it. We have that as a base, and then we also have the the thresholds that you gave, so 9.8 points on average, or 1 to 5 points by the closing line. I think those are good success criteria as well."
  - **Beats the simple Elo:** the best rating beats a chess-style Elo fed only the margin of victory (rung 1), on next games' margins, with the 90% interval of the gap below zero.
  - **Near the close:** on the same games, 2016–2024, it misses the margin by no more than 1.5 points more than the closing line (which misses by 9.8, so about 11.3 or less), and the total by no more than 1.5 points more (10.4, so about 11.9 or less). The CEO confirmed on 2026-11-07 that "1 to 5" meant 1 to 1.5 points.
  - **Claude's view:** agreed. Within 1.0 point of the close would be a strong result. The long horizon is judged against the simple yardstick below, since we have no market history for season wins.
- **Each hunch:** held if its version beats rung 1 on next games' margins over 2016–2024 (2020–2024 for H3), with the 90% interval of the gap below zero, compared by whole weeks.
- **Signal:** each rating beats 20 of 20 shuffled versions of itself (VALIDATION.md §5).
- **Calibration:** win chances calibrated; margin and total ranges hold about 80% inside q10–q90.
- **Long horizon:** wins over the next 3 games and the rest of the season, against a simple yardstick (the current win rate pulled toward .500).
- **Seasons:** trained from 1999 if old seasons help, reported 2016–2024; the 2025 vault stays closed.

## Inputs and outputs
- **Inputs:** game results and scores; play-by-play for H3 and H4; snaps and the injury report for H1 and H2. All through the gateway, each with its known-at rule.
- **Outputs:** per team and game: ratings (overall, offense, defense), win chance, and margin and total with q10, q50 and q90. Per team and moment: wins over the next 3 games and the rest of the season, with ranges.

## How it will be used
Win chance, margin and total feed the betting products and the ledger, where closing line value is measured. The ratings feed team-efficiency, game script and fantasy game environments.

## Plan
Part 1's time box: 2–3 sessions.
- **Rung 0:** home field only; last season's point differential.
- **Rung 1:** the CEO's base: a chess-style Elo fed only the margin of victory. Then the usual extras (home field, QB adjustment, the one-third pull), each kept only if it helps.
- **Rung 2:** the hunches H1, H2, H3, H4 and H7, each a variant against rung 1.
- **Rung 3:** the hunches that held, combined, with each rating's own uncertainty (the tracking analogy) for the ranges and the long horizon.
- **Part 2 (later):** conditional strength (H5), after `stabilization` (H6).
