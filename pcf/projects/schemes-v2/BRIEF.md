# Brief: Schemes v2 (`schemes-v2`)

**Status:** building, 2026-11-09 (agreed 2026-11-09 for the first build: traits and anti-traits, the CEO's "Yes, start building"; scheme against scheme stays in discovery; building, [EXPLORATION.md](EXPLORATION.md)) · **Layer:** expert · **Cadence:** to be decided: likely two experts, in_season and retrospective (rule m; see Inputs)

## The usual way
*Claude, 2026-11-07, before any research.*
- **Charting:** analysts tag every play from film.
  - Offense: personnel (11, 12, 21), formation, shotgun or under center, motion, play-action and run-pass options, run concepts (zone or gap) and pass concepts.
  - Defense: coverage shell (one deep safety or two), man or zone, blitz rate and men in the box.
- **Tendencies:** the tags become rates in neutral situations, adjusted for what the situation expects ("pass rate over expected" is the standard).
- **Grouping:** clustering or a few axes, often labelled by coaching tree.
- **Uses:** scheme fit for players, matchups (a man-heavy defense against an offense that beats man), and what changes when a coordinator changes.

## Analogies
1. **Investment style analysis.** A fund's style can be read from what it holds, or only from how its returns move with known factors. Schemes can likewise be read from charted labels, or from the patterns they leave in results: who gets the ball, where, and when.
2. **Dialects.** Most words are shared; what differs is how often each is used. Dialects spread with people as schemes spread with coaches, so coaching trees work like language families, and a team is often a blend, not one category.
3. *(Added 2026-11-08, for H10.)* **Movers in labor economics.** To tell whether a worker's pay comes from the worker or from the firm, economists follow people who switch firms: what moves with them is theirs, and what stays is the firm's (the "movers" design). Health economists do the same with patients who move between regions, to separate a doctor's habits from a place's. H10 is this design applied to football: coaches and players who change teams.
4. *(Added 2026-11-08, for H15.)* **The realized niche (ecology) and revealed preference (economics).** A species' *fundamental* niche is everywhere it could live; its *realized* niche is where it actually lives, narrowed by competitors and its own limits. Where it's absent though the habitat suits it says something about the species. Economists read preferences and constraints from what people choose, and from what they pass up when it's on offer. H15 reads a team's limits from the plays it passes up.

## CEO hunches
*The CEO's words as said on 2026-11-08, before Claude's research. Each gets a verdict in [`projects/HUNCHES.md`](../HUNCHES.md).*

| # | Hunch, in short | What the usual way says | How the exploration will test it |
|---|---|---|---|
| H9 | Rock-paper-scissors: circles (A beats B, B beats C, C beats A) come either from flukes in close games or from schemes that give one team an edge over another | Matchups are a scouting talking point; models rate teams on one line (strength plus home field) | (1) Are circles more common than strength plus luck produce? (first look below). (2) The sharper test: do offense-style × defense-style pairings predict margins beyond Elo? |
| H10 | What follows a coach or coordinator to a new team is the scheme; what follows a player is their role. Schemes and roles are the consistent parts of play style | Schemes are labels from charting, often by coaching tree; roles come from usage at one team | The movers design (analogy 3): for each tendency, does it move with the play caller, the player, or stay with the roster? |
| H12 | Player performance depends on the fit between a player and a scheme, beyond the talent around them: a QB who moves between two offenses of equal EPA but different tendencies can go from +0.10 to −0.10. The golden goose is a causal process, close to double machine learning | A player's efficiency is theirs, adjusted for teammates and opponents; scheme isn't in the model | Movers again: a player's change in efficiency after a move, against the distance between the old and new schemes, with the talent around them, age and regression to the mean partialled out (double machine learning, with a simple fixed-effects version as the yardstick) |
| H13 | Each scheme breaks or morphs consistently against an opposing scheme: with 5–7 scheme clusters (pass over expected, zone over expected, …), team A sits in its own cluster but, whenever it plays a cluster-3 opponent, it uses a different cluster than normal | Opponent adjustment is one average response: every team passes a little more against a strong run defense | Leave-one-opponent-out: team A's tendencies against cluster-3 opponents against its tendencies in its other games, beyond the average team's response to cluster 3, and whether the same morph repeats (later games, next season, the same coach) |
| H14 | Schemes are like conditions: noise on their own, alpha against another scheme. Each offensive scheme (or cluster) should show almost no association with EPA or winning until a defensive scheme is introduced as the condition | Styles are judged on their own ("pass-heavy offenses are better"); ratings and the market price the main effects | Two parts per tendency and per cluster pair: the main effect on game EPA and margin beyond team strength (expected near zero) and the offense × defense interaction (expected clearly non-zero), against a shuffled-opponent null |
| H15 | Restricted schemes: a team deploys the most favorable plan against each opponent unless its personnel or coaching can't execute it. What a team avoids, especially when it would be favorable, is its **anti-cluster**: the limits of the team, coach or QB. It predicts a performance loss when they attempt it (rare) or when a clearly favorable plan is avoided | What a team doesn't do is read as its style or preference, and only what it does is measured | (a) When a team does use its avoided option, it does worse than teams that use it often, in the same situation; (b) against opponents weak to the avoided option, it falls short of its strength more than other teams do; (c) whose limit it is (coach, QB, roster), by the movers design |
| H11 | Knowing a scheme should predict performance under conditions (for example, a team losing at halftime most likely won't come back), or predict the matchups in H9 | Scheme labels are judged by whether they look right to film people | Do scheme tendencies predict how a team does in a game state, beyond the win-probability model's expectation for that state? |

**H9.**
> "what are the core differences and patterns between teams that beat each other and simultaneously lose to each other, like rock-paper-scissors? Let me explain with an example, if team an overcomes team b, then next week team b plays team c and wins, then next week team c plays team an and beats them too. Now we have a circle of teams outperforming each other. To me, there are two explanations, either the games were really close and one or two of the games are flukes, or the schemes that each team utilizes determines which team would have an advantage over another team."

**H10.**
> "My second hunch is that schemes and roles must be consistent, but it depends on which part of play styles is consistent. Let me explain, if a player leaves one team and joins another, what tendencies and charters follow that player between teams? Those consistencies are what should be known as roles. The same goes for head coaches and coordinators, if they leave a team, what tendencies and charters follow them is what should be considered a scheme."

**H11.**
> "A successful criteria of knowing a scheme could be two things, either the same as my first hunch like rock-paper-scissors or that we can predict performance based on conditions, like if a team is losing at halftime then they will most likely not be able to come back."

**H12.**
> "Another hunch of mine is that player performance is related to schemes and roles in some way that is not explained by personnel performance. Let me explain by example, a quarterback is averaging 0.10 epa per play, then they leave their team and join another offense that is averaging 0.10 epa per play, however this new offense has statistically significant differences in playcalling and charter tendencies. Then, we notice that this quarterback averages -0.10 epa per play on this new and different offense. Most of my discovery hunches that are somewhat original follow this pattern. Essentially, I think that the golden goose in scheme identification comes from a causal process; something close to double machine learning."

**H13.**
> "Another hunch of mine would be that each scheme will break or morph consistently against an opposing scheme. For example, we find 5 or 6 or 7 clusters of scheme across one or more domains - passing over expected or zone over expected - and team a will fit into a cluster but whenever team a plays a cluster type-3 then that team a utilizes a different than normal schematic cluster."

**H14.**
> "Also, one good check is like to add to our schemes expert when exploring is that schemes should be like conditions. Schemes are considered to be noise on their own but schemes become alpha when compared against another scheme. The check essentially means that each scheme itself should show almost zero association with epa or winning, however when two teams' schemes are compared against each other then we should expect a significant result in epa or winning odds. So, if we look at clusters of schemes for offense we would expect each cluster to have no effect on outcomes until we introduce a defensive cluster as a condition."

**H15.**
> "I think I have another hunch! Restricted schemes… a team will always deploy the most favorable scheme and game plan against their opponent, unless their personnel or coaching prowess is incapable of effective implementation. Therefore a team can have a fluid scheme but when we find them avoiding a specific cluster then that team or coaching prowess or quarterback should be assigned the anti-cluster. An anti-cluster describes the limits of a team or personnel or coach, therefore it should predict performance loss when they either attempt that scheme (unlikely) or when they have a clearly favorable plan that is avoided (zone against the run)."

**Scope and the old model (the CEO's words).**
> "This expert would definitely cover both offense and defense respectively."

> "I'm not quite sure what the old model got wrong, I think my exploration was too narrow and I ended up finding nothing reliable."

> "I do not think it necessarily should follow the same exact structure as my old model."

### CEO decisions so far
- **2026-11-08, game states:** in-game states are for diagnosis (H11), never live predictions: "we can use that data for diagnosis but you are still correct that we will not be making live production level predictions."
- **2026-11-08, play callers:** head coaches first, from the schedule, "to ensure we have the correct methodology to discover schemes and discover the exact features to best describe schemes". Coordinators come after, as their own small table (a new data source, signed off in principle; built once the method works).
- **2026-11-08, hunches:** Claude proposes causal ideas in the same pattern; they count as hunches only if the CEO edits them significantly, otherwise they go in IDEAS.md as Claude's.
- **2026-11-08, Claude's ideas C1–C5:** the CEO: "I think your proposed ideas are great!" Kept unedited, so they are Claude's ideas I21–I25 in IDEAS.md, tested in this exploration.
- **2026-11-08, H12 starts with QBs and wide receivers:** "Let's start with QBs and wide receivers for h12 scheme fits."
- **2026-11-08, schemes change within a season:** "A scheme can definitely change when there is a faculty change or a personnel change within a season." So a scheme is measured per *regime*, not per team-season: a stretch of games with the same head coach and the same starting QB (coordinators join when their table exists). A regime ends at a mid-season firing, a QB change, or the season's end.
- **2026-11-09, "clearly favorable" for H15 (the CEO's call):** "Clearly favorable should be defined as what teams usually do against that opponent combined with standard football strategy like running the ball more when leading or playing zone coverage against a play that has a high chance of being a rushing attempt." So the favorable plan for a play is the league's expected choice there: a model of what the average team does, given the situation (down, distance, field position, score, time, the offense's run chance and personnel on the play) and this opponent's normal tendencies. A team avoids an option when it uses it less than that expectation.
- **2026-11-09, direction after the exploration (the CEO's call):** traits and anti-traits first; scheme against scheme stays in discovery. In the CEO's words (this also extends H9):
  > "I think we should probably start with traits and anti-traits, because like you said, we have the most evidence for that. However, I also think that we should do more discovery with the scheme against scheme, because I think there has to be some sort of pattern that occurs when you have three teams and each one beats the other one, and you can't really tell who's the best out of the three. And I would assume that it's either completely random or the outcomes are chosen by schemes, because one team is simply better matched up against another team and they can exploit weaknesses, or their weaknesses are not exploited. And therefore, you know, you have this like rock, paper, scissors ring, the circular winning pattern where one team can beat another, but that team doesn't mean they're going to beat a different team. [...] See if we can find some sort of way to explain how there can be so many different teams that should be able to beat another team, or maybe that they don't beat a team, but so many different patterns where there's a mixture of performance where you would expect a team to play really well against someone, but they actually play far worse than expected. And hopefully that would be explained by schemes. But I think definitely to start, let's first go through traits and anti-traits."
  - **Claude's reading of the discovery thread (assumptions, stated first):** the CEO offers two explanations for circles and surprise games: "completely random" or "chosen by schemes". There is a third: matchup effects that are real but not about schemes (one team's left tackle against one pass rusher, injuries that week, weather). So the first question isn't "do schemes explain surprises?" but "is there anything matchup-specific to explain at all?" The cheapest test is **rematches**: division rivals play twice a season. If team A beat its expectation against team B in the first game, does it again in the second? That repeat is the ceiling on what any matchup explanation, schemes included, can ever add. Then: how much of that ceiling the scheme terms (F7, F9) reach.
  - **The CEO, later the same day (2026-11-09), sharpening it to units:**
    > "I think another good way to help the schemes versus schemes, rock, paper, scissors analogy is maybe it's not an entire team beats an entire other team, and then you have the rock, paper, scissors, circular winning strategy, but rather it's offense A does way better against defense B, and then offense A doesn't do very well against defense C. Then, offense D plays well against defense C and then offense D plays poorly against defense B."
    - *Claude's reading:* the circle is between an offense and a defense, not two whole teams. That is the level H14's test already used (an offense's EPA against a defense, beyond both units' strength: F7, held-out r +0.028), so the tests so far do address this version. What they haven't asked is how much unit-against-unit structure exists at all. So the rematch ceiling runs at this level: when offense A beats its expectation against defense B in their first meeting, does it again in the second?
  - **What the exploration already says:** circles are rarer than chance (18.1% against 21.2%), and style pairings predict the miss against the close at r +0.035. So the expectation is a low ceiling; the rematch test says how low.
- **2026-11-09, anti-traits (the CEO's calls, after the traits slice):** "D1 should be pass and shotgun plus defense first. D2 should be the team's gain from that option in its next game." So:
  - **Which:** offense pass and shotgun, live; and defense man coverage, two-high shells and blitzes, from participation, so from finished seasons only (rule m).
  - **Judged on:** the team's gain from the option in its next game: how much better its plays go when it takes the option than when it doesn't, against the league's usual gain. The anti-trait claim: a team that avoids an option gains less from it.
  - *Claude's assumptions, stated before building:* the anti-trait is expected to be faint (pregame avoidance carried +0.03 and +0.02 per sd for pass and shotgun in F18); the defensive ones can only help the next season's forecasts; if a variant doesn't keep F18's sign on held-out seasons it is recorded as noise.
- **2026-11-09, after the anti-traits: schemes are conditional (the CEO, restating H14 as the core of the project):**
  > "Okay, so how much are we validating a scheme as something that needs to be conditioned upon another scheme to show outcome differences? So what I mean is schemes must be compared against other schemes, or else a scheme on its own in a vacuum basically carries no information. It just describes tendencies and charters, and just it's diagnostic. However, when you compare one player that fits into a scheme, or maybe I shouldn't say a player, but one offense that fits into a scheme and then another offense that fits into another scheme, and those schemes don't on their own make any predictions, but when you take an offense in their scheme and compare it to a defense in their scheme, then that does show a difference in outcomes. Maybe that defensive scheme plays well against that offensive scheme. I would think that that's like one of the most underlying fundamental factors of schemes. I think we should still try to investigate if that is solvable, if we can discover any kind of features that fit that pattern. Because I think schemes are inherently conditional. Like a scheme on its own means nothing, but a scheme compared to another scheme actually gives an outcome. Just like genetics on their own do explain, like, this isn't a perfect analogy, but genetics on their own do explain some variants, but genetics don't create a phenotype unless you have an environment to interact with your genetics. So you need genetics and environment, obviously, to create evolution or to create, like, evolving phenotypes. But basically, I don't know if there's a better analogy, but generally, schemes are conditional. That's what I really want to look for. That's what I really want to find in the data. I want to find some sort of pattern, some sort of feature that we could leverage to say, like, hey, this team is going to perform well against this defense, but perform not very well against this other defense, regardless of how good the defenses are, strictly just on the types of defense."
  - *Claude's reading:* this is H14 (and H9 at unit level), now named the project's central question. The target is an offense's result against a defense **beyond both units' strength**, explained by their styles only. The method is to be chosen next (options given to the CEO the same day).
  - **The CEO's order, the same day:** "I'd love to try all of those options. You did a great job creating those options, thank you! We can start with a, then b, then e, then c, then d!" So:
    - A, the rematch ceiling;
    - B, the play-by-play matchup map, then one game test;
    - E, the CEO's candidate matchups;
    - C, matchup traits learned from results;
    - D, the wider pair scan (the tempting-but-bad option, run as a test rather than argued).
  - **A, done 2026-11-09 (EXPLORATION F20):** a real within-season pairing part, about 9% of what strength leaves, which doesn't carry to next season; the tendencies tried so far reach about 1% of it; the raw first-meeting residual doesn't beat the close.
  - **A2, the CEO's look-alike test (same day, while B ran):**
    > "I think another way to think about the rematch pattern (a) is that it should also hold for teams that play against another opponent that fits the same scheme as past opponents. This will rule out the option that a rematch simply describes a good team beating a bad team whereas different teams that fit similar styles share similar outcomes in the same direction after accounting for elo or average epa."
    - *Claude's reading:* F20's residual already removes both units' season strength, and the same offense's results against *other* defenses don't repeat (the null is near zero), so "good beats bad" isn't what A found. The look-alike test adds something different: whether the pairing part travels with the opponent's *style* (a scheme effect) or stays with the specific opponent (players, health, game plan). It also checks strength look-alikes directly, as the CEO asked.
  - **B and A2, done 2026-11-09 (EXPLORATION F21, F22):** the play-by-play map has real interactions (passing into 8-man boxes, play action into a blitz), but carried to games through teams' call mixes or their own splits they explain nothing; and results don't follow the opponent's style. So the within-season matchup part belongs to the specific opponent, not to scheme types. Next in the CEO's order: E (the CEO's candidate matchups), then C, then D.
  - **E, the CEO's candidate matchups (H16) and a caution (H17), same day:**
    > "Some pairings that I think might be effective are cover two tendencies against passing offenses that throw the ball deep consistently. Another one would be a team that spreads the ball around to multiple players and multiple skill positions will perform well against a defense that puts extra players in the box. Another one might be a defense that blitzes more than average will perform poorly against an offense that has a short average depth of target. Another one could be a defense that prefers to utilize defensive linemen that are heavy (weight) will perform well against a team that runs the ball more than expected. I think another thing to keep in mind is that schemes can also be deployed by coaches to mask player deficiencies just in the inverse like a coach will focus on showcasing their good players. I don't know if there is a good analogy for that type of conundrum, but we need to be mindful that coaches are trying to maximize their outcomes with their scarce resources."
    - *Claude's assumptions, stated before running:* each pairing's direction is fixed in advance; with four tries the bar is 1.25% one-sided each. Two-high × deep and blitz × depth were among F7's 77 untargeted pairs, where none stood out, so the expectation is faint at best. Heavy DL needs a new measure (listed weight of the linemen on the field, from participation, 2016+), and so does target spread (effective number of receivers).
    - *An analogy for H17:* **confounding by indication** in medicine. Doctors give the strongest treatment to the sickest patients, so the treatment can look harmful in raw data. Coaches give the "treatment" (a scheme) to the rosters that need it, so a style's effect is tangled with the weakness it was chosen to hide. Economics has the other half, **comparative advantage**: with scarce resources, each team specializes in what its players do relatively best. H15's anti-traits are one way in: what a team avoids marks the weakness.
- **2026-11-08, regimes (the CEO's call):** "A change in coach or starting quarterback should define the end of a regime, plus I think if that finds very little patterns then we can look for high player turnover from season to season." So the regime is head coach plus starting QB; high roster turnover between seasons is the fallback boundary if that finds little.

### First look at H9 (2026-11-08, discovery only)
[`explore/cycles.py`](explore/cycles.py), 2016–2024, 2,467 games, 4,495 triangles of teams that all played each other in a season.

| | Share of triangles that are circles |
|---|---|
| Actual | **18.1%** |
| Coin flips | 25.0% |
| Elo's win chances, games independent | 21.6% (20.7–22.6%) |
| The close's win chances, games independent | 21.4% (20.3–22.5%) |
| Elo's chances plus a hidden season strength per team, sized to match the real spread of wins | 21.2% (20.1–22.3%) |

- **Circles are *rarer* than strength plus luck predicts, not more common.** Real seasons are more ordered than any of the chance models. My expectation (about as common as chance) failed in the other direction. The likely reason: strength differences are larger, or move more within a season, than the forecasts know. That's a team-strength finding (it echoes elo#F13), not a scheme one.
- **Flukes, partly:** games inside circles are closer than games inside ordinary triangles (54% decided by 7 or fewer, against 47%; at least one game decided by 3 or fewer in 62% of circles, against 55%).
- **What it doesn't rule out:** a circle uses one bit per game (who won). A scheme edge worth a point or two would barely change who wins, so it can't show here. H9's real test is on margins (the table above, column 3, test 2).

### Claude's ideas, in the CEO's causal pattern (2026-11-08; the CEO kept them unedited, so they are IDEAS I21–I25)
*My expectation is given with each, so the result means something.*

| # | Idea | Design | My expectation |
|---|---|---|---|
| C1 (I21) | **Stayers for coaches.** When a head coach changes but the QB and most starters stay, the tendencies that change (against teams that kept their coach) are the coach's; those that don't are the roster's | Difference in differences: a mirror image of H10's movers design. The two must agree | Pass rate over expected, pace, shotgun rate and 4th-down aggressiveness move with the coach; efficiency mostly stays with the roster |
| C2 (I22) | **QB coverage fit**, a player-level rock-paper-scissors. A QB's efficiency against man versus zone is a lasting trait, and that split times the opposing defense's man rate predicts the QB's game beyond both teams' ratings | Participation coverage, 2016–2025 (retrospective, so diagnosis and next-season priors) | Small but real. It has far more data than circles: every dropback, not one bit per game |
| C3 (I23) | **Receiver depth fit.** A receiver's target depth moves with them (role), but their efficiency per target depends on whether the new offense throws deep: deep threats lose most when they move to a short-passing scheme | Movers: many receivers change teams each year | The best first test of H12's method: the most movers, so the narrowest intervals, before QBs |
| C4 (I24) | **A learning curve.** A player new to a scheme (moved, or a new coach arrived) plays below their eventual level for the first few games, more so the further the new scheme is from the old | Efficiency by games since the change, against scheme distance | A small dip that fades by midseason; useful for early-season projections |
| C5 (I25) | **Tendencies settle fast; efficiency doesn't.** A new head coach's tendencies settle within about 4 games, long before efficiency does | `pcf.validation.consistency` by games into a coach's tenure | Pass rate over expected repeats strongly after 3–4 games. It sets how much a live scheme expert trusts this season against the coach's history |

**The null every scheme-fit test has to beat:** a placebo move. Give each mover the scheme distance of a random team instead of their real one; the effect has to vanish. Regression to the mean shows up just as strongly in the placebo, so it can't fake a result.

## The question
How does each team play, on offense and on defense, in ways that belong to its play caller rather than to its players or to luck? And do those styles explain who beats whom and how teams do in particular game states?

## Why it matters
- **Matchups:** if styles interact (H9), side and total forecasts gain a term no rating has.
- **Coaching changes:** when a coordinator moves, we'd know what moves with them, the moment the hire is announced (offseason).
- **Roles:** the same design tells which player tendencies are theirs (H10), feeding `roles-archetypes`, player projections after a trade or signing, and the consistency meta process (IDEAS I20).
- **Game environments:** pace, pass rate and how a team plays when behind feed totals, fantasy and props.

## Terms
- **Standard terms used:** EPA, pass rate over expected, neutral situation, personnel, play-action, man and zone coverage (`docs/GLOSSARY.md`).
- **New terms (draft):**
  - **Tendency:** a rate in comparable situations (e.g. shotgun rate on 1st and 10 in a one-score game), adjusted for what the situation expects.
  - **Scheme:** the tendencies that move with a play caller when they change teams (H10).
  - **Role:** the tendencies that move with a player when they change teams (H10).
  - **Roster trait:** the tendencies that stay with the team when the play caller leaves.
  - **Circle:** three teams that each beat one of the others in the same season (H9).
  - **Mover:** a play caller or player who changes teams between seasons (or mid-season).
  - **Regime:** a stretch of a team's games with the same head coach and the same starting QB (later, the same coordinators). A scheme is measured per regime.
  - **Morph:** how a team's tendencies change against one kind of opponent, beyond how the average team changes against it (H13).

## Builds on
| Project | What we use | Why |
|---|---|---|
| `elo` | ratings in the `margin` history (decision 0021); its margin misses | Matchup effects are measured on what Elo misses; the ratings set "expected" |
| `tag-tables` | situation tags (score, clock, down and distance) | Neutral situations and game states (H11) |
| `participation` | snap shares | Which players moved, and how much they played (H10's player side) |
| `elo` H5, H6 | "strength is conditional: … against heavy zone coverage, when trailing at halftime" | H11 is H5 measured through schemes |

**Already tried:** `schemes-v1` (`old/code/Schemes_Model.ipynb`): over-expectation features, then PCA, then clustering into team schemes. Little usable signal. The exploration reads it first (read-only) to see why. CONSISTENCY.md: "finishing" repeats (r 0.28 week to week, 0.22 season to season), a candidate for H11.

## Assumptions
- **Tendencies can be measured from free data.** Play-by-play has shotgun, no-huddle, pass rate over expected, pass depth and direction (1999 on). FTN charting has play-action, motion, blitzers and men in the box (2022 on, about two weeks behind). Participation has formation, personnel, coverage and routes (2016–2025, after the season only).
- **Play callers can be identified.** nflverse has head coaches only. Coordinators and who calls plays aren't in our data (an open decision below).
- **Enough movers.** Each season perhaps 10–20 coordinators and many players change teams. Coordinators are few, so intervals will be wide.
- **For H11 (Claude's assumptions, stated first, 2026-11-09):**
  - *"Can't come back" is already in the win-probability model.* A team trailing at halftime already has a low win chance. The hunch matters only if schemes predict the result *beyond* that chance, so the test uses the closing line's win chance at halftime, which knows both teams' strength.
  - *Win or loss is blunt:* one bit per game. The second-half margin beyond the close carries far more.
  - *Tendencies must be known before the game* (the regime's earlier games), so the game's own script can't leak in.
  - *My expectation:* pass-avoiding, slow and heavy teams come back less often when trailing (tying to H15); small effects otherwise.
- **For H12 (Claude's assumptions, stated first):**
  - *Movers aren't random.* Players move because they declined, got expensive or were cut. A QB at +0.10 who moves would drift down anyway (regression to the mean, age). Double machine learning removes only what we measure; the main confounders to measure are prior efficiency (shrunk), age, the new and old supporting cast *without* the player, and opponents.
  - *The new offense's +0.10 includes its old QB.* The supporting cast has to be measured without the position that changed.
  - *Scheme distance must be known before the move:* the new team's tendencies from before the player arrived, or the new coach's at their previous team. Otherwise the player's own play shapes the "scheme".
  - *Few movers, noisy outcomes.* QB EPA per play needs hundreds of plays to settle; a few dozen QB moves since 2006. Intervals will be wide; receivers and backs move far more often.
  - *Simpler alternative first (rule k):* a movers regression with a player effect, a team-season effect and one fit term (player style × scheme distance). Double machine learning must beat or match it.
  - *QBs and receivers together (the CEO's choice):* receivers first test the method (many movers, narrow intervals), QBs carry the stakes. A receiver's "move" also includes a new QB throwing to them, so the QB is part of the receiver's supporting cast.
- **For H13 (Claude's assumptions, stated first):**
  - *"Normal" must leave the opponent out.* Team A's usual cluster is measured from its games against other clusters, or the morph is partly measured against itself.
  - *The opponent's cluster must be known before the game:* from the opponent's earlier games that season (or regime), never from the game itself.
  - *The hunch is the team-specific part.* Every team bends against some opponents (more passing against a run-stuffing defense); that average response is ordinary opponent adjustment. H13 says team A bends *its own way*, and does it again. So the test removes the average team's response to cluster 3 first.
  - *Few games per cell.* About 17 games across 5–7 opponent clusters is 2–4 games a cell a season. A morph has to be pooled across a coach's tenure to be measurable, which ties H13 to H10: if a morph is a choice, it should follow the play caller.
  - *Simpler alternative first (rule k):* no clusters. Each team (or coach) gets a slope: how its pass rate over expected moves with the opponent's defensive tendencies. Consistent slopes are the morph. Clusters earn their place only if they beat the slopes.
  - *My expectation:* the average response is clearly real; the team-specific morph is small and mostly noise, except for a few game-planning coaches, where it repeats.
- **For H14 (Claude's assumptions, stated first):**
  - *"No association" has to mean beyond team strength.* Good offenses pass more and play faster because they are good, and teams that lead run more. A raw tendency will correlate with EPA through talent and game state. The claim is about the part left after the ratings (Elo, the close, season-to-date EPA).
  - *A main effect isn't a failure of the useful part.* A tendency with a main effect is partly a talent proxy; one with neither a main effect nor an interaction is noise; one with only an interaction is a condition in the CEO's sense. Every tendency gets one of those three labels.
  - *Many pairs are tried*, so the interaction is judged against a shuffled-opponent null (the largest effect among all pairs when opponents are shuffled), not one pair's p-value.
  - *Tendencies must be known before the game:* season-to-date, never the game's own plays (the game's own tendencies are partly the game script).
  - *Simpler alternative first:* continuous offense × defense products before clusters; clusters must beat them.
- **For H15 (Claude's assumptions, stated first):**
  - *Teams choose rationally, and game theory says how to read it.* A team mixing two options well makes both about equally good at the margin (a mixed strategy), so *avoiding* one isn't a limit by itself: it may be a style or a bluff. It's a limit only if the avoided option does *worse* when the team uses it. So test (a) is the key one: avoidance plus a penalty is a limit; avoidance without one is a preference.
  - *"Favorable" needs a definition that doesn't use the team itself:* the CEO chose (2026-11-09) what the average team does against this opponent, combined with standard football strategy for the situation (see CEO decisions). It measures the usual choice, not whether the choice works, so test (a) still has to show that avoiding it costs something.
  - *Rare uses are selected.* A spread team goes under center mostly on short yardage and at the goal line; a zone team plays man in the red zone or when desperate. Every comparison has to be within the same situation (down, distance, field position, score), against teams that use the option often.
  - *The opponent chooses too:* a defense may sit in zone *because* the offense beats man. What the opponent did is part of the situation.
  - *Clusters were noise at game level (F12),* so the simpler version comes first: an anti-trait per tendency (the options a team uses least against the league's rate), then clusters only if they beat it.
  - *Whose limit:* the same split as F3 (coach, QB or roster), from what happens to the avoidance when the coach or QB changes.
  - *My expectation:* (a) a penalty for some constraint-like options (under center for shotgun-heavy QBs, heavy personnel for spread offenses, man coverage for zone-heavy defenses), little for strategic ones (no-huddle, tempo); (b) small, like H14's faint signal.
- **A tendency is a choice, not a forced response.** Shotgun when trailing is the game state talking; neutral situations and an expected-rate adjustment are meant to remove that.

## Goals
1. A map of tendencies: which ones are consistent (CONSISTENCY.md), and whose they are (play caller, player, roster).
2. A test of matchups on margins (H9), of game-state performance (H11, diagnosis only), of scheme fit (H12) and of morphs against opposing schemes (H13).
3. Scheme features for downstream experts, saved like Elo's ratings. **First build (CEO, 2026-11-09): traits and anti-traits.** Per team-week, known before kickoff: each tendency against the league's usual choice (the trait), shrunk toward the coach's history; low use is the anti-trait (F17, F18). *Built 2026-11-09: traits RESULTS R1–R4, anti-traits R5–R9.*
4. Discovery continues on scheme against scheme (H9, H14): the rematch ceiling first.

## Tests
*Draft, to agree with the CEO.*
- **H9, matchups:** an offense-style × defense-style term improves held-out margin (or total) forecasts over Elo, with an interval clear of zero; the shuffled-pairings version doesn't.
- **H10, whose is it:** for each tendency, the share that moves with a play caller (and with players) across movers, with an interval. A tendency counts as **scheme** if it moves with the play caller clearly more than it stays with the roster.
- **H12, scheme fit:** among movers, the distance between the old and new schemes predicts the change in a player's efficiency beyond prior efficiency, age and supporting cast, with an interval clear of zero, and in the direction the fit term says (the same move is worse for some styles than others); the shuffled-scheme version shows nothing.
- **H13, morphs:** a team's (or coach's) deviation from its own normal against an opponent cluster, beyond the average team's deviation, repeats out of sample (the second half of a season, or the next season under the same coach) with an interval clear of zero; with shuffled opponent clusters it doesn't. If it holds, a morph term improves held-out game-environment forecasts (pass rate, pace) or margins.
- **H14, schemes as conditions:** per tendency (and per cluster), the main effect on game EPA residuals beyond strength is near zero, while the offense × defense interaction is larger than the shuffled-opponent null's 95th percentile.
- **H15, anti-clusters:** (a) plays from a team's avoided options have lower EPA than the same options by frequent users, in the same situation, with an interval clear of zero and a shuffled-team null; (b) a team's avoidance × the opponent's weakness to that option lowers the team's EPA beyond strength, held out; (c) the avoidance follows the coach or the QB, not chance.
- **H11, conditions:** scheme tendencies predict a team's result from a given game state (e.g. trailing at halftime) beyond the win-probability model's expectation for that state, on held-out seasons.
- **Traits and anti-traits (the first build), draft:** each trait repeats (CONSISTENCY.md); known before kickoff, it predicts the team's own next-game tendencies (pass rate, pace, depth) better than the league average and a rolling mean; the anti-trait term (avoidance × the play's usual choice) keeps F18's sign on held-out seasons; the shuffled-team version of each shows nothing.
- **Signal and no noise** (VALIDATION.md): beats its shuffled self; the no-noise target to be proposed after the exploration (CEO approves).
- **Failure looks like:** no tendency moves with play callers more than chance, and neither matchup nor game-state test finds anything. Then schemes are roster traits, and that is itself a finding for `roles-archetypes`.
- **Seasons:** 2006–2024 for play-by-play tendencies, 2016–2024 with participation, 2022–2024 with FTN. The vault (2025) stays closed.

## Inputs and outputs
- **Inputs:** play-by-play (known after each game), FTN charting (kickoff + 14 days), participation (after the season: retrospective only), snap counts, head coaches from the schedule, and possibly a play-caller table (decision below).
- **Outputs (draft):** per team-week, offense and defense tendencies (live), and per team-season the scheme, role and roster parts (retrospective); matchup terms if H9 holds.
- **Cadence:** the live fields and the post-season fields probably make two experts, as with Context and VOE (rule m).

## How it will be used
Matchup terms for sides and totals; coaching-change priors in the offseason; scheme context for `roles-archetypes` and player projections; game-environment features for fantasy and props.

## Plan
Exploration first, time-boxed: (1) why v1 found little; (2) the tendency list and its consistency, per regime (I25); (3) the movers and stayers designs with head coaches (H10, I21); (4) matchups on margins (H9) and morphs (H13); (5) game states (H11, diagnosis); (6) scheme fit for receivers and QBs (H12, I22–I24). The ladder after: tendencies as plain rates → shrunk rates → a few axes → (only if it beats them) clusters. **After the exploration (2026-11-09):** (a) agree this brief around traits and anti-traits; (b) build them up the ladder; (c) in discovery, alongside: the rematch ceiling for scheme against scheme, then the coordinator table.
