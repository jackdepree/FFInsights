# Brief: VOE, value over expected (`voe`)

> The CEO's pick, 2026-11-19, in the strategy chat. This file gets the kickoff, the hunches, the exploration's changes and the agreed brief; the build happens in its own session, from this file.

**Status:** exploring (2026-11-19: kickoff written; the CEO's direction and hunches H69-H74 recorded with odds; Claude's expectations written before the first run) · **Layer:** expert · **Cadence:** open (see "Open")

**The name.** The CEO, 2026-11-19: "I don't want to call it version 2, I just want to call it VOE." So the project is `voe`. The registry's two older entries, `voe-live` and `voe-retro`, stay as the two cadences VOE may come in (rule m); the brief decides which one this project builds first.

## What the CEO asked for
*Word for word, 2026-11-19.*

"Okay, well, I would like to start working on the value over expectation model. And I think we can start by working on basically like a version 2. I don't want to call it version 2, I just want to call it VOE. But we can basically start by just trying to recreate responsibly recreate what I did in the past. Kind of go along the same assumptions, the same constraints, same limitations, same advantages. Build that out, or at least explore it. Start the brief. Obviously, this is the strategy and vision. So we're just going to be looking at the brief and exploration. But I think what we could also do is we could also brainstorm the gaps that this specific model has. Like what are the constraints when we use just a simple MLP or a simple neural net to predict everything? What are the constraints when we use historical EPA for every position? What are the constraints when we use either maybe we're looking at every single possible position on the field, or we're just clumping everything into like a latent space and then predicting it? So like if we first kind of do a brief, kind of do an exploration, and then we're also like thinking about it in like a machine learning perspective and a data science perspective and a causal perspective, like how how does each thing that we decide, each tool we decide to utilize, each technique we deploy, how does that change the output? Plus, if we change that, coupled with maybe a couple other like multiple other changes, how can we make a a sister model or like a cousin model that kind of does the same thing but in a slightly different way, and hopefully captures different signal, captures like a different variable, a different feature, and has a different output, but maybe it might be interpreted in the same family, in the same genus of like idea, like trying to measure, okay, if we account for as many things as we want to account for, and then we make a prediction, and then we also maybe we even do some propensity modeling, maybe we even do some double machine learning, maybe we even do blah blah blah blah blah, like a ton of other things. If we account for all these things, we make an expectation and an estimate, and then if we measure that estimate against every single person's participation and their own outcomes, does that give us a reliable measure of player value? Does that give us like an advanced metric of plus minus? Does that give us an estimation of wins above replacement? Does that give us like this causal estimate of this person is contributing this amount? That's just how I want to start off. What do you think?"

**What the ask contains, in four parts:**
1. **Recreate the old VOE responsibly**: its assumptions, constraints, limitations and advantages, under PCF's rules.
2. **Map its gaps** from three angles (machine learning, data science, causal): what each decision does to the output, alone and in combination.
3. **Design a family of sister and cousin models** that measure the same idea differently and catch different signal.
4. **The football claim underneath:** an expectation that accounts for enough, measured against each player's own participation and outcomes, gives a reliable player value: a plus-minus, a wins above replacement, a causal "this player contributes this much".

## The usual way
*Claude, before any research.*

Most public football player value gives credit only to the players who touch the ball: a QB's EPA per dropback or completion over expected, a back's rushing yards over expected, a receiver's yards per route run. Linemen and defenders are left to film grades, which come from people charting every snap. The few attempts to cover all 22 players come from academic work, such as nflWAR (Yurko, Ventura and Horowitz, 2018), and from plus-minus borrowed from basketball and hockey. nflWAR fits expected points and win chance per play, then splits each play's EPA among the passer, the receiver, the rusher and the offensive line (through the run gap) with a mixed model, then subtracts a replacement level and converts points to wins. Plus-minus regresses each play's result on who was on the field. In football it struggles more than in basketball, because 22 players share every play and starters rarely sit, so their effects are hard to tell apart.

## Analogies
*Claude. Ways to look at it, not answers.*

