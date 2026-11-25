# Stabilization: how many attempts until a rate is real, and how far to pull it back

> **Status:** kickoff, 2026-11-25 (the CEO: "Kick off stabilization"). The usual way and two analogies are below, with what we already know. The CEO's direction and hunches H113 and H114 are in (2026-11-25, 25% each), with Claude's odds and three ways to test them (one exploratory). Waiting for the CEO to confirm the hunches' wording, give sizes if they like, and pick the methods; then the exploration runs.

## Why now

- **Everything it needs is done:** the grain tables (player-game and player-season rows from play-by-play) and the validation harness.
- **Every expert already shrinks its own way.** pace and schemes-v2 have `_shrunk` variants, opportunity-quality pulls efficiency back by one rate per position (F37), and td-expert keeps a tenth of touchdowns over expected (F64). Each answer was found once, for one measure. One shared answer (how far to trust a rate after n attempts, and how sure to be of it) would let every expert, and every new measure, start from it.
- **It's the base of player-level uncertainty.** qb-talent, the game simulator and the outcome ranges (floor, median, ceiling) need to know how wide a player's true rate could be, not just its middle.
- **A hunch waits on it:** H6 (consistent measures predict other outcomes) was first filed here. Its sharpened test now runs in I141's night build. This project answers the question underneath: how consistent each player measure is, at each sample size.

## The usual way

Baseball's sabermetrics answered this first. A rate's **stabilization point** is the sample at which its split-half reliability reaches 0.5: odd attempts against even ones, correlated across players. At that point the observed rate is half signal and half noise. The point also gives the shrink: add that many attempts at the league average to the player's own (Tango's "regress by k"), so a rate with k = 300 and 300 attempts is pulled halfway back. The same idea, written as a model, is **empirical Bayes**: a beta-binomial for yes-or-no rates (catch rate, sack rate) and a normal-normal for averages (EPA a play). Each player's estimate is a weighted mix of his own rate and the population's, weighted by how much the population really varies against how noisy his sample is.

Football writers quote the same kind of numbers: "sack rate stabilizes in about a season's dropbacks; interception rate never does; yards per carry barely stabilizes at all." They are usually computed once, for all players of a position, and against the league average.

## Two analogies

- **Insurance: credibility theory (Bühlmann).** An actuary pricing a fleet's premium mixes its own claims record with the rate for its class: premium = Z × own + (1 − Z) × class, with Z = n / (n + k) and k = the expected noise over the true spread between fleets. Two things carry over that the usual way skips:
  - **The class matters as much as the shrink.** Actuaries pull toward the right class, not toward everyone: a delivery fleet toward delivery fleets. For a player that's his role (P11: much of what repeats is role), his team or his scheme, not his position's average.
  - **Credibility can be layered:** a player toward his role, his role toward the position. A thin role borrows from the next level up.
- **Psychometrics: test reliability and item information.** A test's reliability depends on how many questions it has, and on how much each question says. A hard question separates strong from weak students; an easy one tells you little. Three things carry over:
  - **Not every attempt is equal.** A contested deep target may say more about a receiver than a screen. Counting attempts by their information, perhaps by context-live's expectation, would make a rate stabilize sooner in real attempts.
  - **Reliability changes with conditions** (measurement invariance). A rate measured before a move may not mean the same after it. H26 already found that a new team, a new coach and part-time roles break consistency.
  - **Talent drifts.** A test score from three years ago is weaker evidence than last month's. The pull-back should also forget: aging, role changes and injuries move the true rate, so old attempts should count for less.

## What we already have

**Findings: how fast things become real:**
- **Fast:**
  - pass rushers' pressures per dropback (season to season DL 0.63, OLB 0.72; movers keep 81% and 97%; F9);
  - a receiver's route mix (vertical share r 0.51, F86);
  - a new head coach's tendencies (80-90% of their level in 1-2 games, F89);
  - target share and depth, which travel with the receiver (F1).
- **Slow, or never:**
  - efficiency per chance (week to week 0.02; a player keeps 0.12 of his points over expected per chance at 20-50 chances, 0.36 at 100-200, 0.6 at 400+; F37);
  - touchdowns over expected (keep about a tenth, F64; a season of them is dice, F68);
  - yards per carry (his own past removes 4.7% of the error next season, F15);
  - running backs' catching over expected (noise, F14);
  - defensive backs' coverage (0.15 to 0.37, F19).
