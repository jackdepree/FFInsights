# Results: Crude forecaster (`crude-forecaster`)

**Date:** 2026-11-17 · **Status:** validating (waiting on the CEO's spot-check, the vault call and the merge) · **Brief:** [BRIEF.md](BRIEF.md) (agreed 2026-11-15) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** `crude-forecaster` · **Champions:** 12, one per target and horizon (the ladder below); no model registered (a yardstick, like `baselines`) · **Decision:** [0037](../../docs/decisions/0037-crude-forecaster.md)

## In short
PCF now has one yardstick for every expert, hunch and idea: a deliberately simple forecast of yards (QBs' passing, RBs' rushing, WRs', TEs' and RBs' receiving, a team's yards gained and, mirrored, allowed), for the next game, the next 3 and the rest of the season, at the Saturday run, with any saved expert output added as an input and scored two ways (added alone, and its fair share). **It works as a yardstick, with one caveat about how small a gain it can read.**
- **The crude forecast beats the season-so-far average everywhere** (all 12 tables, 7% to 35% of its squared error, R1), its 80% ranges hold 77–80% (R12), and every champion passes 9 of 9 leakage checks and beats 20 of 20 shuffled refits.
- **The lasso is the champion in 9 of 12.** The trees never beat it; the CEO's mix (lasso and trees averaged) beats both only for receiving yards (next game and next 3) and passing yards over the next 3 (R2).
- **Participation is worth the most to every player forecast, in both halves of the seasons** (next game: passing 10.6%, rushing 3.3%, receiving 3.7% of the crude forecast's error); **Elo, then team efficiency, lead for team yards** (1.9% and 1.1%). Pace and schemes add nothing clear anywhere (R3–R6). The exploration's order holds; the sizes are smaller, as the row rule and one forecast moment said they would be.
- **The caveat:** the intervals resample weeks, not fits, so they miss the yardstick's own fitting noise. A shuffled copy of an expert got a clear fair share in 1 of 12 tables (+0.03%) and a clear added-alone gain in one (team yards, next 3: +0.57%). **Read a gain only when it clears its interval and the noise floor**: about 0.2 points of share for rushing and receiving, 0.5 to 1 point for passing and team yards (R7).

**Numbers:** [build/yardstick.txt](build/yardstick.txt) (from [build/yardstick_run.py](build/yardstick_run.py)); tables in `data/outputs/crude-forecaster/yardstick/<target>_<horizon>/`; scorecards in `data/outputs/crude-forecaster/<variant>/<run_id>/scorecard.html`.
**Vault (2025):** not opened. Participation, Elo and pace have no 2025 histories saved (their vaults are closed or spent), and the row rule needs participation's: the CEO's call (open questions).
**Versions tried:** one build version. 4 rungs × 12 targets and horizons on the yardstick board, then the 12 champions once through the harness (team yards next game twice: a first check run before the full board). 2019–2024 were looked at once before, by the exploration.

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal / no noise, or beats baselines | Every champion beats its season-average rung with the whole 90% interval below zero, and 20 of 20 refits on shuffled outcomes. The mix champions also beat their lasso and trees rungs in the harness. No downstream no-noise target: the yardstick is the tool other experts' downstream numbers come from (the brief) |
| Calibration and range coverage | q10–q90 holds 77.2% to 80.5% (bar 75–85%), 49.5% to 52.5% above q50 (bar 45–55%), every season inside 70–90% except passing rest of season in 2021 (91.7%: too wide), so that one scorecard reads "fail" (R12) |
| Leakage | 9 of 9 blocking checks pass for all 12 champions (identical at 25 cutoffs under the future changed and deleted; vintage sound for all 15 pinned histories). No feature above \|r\| 0.9 |
| Football sanity (CEO review pending) | Highest passing forecasts: Brady 2021, Mahomes 2019, Prescott 2020. Lowest of those expected to play: Taysom Hill's games and 2019 Bortles (they take snaps but barely throw). Team yards: early-season 2019 Ravens, Patriots and Cowboys highest (490–476); 2019 Jets, 2024 Panthers, 2023 Steelers lowest (278–287) |
| CEO spot-check | pending |

## Hunch verdicts
Copied into [`projects/HUNCHES.md`](../HUNCHES.md). "Expected to play" rows, next game, unless stated.

| # | Hunch | Verdict | Evidence, with its size | Real? | Pays? |
|---|---|---|---|---|---|
| H50 | Opponent-aware experts add the most | **partly**: failed for player yards, held for team yards (R3, R4) | Players: participation first in all 9 tables; Elo and team efficiency second at most (passing next 3 Elo +1.47%, rushing next efficiency +0.58%). Team yards: Elo +1.91% alone, +1.33% share; efficiency +1.10%, +0.60%; next 3 the same order | partly | yes, small: 0.4–2.9% |
| H51 | Past yards and first downs carry most of the explained variance | **held** (R9) | Yards-only inputs give 93% (passing), 99% (rushing), 98% (receiving), 90% (team) of the full crude forecast's share; first downs add 1.8, 0.0, 0.5 and 5.1 points of that | yes | first downs: little (team yards +0.45 pts) |
| H52 | Wide receivers' yards are the easiest to predict | **failed** (R10) | Players who took a snap: typical miss over the average QB passing 0.29, RB rushing 0.60, WR 0.65, TE 0.74, RB receiving 0.87; share removed RB rushing 43%, TE 40%, WR 36%, RB receiving 21%, QB passing 6% | no | not a forecast |
| H53 | Experts improve efficiency more than volume | **unclear** (not retested; the exploration's verdict stands) | The build forecasts yards only (the CEO's call 4); attempts and yards per attempt weren't targets | partly (exploration) | partly, small (exploration) |
| H54 | Recent games carry forward | **held for players, failed for teams** (R11) | Last-4 and trend inputs: passing +0.71% (0.11 to 1.34), rushing +1.46%, receiving +0.65%, team +0.36% (not clear). With participation in: passing +0.13% (not clear), rushing +0.74% (0.33 to 1.16), receiving +0.37% (0.21 to 0.52): for QBs "recent" was who starts | yes for RBs and receivers; for QBs it's the role | yes, small: 0.4–0.7% beside participation |
| H55 | Boom-or-bust is a lasting trait | **held for rushing and receiving, failed for passing; doesn't pay** (R11) | Game-to-game spread, season to season: rushing 0.60, receiving 0.68 (traits), passing −0.05 (a state); spread over his average 0.58–0.72 (traits, partly the average again). As an input: −0.32% to −0.03% for the middle, nothing clear for the range with participation in | yes, for RBs and receivers | no |

## Terms
As the brief and the glossary (crude forecast, expected to play, added alone, fair share, shuffled copy, yardstick table). One addition:
- **Noise floor:** the largest gain a shuffled copy of an expert reaches on a table, over its seeds and early seasons left out. A gain smaller than it isn't read, whatever its interval says.

## Findings
Numbered R so they don't collide with the exploration's F1–F12. "Share" is the share of squared error removed; intervals are 90%, resampling whole weeks; rows are players expected to play (participation's chance of a snap at least 50%) and every team-game; held out 2019–2024, fit from 2016, one refit a season.

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| R1 | **The crude forecast beats the season-so-far average on every target and horizon.** The lasso removes 7.3% (rushing, next game) to 35.1% (team, rest of season) of the season average's error; range score 2.2% to 9.5% better | yardstick.txt §1, `lasso>season` | strong | all 12 |
| R2 | **The lasso is the yardstick; the trees never beat it; the mix earns its place only for receiving and passing next 3.** Trees against the lasso: −0.2% (receiving next 3, level) to −18.7% (team rest). Mix against the lasso, range score: receiving next +0.40% (0.26 to 0.54), next 3 +0.57%, passing next 3 +0.94% (0.19 to 1.70); elsewhere level or worse (team rest −3.1%). The longer the horizon, the worse the trees | §1 | strong | champions: mix for passing next 3, receiving next and next 3; lasso elsewhere |
| R3 | **Participation is first on every player table, in both halves of the seasons.** Added alone, next / next 3 / rest: passing 10.6 / 11.8 / 6.4%, rushing 3.3 / 3.1 / 1.3%, receiving 3.7 / 4.5 / 3.1%. Its fair share is within 1 point of added alone everywhere: it overlaps with nothing | §2 | strong | QB, RB, WR, TE |
| R4 | **For QBs, participation's worth is entirely "will the expected starter play".** On rows where he took a snap it adds 0.0% (−2.7 to +2.6) to passing yards next game; on all rows expected to play, 10.6%. For backs and receivers it keeps a part (rushing 1.1%, receiving 2.1%): how much they play still varies among those who play | §2, the check rows | strong | QB vs RB, WR, TE |
| R5 | **Team yards: Elo first, team efficiency second, the same in both halves; nothing clear for the rest of the season.** Next game Elo +1.91% alone (1.26 to 2.60), +1.33% share; efficiency +1.10%, +0.60%; next 3 Elo +2.86%, +1.95%, efficiency +0.95%, +0.31%. Their fair shares are 30–70% of added alone: they carry some of the same thing (the exploration's F7). Rest of season: no member clear | §2 | strong for the order; medium for efficiency's size | team-game |
| R6 | **Pace and schemes add nothing clear to any table**, and a few small harms. Squared error: pace's fair share +0.42% (0.07 to 0.74) for passing next 3 is the only clear gain, inside that table's noise floor. Range score: schemes adds noise for receiving next 3 (−0.12%) and rest (−0.10%); pace for rushing next 3 (−0.47%) and rest (−0.23%) | §2 | medium | all |
| R7 | **The yardstick reads gains above a noise floor, not every gain whose interval clears zero.** Week-resampled intervals miss fitting noise. Refitting with three tree seeds and each early season left out moves an added-alone gain by 0.04–0.31 points (rushing, receiving), 0.29–1.26 (passing) and 0.42–1.35 (team). The shuffled copy's fair share covered zero in 10 of 12 tables; it was clear in two, −0.03% (rushing rest) and +0.03% (receiving rest). Added alone, it was clear once: +0.57% (0.02 to 1.12) on team yards next 3. On the range score it showed "adds value" in passing next (+0.34%) and rushing next 3 (+0.01%) | §2, §3 | strong | every reading of this yardstick |
| R8 | **Opponent-aware experts help player forecasts only over short horizons, and hurt over the rest of the season.** Elo passing next 3 +1.47% (0.54 to 2.39), rushing next +0.35%; efficiency rushing next +0.58% (0.33 to 0.83), receiving next 3 +0.17%. Rest of season: Elo −0.44% (rushing), −0.56% (passing); efficiency −1.60% (passing), −0.48% (rushing). A next-game rating isn't a rest-of-season schedule | §2 | medium | players |
| R9 | **H51: past yards are nearly all of the crude forecast.** Yards-only inputs keep 93% (passing), 99% (rushing), 98% (receiving), 90% (team) of its share; first downs bring them to 95, 99, 99, 95% | §4 | strong | next game |
| R10 | **H52: QBs have the smallest typical miss, RB rushing the most explained.** Took-a-snap rows: QB passing 0.29 of the average, RB rushing 0.60, WR 0.65, TE 0.74, RB receiving 0.87. Among QBs who play, the crude forecast explains only 6% of passing yards: starters' games vary around similar averages | §4 | strong | next game |
| R11 | **H54 and H55: recent form keeps a little beside participation for backs and receivers; spread doesn't help.** Recent inputs with participation in: rushing +0.74%, receiving +0.37%, passing +0.13% (not clear), team +0.36% (not clear). Spread: no gain for the middle (−0.32% to −0.03%) or the range with participation in. Its repeat: rushing 0.60 and receiving 0.68 season to season (`pcf.validation.consistency`), passing −0.05 | §4 | medium | next game |
| R12 | **The ranges are honest.** Fifths of the forecast by position, from the latest 20% of each window's misses: q10–q90 holds 77.2–80.5% for the champions, 49.5–52.5% above q50; one season outside its bar (passing rest of season 2021, 91.7%) | scorecards | strong | all 12 |
| R13 | **The longer the horizon, the more the crude forecast explains and the less the experts add.** Receiving 40 → 56 → 58% of the error around the average (next, next 3, rest); rushing 43 → 54 → 51%; passing 20 → 26 → 28%; team 9 → 14 → 14%. All experts together for rushing: 3.8 → 3.2 → 0.7% | §1, §2 | strong | all |
| R14 | **SHAP isn't the test, shown on team yards.** On held-out rows the fitted model leans on schemes (mean \|SHAP\| 4.2 yards) and pace (3.5) about half as much as on Elo (7.8), yet neither improves a held-out forecast (R6). For players, participation's \|SHAP\| is 2.2 times the crude inputs' for QBs and 0.4–0.6 times for backs and receivers | §5, build/shap_*.png | strong | method |

## The ladder
Per target and horizon (next game shown; the others in yardstick.txt §1). Share against the scored rows' average, range score in yards.

| Rung | Method | Passing | Rushing | Receiving | Team | Result vs the rung below | Takeaway carried forward |
|---|---|---|---|---|---|---|---|
| 0 `season` | season-so-far average (last season's in week 1), ranges by position and fifth | 9.7%, 24.23 | 38.0%, 5.86 | 33.5%, 4.96 | −6.8%, 20.24 | — | Players' averages are most of the forecast; a team's isn't |
| 1 `lasso` | lasso on the 21 crude inputs, penalty picked on the window's earlier 80% | 20.0%, 23.63 | 42.5%, 5.73 | 40.2%, 4.78 | 8.8%, 19.36 | beats rung 0 on all 12 (R1) | Yards averages carry it (R9); recent form for players (R11) |
| 2 `trees` | xgboost, fixed plain settings | 16.5%, 24.04 | 40.7%, 5.78 | 40.0%, 4.78 | 3.6%, 19.96 | beats the lasso on none (R2) | Little interaction for trees to find in averages |
| 3 `mix` | lasso and trees averaged (the CEO's) | 19.8%, 23.66 | 42.5%, 5.72 | 40.6%, 4.77 | 7.8%, 19.50 | beats both for receiving next and next 3 and passing next 3 (R2) | Champion where it wins; otherwise the lasso |

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
- **The intervals are too narrow, and that's the main risk.** They resample weeks on fixed forecasts, so fitting noise isn't in them (R7). A shuffled copy got a clear +0.57% once, and a reader who trusts intervals alone would call it signal. The noise floor fixes the reading, but it was measured only on next-game tables (three seeds, three early seasons left out); for the longer horizons it's borrowed. A table read by someone who skips §3 can mislead.
- **The vault is closed.** All numbers are 2019–2024, which the exploration had already looked at once. Small gains (pace's +0.42%, efficiency's +0.17%) are exactly the kind retro pattern P8 says don't survive.
- **The row rule borrows participation.** "Expected to play" is participation's own forecast, so participation is scored on rows it chose. A row rule from another source would change its number (most likely up for passing, where its gain is starters who sat).
- **Yards aren't the products** (the brief's flagged assumption). An expert worth 0.0% here could still matter for touchdowns, fantasy points or margins: Elo is built to forecast points, and yards are only part of how points are made. Not tested here.
- **Rest-of-season numbers are thin.** Each player-season's rest-of-season rows share most of their outcome, so 6 seasons of them are closer to 6 × 32 teams of independent outcomes than to their row count. Its intervals (resampling weeks) understate that, and nothing in the rest-of-season tables beyond participation clears the floor.
- **The ladder rule is mine.** The mix is champion where it beats both plain rungs, even though the trees didn't beat the lasso (rule k says the ladder stops there). Decision 0037 call 12; the CEO can veto it, and the three mix champions would become lassos, which lose 0.4–0.9% of range score.

## Pitfalls
- **The leakage checks rebuild moments with the future deleted**, where later moments have no expert values at all; a strict "more than 2% missing raises" stopped them. Missing values are now logged, not raised (decision 0037 call 15).
- **Variant histories had no way in**: the gateway read only `outputs/<id>/<run>/`. Variant pins in the registry (`history_runs`) fix it for every project (call 1).
- **The shuffled copy must shuffle a whole expert's columns together within a week**, or it keeps the columns' relation to each other and isn't a clean null.

## Not looked at
- **The vault** (2025): the CEO's call below.
- **H53** (volume against efficiency): yards only, the CEO's call 4.
- **QB rushing yards** (I67), fantasy points, touchdowns, game results; the play level (the CEO: later).
- **Fitting noise for next 3 and rest of season**, and a noise floor by position.
- **A row rule not from participation** (the depth chart, or last week's snaps).

## Could be improved
1. **Put the noise floor in the table itself**: run the shuffled copy with several seeds on every table and print the floor beside each gain, so the reading in R7 is automatic.
2. **Resample fits as well as weeks** for the interval (a few refits per resample), so one interval carries both noises.
3. **Early-season passing** (the week 2–4 miss): let the week-1 input lean less on last season for QBs with a new team or coach.
4. **A lighter mix**: weight the trees less where they lose, rather than an even average.

## Don't redo
- **Don't tune the trees** to make them beat the lasso: the crude inputs are averages with little interaction to find (R2); a yardstick should change rarely.
- **Don't read SHAP as worth** (R14); the fair share on held-out error is the measure.
- **Don't score an expert on all rostered players** (easy zeros, the exploration's case against): the row rule is the fix.

## Interface card
Also in this project's `interface` block in `registry.yaml`.

| | |
|---|---|
| **Inputs** | `player_game` roster, stats, snaps; `team_game` schedule, stats (gateway only); the 15 pinned histories in `registry.yaml` `history_runs` (participation `trees_week`, `lasso_h3`, `lasso_rest`; Elo `margin`, `total`; team-efficiency `off_next3_change`; pace's 5; schemes-v2's 4) |
| **Outputs** | `pcf.baselines.crude`: 48 variants `<target>_<horizon>_<rung>` (`variant(target, horizon, method)`, `with_experts(cls, added=...)`); histories in `outputs/crude-forecaster/<variant>/<run_id>/history.parquet`: `passing_yards`, `rushing_yards`, `receiving_yards`, `team_yards_gained` (and `_next3`, `_rest`: yards per game over the window), mean q10 q50 q90; `allowed.parquet` beside each team history (`team_yards_allowed`, filed under the defense). The yardstick: `yardstick.build_board`, `load_board`, `gain`, `shapley`, `noise`, `score_input`; tables in `outputs/crude-forecaster/yardstick/<target>_<horizon>/` |
| **Level of detail** | player-game (QB passing; RB rushing; WR, TE, RB receiving), players expected to play only; team-game |
| **Interval** | regular season, every week from week 1; fit from 2016, scored 2019–2024 |
| **Cadence** | in_season |
| **Known at** | the Saturday run (Thursday games at the Thursday run) |
| **How to use it** | As a yardstick, never a product: `score_input(board, frame, name)` scores a new expert's or idea's input (a frame on the board's keys) against the crude forecast in minutes, alone and with participation in. Read a gain only above the table's noise floor (R7). Cite it as a yardstick row in each new RESULTS.md |
| **Feeds** | every later RESULTS.md (a yardstick row); the retro's ranking of what's been built |

## Open questions for the CEO
1. **The vault (2025).** Participation, Elo and pace have no 2025 forecasts saved, and the row rule needs participation's. (A) run participation and Elo on 2025 to make them (that opens their vaults); (B) open this project's vault on the crude forecast only, scored on players who took a snap (Claude's lean: it tests the yardstick itself and spends nothing else); (C) keep it closed and let the live 2026 ledger be the test.
2. **The spot-check:** pick one finding or call (R4 and R7 are the most consequential).
3. **The ladder rule** (case against): keep the mix as champion where it beats both plain rungs, or stop at the lasso everywhere?
