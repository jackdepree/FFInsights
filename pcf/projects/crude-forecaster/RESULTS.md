# Results: Crude forecaster (`crude-forecaster`)

**Date:** 2026-11-17, updated 2026-11-19 (the CEO's answers, the lasso everywhere, the R7 spot-check) · **Status:** validating; the CEO approved the merge on 2026-11-19, with no vetoes · **Brief:** [BRIEF.md](BRIEF.md) (agreed 2026-11-15) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** `crude-forecaster` · **Champions:** the lasso for all 12 targets and horizons (the CEO, 2026-11-19); no model registered (a yardstick, like `baselines`) · **Decision:** [0037](../../docs/decisions/0037-crude-forecaster.md)

## The CEO's answers (2026-11-19, word for word)
- **The vault:** "I think for the crude forecaster, we can just keep it closed and let the live 2026 ledger be the test." (Option C.)
- **The spot-check:** "I think you should probably spot check R7, how small a gain the yardstick can read. I think that's probably pretty important to know the constraints, the limitations of the model." (Below: "The spot-check: R7".)
- **The champion rule:** "Yeah, just simplify it. We can keep lasso everywhere. I think that's fine. It increases, readability and then interpretability. You can look at the coefficients and the t-test and the p-value. So I think that's good."
  - **A caveat on that, from Claude:** a lasso's coefficients don't come with ordinary t-tests or p-values. It picks and shrinks its inputs on the same rows, so the usual standard errors don't hold, and an OLS refit on the inputs it kept gives p-values that are too small. The readable substitute is the coefficient table (R15): each input in yards per unit, with a 90% interval from refits on resampled weeks and how often those refits kept it.
- **Vetoes:** "I don't have any vetoes for the crude."
- **The merge:** "that merge is approved by me."

## In short
PCF now has one yardstick for every expert, hunch and idea: a deliberately simple forecast of yards (QBs' passing, RBs' rushing, WRs', TEs' and RBs' receiving, a team's yards gained and, mirrored, allowed), for the next game, the next 3 and the rest of the season, at the Saturday run. Any saved expert output can be added as an input and scored two ways: added alone, and its fair share. **It works as a yardstick; the spot-check sets how small a gain it can read.**
- **The crude forecast beats the season-so-far average everywhere** (all 12 tables, 7% to 35% of its squared error, R1). Its 80% ranges hold 77–80% (R12), and every champion passes 9 of 9 leakage checks and beats 20 of 20 shuffled refits.
- **The lasso is the champion everywhere** (the CEO). The trees never beat it. The mix (lasso and trees averaged) did beat both for receiving yards (next game, next 3) and passing over the next 3; keeping the lasso there costs 0.4–0.9% of range score (R2).
- **Participation is worth the most to every player forecast, in both halves of the seasons** (next game: passing 10.6%, rushing 3.3%, receiving 3.7% of the crude forecast's error). **Elo, then team efficiency, lead for team yards** (1.9% and 1.1%). Pace and schemes add little: one clear gain each (schemes on passing over the next 3, pace on team yards next game, which overlaps Elo) (R3–R6).
- **How small a gain it can read** (the spot-check, R7): about **0.1 points of share for receiving, 0.2–0.3 for rushing, 0.5 for passing and 0.7 for team yards next game, about 1 point over the next 3**. A gain counts when its interval clears zero **and** it beats 19 shuffled copies of itself. The first version of R7 used one shuffled copy and a fixed floor, and set the floor too high for rushing and receiving.

**Numbers:** [build/yardstick.txt](build/yardstick.txt) (from [build/yardstick_run.py](build/yardstick_run.py)), [build/spotcheck_r7.txt](build/spotcheck_r7.txt) ([spotcheck_r7.py](build/spotcheck_r7.py)), [build/coefficients.txt](build/coefficients.txt) ([coefficients_run.py](build/coefficients_run.py)); tables in `data/outputs/crude-forecaster/yardstick/<target>_<horizon>/`, `spotcheck_r7/`, `coefficients/`; scorecards in `data/outputs/crude-forecaster/<variant>/<run_id>/scorecard.html`.
**Vault (2025):** kept closed (the CEO, 2026-11-19, option C): the live 2026 ledger is the test. Participation, Elo and pace have no 2025 histories saved, and the row rule needs participation's.
**Versions tried:** one build version: 4 rungs × 12 targets and horizons on the yardstick board, the 12 champions through the harness, then the three mix champions rerun as lassos (the CEO's rule). The spot-check added 19 shuffled copies per expert on six tables. 2019–2024 had been looked at once before, by the exploration.

**The champions' harness runs** (2019–2024, refit each season, 20 shuffled refits; range score in yards, lower is better; "vs season" is the champion minus the season-average rung, 90% interval):

| Champion | Run | Range score | vs season | 80% range holds |
|---|---|---|---|---|
| `passing_next_lasso` | 4f33e228 | 23.63 | −0.59 (−0.82 to −0.38) | 80.0% |
| `passing_next3_lasso` | 68412aa5 | 19.65 | −0.58 (−0.86 to −0.28) | 78.9% |
| `passing_rest_lasso` | 70e87f25 | 19.45 | −0.90 (−1.18 to −0.63) | 77.6% (2021: 91.7%) |
| `rushing_next_lasso` | 43a6d6b7 | 5.73 | −0.13 (−0.18 to −0.09) | 80.4% |
| `rushing_next3_lasso` | 2939a945 | 4.43 | −0.16 (−0.21 to −0.11) | 80.0% |
| `rushing_rest_lasso` | 8f9d04a6 | 4.28 | −0.21 (−0.27 to −0.16) | 80.4% |
| `receiving_next_lasso` | 1e66e90a | 4.78 | −0.18 (−0.22 to −0.14) | 79.9% |
| `receiving_next3_lasso` | 695c8301 | 3.49 | −0.23 (−0.29 to −0.18) | 79.6% |
| `receiving_rest_lasso` | 2da887f2 | 3.10 | −0.23 (−0.28 to −0.18) | 80.5% |
| `team_next_lasso` | ce8178b0 | 19.36 | −0.88 (−1.13 to −0.65) | 78.7% |
| `team_next3_lasso` | 9e079f91 | 12.36 | −0.88 (−1.10 to −0.65) | 78.0% |
| `team_rest_lasso` | c2d3747a | 10.49 | −1.10 (−1.47 to −0.77) | 77.2% (2021: 69.5%) |

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal / no noise, or beats baselines | Every champion beats its season-average rung with the whole 90% interval below zero, and 20 of 20 refits on shuffled outcomes. No downstream no-noise target: the yardstick is the tool other experts' downstream numbers come from (the brief) |
| Calibration and range coverage | q10–q90 holds 77.2% to 80.5% (bar 75–85%), 49.5% to 52.9% above q50 (bar 45–55%). Every season is inside 70–90% except two rest-of-season forecasts in 2021, the first 17-game season: passing 91.7% (too wide) and team yards 69.5% (too narrow), so those two scorecards read "fail" (R12) |
| Leakage | 9 of 9 blocking checks pass for all 12 champions (identical at 25 cutoffs under the future changed and deleted; vintage sound for all 15 pinned histories). No feature above \|r\| 0.9 |
| Football sanity | Highest passing forecasts: Brady 2021, Mahomes 2019, Prescott 2020. Lowest of those expected to play: Taysom Hill's games and 2019 Bortles (they take snaps but barely throw). Team yards: early-season 2019 Ravens, Patriots and Cowboys highest (490–476); 2019 Jets, 2024 Panthers, 2023 Steelers lowest (278–287). The CEO raised nothing (2026-11-19) |
| CEO spot-check (2026-11-19): R7 | Done (below). It changed R7's rule and numbers, not its point; R6 was corrected beside it |

## Hunch verdicts
Copied into [`projects/HUNCHES.md`](../HUNCHES.md). "Expected to play" rows, next game, unless stated.

| # | Hunch | Verdict | Evidence, with its size | Real? | Pays? |
|---|---|---|---|---|---|
| H50 | Opponent-aware experts add the most | **partly**: failed for player yards, held for team yards (R3, R5, R8) | Players: participation first in all 9 tables; Elo and team efficiency second at most (passing next 3: Elo +1.80% alone; rushing next: efficiency +0.58%). Team yards: Elo +1.91% alone, +1.33% share; efficiency +1.10%, +0.60%; next 3 the same order | partly | yes, small: 0.4–2.9% |
| H51 | Past yards and first downs carry most of the explained variance | **held** (R9) | Yards-only inputs give 93% (passing), 99% (rushing), 97% (receiving), 90% (team) of the full crude forecast's share; first downs add 1.8, 0.0, 0.7 and 5.1 points of that | yes | first downs: little (team yards +0.45 pts) |
| H52 | Wide receivers' yards are the easiest to predict | **failed** (R10) | Players who took a snap: typical miss over the average QB passing 0.29, RB rushing 0.60, WR 0.66, TE 0.74, RB receiving 0.86; share removed RB rushing 43%, TE 40%, WR 36%, RB receiving 21%, QB passing 6% | no | not a forecast |
| H53 | Experts improve efficiency more than volume | **unclear** (not retested; the exploration's verdict stands) | The build forecasts yards only (the CEO's call 4); attempts and yards per attempt weren't targets | partly (exploration) | partly, small (exploration) |
| H54 | Recent games carry forward | **held for players, failed for teams** (R11) | Last-4 and trend inputs: passing +0.71% (0.11 to 1.34), rushing +1.46%, receiving +0.91%, team +0.36% (not clear). With participation in: passing +0.13% (not clear), rushing +0.74% (0.33 to 1.16), receiving +0.40% (0.22 to 0.57): for QBs "recent" was who starts | yes for RBs and receivers; for QBs it's the role | yes, small: 0.4–0.7% beside participation |
| H55 | Boom-or-bust is a lasting trait | **held for rushing and receiving, failed for passing; doesn't pay** (R11) | Game-to-game spread, season to season: rushing 0.60, receiving 0.68 (traits), passing −0.05 (a state); spread over his average 0.58–0.72 (traits, partly the average again). As an input: −0.32% to +0.01% for the middle, nothing clear for the range with participation in | yes, for RBs and receivers | no |

## Terms
As the brief and the glossary (crude forecast, expected to play, added alone, fair share, shuffled copy, yardstick table). One addition, changed by the spot-check:
- **Noise floor:** what a gain must beat to be read. It has two parts: its 90% interval from resampled weeks clears zero, and it beats all 19 copies of the same expert shuffled within each week (a permutation test, p = 0.05). The first definition (the one shuffled copy's largest gain across refits) is retired (R7).

## Findings
Numbered R so they don't collide with the exploration's F1–F12. "Share" is the share of squared error removed; intervals are 90%, resampling whole weeks; rows are players expected to play (participation's chance of a snap at least 50%) and every team-game; held out 2019–2024, fit from 2016, one refit a season; the lasso champion.

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| R1 | **The crude forecast beats the season-so-far average on every target and horizon.** The lasso removes 7.3% (rushing, next game) to 35.1% (team, rest of season) of the season average's error; range score 2.2% to 9.5% better | yardstick.txt §1, `lasso>season` | strong | all 12 |
| R2 | **The lasso is the yardstick; the trees never beat it.** Trees against the lasso: −0.2% (receiving next 3, level) to −18.7% (team rest). The mix beat the lasso on range score for receiving next (+0.40%, 0.26 to 0.54), receiving next 3 (+0.57%) and passing next 3 (+0.94%, 0.19 to 1.70): what the CEO's simpler rule gives up there. Elsewhere the mix ties or loses (team rest −3.1%). The longer the horizon, the worse the trees | §1 | strong | all 12 |
| R3 | **Participation is first on every player table, in both halves of the seasons.** Added alone, next / next 3 / rest: passing 10.6 / 12.2 / 6.4%, rushing 3.3 / 3.1 / 1.3%, receiving 3.7 / 4.5 / 3.1%. Its fair share is within 1 point of added alone everywhere: it overlaps with nothing | §2 | strong | QB, RB, WR, TE |
| R4 | **For QBs, participation's worth is entirely "will the expected starter play".** On rows where he took a snap it adds 0.0% (−2.7 to +2.6) to passing yards next game; on all rows expected to play, 10.6%. For backs and receivers it keeps a part (rushing 1.1%, receiving 2.2%): how much they play still varies among those who play | §2, the check rows | strong | QB vs RB, WR, TE |
| R5 | **Team yards: Elo first, team efficiency second, the same in both halves; nothing clear for the rest of the season.** Next game Elo +1.91% alone (1.26 to 2.60), +1.33% share; efficiency +1.10%, +0.60%; next 3 Elo +2.86%, +1.95%, efficiency +0.95%, +0.31%. Their fair shares are 30–70% of added alone: they carry some of the same thing (the exploration's F7). All four beat 19 shuffled copies of themselves (R7) | §2, spotcheck_r7.txt | strong for the order; medium for efficiency's size | team-game |
| R6 | **Pace and schemes add little: one clear gain each, and a few small harms** (corrected 2026-11-19). Schemes on passing over the next 3: +0.81% alone (0.33 to 1.25), +0.59% fair share, range score +0.92%. It beats its 19 shuffled copies, but only just (theirs reach +0.65%), and it was +0.14% (not clear) under the mix. Pace on team yards next game: +0.66% alone (0.06 to 1.25), beats its copies, but its fair share is +0.04% (Elo and efficiency carry the same thing), its range score is −0.37%, and leaving out one early season moves it from −0.30% to +0.66%. Harms on the range score: schemes receiving next (−0.08%) and rest (−0.10%); pace receiving next (−0.08%), rushing next 3 (−0.47%) and rest (−0.23%) | §2, spotcheck_r7.txt | medium | all |
| R7 | **How small a gain the yardstick can read** (the CEO's spot-check, 2026-11-19; rewritten): roughly **0.1 points of share for receiving, 0.2–0.3 for rushing, 0.5 for passing and 0.7 for team yards next game, and about 1 point over the next 3**. Three noises set it. (1) Which weeks happened (the interval's half-width for an expert worth nothing: receiving ±0.07, rushing ±0.1–0.25, passing ±0.3–0.45, team ±0.55–0.6). (2) Chance: the best of 19 copies of an expert shuffled within each week reaches +0.02% (receiving), +0.05% (rushing), +0.30% (passing next), +0.44% (team next), and +0.65–0.90% for passing and team over the next 3. (3) Which seasons trained it: leaving one early season out moves a gain by 0.03–0.12 points (receiving), 0.04–0.22 (rushing), 0.3–1.3 (passing) and 0.4–1.0 (team). A gain counts when (1) clears zero and it beats all of (2); (3) is reported as how fragile it is | spotcheck_r7.txt, §3 | strong | every reading of this yardstick |
| R8 | **Opponent-aware experts help player forecasts only over short horizons, and hurt over the rest of the season.** Elo passing next 3 +1.80% (1.03 to 2.56), rushing next +0.35%; efficiency rushing next +0.58% (0.33 to 0.83), passing next 3 +0.85%, receiving next +0.09% (0.02 to 0.15); all beat their shuffled copies. Rest of season: Elo −0.44% (rushing), −0.56% (passing); efficiency −1.60% (passing), −0.48% (rushing). A next-game rating isn't a rest-of-season schedule | §2, spotcheck_r7.txt | medium | players |
| R9 | **H51: past yards are nearly all of the crude forecast.** Yards-only inputs keep 93% (passing), 99% (rushing), 97% (receiving), 90% (team) of its share; first downs bring them to 95, 99, 98, 95% | §4 | strong | next game |
| R10 | **H52: QBs have the smallest typical miss, RB rushing the most explained.** Took-a-snap rows: QB passing 0.29 of the average, RB rushing 0.60, WR 0.66, TE 0.74, RB receiving 0.86. Among QBs who play, the crude forecast explains only 6% of passing yards: starters' games vary around similar averages | §4 | strong | next game |
| R11 | **H54 and H55: recent form keeps a little beside participation for backs and receivers; spread doesn't help.** Recent inputs with participation in: rushing +0.74%, receiving +0.40%, passing +0.13% (not clear), team +0.36% (not clear). Spread: no gain for the middle (−0.32% to +0.01%) or the range with participation in. Its repeat: rushing 0.60 and receiving 0.68 season to season (`pcf.validation.consistency`), passing −0.05 | §4 | medium | next game |
| R12 | **The ranges are honest, except rest of season in one season.** Fifths of the forecast by position, from the latest 20% of each window's misses: q10–q90 holds 77.2–80.5% for the champions, 49.5–52.9% above q50. Two seasons outside their bar, both rest of season in 2021: passing 91.7% (too wide), team yards 69.5% (too narrow). A season of rest-of-season rows is many near-copies of one outcome per player, so one season swings far | scorecards | strong for next game and next 3; medium for rest of season | all 12 |
| R13 | **The longer the horizon, the more the crude forecast explains and the less the experts add.** Receiving 40 → 56 → 58% of the error around the average (next, next 3, rest); rushing 43 → 54 → 51%; passing 20 → 26 → 28%; team 9 → 14 → 14%. All experts together for rushing: 3.8 → 3.2 → 0.7% | §1, §2 | strong | all |
| R14 | **SHAP isn't the test, shown on team yards.** On held-out rows the fitted model leans on schemes (mean \|SHAP\| 4.2 yards) and pace (3.5) about half as much as on Elo (7.8), yet neither has a fair share of the held-out gain (R6). For players, participation's \|SHAP\| is 2.2 times the crude inputs' for QBs and 0.4–0.6 times for backs and receivers | §5, build/shap_*.png | strong | method |
| R15 | **The lasso, read by its coefficients** (next game, every expert in, fit on 2016–2024). Passing: participation's chance of a snap is worth 210 yards per unit (146 to 226), and with it in, the lasso keeps no yards average at all; the penalty sits at the top of its grid (1.0), so it may want more. Rushing and receiving: participation's share and its share-if-active pull against each other (+115 and −78; +102 and −74 yards), last season's and this season's yards each about +0.1 to +0.3 yards per yard. Team yards: Elo's margin +1.8 yards per point (1.3 to 2.4), its total +1.5; most crude inputs are dropped; the penalty is again at the grid's top | coefficients.txt | medium: shrunk, intervals approximate | next game |

## The spot-check: R7 (the CEO's pick, 2026-11-19)
**The question:** how small a gain can the yardstick read, and what limits it?

**The rows.** Six tables (next game for all four targets; next 3 for team and passing yards), every expert, lasso champion, players expected to play, 2019–2024. For each expert: its added-alone gain and 90% interval from resampled weeks, then 19 copies of it with its own columns shuffled together within each week, each refit through the same walk ([spotcheck_r7.txt](build/spotcheck_r7.txt)).

**What it found.**
- **Real gains clear their copies by a wide margin.** Participation beats every one of its copies on every table (passing +10.6% against copies up to +0.30%), and so do Elo and efficiency on team yards (+1.91% and +1.10% against +0.44% and +0.14%).
- **The copies set the chance floor, and it differs by target:** a few hundredths of a point for receiving and rushing, 0.3 for passing next game, 0.4 for team yards next game, 0.65–0.90 for passing and team yards over the next 3 (larger copies of larger experts: Elo has 6 columns and its copies reach +0.87% on team yards next 3).
- **R7 as first written was off in both directions.** For rushing and receiving its "about 0.2 points" floor was 5–10 times the chance floor: it would have discarded efficiency's +0.09% on receiving next (0.02 to 0.15), which beats all its copies and is stable across refits (+0.05% to +0.09%). For passing and team yards over the next 3, the one shuffled copy's +0.57% understated what chance can do (+0.87%).

**The alternative, and why it isn't enough alone.** The permutation test asks "does this expert's information beat noise of the same shape?" It can pass a gain of nothing: on receiving next, schemes' 19 copies all lose a little (the lasso drops them), so schemes' −0.00% "beats" them. So the rule needs both halves: the interval for "is the gain above zero", the copies for "is it more than chance". Under that rule the readings change in three places against the interval alone: none (the interval was never too lenient on these tables), but the permutation would have passed Elo's +0.21% and efficiency's +0.26% on passing next, which the interval rightly holds back.

**What would change the answer.**
- **More copies.** 19 copies give p = 0.05 at best. Schemes on passing next 3 (+0.81% against a best copy of +0.65%) is at that edge; 99 copies would tell. Until then it's a "probably".
- **The vault, or the live 2026 ledger.** Every number here is 2019–2024, which the exploration and the build have both seen. A gain under the floor on new seasons is the test that matters, and the CEO's call makes the 2026 ledger it.
- **Another row rule.** The rows are participation's choice (the case against); a depth-chart rule would move participation's numbers and the floor for passing.

**Its constraints and limitations.**
- **Floors by table, not one number.** Passing and team yards are noisy targets with few rows (3,413 and 3,198), so their floors are 5–20 times receiving's (36,125 rows).
- **The refit noise was measured on next-game tables only**, three refits each (one early season left out); for longer horizons it's unknown.
- **Over the next 3 the floor is about 1 point** for passing and team yards: an idea worth less than that over a 3-game window can't be told from chance here.
- **It reads worth on the crude forecast of yards, not on products** (the brief's flagged assumption).

## The ladder
Per target and horizon (next game shown; the others in yardstick.txt §1). Share against the scored rows' average, range score in yards.

| Rung | Method | Passing | Rushing | Receiving | Team | Result vs the rung below | Takeaway carried forward |
|---|---|---|---|---|---|---|---|
| 0 `season` | season-so-far average (last season's in week 1), ranges by position and fifth | 9.7%, 24.23 | 38.0%, 5.86 | 33.5%, 4.96 | −6.8%, 20.24 | — | Players' averages are most of the forecast; a team's isn't |
| 1 `lasso` | lasso on the 21 crude inputs, penalty picked on the window's earlier 80% | 20.0%, 23.63 | 42.5%, 5.73 | 40.2%, 4.78 | 8.8%, 19.36 | beats rung 0 on all 12 (R1) | **The champion everywhere** (the CEO). Yards averages carry it (R9); recent form for players (R11) |
| 2 `trees` | xgboost, fixed plain settings | 16.5%, 24.04 | 40.7%, 5.78 | 40.0%, 4.78 | 3.6%, 19.96 | beats the lasso on none (R2) | Little interaction for trees to find in averages |
| 3 `mix` | lasso and trees averaged | 19.8%, 23.66 | 42.5%, 5.72 | 40.6%, 4.77 | 7.8%, 19.50 | beats both for receiving next and next 3 and passing next 3, by 0.4–0.9% of range score (R2) | Reported, not champion (the CEO: readability) |

## Where it misses
From the champions' scorecards, lens list 2026-11-15 (miss-lenses D1). Passing yards next game, 3,413 player-games; the other targets' lists are in their scorecards.

| Lens | Group | Rows | Average miss (actual − predicted) | 90% interval | Idea |
|---|---|---|---|---|---|
| week | weeks 2–4 | 586 | +15.5 | 9.9 to 21.5 | early-season passing is forecast too low: last season's average shrinks too far (the trend input knows only last season) |
| depth | 2 (backup) | 339 | −17.7 | −28.3 to −7.8 | backups expected to play throw less than forecast |
| team_change | QB changed in season, games 1–4 | 927 | −25.4 | −31.4 to −19.3 | a new starter's first games: too high; I68 |
| tag | backup QB start | 627 | −29.5 | −43.0 to −15.8 | the same |
| snap_share *(after)* | 75%+ | 2,856 | +28.1 | 25.6 to 30.8 | explained by playing time, as every baseline (miss-lenses) |
| qb_efficiency *(after)* | true | 1,622 | +43.9 | 40.8 to 47.0 | what happens in the game |

## The case against
- **The readable gain is large for passing and team yards.** Half a point of share next game and a full point over the next 3 (R7): most single ideas will be worth less than that, so on those targets the yardstick will mostly say "can't tell". Receiving and rushing read much finer.
- **The vault stays closed.** All numbers are 2019–2024, which the exploration had already looked at once. Small gains (schemes' +0.81% on passing next 3, pace's +0.66% on team yards) are exactly the kind retro pattern P8 says don't survive; the 2026 ledger is their test.
- **The row rule borrows participation.** "Expected to play" is participation's own forecast, so participation is scored on rows it chose. A row rule from another source would change its number (most likely up for passing, where its gain is starters who sat).
- **Yards aren't the products** (the brief's flagged assumption). An expert worth 0.0% here could still matter for touchdowns, fantasy points or margins: Elo is built to forecast points, and yards are only part of how points are made. Not tested here.
- **Rest-of-season numbers are thin.** Each player-season's rest-of-season rows share most of their outcome, so its intervals (resampling weeks) understate the uncertainty, and nothing in the rest-of-season tables beyond participation clears the floor.
- **The lasso's coefficients are shrunk** (R15). With every expert in, the passing lasso keeps no yards average, and its penalty is at the top of the grid. Read the coefficients for direction and rough size, never as causal or exact; "does it help" is the yardstick's held-out test.

## Pitfalls
- **The leakage checks rebuild moments with the future deleted**, where later moments have no expert values at all; a strict "more than 2% missing raises" stopped them. Missing values are now logged, not raised (decision 0037 call 15).
- **Variant histories had no way in**: the gateway read only `outputs/<id>/<run>/`. Variant pins in the registry (`history_runs`) fix it for every project (call 1).
- **The shuffled copy must shuffle a whole expert's columns together within a week**, or it keeps the columns' relation to each other and isn't a clean null.
- **One shuffled copy isn't a floor** (the spot-check): its gain is one draw from a spread, and the spread depends on the expert's size and the target.

## Not looked at
- **The vault** (2025): closed (the CEO).
- **H53** (volume against efficiency): yards only, the CEO's call 4.
- **QB rushing yards** (I67), fantasy points, touchdowns, game results; the play level (the CEO: later).
- **Refit noise for next 3 and rest of season**; permutation copies for rest of season.
- **A row rule not from participation** (the depth chart, or last week's snaps).

## Could be improved
1. **Put the permutation test in every table** (I69): 19 copies per expert by default (99 when a gain sits near its copies), printed beside each gain with the refit spread.
2. **Widen the lasso's penalty grid** above 1.0: passing and team yards pick its top value (R15).
3. **Early-season passing** (the week 2–4 miss): let the week-1 input lean less on last season for QBs with a new team or coach.
4. **Resample fits as well as weeks** for one interval that carries both noises.

## Don't redo
- **Don't tune the trees** to make them beat the lasso: the crude inputs are averages with little interaction to find (R2); a yardstick should change rarely.
- **Don't read SHAP as worth** (R14); the fair share on held-out error is the measure.
- **Don't read a lasso coefficient as a t-test** (R15): use the resampled interval, and the yardstick for worth.
- **Don't score an expert on all rostered players** (easy zeros, the exploration's case against): the row rule is the fix.

## Interface card
Also in this project's `interface` block in `registry.yaml`.

| | |
|---|---|
| **Inputs** | `player_game` roster, stats, snaps; `team_game` schedule, stats (gateway only); the 15 pinned histories in `registry.yaml` `history_runs` (participation `trees_week`, `lasso_h3`, `lasso_rest`; Elo `margin`, `total`; team-efficiency `off_next3_change`; pace's 5; schemes-v2's 4) |
| **Outputs** | `pcf.baselines.crude`: 48 variants `<target>_<horizon>_<rung>` (`variant(target, horizon, method)`, `with_experts(cls, added=...)`); the champion is `<target>_<horizon>_lasso`. Histories in `outputs/crude-forecaster/<variant>/<run_id>/history.parquet`: `passing_yards`, `rushing_yards`, `receiving_yards`, `team_yards_gained` (and `_next3`, `_rest`: yards per game over the window), mean q10 q50 q90; `allowed.parquet` beside each team history (`team_yards_allowed`, filed under the defense). The yardstick: `yardstick.build_board`, `load_board`, `gain`, `shapley`, `noise`, `score_input`, `coefficients`; tables in `outputs/crude-forecaster/yardstick/<target>_<horizon>/` |
| **Level of detail** | player-game (QB passing; RB rushing; WR, TE, RB receiving), players expected to play only; team-game |
| **Interval** | regular season, every week from week 1; fit from 2016, scored 2019–2024 |
| **Cadence** | in_season |
| **Known at** | the Saturday run (Thursday games at the Thursday run) |
| **How to use it** | As a yardstick, never a product: `score_input(board, frame, name, beside=("participation",), copies=19)` scores a new expert's or idea's input (a frame on the board's keys, or `existing=` board columns) against the crude forecast in minutes, alone and with participation in (Elo for teams). With `copies=19` it returns the copies' largest gain and `counts`: the interval clears zero and the gain beats every copy (R7, I69); print the copies' largest gain beside every row. Readable down to about 0.1 points (receiving), 0.2–0.3 (rushing), 0.5 (passing), 0.7 (team) next game, 1 point over the next 3. `coefficients(board, added, extra=...)` reads the lasso. Extra boards: `variant("qb_rushing", ...)` (I67) and `rows="depth"` (I70), scored but not published. The batch's inputs: `pcf.baselines.crude.inputs`. Cite it as a yardstick row in each new RESULTS.md |
| **Feeds** | every later RESULTS.md (a yardstick row); the retro's ranking of what's been built |

## The yardstick batch (2026-11-23)
*Retro 3's group D, run in the build chat ([YARDSTICK_BATCH.md](YARDSTICK_BATCH.md); the CEO: "Yes, start it"). Discovery: nothing ships. Decision [0042](../../docs/decisions/0042-yardstick-batch.md). Numbers: [`explore/yardstick_batch/`](explore/yardstick_batch/) (`run_batch.py`, one `.txt` per idea; `check_beside_elo.txt`, `consistency.txt`); tables in `data/outputs/crude-forecaster/yardstick_batch/`.*

The rule for every row: lasso champion, fit from 2016, scored 2019–2024 (the 2025 vault untouched); share of the crude forecast's squared error removed, with its 90% interval from resampled weeks; **counts** when that interval clears zero **and** the gain beats all 19 copies of the input shuffled within each week. The copies' largest gain is beside every row. Each bet's reading was written into `run_batch.py`'s header before the first result: the verdict reads the added-alone number unless the bet names what it sits beside.

| Idea | Input | Board (rows) | Alone (90%) | Beside participation / Elo (90%) | Copies' max | Counts? | Claude's odds: came true? |
|---|---|---|---|---|---|---|---|
| **I48** | Garbage-time yards per game, this season and last, beside the pooled averages | passing / rushing / receiving next (3,413 / 10,207 / 36,125) | +0.29% (−0.02 to +0.60) / +0.01% / +0.03% | +0.15% / +0.00% / −0.01% | +0.03% / +0.03% / +0.00% | no, on all three | 75% "holds": **failed**. The split ties the pooled yards (range score within +0.02%), but a garbage yard is worth far less than the rest: 0.40 of a yard for receiving (0.28 to 0.51), 0.24 rushing (0.06 to 0.42), −0.09 passing (−0.37 to 0.17), against the bet's 0.8 |
| **I59** | Pace's PROE and schemes-v2's 4 traits, WR and TE rows | receiving next / rest (25,918) | +0.01% / +0.05% | beside participation and efficiency: −0.01% (−0.05 to +0.03) / −0.08% | +0.02% / −0.01% | no | 30% that 1%+ survives: **didn't** (the 70% side came true) |
| **I60** | A games-played forecast (games so far shrunk to last season's rate; this week's report) | rest of season: passing / rushing / receiving / team | +0.19% / +0.09% / **+1.29% (+0.99 to +1.58)** / −0.46% | −0.79% / −0.03% / **+0.66% (+0.44 to +0.88)** / beside Elo **+2.84% (+1.42 to +4.47)** | +0.19% / +0.01% / +0.02% / +0.18% (beside Elo) | receiving (both); team beside Elo | 60% "2+ points": **failed** on the pre-set reading (best alone: +1.29%). The room is real: the hindsight share of games played is worth 70.2% (passing), 26.8% (rushing), 23.8% (receiving), 4.2% (team) |
| **I67** | QB rushing as a target; each expert's worth on it | qb_rushing next (3,413) / next 3 (2,966) | the crude forecast removes **34.5%** of the error around the average (next; 51.4% next 3), +10.2% (+6.8 to +13.6) over the season average; participation **+0.68% (+0.24 to +1.13)**, against RB rushing's +3.32% on the same run | — | participation's: +0.09% | participation only (Elo, efficiency, pace, schemes don't) | 70% participation worth less on QBs: **held**. "Removes 20–35%": **held**, at the top (34.5%) |
| **I70** | Participation, on depth-chart rows (starter or first backup) | next: passing (6,239 rows against 3,413) / rushing / receiving / QB rushing | **+38.8%** against +10.6% on its own rows / **+11.4%** against +3.3% / **+9.9%** against +3.7% / +8.3% against +0.7% | — | +0.08% / +0.02% / +0.01% / +0.04% | yes, all | 65% "passing rises, the others move under 1 point": **failed**. Passing rose, but rushing moved 8.0 points and receiving 6.2 |
| **I75** | Roster continuity: offense's own; the opposing defense's (pre-season, from the week-1 depth chart) | team rest (3,198) | offense −1.44% (−2.23 to −0.71); defense −0.03% | offense beside Elo **+2.21% (+1.00 to +3.48)**; defense −0.02% | +0.13% / +0.25%; beside Elo +0.29% / +0.51% | offense beside Elo only | defense 50%: **failed**; offense 30%: **didn't** (alone it hurts). Hindsight versions: offense −0.20% (−0.13% beside Elo), defense +0.14% |
| **I84** | A mover's first-4-games prior: his own old share, or the new team's slot | movers' rows: receiving (WR, TE; 1,755) / rushing (RB; 725) | own +1.56% / slot **+2.64%**; own −1.23% / slot **+2.03%** | own +0.47% / slot +0.74%; own −0.85% / slot +1.27% | +0.17% / +0.13%; +0.30% / +0.29% | both priors for receivers; slot only for backs | receivers 80% own wins: **failed** (own over slot −1.11%, −2.44 to +0.32). Backs 75% slot wins or ties: **held** (own over slot −3.32%, −6.34 to −0.31). Size 2–5% on movers' rows and under 0.3% overall: **held** (0.09%, 0.14% overall) |
| **I114** | The line: the team's expected margin, the total, its implied points | team next; passing, rushing, receiving next. Honest: ESPN's openers, 2023–2024 (900 team rows) | **honest +5.19% (+2.28 to +8.18)** (ceiling on the same rows +8.37%; on every row +6.86%); passing +0.70% (−0.39 to +1.84), rushing +0.18% (+0.02 to +0.33), receiving −0.01% | honest beside Elo +2.03% (−0.18 to +4.22); passing −0.60%, rushing +0.25%, receiving +0.01% | +0.14%; +0.33%, +0.04%, +0.01% | team alone; rushing (small) | teams 75%: **held**. Players 40% (2%+ on one): **didn't** (the 60% side came true). The kickoff line is a ceiling, never known at the Saturday run |

**What it says, in short.**
- **The line is the biggest input the batch found** (I114): ESPN's opening line, known at the Saturday run, removes 5.2% of the crude forecast's team-yards error next game, about 60% of what the near-closing line would (8.4% on the same games). Players barely: what the line knows about a player's yards, his own averages and participation already carry.
- **Availability is most of the room in rest-of-season forecasts, and the crude forecast of it gets little** (I60): knowing the share of games he went on to play would remove 24–70% of the error; a forecast from his games so far and the report removes 1.3% for receivers and nothing for QBs and backs.
- **The row rule hides most of participation's worth** (I70): on the depth chart's starters and first backups, participation is worth 3–4 times its R3 number. Most of that is "will a listed player play at all" (the depth rows double the QB rows with backups who rarely play: the exploration's easy zeros), so the yardstick's rule stays; the R3 numbers are participation's worth among players already expected to play, as R4 said.
- **QB rushing is a readable target** (I67): the crude forecast removes 34.5% of its error, participation adds 0.7%, and nothing else clears the floor.
- **Movers: the new team's slot adds more than his own old share** (I84), for backs clearly and for receivers not clearly. His own last-season yards are already on the board (`y_ls`, `vol_ls`), so the own-share prior mostly repeats them: this doesn't contradict F1 (target share travels), it says the slot is the new information.
- **Pass-heaviness (I59), garbage time (I48) and roster continuity (I75) add nothing on their own.** Garbage yards are worth a third of a yard or less, but they're 6% of a player's yards, so splitting them out costs nothing measurable.

**Beside Elo on team rest of season** (`check_beside_elo.txt`). Two team inputs hurt alone and help only beside Elo (I60's starters' games, I75's offense continuity), and on that board Elo itself doesn't help (−0.86%, −2.35 to +0.55). Against the plain crude forecast, crude + Elo + the input still gains: starters' games **+2.01% (+0.95 to +3.07)**, range score −0.12% (not clear); offense continuity **+1.37% (+0.25 to +2.44)**, but its range score is **worse** (−1.18%, −2.12 to −0.27). The copies (crude + Elo + a shuffled input) reach −0.63% and −0.74%. So the inputs repair something in Elo's rating over a rest-of-season window: a team's rating doesn't know its starters will miss games or are new. A new idea (I115) tests it inside Elo. Continuity's hindsight version doesn't help even beside Elo (−0.13%), which says its gain isn't "new players" as such.

**The case against.**
- **The 2019–2024 seasons have now been read many times.** The batch adds 8 ideas, about 100 rows; a few will clear the rule by chance even with 19 copies (p = 0.05 a row). The rows that count on one board and nowhere else (I60's receiving, I114's rushing at +0.18%) are the most likely to be that.
- **The honest line has two seasons** (179 games in 2023, 271 in 2024), so its interval is wide (+2.3% to +8.2%), and the lasso learns the line's weight from kickoff lines and then reads openers. If openers are noisier than the close in a way the weight doesn't fit, the honest number is low; if 2023–2024 were kind to lines, it's high.
- **Every input is a crude version of its idea.** A fitted availability model, a real slot model for movers or a continuity weighted by snaps would score differently. A failed bet here says "the crude version adds nothing", not "the football claim is false". The verdicts' "real?" columns say which claims were tested as claims (I48's weight, I60's room, I67, I70) and which only as inputs.
- **"Beside Elo" readings rest on a board where Elo hurts.** The I60 and I75 team gains are Elo repairs, not stand-alone signal; they count by the rule, and they're read here as a lead (I115), not a verdict.
- **I84's own-share prior is half on the board already**, so the head-to-head favours the slot by construction. A test of "whose share it is" (F1, F2) needs the own share against the slot with his own past yards held out, which isn't the yardstick's question.

## Open questions for the CEO
None left from the build. From the yardstick batch (2026-11-23), in the batch's report:
1. **QB rushing as a published target** (I67): a 13th yardstick table, or leave it as a board the yardstick can score on request? It changes what the yardstick predicts, so it's the CEO's call.
2. **The line at the Saturday run** (I114): ESPN's openers exist from 2023; our own collected lines from 2026. Use the opener as a yardstick input from now on (the crude forecast would then carry the market), or keep the yardstick market-free so experts are scored against football only?
