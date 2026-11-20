# Exploration: VOE, value over expected (`voe`)

> A first look at the CEO's ask (the old VOE, recreated responsibly) and hunches H69 (plus-minus with shrinkage), H70 (a player against whoever else plays his spot), H72 (in-game injuries) and H73 (extending a trusted measurement to everyone). H71 (a latent space) and H74 (other experts as confounders) wait for later cousins.
> Run on 2026-11-19 with three scripts. Regular seasons 2016–2024 with true participation; the vault (2025) wasn't read.
> - [`explore/first_look.py`](explore/first_look.py) (output [`first_look.txt`](explore/first_look.txt))
> - [`explore/checks.py`](explore/checks.py) ([`checks.txt`](explore/checks.txt)): players who moved, the QB split, the injury placebo
> - [`explore/qb_games.py`](explore/qb_games.py) ([`qb_games.txt`](explore/qb_games.txt)): whole games without the main QB
>
> The CEO's odds and Claude's expectations were committed before the first run (BRIEF.md, "CEO hunches").

**How to read the numbers:**
- **The leftover** is a play's EPA less what the situation alone expects. It's signed for the side, so a defender's leftover is minus the offense's: good for him is positive.
- **"Repeats"** is a correlation from 0 (luck) to 1 (all about him), with its 90% interval in brackets.
  - **Halves:** odd weeks against even weeks.
  - **Season to season:** one season against the next.
  - **Moved:** season to season for players who changed teams. This is the part of a value that can't be his team.
- **The roster-change test** asks how much a team's next-season EPA over expected a play is better forecast than from its own last season. It adds the players it actually used, each weighted by his share of its plays and valued at what he did the season before. It's scored as a percentage of the squared error removed, on 2019–2024, fitting only on earlier seasons.

**Verdict: GO, with the problem now measured.**
- **There is player value in this data, but most of what any of these methods calls "a player's value" is his team.**
  - A player's on-field number repeats 0.27 season to season if he stays on his team, and 0.03 if he moves.
- **Plus-minus pulls a little of the player out** (0.07 for movers).
- **Quarterbacks are the clear exception.**
  - Their values carry a team's next offense: +13.9% of the error.
  - A team without its main QB for a whole game is 0.070 EPA a play worse.
- **The old design's numbers repeat mostly by construction,** and its slot model explains almost nothing of a play it hasn't seen.
- **The in-game injury experiment is clean but finds no change,** for QBs included. The whole-game version of the same idea does find the QB.

## The noise ceiling (measured first)

| What | How much room |
|---|---|
| **A team's offense, EPA over expected a play** | <ul><li>Halves 0.57 (0.50 to 0.63): a full season is 0.73 reliable.</li><li>Season to season 0.35.</li><li>Teams spread 0.086 a play over a season.</li></ul> |
| **A team's defense** | <ul><li>Halves 0.29 (0.20 to 0.38): a full season is 0.45 reliable.</li><li>Season to season 0.24.</li><li>Defense is half as measurable as offense on this outcome.</li></ul> |
| **A single play** | <ul><li>The leftover's spread is 1.38 points a play.</li><li>The 22 players together explain at most +0.08% of a held-out play's leftover (plus-minus at its best shrinkage, 2017).</li><li>A player's value lives only in season-long sums.</li></ul> |
| **Pure dice on a player-season** | <ul><li>At the median 633 plays, luck alone moves a player's on-field average by 0.055 a play.</li><li>Teams' real spread is 0.078.</li><li>For one player, luck is two-thirds the size of the whole team effect.</li></ul> |
| **A player's raw on-field average** | <ul><li>Halves 0.35, season to season 0.23 (QB 0.39, OL 0.26, DL 0.14).</li><li>Moved 0.03 (−0.02 to 0.08).</li><li>The room for "the player, not his team" in this number is close to none.</li></ul> |
| **Fitting noise** | Plus-minus values at a third or three times the shrinkage agree 0.96 and 0.99 with the chosen one. The method is stable; its inputs are the problem. |

## Findings

