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