1. **Regularized plus-minus in basketball (RAPM).** Ten players share every possession, so the outcome is regressed on all ten at once, and ridge shrinkage pulls everyone toward average until the data says otherwise. Two lessons came out of it.
   - Players who always share the floor can't be separated, however clever the model.
   - The best versions add a prior from box-score stats, which settles them years sooner.
   - What it suggests looking at: which of PCF's 22 slots are ever apart, such as the left tackle and the left guard or the QB and his WR1. Also how much a stats prior steadies the ratings.
2. **Gene knockouts in biology.** To learn what a gene does, you switch it off and watch what changes. Two catches have to be designed around.
   - Redundancy: switch off one gene and a backup covers for it, so a gene that matters can look useless.
   - Epistasis: a gene's effect depends on which other genes are present, so its effect can't be stated without the background.
   - Your old VOE is a knockout experiment. It switches a slot off by setting it to the average and measures the change.
   - What it suggests looking at: what the knocked-out player is replaced by (the average, his actual backup, or a replacement-level player), and whether a receiver's value depends on his QB.

## What the old VOE did
*Claude's close read of `old/code/VOE_Model_Training.ipynb` and `VOE_Model_Prod.ipynb`, 2026-11-19. `old/` is read-only; nothing there was changed.*

**The pipeline, in five steps:**

