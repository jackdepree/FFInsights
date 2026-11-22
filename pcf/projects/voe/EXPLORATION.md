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

---

# Third look: games missed, to size the ratings (direction c, I73)

> Run 2026-11-20, after the CEO's pick: "C, use missed games to size ratings". The design, the pass rules and Claude's expectations were committed before the run (BRIEF.md, "The CEO's direction after the second look").
> - [`explore/games_missed.py`](explore/games_missed.py) ([`games_missed.txt`](explore/games_missed.txt)).
> - Team-games 2016–2024, with each season's final week dropped. The sizing uses 2018–2024, where the ratings exist. The vault wasn't read.

**How to read it:**
- **An absence cost** is how much a team's EPA over expected a play (for the side the player is on) changes in a game he missed. It is measured against the same team's other games that season, and adjusted for the opponent.
- **k** is how many times a rating must be multiplied to match the real drops. k = 1 means the rating is already the right size.
- **Three versions were run.** Two problems with the pre-registered definition showed up in the results, so two checks were added, each labelled as a check:

| Version | Who counts as a regular | What counts as missing |
|---|---|---|
| **Pre-registered** | Typical share of his side's plays 50%+, 4+ such games | Any fall below his typical share, as a fraction (partial games count) |
| **Check 1** | The same | Whole games only (no snaps); partial games count as played |
| **Check 2 (the cleanest)** | Each team-season's main starters by plays: QB1, RB1, WR1–3, TE1, OL1–5, DL1–4, LB1–2, DB1–5 | Whole games only |

**Verdict: absences can be measured; the ratings can't be sized from them.**
- **Real positional costs:**
  - A team that loses its main starter for a game loses about 0.05 EPA a play at QB.
  - It loses 0.01 to 0.02 at WR, OL, DL, LB and DB, per player missing.
  - These costs predict held-out games: +0.76% of the error inside a season, about a sixth of the room there is.
- **The ratings don't add to them.**
  - Plus-minus doesn't tell which absences hurt more, at any position.
  - Only the own-stats rating (b) does, and only for QBs.
  - Sized ratings never beat the plain positional averages on held-out games.

## Findings

| # | Finding | Numbers |
|---|---|---|
| F19 | **A single game is almost all dice.** | <ul><li>A team-game's rate, less its season's mean, has sd 0.179 EPA a play.</li><li>Dice alone over a game's 62 plays: 0.175.</li><li>So everything real that moves a team from game to game, absences included, is about 4% of a game's variance.</li></ul> |
| F20 | **What a main starter's absence costs, per full game** (check 2; interval, then the shuffled null). | <ul><li>QB −0.049 (−0.068 to −0.030; null ±0.017).</li><li>OL −0.013 per lineman (−0.021 to −0.006; null ±0.007).</li><li>WR −0.014 (−0.023 to −0.003; null ±0.010).</li><li>LB −0.021 (−0.034 to −0.007; null ±0.014).</li><li>DB −0.016 (−0.022 to −0.009; null ±0.008).</li><li>DL −0.011 (−0.020 to −0.001; null ±0.010).</li><li>RB −0.010 and TE −0.014, both spanning 0.</li><li>Two starting linemen out cost about half a QB.</li></ul> |
| F21 | **How an absence is defined changes the answer.** | <ul><li>**Counting partial games picks up game script.** Starters sit in blowouts. Rotational players' "absences" show costs (TE −0.030, DB −0.014), and DL (+0.013) and WR (+0.010) get the wrong sign.</li><li>**Counting a midseason replacement as a regular cancels absences.** He and the starter are each "missing" when the other plays. The QB cost falls to −0.019 (check 1), against −0.049 with main starters only (check 2) and −0.067 for the main QB alone (F5).</li></ul> |
| F22 | **Plus-minus doesn't size absences; the own-stats rating does, for QBs only.** | **With each group's average cost in the same fit, k says only whether a bigger rating gap means a bigger drop** (check 2):<ul><li>Plus-minus from own stats (a): QB 2.2 (−2.5 to 6.8), others −1.2.</li><li>The first look's plus-minus: QB 1.2 (−4.0 to 6.1).</li><li>The own-stats rating (b): QB 12.7 (3.9 to 22.1), others 2.9 (−6.1 to 13.6).</li></ul>**Without the averages, k must also carry the average drop:** (a) QB 5.2; (b) QB 19.7 and others 12.0; plus-minus QB 4.1.<ul><li>A starter and his replacement differ by only about 0.001 a play on these ratings, against a real gap of about 0.05 at QB.</li></ul> |
| F23 | **The positional averages extend to new seasons; the ratings add nothing.** | Held-out team-games 2022–2024 (check 2; the share of within-season error removed):<ul><li>Group averages +0.76% (0.11 to 1.43); fit on 2016–2021, +0.87%.</li><li>Sized (a) +0.005%; sized (b) +0.25% (−0.38 to 0.85).</li><li>Averages plus sized (b) +0.83%, which is +0.07 points over the averages alone.</li><li>Sized (a) alone is worse than the averages by 0.76 points (−1.40 to −0.08).</li><li>In the pre-registered version and check 1, nothing clears 0.</li></ul> |
| F24 | **Sizing makes the roster-change test worse.** | <ul><li>2022–2024, with the new-player share in the baseline.</li><li>The first look's plus-minus unsized +4.2% (−3.9 to 11.6); sized −1.9%.</li><li>Plus-minus from own stats unsized +3.7%; sized −3.0%.</li><li>k for non-QBs, fit on 2018–2021, comes out negative, which flips their sign.</li></ul> |