| # | Finding | Numbers |
|---|---|---|
| F1 | **Every on-field number is mostly the team.** | <ul><li>Raw on-field average: stayed 0.27, moved 0.03.</li><li>Plus-minus: stayed 0.29, moved 0.07 (0.03 to 0.12).</li><li>Plus-minus and the raw average agree 0.92 for every group.</li></ul> |
| F2 | **The shrinkage the data picks makes plus-minus nearly an on/off sum.** | <ul><li>The best shrinkage for predicting held-out plays (ridge alpha 10,000) leaves player values spread only 0.003 to 0.004 a play.</li><li>A whole game without a team's QB costs 0.070.</li><li>It is right for predicting a play, and far too strong for sizing a player: the values rank players but don't size them.</li></ul> |
| F3 | **Some value moves with players.** | <ul><li>Plus-minus for movers: OL 0.11 (0.00 to 0.22), WR 0.12 (−0.02 to 0.26), DL 0.08.</li><li>QB −0.07, but on only 36 movers.</li><li>Small, near the edge of the intervals.</li></ul> |
| F4 | **Quarterbacks carry a team's next offense.** | <ul><li>Plus-minus with last season's prior: +6.9% on the next offense (1.9 to 12.1).</li><li>QBs alone: +13.9% (8.0 to 19.1).</li><li>Everyone else: +2.2% (−2.3 to 7.1).</li><li>On defense no version helps (−0.3% to −4.7%).</li></ul> |
| F5 | **The whole-game absence sees the QB.** | When a team's main QB misses a whole game, the offense is −0.070 EPA a play (−0.085 to −0.053) against his games that season (175 team-seasons, 639 games). |
| F6 | **The old design's model barely explains a play.** | <ul><li>The ridge from the 22 slot ratings explains −0.4% to +0.2% of a held-out play's leftover (pass and run, 2018–2024).</li><li>The old notebook's 0.80 came from a leak or a bug.</li></ul> |
| F7 | **The old design's expected VOE repeats by construction.** | <ul><li>Halves 0.92, because the rating windows overlap.</li><li>Season to season 0.36; moved 0.28, carried over by the career part of the rating.</li><li>OL 0.09 and DB 0.06 season to season. The summed per-game version repeats 0.64 week to week, which matches the old notebook's figure but is mostly construction and volume.</li></ul> |
| F8 | **The old design's realized VOE is faint.** | <ul><li>Season to season 0.10 (QB 0.23).</li><li>It agrees with plus-minus only 0.22 (OL −0.04).</li></ul> |
| F9 | **A player against whoever else plays his spot barely repeats.** | <ul><li>Halves 0.05, season to season 0.07 (RB 0.15, LB 0.12).</li><li>QBs and linemen are almost never off while their group plays: a weight of about 20 plays a season, against about 200 for backs and defensive linemen.</li><li>It agrees 0.45 with plus-minus (RB 0.61, DL 0.64).</li></ul> |
| F10 | **The in-game injury design is unbiased, and it finds nothing.** | <ul><li>1,342 regulars who left injured (on 60%+ of plays before, 2 or fewer after).</li><li>Change after less before, less the same team's other games at that point: +0.013 (−0.005 to +0.031).</li><li>Placebo (1,736 hurt who came back): −0.002.</li><li>QB +0.04 (−0.03 to +0.12). WR +0.10 (+0.03 to +0.17), the wrong way.</li></ul> |
| F11 | **Injuries come after bad stretches.** | <ul><li>The five plays before an injury that took the player out averaged −0.058, against −0.021 for his team's whole stretch before it.</li><li>Part of any "after" gain is a return from a bad stretch, which the control at the same point in the game doesn't fully remove.</li></ul> |

## The CEO's ask: the old VOE, recreated responsibly

- **What was recreated:**
  - Ratings from each player's last 50 snaps (a tree model of his next 6, fit only on earlier seasons).
  - The 22 depth-chart slots.
  - Ridge from slot ratings to the play's leftover, pass and run apart, earlier seasons only.
  - The knockout to the slot's average.
- **Fixed:** defense's sign, walk-forward fits, per snap instead of per game, and no outcome-based features.
- **Result:**
  - It runs, and its numbers repeat, but mostly because of how they're built (F6 to F8).
  - It agrees with plus-minus only 0.22.
  - It adds +1.1% (−1.2 to +3.1) to a team's next offense.
- **What it taught:** the knockout is the right question, but a rating built from the team's shared leftover can't answer it. The rating going in (D7 in the brief) is where the old design breaks, more than the model class (D5).

## The hunches