- **Who to pull toward:**
  - one pull-back rate per position was as good as one per player (F37);
  - players whose pattern held across teams didn't keep more (H62 failed);
  - the kept share swings by season (0.15 in 2016, 0.38-0.47 in 2018-2024, 0.24 in 2025; I104).

**Code and tables:**
- `pcf.validation.consistency`: split-half and season-to-season r with intervals.
- [`CONSISTENCY.md`](../CONSISTENCY.md): about 220 measures, mostly team level.
- The grain tables' player-game rows, and play-by-play per play from 1999, free and in season.

## The backlog that fits

- **I104:** a kept share that changes by season, set from what this season's gaps have already done.
- **I14:** ranges should widen with how much a player's share swings.
- **I52:** real but redundant traits belong in the ranges, not the middle.
- **H26** (held): the conditions that break a rate's consistency; here, they'd set where the pull-back restarts.
- **I152** (a dream): where a player's role is heading, which is the drift side of the same question.

## What it would deliver (a sketch, for the CEO to change)

For every player rate we use, by position:
- its stabilization point;
- the shrunk rate after n attempts, with an interval;
- what it's pulled toward;
- how fast old attempts fade.

All of it is known before each game and served to the other experts. The test: the shrunk rate forecasts the player's next games and the rest of his season better than the raw rate, better than one rate per position, and better than each expert's own shrink. The intervals should hold their coverage.

## The CEO's direction and hunches (word for word, before any test)

**The CEO, 2026-11-25:** "I think it would be really interesting to see if we could model the effects of other teammates. And so we can take we obviously explore lots of features and lots of outcomes, but we can only keep the ones that actually have signal, obviously, or have some sort of consistency. And we can still track the outliers too, because those might have some impact. So really what comes to mind is two things, is like under this first principle of the effects of teammates, or the effects of your teammates and their outcomes. So let's say like maybe we're getting a lot of pressures, and we can say, okay, well, what's the effect of pressures or a certain high pressure rate on a wide receiver's like yards per catch or yards per route run, right? Like let's say we want to measure that, or maybe we want to measure a wide receiver's target share or something like that. So we are essentially saying like, okay, we could use a causal diffusion model and say like okay, learn all of these interactions and learn the noise and try and denoise our situation, and then based on a certain pressure rate and based on this observed yards per route run for wide receivers or tight ends or whatever, then we can say like, okay, is it gonna stabilize at where it is right now, or is it going to regress towards a mean, or is it getting affected a lot by this one thing? Like, is it being propped up by something else, by maybe like there's a really low pressure rate and so it's actually being propped up? So it's almost like an over-expected kind of model. I think this might not fit in the stabilization expert, but I think it's an interesting idea. And then on the flip side, On the flip side, we can say, okay, let's say we have found in the past that, for example, let's say a dot is very consistent. For example, this might not actually be true, but let's say average depth of target is very consistent from week to week and season to season within like an offense or with a quarterback or with a wide receiver or whatever, or even a quarterback tight end pairing or something like that. Under some sort of condition, this feature X is consistent. Given this feature X being consistent, what can we expect other outcomes to be? What can we expect those outcomes rates to be? So maybe someone's getting an ADOT of 14, but their yards per route run is really low or really high. And maybe we can say, okay, based on this number, we actually expect it to regress. So a lot of like the regression, like regress as in like regress towards the mean, I'm thinking based on conditional and interactions and interaction features based on like their offense and maybe even the defense that they play, probably mostly their offense. And I would want to apply the same stuff for defense in the defense world. I don't want to just make offense stats. So this is kind of like the flip side of what I just said. So it'd be kind of two hunches. I would be 25% confident for both of them. Number one, the first hunch would be that consistent principles have an effect on outcomes. And then the other one would be based on a consistent principle. Well, I guess maybe they're the same hunch. I'm kind of just like saying a lot of words, but I'm kind of trying to show you what the absolute, to me, like the limit, like the best case scenario of the stabilization expert could be. This is kind of what I'm thinking. So it's a little, I know I'm not great at speaking about this, but those are my first two hunches, or maybe it's just one hunch. I'm about 25% confident. And then and like you said, for the usual way how baseball does it, I think that's great. Like almost like how biology measures the lethal dosage of like 50%. When does a population, 50% of them die with a given dosage? It's almost like that. I wonder if we can draw some analogies from there, but that's similar to what you said with even and odd attempts when they agree at 0.5. Half signal, half noise. It would be also interesting to say within this expert, like if we could give a bounds, like maybe we look at a sample, like a historical cumulative sample for a given player, and we're looking at their specific outcomes. So like maybe for a pass rusher, it would be pressures per pass play or whatever. And we want to say, okay, here's their cumulative career level. Maybe it's like 10%. And then maybe we can say for like the last 50 snaps that apply to this bin or whatever, they're actually now at a 20% level. And we can give a range and say, okay, well, based on those two features and maybe like everything else, but based on those two features for sure, what do we think the range is going to be? Like, are they at like a peak? Are they going to go down? Are they going to stabilize here? I don't know. Like, can we give a range of their expected outcome? So a lot of this is almost like, I think we could even bring in some time series analysis. I think stabilization would be really interesting for time series. Like we can experiment on different granularities, like maybe a team level for each game, or maybe even each drive or each quarter of a game. We can look at like stabilization, like are they going to stabilize, or is there some sort of pattern, or are they like increasing at a significant rate that we should interpret as their new level, their new stable level. And then we can look at like player level. We can look at position level. We can say like, okay, if a running back gets this rate, this outcome rate, then we can expect them to stay at this outcome rate for a while, given like one or two extra facts. I don't know. I think what I'm saying a bunch of like random things, like very hypothetical and very like pushing the limits of what this expert could do, because basically I think what you said already, you said a lot of really good things that we should definitely go for in your first run of the brief, because like as we keep making experts and we keep having findings, you have a better and better understanding of where to go. So I think it should be players and teams, and then I think it should be judged on like I think for the stability metric, it would be very interesting to look at things that aren't exactly outcomes, but they're football real, because all the downstream models are all going to be trying to predict like football outcomes, but this model can take up the mantle and say, I'm gonna try and look at things that are real, and that are like real things that happen in football and real things that like describe performance, but they're not the traditional outcomes like yards or touchdowns or interceptions or whatever. And that being said, I would also want it to be judged on obviously the next few games, obviously the next season, but also it'd be really interesting to make a prediction for a player's like the rest of their career, their entire career, from like any given point onwards. I think that would be super interesting too."