## Against the pass rules and the expectations written before the run

**The pass rules:**
- **Absence costs are measurable at QB in every version.**
  - Pre-registered: QB, TE and DB clear 0, but the placebo flags TE and DB (F21).
  - Check 2: QB, WR, OL, DL, LB and DB clear 0.
- **Sizing works? No, in every version.** Sized ratings never beat the group averages on held-out games (F23).

| Expectation | Result |
|---|---|
| QBs show a clear drop of 0.05 to 0.09, 95% | yes: −0.051 pre-registered, −0.049 in check 2 (the bottom of the range) |
| At least one other group clears 0, at 0.005 to 0.02 (I73), 70% | yes: TE and DB pre-registered; five groups in check 2, at 0.011 to 0.021 |
| Two or more other groups, 40% | yes |
| k for QBs above 3 for every rating, 85% | no as registered: (a) 2.7, first look's plus-minus 2.5. In check 2: 5.2, 19.7 and 4.1 |
| The own-stats rating needs a smaller k than plus-minus, 50% | no: it needs a larger one (its values are smaller) |
| Sized ratings beat predicting no change on held-out games, 60% | no: (a) +0.005%, (b) +0.25% spanning 0 |
| They beat each group's average (I73), 35% | no |
| Adding them to the averages helps by more than the interval, 25% | no: +0.07 points |

## The case against the third look

- **The definition was fixed after the first results.**
  - The pre-registered version had two flaws, game script and replacement starters (F21), so two checks were added after seeing them.
  - Check 2 is what Claude would choose now, and the problems it fixes are visible in the numbers. But it is a second try, so its intervals are worth less than a pre-registered one's.
- **The placebo isn't a pure null.** Rotational players (10–50% of plays) do play. The LB placebo's +0.014 and the DB placebo's −0.012 may be real effects, scheme choices, or game script that the whole-game rule doesn't fully remove.
- **Little power to size players.**
  - One game is 96% dice (F19).
  - A starter and his replacement differ by tiny amounts on shrunk ratings.
  - "The ratings don't explain which absences hurt more" might partly mean "a few hundred absences can't show it".
- **Absences aren't random.**
  - Teams rest, bench and manage players, and some absences follow bad stretches (F11).
  - Benching a bad starter makes his absence look like a gain.
  - "Games after his last appearance" can include releases inside the season.
- **The opponent adjustment is a season rate,** not a strength at the time of the game.
- **Not tried:**
  - inactive lists (the game-day `INA` status) as a cleaner absence;
  - a shrinkage chosen on this sizing test;
  - more than two classes (QB and others) for k.

## What this means for the brief

1. **Value over replacement is measurable by position, not yet by player.** The data says what a starting QB, lineman or DB is worth over his replacement on average. It can't yet tell one lineman from another.
2. **QBs are the one place a player-level size exists:** the own-stats rating's QB gap tracks the size of the drop (F22).
3. **The ratings stay what they are:** they rank players within a position, mostly by team for non-QBs (F1, F16). Sizing them from absences failed. Making them bigger only adds noise (F24).
4. **For the CEO:** the direction from here (BRIEF.md, "Open after the third look").

---