| # | Verdict | Real? | Pays? | Against the odds |
|---|---|---|---|---|
| **H69** plus-minus with shrinkage | **held in part.** Repeats 0.25 season to season (QB 0.40, OL 0.30, WR 0.31, DL 0.12); but moved only 0.07, so mostly the team (F1). With a prior it carries a team's next offense +6.9%, nearly all through QBs (F4); defense never | partly: real for QBs, faint for others | partly: +6.9% offense (QBs +13.9%), defense no | CEO 75%. Claude 60% on 0.2+ repeat (held as stated: 0.25, though mostly team), 40% on 1%+ travel (held for offense with a prior) |
| **H70** a player against whoever else plays his spot | **failed.** Repeats 0.07 season to season; only backs (0.15) and linebackers (0.12) faintly; nothing on the roster-change test (F9) | no for most groups | no | CEO 60%. Claude 45% on 0.15+ in two groups (failed: one group reaches 0.15); 30% on 0.5+ agreement with plus-minus (0.45 overall; 4 groups above 0.5) |
| **H72** in-game injuries | **failed in this design.** No change pooled (+0.013), no group a clear drop, the wrong sign for WRs (F10); not credited to him (0.00 with his value less his backup's). But a whole game without the main QB costs −0.070 (F5) | unclear: the effect exists across games, not within them here | no | CEO 90%. Claude 85% on a clear QB drop (failed: +0.04, −0.03 to +0.12); 35% any other group (none); 30% credited (no) |
| **H73** extending the measurement to everyone | **failed in this first look.** A model of the injury change from what was known before (group, his value, his backup's, his plays) removes 0.23% of the held-out error, the group's average 0.13% | unclear: the measurement it would extend wasn't there | no: +0.23% | CEO 60%. Claude 20% (as expected) |

## The case against this exploration

- **One outcome.** Everything here is EPA over the situation, which has a long tail and is shared by all 22 players. A per-skill outcome (pressure, completion, run yards over expected, from context-live) could show players that EPA can't. This look says nothing about those.
- **The shrinkage was chosen for predicting plays.** That choice flattens players toward their team (F2). A prior by position or from each player's own stats is the standard fix, and it wasn't tried. Plus-minus may look better with it.
- **The roster-change test uses who actually played the next season.** That is hindsight on playing time. It's fair for asking "does the value travel?" but it isn't a forecast.
- **Movers are few and not random.** Teams let go of players they value less, and they sign players who suit them. 36 QBs is too few to read.
- **The injury events come from text.** A player was matched by team, jersey number and last name in the play description, and "left" means 2 or fewer plays after. Some events are wrong, and some short absences are counted as leaving. The before window is depressed by the bad stretch leading to the injury (F11).
- **The recreation is a recreation.** It used the old design's main features, not every one of them, and EPA less a situation model instead of the old context model, which had leaks. A closer copy might score differently. The old outputs (`voe_weekly_data.xlsx`) weren't compared: reading `.xlsx` needs a library the project doesn't have.

## What this means for the brief

1. **The hard part is now measured:** separating players from their team.
   - Every method tried leaves most of its value on the team (F1).
   - QBs are the exception (F4, F5).
   - A VOE that is a player's value has to be judged on movers and on the roster-change test, never on split halves alone.
2. **The rating going in matters more than the model.** The old design's weakness is its shared input (D7), not the MLP or the slots.
3. **Natural experiments: whole games, not within a game.** Games a player missed give hundreds of clean absences for every position and found the QB. This is the version of H72 and H73 to try next.
4. **The cousins' ranking moves.** Three methods that bring in the player's own signal should come before the latent space, because each one gives the player information his team doesn't share:
   - plus-minus with a prior from his own stats;
   - who did what;
   - skill VOE.
5. **For the CEO:** the direction from here (BRIEF.md, "Open after the exploration").

---

# Second look: each player's own ratings (directions a and b, H75)

> Run 2026-11-19 to 2026-11-20, after the CEO chose directions (a) and (b) together and bet H75 ("90% confidence if we incorporate the plus minus sum into the vow model"). The pass rules and Claude's expectations were committed before the run (BRIEF.md, "The CEO's direction after the exploration").
> - [`explore/ratings.py`](explore/ratings.py) (output [`ratings.txt`](explore/ratings.txt)): the ratings, the VOE models, the roster-change test, the missed-QB check.
> - [`explore/mlp_check.py`](explore/mlp_check.py) ([`mlp_check.txt`](explore/mlp_check.txt)): why the first MLP failed, a fair refit, and the new-player check.
>
> Held-out plays: 2019–2024. The roster-change test: 2020–2024, because it needs an earlier season to fit on. Regular seasons only; the 2025 vault wasn't read.

**What was built:**
- **Two ratings per player and season,** each made only from seasons before the play's season:
  - **(a) Plus-minus that starts from his own stats.** Each season's plus-minus is pulled toward what his own stats and last season's plus-minus say, instead of toward 0.
  - **(b) The own-stats rating.** His season's own numbers mapped to next season's plus-minus, one lasso per position group. The numbers: EPA a dropback, carry and target; NGS completion and run yards over expected, separation and YAC over expected; PFR pressures, drops, targets allowed and missed tackles; sacks, hits, tackles for loss and passes defended. It contains no on-field team outcome.
  - New players get their group's learned new-player value instead of 0.
- **The old VOE design on top:**
  - Each play's 101 slots carry the ratings of who played there.
  - **The plus-minus sum** (offense minus defense, for each rating) is added as an input, as the CEO asked.
  - The models: a lasso and a small MLP (32 units, 3 seeds), plus plain sums as the simple rung.
  - The knockout replaces one side's players with the slot's average.

**Verdict: H75 held in part.**
- **Real? No.** In games the main QB missed, the knockout predicts only about a ninth of the drop that actually happens.
- **Pays? Yes, by the rule written before the run:** +7.8% on a team's next offense, with the 90% interval just above 0.
  - Two caveats come with it. It's no better than the first look's plain plus-minus sum on the same seasons (+7.2%).
  - It shrinks to +5.3%, with the interval crossing 0, once the share of plays a team gave to new players is in the baseline.
- **The plus-minus sum is what makes the VOE model work at all.** The same lasso with slots only explains less of a play and adds nothing to the next season (−0.3%).
- **The slots themselves add nothing over plain sums.** The small MLP does worse than the lasso.

## Findings

| # | Finding | Numbers |
|---|---|---|
| F12 | **The sum carries the VOE model; the slots don't.** | <ul><li>Held-out plays explained: plain sums of (a) and (b) +0.161% (0.12 to 0.20).</li><li>The VOE lasso with slots and sums +0.087% (0.005 to 0.158).</li><li>The lasso with slots only +0.045% (−0.04 to +0.12).</li><li>The lasso keeps 0 to 17 of its 202 slot inputs a fit.</li><li>Every model is far under the ceiling (about 0.4%).</li></ul> |
| F13 | **H75 pays by its rule, but not past simple plus-minus.** | The roster-change test on offense, 2020–2024, same rows:<ul><li>The VOE lasso +7.8% (0.2 to 15.5).</li><li>Plain sums (a)+(b) +8.7%.</li><li>The first look's plus-minus with prior +7.2% (0.9 to 13.6).</li><li>The recreation +1.2%.</li></ul> |
| F14 | **Much of the gain is who had to play, not how good they are.** | <ul><li>The share of a team's plays by players who didn't play the season before (mostly rookies), alone, adds +4.6% to its next offense and +6.6% to its next defense.</li><li>With that share in the baseline: the lasso +5.3% offense (−2.8 to 12.3), +2.7% defense; plain sums +4.6% and +2.4%; the first look's plus-minus +6.0% and −1.6%.</li><li>The own-stats rating marks new players below known ones (QBs −0.0017 against +0.0003), so it counts them.</li><li>The test uses who actually played, so the share partly records injuries during the season: hindsight.</li></ul> |
| F15 | **The knockout still can't size a QB.** | <ul><li>Games the main QB missed whole (122 team-seasons, 468 games): actual −0.067 EPA a play.</li><li>Predicted: the lasso −0.008; plain sums −0.015 (the best, a fifth of it); the first look's plus-minus sum −0.003.</li><li>The ratings rank players, but they are shrunk too far to size them (F2).</li></ul> |
| F16 | **The own-stats rating is a steady trait of the player, but it doesn't predict his plus-minus on a new team.** | <ul><li>Season to season, from separate seasons' stats: 0.42 if he stayed, 0.14 (0.08 to 0.20) if he moved.</li><li>Predicting this season's plain plus-minus: 0.15 if he stayed, 0.03 if he moved (TE 0.22, DB 0.12, OL −0.10).</li><li>Last season's plain plus-minus does that at 0.07 for movers.</li></ul> |
| F17 | **Starting plus-minus from his own stats changes almost nothing.** | <ul><li>Predicting next season's plain plus-minus: (a) 0.30 stayed, 0.08 moved, against plain plus-minus's 0.29 and 0.07.</li><li>At this shrinkage the prior moves values very little.</li></ul> |
| F18 | **A small MLP is the wrong tool at this signal size.** | <ul><li>The first fit explained −47% of a held-out play. It standardized slots that are filled on 0.03% of plays, so 30% of plays had an input beyond 8 units (one 183), and it predicted swings the leftover doesn't have (sd 0.32).</li><li>The fair refit (slot ratings left in rating units, early stopping on the last training season, the average kept when no epoch beats it) beat the average on its validation season in only 6 of its 72 fits.</li><li>It explains +0.006% of a held-out play on the lasso's inputs, and +0.054% on the four side sums, against +0.151% for a linear fit on the same four.</li><li>Seeds spread 0.06 points, less than the gap to the lasso.</li></ul> |

## Against the expectations written before the run

| Expectation | Result |
|---|---|
| H75 holds on both counts, 65% | held in part (pays yes, real no) |
| Real (the QB knockout reaches a third of the actual drop), 50% | no: a ninth (−0.0076 against −0.067) |
| Pays, 85%, at about +7% (+4 to +10) | yes, +7.8%; within the size range |
| The slots add 1+ point over plain sums, 30% | no: the lasso +7.8% against plain sums +8.7% |
| Own stats add 1+ point over plus-minus alone on offense, 45% | yes as stated: +8.7% against +3.0% (model-based values). But most of it is the new-player share (F14) |
| Any version helps defense with its interval above 0, 25% | no: the best, +6.6%, spans 0, and it is the new-player share |
| The own-stats rating repeats 0.2+ for movers, 55% | no: 0.14 |
| The MLP is no better than the lasso by more than 0.05 points, 80% | yes |
| The MLP is worse than the lasso, 60% | yes |
| Seeds spread more than the gap between the MLP and the lasso, 60% | no: 0.06 against 0.08 |
| The best model explains 0.3% of a play or less, 90% | yes: 0.16% |

## The case against the second look

- **The roster-change test still uses who actually played.**
  - F14 shows how much that matters: a count of new players scores almost as well as any rating.
  - A forecast would use the pre-season depth chart instead. Until then, every travel number here mixes "who is good" with "who had to play".
- **The shrinkage was kept from the first look,** chosen for predicting plays. It's the reason the ratings can't size a QB (F15), and why the prior in (a) barely moves anything (F17).
  - A model built to size players would choose it on the sizing test instead (games missed, F5).
  - **Rescoring with refits:** the model-based roster values come from a fit refit every season, so each season's scale moves. That adds noise the plain roster sums don't have: the first look's plus-minus scored +3.7% as a refit sum and +7.2% as a plain roster sum.
- **The MLP was given one fair chance, not a search.**
  - A network with a linear shortcut, much heavier penalties, or many more seeds might match the linear fit.
  - Claude expects it can't beat a linear fit by much under a ~0.4% ceiling, but that wasn't tested.
- **(b) is a stand-in for skill VOE.**
  - NGS and PFR stats are noisy, and some carry the team: a receiver's EPA depends on his QB.
  - PFR starts in 2018, so the earliest stats model had none.
  - Skill VOE proper (context-live's expected outcomes) wasn't run.
- **Few seasons.** Five test seasons of 32 teams each, so a 5% gain has an interval about 13 points wide.

## What this means for the brief

1. **The CEO's instinct about the sum was right in one way:**
   - Without the plus-minus sum, the VOE design has nothing to work with.
   - With it, the design reduces to the sum. The slots and the knockout add nothing a plain sum doesn't already have.
2. **The no-noise target needs the new-player share in its baseline.** Otherwise, any rating that marks new players below average looks like it travels. The share is also a team feature in its own right (I75).
3. **Sizing a player is the open problem, not ranking him.** The only number that sizes a QB is the whole-game absence (F5). That points to direction (c), games missed (I73), as the way to calibrate the size of every rating.
4. **Use linear models for the VOE expert.** The MLP's lesson goes in KNOWLEDGE at the end of the project: at a signal of about 0.1% of a play, a network fits noise first.