### The hunches (the CEO's odds; the wording "as read" is Claude's, for the CEO to confirm or edit)

| # | The claim | The CEO's odds | Claude's odds |
|---|---|---|---|
| **H113** | **Teammates prop rates up or hold them down.** A player's rate is partly his teammates' outcomes: a receiver's yards per route run rises when his line allows few pressures. Once teammates' outcomes are taken out, what's left is what stabilizes, and a rate propped up by an unusual teammate condition regresses when the condition changes | 25% (no size given) | As read: 70% that teammates' outcomes move the rate (clear of 0); **25% that the rate with them taken out forecasts the player's next season better than the raw rate**, clearly. F24 found that taking measures over the situation barely changed them, and methods have won 2 of 6 |
| **H114** | **A consistent measure sets where the others regress to.** Given a measure that is consistent for a player under some condition (a receiver's aDOT, within his offense or with his QB), his other rates regress toward what that measure implies, not toward the position's average: a 14-yard aDOT with a low yards per route run should rise. The same holds for defense | 25% (no size given) | As read: **45% that pulling toward what the consistent measures imply beats pulling toward the position's average** on next season's rate, clearly, for at least one rate (offense or defense); 30% for most rates tested; size 1-3% of the error. F37 (one pull-back rate per position was as good as one per player) is the case against; P11 (much of what repeats is role) is the case for |

The CEO's own read: "maybe they're the same hunch." They share a frame, a rate read against a condition. They are kept apart because they can fail apart. H113 conditions on teammates' outcomes, which change week to week. H114 conditions on the player's own consistent traits.

### The CEO's direction

- **Scope:**
  - players and teams, and defense as much as offense;
  - many features and outcomes explored, keeping only those with signal or consistency;
  - outliers tracked, not dropped.
- **What it measures:** things that are "football real" and describe performance but aren't the traditional outcomes (yards, touchdowns, interceptions). The downstream models already chase those.
- **Ranges:** from a player's career level and his recent level in the same situation (a pass rusher at 10% career and 20% over his last 50 snaps): is he at a peak, at a new level, or is it noise? With a range.
- **Time series:** does a rate settle, show a pattern, or rise fast enough to read as a new level? At several levels of detail: each game, drive or quarter for teams; players and positions too.
- **Judged on:**
  - the next few games;
  - the next season;
  - **the rest of his career, from any point on.**
- **The CEO's analogy:** biology's lethal dose for 50% (LD50). Treat reliability as a dose-response curve: the number of attempts is the dose. Read the 50% point, and also how steep the curve is.
- **The CEO's method push:** a causal diffusion model that learns the interactions and the noise, and denoises a player's situation.

### What Claude reads into it (assumptions, limits, a simpler version)

- **The goal fits the analogies.** H114 is credibility theory's "pull toward the right class," with the class set by the player's own consistent traits. H113 is psychometrics' "the score depends on the conditions it was taken in." The LD50 curve is the usual stabilization point drawn whole.
- **The record leans against size, not against direction:**
  - pulling toward the position was as good as pulling toward each player (F37);
  - taking rates over the situation barely changed them (F24);
  - a diffusion model lost to trees (F30), and an autoencoder lost to PCA (F80).
  - So Claude expects real effects that are small.
- **Rest of career** needs two things. One is careers that are finished: the scored set would be players who started 2006-2014, so the survivors aren't the only ones counted. The other is an aging curve, and `aging` isn't built. The career horizon can be scored here as a side output, with its limits stated, or left to `aging` and `career-snaps`.
- **"Football real" measures, a first list** (all free; per play from play-by-play, or per player-week from Next Gen Stats):
  - **Receivers:** target share per route, aDOT, yards per route run, separation (NGS), catch over expected, yards after the catch over expected.
  - **Backs:** carries per run snap, yards after contact.
  - **QBs:** time to throw, aggressiveness (NGS), sacks per pressure.
  - **Pass rushers:** pressures per rush.
  - **Coverage:** throw depth against, catch rate allowed.
  - **Teams:** pressure rate allowed and made, pass rate over expected, shotgun, pace, explosive-play rate.

## Ways to test it (for the CEO to choose; one is exploratory)

1. **The usual way, drawn whole: reliability curves and a simple pull-back** (the base, and the noise ceiling). This is the simple side under rule k.
   - For every measure, players and teams, split-half reliability at 10, 25, 50, 100 and more attempts. Fit as a dose-response curve, like the CEO's LD50: the 50% point plus its slope.
   - Then pull back by k toward the position's average, with empirical-Bayes intervals.
   - Cost: a session. Every other method is scored against this one.
2. **Conditional credibility with drift (tests H113 and H114, and the ranges).**
   - Each rate is pulled toward what the player's consistent measures predict (role table, aDOT, team, QB: H114), after his teammates' outcomes are taken out (H113).
   - A local-level time-series model (a Kalman filter) lets the true rate drift. Career-to-date and recent attempts then mix by how much evidence each has. Its interval says peak, new level or noise: the CEO's range.
   - Run at game, drive and quarter levels for teams.
   - Assumes rates drift slowly and roughly normally. Cost: a session or two.
3. **Exploratory: a denoising model over a player's whole set of rates at once** (the CEO's push).
   - A conditional diffusion model learns to strip noise from a player's observed rates together, conditioned on his teammates' and his offense's rates. A high aDOT can then inform his yards per route run without anyone choosing that pair.
   - Its plain twin is a multivariate empirical-Bayes pull (all rates shrunk together using how they move together, James-Stein in many dimensions). That twin is what it must beat: under rule k a tie goes to the twin.
   - Assumes the joint shape of real rates can be learned from about 10-20 thousand player-seasons. Cost: a session or two of CPU and many choices.
   - The record (F30, F80) says it will likely tie.

**How each is scored:** the rate's own next few games, next season and (if kept) rest of career, against the raw rate and the position's average. Intervals are judged by coverage. Measures are kept only if they repeat (`pcf.validation.consistency`) or forecast. The noise ceiling comes first.