# Fourth look: success as VOE's outcome (H89; written before the run, 2026-11-21)

> The CEO, 2026-11-21: "Can we try binary success as an outcome for voe? Success can be defined as positive epa, or it could be defined as positive wpa. Then the delta between the binary outcome and the probability of a success would be attributed to each player on the field. We can still use an arbitrary rating system for the inputs of each player alongside the important charters and context model outputs as inputs. ... My odds are 75% that it will be better than raw epa as the outcome."
>
> The CEO's answers to Claude's questions, 2026-11-21: "1c, 2; we should stick to epa as success then. 3; c, the inputs are all context expert outputs plus the individual rating for each player on the field. Each play's expected outcome is measured against the counter example. The counter example systematically replaces player ratings with "average" for that position. Then the delta between the expected outcome on the full fit and the expected outcome on the counterexample fit is attributed to the left out players. 4; the expected size is most likely small, 5 pp of error removed."

**Two arms, identical machinery** (the second look's `ratings.py`, run twice). Only the outcome changes:
- **The EPA arm:** a play's EPA, as in the first three looks.
- **The success arm:** a play's success, EPA above 0 (nflverse's definition), as 1 or 0. Its expected chance comes from the same situation trees as the EPA arm's expectation (each season fit on the six before it), as a classifier.

**In each arm, everything downstream is built on that arm's outcome:**
- **The leftover:** the outcome minus its expectation.
- **The plain plus-minus:** each season on its own.
- **Rating (a):** plus-minus that starts from his own stats.
- **Rating (b):** the own-stats rating, his own stats mapped to next season's plus-minus on that outcome.
- **The VOE model:** a lasso, pass and run apart, fit on 2018 to T-1 and scored on season T (2019-2024).
  - Its target is the play's outcome itself (EPA, or success as 0 or 1).
  - Its inputs are the slot ratings and the plus-minus sums, as in the second look, plus the situation expectation and context-live's back-history expectations (calls16 edition: pressure, sack, completion, time to throw, depth, run yards; decision 0038). That's the CEO's "all context expert outputs plus the individual rating for each player on the field".
- **The counterexample** (the CEO's design, the second look's knockout): a side's players' ratings are replaced by each slot's average. The side's value on a play is the full prediction less the counterexample's.

**Claude's technical calls, for the CEO to veto:**
- The success arm's model is a linear lasso (a linear probability model), so the two arms differ only in their outcome. The knockout's delta is then directly in success-chance units.
- Context-live's expectations are added as inputs in both arms. The second look had none.
- The ratings are made fresh on each arm's outcome. If both arms shared EPA-based ratings, a linear model would make their player values almost the same ranking, and the outcome couldn't show.

**The two yardsticks (the CEO: both must improve):**
1. **The roster-change test.** Each arm's knockout values, averaged by team, forecast the team's next season against its last season alone. Both arms forecast the same target: a team's EPA over expected a play (offense and defense, 2020-2024, fit on earlier seasons). The score is the gain in squared error removed, pooled over offense and defense, with a 90% interval from resampling teams. The new-player share isn't in this baseline, so both arms are read the same way (the second look's caveat applies to both). Beside it, the simple rung: each arm's plain sums of (a) and (b).
2. **The movers' repeat.** Each arm's plain plus-minus, this season against next, for players with 300+ plays in both seasons, each season's mean taken out. The first look's EPA value: moved 0.03 to 0.07. Read on movers, with stayers beside them, and a 90% interval on the difference from resampling players.

**Pass rule for H89:**
- **Held** if the success arm beats the EPA arm on both yardsticks (the roster-change gain and the movers' repeat), with at least one difference's interval above zero.
- **Failed** if the EPA arm is better on both.
- **Unclear** otherwise.

**The bets:**
- **The CEO:** 75% that success is better than raw EPA as the outcome. The expected size: "most likely small, 5 pp of error removed".
- **Claude,** for the claim as defined (better on both): 30%. The roster-change target is EPA itself, which favours the EPA arm, and success throws away the size of a play, which carries real information about the players as well as noise.
- **Side bets:**
  - The success arm's movers' repeat is higher: 55%.
  - Its roster-change gain is higher: 35%.
  - Its roster-change gain is 5 points or more above the EPA arm's (the CEO's size): 10%.
  - Its plain plus-minus repeats 0.05 or more higher season to season (all players; the side bet written with H89): 50%.