1. **The context model's leftover.** Every play's EPA, less what the old context model expected from the situation: `residual_epa`. The context model's inputs included predicted pressure, time to throw, rushing yards and yards after catch. The play's own variance encoder was computed on all the data (a leak noted in `docs/OLD_INVENTORY.md`).
2. **A rating for each player, on each play** (`plyr_epa_forecaster`).
   - **Inputs:** his last 50 snaps up to the play. These cover the average and spread of the residual EPA of plays he was on, yards, pressure and the context model's predictions, plus his career residual EPA per snap.
   - **Target:** the summed residual EPA of his next 6 snaps (the function's default is 3).
   - **Model:** XGBoost.
   - **The catch:** the play's residual EPA is the same number for all 22 players on it. So a player's rating is a running on-field plus-minus, which he shares with every teammate on those snaps.
3. **Slots.** Each player gets a depth-chart label (QB1, WR2, CB3, LT1, …; about 90 slots), ranked by his average depth. The ratings are pivoted so each play is one row with about 90 columns, 0 when a slot is empty.
4. **The VOE model.** It predicts the play's residual EPA from the slot ratings. Pass and run plays had separate models: ridge by default, with an MLP (two layers of 200) and XGBoost also tried. Some versions added the context model's predictions as inputs.
5. **The knockout.** Groups of slots are set to their average rating, and the model predicts again (`voe_y0`). Two outputs were summed per player and game:
   - **expected VOE** = the prediction with him − the prediction with his slot at average. It never uses what happened on the play. It's his rating times how much his slot matters. With ridge it is exactly the slot's coefficient × (his rating − the slot average).
   - **realized VOE** = what happened (residual EPA) − the prediction with his slot at average. Every player on the play gets nearly the whole play's leftover, so the credit adds up to about 22 times the play.

**What it found** (the notebooks' own outputs; random splits, so optimistic):
- **Week to week:** realized VOE repeats 0.24 and expected VOE 0.32. Fantasy points repeat 0.49.
- **Against the next week's fantasy points:** realized VOE −0.06 and expected VOE 0.02. In the training notebook, the summed short version had 0.32, which is mostly volume (more snaps, larger sums).
- **How much of the play the slot ratings explain:** an early random split reported 0.80 (pass) and 0.62 (run). That is far too high for ratings known before the snap, so something leaked. The later 5-fold version reported 0.03 to 0.06.
- **The top and bottom of the career list:** the top is the 2016–2018 Patriots' offense (Thuney, Cooks, Brady, Andrews, Mason) and the bottom is the Vikings' defenders (Harrison Smith, Kendricks, Barr). The list measures team on-field results, and defenders carry the offense's sign. The line that would flip it is commented out, so a negative number for a defender means good.

**Its assumptions, constraints, limitations and advantages**, as the CEO asked:

| | |
|---|---|
| **Assumptions** | <ul><li>A play's result, less the situation, belongs to the players on the field.</li><li>A player's recent on-field results say how good he is.</li><li>A depth-chart slot stands for a role.</li><li>Setting a slot to the average is a fair "without him".</li><li>A player's value is the same across plays of one kind (pass or run).</li></ul> |
| **Constraints** | <ul><li>Needs participation (who was on the field), which is post-season only (2016–2025).</li><li>Depth charts are weekly, and daily from 2025.</li><li>EPA is the only outcome.</li></ul> |
| **Limitations** | <ul><li>Teammates share one number per play, so their ratings are nearly alike (collinearity built in).</li><li>The 50-snap windows overlap, so the ratings repeat week to week partly by construction.</li><li>Defense has the wrong sign.</li><li>The knockout's "average player" puts lineups in front of the model that it never saw.</li><li>Expected VOE ignores the play's result, and realized VOE hands everyone the whole play.</li><li>Random splits everywhere, and hyperparameters chosen on the test rows.</li><li>The scale is sums per game, so it rewards volume.</li></ul> |
| **Advantages** | <ul><li>All 22 positions, linemen and defenders included, where public metrics stop at the ball.</li><li>Uses who was actually on the field.</li><li>The situation is taken out first.</li><li>Asks the right causal question ("what would this play be without him?").</li><li>Pass and run apart.</li><li>Its own note already proposes the two VOEs PCF later split into cadences: a prospective one from tendencies, and a retrospective one that splits each play's leftover by who did what (sacks, catches, blocks).</li></ul> |

## What PCF already knows
*From finished work and explorations; the exploration and build must use these.*

- **The expectation now exists as context-live** (done 2026-11-19).
  - For every play, it gives 17 expected outcomes from the situation and both sides' calls, knowing nothing about who the players are, "so later experts credit players only with the difference" (its brief). Pressure, sack, time to throw, completion, depth of target, run yards, success, first down and touchdown are among them.
  - It has no expected EPA; the old VOE's base was EPA less expected EPA. A recreation either builds expected EPA from the situation (nflverse's EPA already takes out down, distance, field position and time), or uses context-live's outcomes.
  - It's known 14 days after kickoff.
- **Players' context differs** by about 0.7 points of success rate (context-live, the CEO's H66). Some players are sent on for worse situations, so an on/off split without context blames them for it.
- **Who was on the field:**
  - True participation covers 2016–2025, after each season.
  - participation-live and participation-late give an in-season map with a chance per player per play.
  - A season plus-minus built from the in-season map correlates only 0.42 to 0.50 with the true one (participation-live#R6). An in-season VOE would be a blurred copy.
- **Plus-minus has been tried in PCF, on pass rate** (player-pace).
  - It repeats for tight ends, receivers and backs (0.42 to 0.62 week to week) and follows tight ends and receivers to new teams.
  - QB and OL plus-minus is weak (0.09 to 0.13), because starters rarely sit. The same will bite VOE.
- **Causal methods have been tried on teams** (team-efficiency, the CEO's H41 to H44). Double machine learning with game state added +0.2% to +0.4% to team ratings. Plain ridge on EPA was close behind.
- **Retro 1's pattern P4:** cleverer weighting, cleaning or methods mostly tie the simple version; they rarely hurt. A pattern, not a finding, but it sets expectations for the propensity and double machine learning cousins.
- **The old outputs exist** (`old/data/voe_weekly_data.xlsx`): a benchmark for where a new VOE agrees and differs (`docs/OLD_INVENTORY.md`).
- **The ported cleaning code exists:** `pcf.data.clean.players` (who was on each play, every listed player), `pcf.data.clean.depth_charts` (time-ordered depth), and `pcf.data.clean.slots` (slot labels and position groups).

## The gap map: each decision, and what it does to the output
*Claude, 2026-11-19, for the CEO's second question. Every row is a fork the old VOE took one way. Changing a row changes what VOE means, not only how accurate it is.*

| # | Decision | The old VOE | Alternatives | What changes in the output |
|---|---|---|---|---|
| D1 | **What "expected" accounts for** | The situation, plus predicted pressure and time to throw | <ul><li>The situation only</li><li>Plus both sides' calls (context-live)</li><li>Plus the teammates</li><li>Plus the opponent's players</li></ul> | <ul><li>Each thing taken out stops being credited. Take out the calls, and a QB isn't credited for a good call made for him.</li><li>Take out pressure, and a tackle's pass blocking and a QB's pocket skill vanish. Pressure is caused by them, so it's a mediator, and controlling for it is a bad control.</li></ul> |
| D2 | **The outcome** | EPA | <ul><li>Success</li><li>WPA (win chance added)</li><li>One context-live outcome per skill (pressure over expected, completion over expected, run yards over expected)</li></ul> | <ul><li>EPA has a long tail: one 80-yard touchdown outweighs ten good plays.</li><li>Success is steadier but blind to size.</li><li>WPA ties to wins but swings with the score.</li><li>Per-skill outcomes give a profile instead of one number.</li></ul> |
| D3 | **Who shares a play's credit** | Expected: knockout of a fitted model. Realized: everyone gets the whole leftover | <ul><li>Only the ball's touchers</li><li>A joint regression on all 22 (plus-minus)</li><li>Shapley values (the fair split of a shared payoff, every order of arrival averaged)</li><li>A split by who did what (targets, carries, tackles, pressures)</li></ul> | <ul><li>How credit adds up: to the play, to 22 times the play, or to nothing fixed.</li><li>Whether linemen and defenders can show up at all.</li><li>How noisy each player's number is.</li></ul> |
| D4 | **How a player enters the model** | A depth-chart slot (QB1, WR2, …) holding his rating | <ul><li>His identity: one column per player, as in plus-minus</li><li>His role on that play (slot, wide or in-line, box or deep)</li><li>A position group's sum</li><li>A learned embedding: a "latent space" where players are points</li></ul> | <ul><li>Slots tie value to the depth chart, which is noisy and is a list rather than a role.</li><li>Identities give a rating per player but need him apart from his teammates.</li><li>Embeddings handle any lineup and find similar players, but only distances mean anything. The axes rotate freely, and a player needs many snaps to get a stable point.</li></ul> |
| D5 | **The model class** | Ridge, an MLP, XGBoost | <ul><li>Linear and additive</li><li>Trees</li><li>An MLP</li><li>A set or graph network over the 22 players (attention)</li></ul> | <ul><li>Additive means a player adds the same with any teammates: no fit, no complements, but stable credit.</li><li>Non-linear models allow fit (a WR better with this QB). Their knockouts then depend on the background (epistasis), and setting one slot to the average creates lineups the model never saw, so the credit can swing.</li></ul> |
| D6 | **"Without him" means** | His slot at the average rating | <ul><li>His actual backup that week</li><li>A replacement-level player (the kind a team can sign off the street)</li><li>Zero</li></ul> | <ul><li>The level and sign of every number.</li><li>Against the average, half the league is negative.</li><li>Against replacement, almost every starter is positive, and that is wins above replacement by definition.</li><li>Against his backup, a star with a good backup looks smaller (redundancy).</li></ul> |
| D7 | **The player's rating going in** | Running 50-snap average of the shared on-field leftover | <ul><li>A career-to-date rating</li><li>A stats prior (his own catches, pressures, tackles over expected)</li><li>None: the model learns each player from scratch</li></ul> | <ul><li>A shared input makes teammates alike, so the model can't split them (collinearity).</li><li>Overlapping windows make it repeat week to week whether or not the skill is real.</li></ul> |
| D8 | **Sides and sign** | One model; defenders take the offense's sign | <ul><li>Offense and defense apart</li><li>One model with defense flipped</li></ul> | Defenders' numbers flip sign. The old career list is upside down for defense. |
| D9 | **The scale** | Sums per player-game | <ul><li>Per snap</li><li>Per snap shrunk toward his position (a credibility weight)</li><li>Converted to points, wins (WAR), or dollars</li></ul> | <ul><li>Sums mix skill and playing time, and the old link to fantasy points is mostly this.</li><li>A rate with shrinkage is a skill, and its uncertainty can be stated per player.</li></ul> |
| D10 | **How it's checked** | Random splits; next week's fantasy points | <ul><li>Walk-forward seasons</li><li>Consistency (split halves, season to season)</li><li>The roster-change test (do players' VOE predict a team's next season when players move?)</li><li>Agreement among cousins</li></ul> | Whether we believe any of the above. Random splits put the future in training, and fantasy points reward volume. |
| D11 | **Which participation** | True participation | <ul><li>The in-season map (participation-live, participation-late)</li><li>Both, as two editions</li></ul> | <ul><li>True participation: after the season only.</li><li>The in-season map: during the season, at about 0.45 of the true plus-minus's agreement.</li><li>This decides the cadence (rule m).</li></ul> |

**Seen from each of the CEO's three angles:**

- **Machine learning: what can be learned from the rows.**
  - **The size of the problem:** about 1,700 players a season against about 33,000 scrimmage plays, so every player-level number needs shrinkage. The shrinkage is the prior, chosen or not.
  - **Identifiability:** if two players are always on the field together, no model can split them. D3, D4 and D5 only decide how the split is guessed.
  - **An MLP on everything:**
    - It fits interactions, but its credit is unstable: retrain with a new seed and the knockouts move.
    - Its fit can't be told apart from leakage on random splits. The old 0.80 is the warning.
  - **A latent space:** it compresses 22 players into a few numbers per player.
    - It's good for "who is like whom" and for lineups it has never seen.
    - It's poor for "how much is he worth", because the axes have no units until something pins them.
    - It's a cousin, not a replacement.
- **Data science: what the number means and how sure we are.**
  - **Units:** points per snap, per game or per season.
  - **The baseline:** average or replacement.
  - **Volume:** kept apart from skill.
  - **Uncertainty per player:** a range, not a point.
  - **Selection inside the folds,** never a grid picked on the test rows.
  - **The tail:** EPA's long tail means a handful of plays decide a season's VOE, so the exploration reports how much one play moves it.
  - **Historical EPA for every position:** EPA measures the ball's result. A cornerback's EPA is mostly the plays thrown away from him, and a guard's is the team's. It works for positions that touch the ball, and for the rest only through plus-minus.
- **Causal: is it "this player contributes this much"?**
  - **The question is a potential outcome:** the play with him, against the same play with someone else. Football never shows both, so every method is a way of guessing the missing one.
  - **The threats:**
    - **Confounding by selection:** coaches choose when he plays (H66). His snap counts follow game script, and his teammates come in packages.
    - **Overlap:** QBs and linemen rarely sit, so there are almost no "without him" plays (player-pace: QB and OL plus-minus weak).
    - **Interference:** a receiver's effect depends on his QB, so "his effect" exists only given a background. This is the knockout's epistasis.
    - **Bad controls:** see D1.
  - **The tools the CEO named, and what each needs:**
    - **A propensity model:** the chance he's on the field given the situation. participation-live already estimates a chance per player per play, which is close to a propensity score.
    - **Double machine learning:** take the situation out of both his presence and the play's result, then relate what's left. It needs overlap.
    - **Natural experiments:** in-game injuries and the backups who replace them, for an unplanned "without him".

## A family of models: sisters and cousins
*Claude's sketches for the CEO's third question. Methods, not hunches: the CEO picks which to chase. Each one changes several decisions above at once, so it should catch different signal and still read as "value over expected".*

| Model | Decisions it changes | What it should catch that the others miss | What it assumes | Cost |
|---|---|---|---|---|
| **The recreation** (the CEO's first ask) | Keeps the design. Fixes D8's sign, D10's splits, D9's per-snap scale and the leak in step 1 | The old idea, honestly scored: the reference every cousin is read against | The old assumptions above | Small: the cleaning is ported |
| **Plus-minus on the leftover** (RAPM) | <ul><li>D3: a joint regression</li><li>D4: identity</li><li>D7: a stats prior</li></ul> | A per-player value with honest uncertainty that splits teammates as far as the data allows | Additive effects, and enough plays apart | Small |
| **Who did what** (the old note's retrospective VOE) | <ul><li>D3: splits each play's leftover by involvement (target, carry, pressure, tackle, pass broken up)</li></ul> | Credit tied to visible actions. Linemen through pressures and sacks allowed, defenders through tackles and passes broken up | The box score marks the right players | Medium |
| **Knockout with the real backup** | <ul><li>D6: his actual backup, or replacement level</li><li>D9: converted to wins</li></ul> | Wins above replacement in the strict sense. The value of a star depends on how deep his team is | The backup's rating is known, and the model can score a lineup with him in it | Medium |
| **A latent-space VOE** (embeddings, or attention over the 22) | <ul><li>D4: embeddings</li><li>D5: a set network</li></ul> | Fit and complements: which receiver is worth more with which QB, and which players are alike | Enough snaps per player; distances mean something | Large; the exploratory one |
| **Skill VOE** (one per context-live outcome) | <ul><li>D2: per-skill outcomes such as pressure over expected (OL, DL), completion over expected (QB, WR), run yards over expected (RB, OL)</li></ul> | A profile per player instead of one number; feeds roles and archetypes | Each skill's outcome is his to own | Medium; context-live has the expectations |
| **Natural-experiment VOE** | <ul><li>D3 and D6: only plays around unplanned changes (in-game injuries)</li></ul> | The cleanest "without him", for the few players who get one | Injuries are as good as random within a game | Small to check, few players |

**A way to compare them, from outside the usual toolbox: the multiverse** (specification-curve analysis, from psychology's response to results that hinge on the analyst's choices). It answers the CEO's "how does each decision change the output, and in combination?" directly.
- **How it works:** run every combination of a few decisions (D1, D2, D3, D6, D9 at two or three settings each) on the same seasons, and report for each decision:
  - how far it moves players' ranks;
  - how far it moves the consistency (does the value repeat?);
  - how far it moves the roster-change test (does it predict a team's next season?).
- **What it assumes:** the decisions can be varied independently.
- **What it costs:** compute, plus the discipline to read it as a map, not a contest. Picking the best cell after the fact is the forking-paths trap it exists to expose.

## What "reliable player value" would have to pass
*Claude's draft tests for the CEO's fourth question; the CEO decides which one is the no-noise target.*

1. **It repeats:** split halves and season to season, per position, measured with `pcf.validation.consistency`. A number that doesn't repeat is noise, however causal its method.
2. **It travels:** when players change teams, the sum of each team's players' VOE predicts its next-season EPA per play beyond last season's team rating. This is the plus-minus world's gold standard, and it is where a real player value and a team effect split apart.
3. **It agrees with its cousins** (convergent validity) where they should agree, and differs where they measure different things.
4. **It passes the football sanity check:**
   - Known great players rank high.
   - Defense has the right sign.
   - Positions sit in a believable order.
   - A team's VOE adds up to roughly its own result over expected.
5. **Against the old outputs:** where it agrees and differs with `voe_weekly_data.xlsx`, and why.

## The CEO's direction
*Word for word, 2026-11-19, after the kickoff.*

"Okay, well, I would personally like to hold off on the retro analysis number 2. I know you just said it's due. I know we should do it, but I want to do VOE and maybe one other cousin, or maybe even some explorations first, because I think this is the first really important model. And so I want to get it done. And then after we get this model and maybe one other cousin, maybe two other cousins, then we can go look back, do retroactive analysis, look at our ideas, look at our hunches, and try and apply those to make more predictions and work on another cousin, or maybe two or three cousins, so that we have like some base value measurements, some causal estimates, and some really cool models. And then we do a retro analysis, and then we work on some more and see if we can get these new ones better. Because I think what we're going to learn by making this VOE model and maybe a war model and maybe a plus minus model, but what we learn by making these is going to be really important. So let's start. Well, I shouldn't say what. Let's start. I think the cousin models that you talked about are all really good. I think all 7 are great. I think we can explore all of them. Because if it turns out that there's nothing there, then we simply just don't do it. I don't think it hurts at all with exploring them. I think you could rank them by how much you think they will help, or how much you think we will learn from trying it, and then we can prioritize the highly ranked ones first. I think the plus and minus shrinkage is really good because it's pretty simple, and I think it would be pretty strong, and it would be pretty fast to do. I think doing like a natural wins above replacement, like you said, like comparing a player with another player. Not even, it doesn't have to be their backup. It could just be just someone else who is taking their position on that field on a certain play. I think that would be a really good natural, like almost a natural experiment that can create a model, an expert. Um, I think a latent space model of 22 players would be super interesting. I think we could create a really powerful latent space that we can apply to a bunch of different downfield models and can really help with machine learning because, of course, computers, machine learning algorithms suffer from the curse of high dimensionality. Um, I think uh, plays or like a natural experiment looking at outcomes within a game when there's an injury within the game. I think that's also super interesting to see if there is any change. We can attribute those changes. And then what we can do with these natural experiments is we can, because really what a natural experiment is we're just measuring the data in a very robust way. And so once we have that measurement, what we can do, I think would be interesting is we can take that robust measurement and then we can start bootstrapping it or trying to predict it on to other situations. So we can say like, hey, we found that we're fairly certain that this measurement is true because we saw the differences in difference, you know, or the difference in differences, or however you say it, the DID, or we did this double machine learning and we're pretty confident about this measurement, but it doesn't apply to everything, and we don't have examples of it everywhere. So what we're going to do is we're going to take all the confounders and we're going to regress those confounders on the outcome, on the measurement, on that feature that we just discovered, and then we're going to apply that to everything, and then we have now a new estimate, which is really cool, a new feature, a new really strong causal output, or maybe not causal, but a really strong, above expectation. I don't know what the best way to say that because it's not technically causal, but it is like it's almost like causal because we're measuring something and we're taking confounders and we're measuring the two expectations against each other. We're trying to find the difference between them. So I think all of those 7 are really good. I think what we can do right now is let's do the VOE. Let's try and recreate it. See how it goes. Let's do the exploration. And then let's also do some of the natural experiments. Let's see if we can use up differences and differences, or a propensity model, or causal inference. Obviously, those are all causal inference. I don't know why I'm saying that, but I meant to say double machine learning. I think these are some really strong techniques that we can use with, because we have so many samples. I know we don't have every single example. And I know that it is good to convert everything to a latent space because we can compare more things together, hopefully. And that's why I kind of wanted to also to build all of those other models like schemes, context, participation, like all those models are almost, they're not exactly latent space, but they're almost like it. We can use those as confounders to say, hey, this play was actually pretty similar to this play over here. They might not look similar in some ways or from one perspective, but from the second perspective, they actually look very similar. So I would like to push out retro number 2. We can do that later after we learn a lot from VOE and some experiments. So let's kick off the brief for value over replacement, please."

**What it settles:**
1. **Retro 2 waits** until VOE and one or two cousins are done (RETRO.md, "Next retro").
2. **All seven cousins get explored,** ranked by how much each should help or teach, highest first (below).
3. **This exploration:** the recreation, plus the natural experiments (in-game injuries, a player against whoever else takes his spot), plus plus-minus with shrinkage, which the CEO rates simple, strong and fast.
4. "Value over replacement" in the last line is read as this project, VOE; wins above replacement is one of its cousins.

## The cousins, ranked
*Claude, 2026-11-19, as the CEO asked: by how much each should help or teach, against its cost.*

| Rank | Model | Why here |
|---|---|---|
| 1 | **Plus-minus with shrinkage** | Cheap, standard, and the bar every other cousin has to clear. It also shows directly which players can be split from their teammates at all |
| 2 | **The recreation** | The CEO's first ask and the reference. It mostly teaches what the old design measured |
| 3 | **A player against whoever else takes his spot** (the CEO's natural wins above replacement) | Cheap, and the most direct view of the overlap problem: where there are plays without him, and where there aren't |
| 4 | **In-game injuries** | The cleanest "without him", for a few hundred players. It tells us whether the plus-minus numbers are believable, and it is the base for H73's extension |
| 5 | **Who did what** | Brings linemen and defenders in through visible actions (pressures, sacks, tackles, passes broken up) |
| 6 | **Skill VOE** (per context-live outcome) | Likely the steadiest numbers, but context-live's walk-forward history covers only 2023-2025, so season-to-season tests are thin until earlier seasons are scored |
| 7 | **Knockout with a replacement player, in wins** | Builds on ranks 1, 3 and 4: it needs a value per player and a replacement level first |
| 8 | **The latent space of the 22** | The largest and most exploratory. Best done once ranks 1 to 5 show what a player's value looks like, so the space can be checked against it |

## CEO hunches
*The CEO's words, 2026-11-19. Confidences given by the CEO the same day, before any run (multiple choice: low about 60%, medium about 75%, high about 90%); no sizes given. Claude's expectations written before the first run.*

| # | Hunch (the CEO's words) | The claim tested | CEO's confidence | Claude expects | How the exploration tests it |
|---|---|---|---|---|---|
| H69 | "I think the plus and minus shrinkage is really good because it's pretty simple, and I think it would be pretty strong, and it would be pretty fast to do." | A plus-minus with shrinkage gives a player value that repeats season to season and is strong | medium (75%) | 60% that it repeats at 0.2 or more, season to season, averaged over position groups: QBs highest (0.4 to 0.6), linemen and defenders lowest (0.05 to 0.2). 40% that it predicts a team's next season, when players move, beyond last season's team rating, by more than 1% of the error | Ridge on each play's EPA over expected (all 22 players, defense signed), a season at a time; split halves within a season, season to season; the roster-change test |
| H70 | "I think doing like a natural wins above replacement, like you said, like comparing a player with another player. Not even, it doesn't have to be their backup. It could just be just someone else who is taking their position on that field on a certain play. I think that would be a really good natural, like almost a natural experiment that can create a model, an expert." | Comparing a player with whoever else plays his spot, inside the same team-game, gives a real player value | low (60%) | 45% that it repeats at 0.15 or more season to season for at least two position groups (rotating spots: RB, DL, LB, WR3). Near 0 for QBs and linemen, who almost never share their spot. 30% that it agrees with plus-minus at 0.5 or more | On minus off, at his position group, inside each team-game, plays weighted; split halves, season to season, agreement with H69 |
| H71 | "I think a latent space model of 22 players would be super interesting. I think we could create a really powerful latent space that we can apply to a bunch of different downfield models and can really help with machine learning because, of course, computers, machine learning algorithms suffer from the curse of high dimensionality." | A latent space of the 22 players helps downstream models | not asked yet | Not tested in this exploration (rank 8) | Later: an embedding against raw inputs, on a downstream target |
| H72 | "plays or like a natural experiment looking at outcomes within a game when there's an injury within the game. I think that's also super interesting to see if there is any change. We can attribute those changes." | When a player leaves a game injured, his team's results over expected change measurably, and the change can be credited to him | high (90%) | 85% that a QB leaving shows a clear drop (0.1 to 0.2 EPA a play). 35% that any other position group's change clears zero. 30% that the size of the change follows the player's earlier value | Plays after an injury note against the same team's plays before it in that game, against non-injury games at the same point (difference in differences); by position group; then against the player's earlier plus-minus |
| H73 | "once we have that measurement ... we're going to take all the confounders and we're going to regress those confounders on the outcome, on the measurement, on that feature that we just discovered, and then we're going to apply that to everything, and then we have now a new estimate" | A measurement trusted from a natural experiment or double machine learning can be extended to every player by modelling it from what is known about him | low (60%) | 20% in this first look: few injury events per player, and each one is noisy, so a model of them should barely beat their average on held-out events | The injury changes as labels, modelled from what was known before the event (position, earlier plus-minus, snaps, the backup's earlier value); held-out seasons |
| H74 | "all those models are almost, they're not exactly latent space, but they're almost like it. We can use those as confounders to say, hey, this play was actually pretty similar to this play over here." | PCF's other experts (schemes, context, participation) work as confounders that find similar plays | not asked yet | Not tested in this exploration | Later, with context-live's plays like this one |

**Claude's expectations for the CEO's ask (not hunches):**
- **The noise ceiling:** a team's EPA per play over expected repeats about 0.4 to 0.5 between the halves of a season for offense and 0.2 to 0.3 for defense. Single players' numbers repeat far less.
- **The recreation, fixed:**
  - Its expected VOE repeats week to week by construction (overlapping windows).
  - Season to season it is mostly the team: 70% that it repeats less than plus-minus once teammates are taken out.
  - 70% that plus-minus beats it on the roster-change test.

## Open
*For the CEO, simple to detailed.*

1. **Your hunches, with odds.** The four claims in your ask could each be one hunch, for example:
   - "the recreated VOE repeats season to season";
   - "it predicts a team's next season when players move";
   - "a latent-space or propensity cousin catches signal the recreation doesn't";
   - "it can be turned into wins above replacement".
   For each, the football claim, a confidence and an expected size, in your own words.
2. **Cadence: after the season, during it, or both.**
   - **Why it matters:** the old VOE needed true participation, which arrives after the Super Bowl (2016–2025). In-season VOE would read the in-season map, which agrees with true plus-minus only about 0.45.
   - **Options:**
     - **After the season (`voe-retro`):** the cleanest, a player-value stat and a prior for next season.
     - **In season (`voe-live`):** weekly, blurrier.
     - **Both:** the same design run on two maps.
3. **Which players first.** All 22, as the old VOE did, or the ball's touchers first and the rest after the recreation shows it can split teammates.
4. **Which cousins the exploration looks at beside the recreation.** At most two or three, so each gets a real test.
