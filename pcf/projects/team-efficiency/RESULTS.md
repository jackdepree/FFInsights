# Results: Opponent-adjusted efficiency (`team-efficiency`)

**Date:** 2026-11-14 · **Status:** validating; done once the CEO approves the merge. **Champion: every play counted equally, with a weaker pull after a new QB or coach on offense** (`change` on offense, `ridge` on defense; the CEO, 2026-11-13 and 2026-11-14) · **Brief:** [BRIEF.md](BRIEF.md) (agreed 2026-11-13) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** `team-efficiency` · **Technical calls:** [decision 0032](../../docs/decisions/0032-team-efficiency-build.md)

## In short
**The champion is the simple rating** (`ridge`: opponent-adjusted EPA per play on every play, counted equally, with recency and last season as a prior), **with P3 on offense**: less of last season carries over after a new QB or head coach (`change`, R11–R12; the CEO, 2026-11-14). The CEO chose the simple rating on 2026-11-13 over the combination, whose honest edge (about +0.3% / +0.9%, R8) is about the size of its own split luck and costs an outcome model, 14 situation bins and cross-fitting. DML alone adds nothing (R3).

PCF now rates every team's offense and defense after every game, opponent-adjusted, from a new table part (`team_game.efficiency`), and forecasts each side's EPA per play over its next 3 games and the rest of the season.
- **The big win is counting every play.** Ratings on every play, counted equally (`ridge`), beat the usual garbage-time rule (`usual`) in all four forecasts, by 3.9–7.5% of its squared error, and in weeks 1–4 too (R2). Against the league's level they remove 14–26% of the error (R1), as the exploration found.
- **The extras the exploration found mostly didn't survive the build.** DML with the game state ties all plays equal everywhere (R3). The combination (DML on plays counted by the representativeness weights) ties over the next 3 games and gains a little over the rest of the season: +0.5% pooled, against the exploration's +0.6% and +1.4% (R4). In weeks 1–4 of the next-3 forecast it's slightly worse (−0.7%). **The check:** the exploration's split was lucky, and refitting the season models every season costs the combination. Measured honestly, with the models frozen, it gains about +0.3% and +0.9% (R8–R10).
- **Elo:** the ratings still add nothing to Elo's margin (R6), because Elo already holds 81% of them, and neither adds to the closing lines (R18). They do forecast points and team fantasy points well above the league's mean (R7).
- **The vault (2025):** all four forecasts beat the league by more than in the backtest; P3 loses a little that season, within its usual spread; the defense's rest-of-season ranges were too narrow (64.7%) (R16).

**Scorecards:** `data/outputs/team-efficiency/<variant>/<run_id>/scorecard.html`. **Numbers:** [build/summary.txt](build/summary.txt), [build/downstream.txt](build/downstream.txt).
**Vault:** opened 2026-11-14 on the champion's four forecasts, twice: the first run failed leakage checks 3 and 4 in 2025, fixed before any 2025 score was read (R16, R17). **Versions tried:** 3 attempts for each champion forecast in MLflow (the build, the first vault run, the rerun); 1 for the other variants (the first run stopped on a bug in how ranges were grouped, before any score).

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal / no noise | The champion's publisher (`off_next3_ridge`, rerun 2026-11-13 to publish its ratings) and all 12 validated variants (`combo`, `dml`, `ridge` × side × horizon) beat 100 of 100 shuffled refits, and each beats the league's level with the whole 90% interval below zero. `ridge` beats `usual` in all four |
| Calibration and range coverage | The 80% ranges hold 79.3–80.3% for every variant, 2016–2024, every season and every games-left group inside the bar. **The vault:** defense rest-of-season holds 64.7% in 2025, under the 70% group bar, so that scorecard reads "fail" (78.4% pooled); the other three hold 75.4–79.2% (R16) |
| Leakage | 9 of 9 blocking checks pass for all 12, and for the champion's four with the vault (identical at 25 cutoffs, 208,458 rows, after R17's fix). No feature above \|r\| 0.9 |
| Football sanity | Best forecast offenses: 2018 Chiefs, 2018 Saints, 2023 49ers, 2024 Bills. Worst: the 2020 and 2023 Jets, 2018 Cardinals. The CEO saw nothing wrong (2026-11-14) |
| CEO spot-check | R6 and R8 (the CEO's picks, 2026-11-14): both hold (R18, R19) |

## The ladder
Skill = the share of the reference's squared error removed, 2016–2024 (4,734 team-weeks per forecast), 90% interval from resampling weeks. "Below" is the rung below.

| Rung | Method | Offense, next 3 | Defense, next 3 | Offense, rest | Defense, rest | Takeaway carried forward |
|---|---|---|---|---|---|---|
| 0 `league` | the league's level | — | — | — | — | The floor |
| – `usual` | ridge on the usual garbage-time rule's plays (F1's yardstick) | +15.7% vs league | +10.3% | +19.8% | +13.0% | The usual way works, but drops plays that count |
| 1 `ridge` | ridge on every play, counted equally | **+4.9%** vs usual (+4.0 to +5.6) | **+3.9%** (+3.0 to +4.7) | **+7.5%** (+6.3 to +8.6) | **+5.2%** (+4.0 to +6.2) | Every play counts (F1 confirmed, larger) |
| 1b `change` | `ridge` with a weaker pull after a new QB or head coach (P3; offense only) | **+0.3%** vs ridge (+0.1 to +0.6) | — (offense only) | **+0.5%** (+0.3 to +0.8) | — | A team's past says less after a change, most of all after a new coach (R11, R12) |
| 2 `dml` | DML with the game state (situation propensity) | −0.2% vs ridge (−0.3 to +0.0) | −0.1% | +0.0% | +0.2% | Ties: EPA already carries the game state |
| 3 `combo` | DML on representativeness-weighted plays | +0.3% vs dml (−0.0 to +0.5) | −0.2% | **+0.4%** (+0.1 to +0.8) | +0.4% (−0.1 to +0.9) | A small gain over the rest of the season only |

By rule k the ladder stops at `ridge` for the next-3 forecast: `dml` doesn't beat it, and `combo` ties it. On the range score the scorecards agree: next 3, `combo` ties `dml` and `ridge` on both sides; rest of season, `combo` beats both on offense and `ridge` on defense, by amounts that round to 0.000.

## Findings
| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| R1 | Opponent-adjusted ratings forecast a side's EPA per play: 19.8% (offense) and 13.8% (defense) of the league level's error removed over the next 3 games, 25.8% and 17.5% over the rest of the season (`ridge`) | summary.txt; matches the exploration's F2 (20% / 13.5%) | strong | 2016–2024, weeks 1–18 |
| R2 | Counting every play beats the usual garbage-time rule by 3.9–7.5% of its error in all four forecasts, and by 3.1–5.9% in weeks 1–4 | summary.txt, scorecards (range score "better" in all four) | strong | all |
| R3 | DML with the game state adds nothing over every play counted equally (−0.2% to +0.2%, every interval across zero but one at +0.0) | summary.txt | strong | all |
| R4 | The combination gains +0.5% (+0.1 to +0.9) over all plays equal on the rest-of-season forecast, pooled over offense and defense, and ties over the next 3 games (−0.1%, −0.4 to +0.2). In weeks 1–4 of the next-3 forecast it's slightly worse (−0.7%, −1.4 to −0.0). The exploration found +0.6% and +1.4% | summary.txt | suggestive: small, and smaller than the exploration | rest of season |
| R5 | The forecasts' 80% ranges hold 79–80% in every season and every games-left group, from the training misses' quantiles alone | scorecards | strong | all |
| R6 | Elo's margin, refit with the offense and defense gaps (from the champion, `ridge`), misses by −0.03 points a game against Elo refit alone (−0.07 to +0.02; −0.3%): no gain. `combo`'s gaps did the same (−0.2%) | downstream.txt, 2017–2024, 2,111 games | strong (no gain) | game margin |
| R7 | The champion's ratings forecast next game's points (−8.5% squared miss, r 0.29) and the team's PPR fantasy points (next game −9.5%, r 0.30; per game over the next 3, −14.1%, r 0.36) against the league's mean; a hair better than `combo`'s (−8.4%, −9.3%, −13.8%) | downstream.txt, 2017–2024 | strong against a weak yardstick | side targets |

## Why the combination's gain shrank (the CEO asked for the check first, 2026-11-13)
[build/diagnose.py](build/diagnose.py), [build/diagnose.txt](build/diagnose.txt). The build's ratings were run through the exploration's own scoring, switching one difference at a time. The numbers are the combination against all plays equal, 2016–2024, next 3 games / rest of season.

| What was switched | Next 3 | Rest | Reading |
|---|---|---|---|
| The exploration's own ratings | +0.6% | +1.4% | Reproduces the exploration |
| The build's ratings | −0.2% | +0.5% | Reproduces the build: the scoring isn't the cause, the combination's ratings are (all plays equal agrees with the exploration's to r 1.000) |
| The forecast map refit each season (the harness's way) | −0.1% | +0.5% | No effect |
| The prior's scale from 2006–2024 | −0.2% | +0.5% | No effect |
| Five other random cross-fitting splits | −0.1% to +0.2% | +0.5% to +0.9% | **Split luck of about ±0.2 points.** The exploration's split (+0.2% / +0.7% on the build's ratings) was on the lucky side |
| The season models fit once on 2006–2015, used for 2017–2024 (out of sample) | **+0.3%** (+0.0 to +0.6) | **+0.9%** (+0.6 to +1.3) | **The biggest piece, about +0.3 / +0.4 points:** refitting the models every season costs the combination |

| # | Finding | Evidence | Confidence |
|---|---|---|---|
| R8 | The exploration's +0.6% / +1.4% was about a third too high. Honestly measured (models out of sample, a random split), the combination gains about +0.3% over the next 3 games and +0.9% over the rest of the season, give or take about 0.2 points of split luck | diagnose.txt | suggestive |
| R9 | **A frozen yardstick beats a moving one.** The gap and outcome models and the weights fit once on 2006–2015 and kept beat the same models refit each season on the 10 before, by +0.3 / +0.4 points. A likely reason: when the models change every season, this season's ratings aren't on the same scale as last season's prior or the forecast map's training rows | diagnose.txt | suggestive: one comparison, cause not tested |
| R10 | **The build's CRC-32 split isn't random.** CRC-32 is linear, so its last bit is a parity of the game id's bits (team codes, week digits): every "salted" version gave the same split. A proper hash (blake2b) gives the same result (−0.0% / +0.5%), so it didn't cause the shrink, but it's the wrong tool | diagnose.txt | strong |

## The first early-season gain: P3, a weaker pull after a new QB or coach (the CEO's pick, 2026-11-13)
Last season's rating carries into this one through the prior: pull × last season's final. P3 keeps less of it on offense when the team starts the season with a new QB (the week-1 depth chart's QB1 isn't last season's most-started QB) or a new head coach (the opening coach isn't the one who finished last season): pull × (1 − 0.25 × new QB − 0.25 × new coach), the settings round two tuned on 2007–2015. The flags count only once known (the start of week 1). 31% of team-seasons have a new QB, 21% a new coach; the flags agree with round two's on 98% and 100% of team-seasons ([summary.txt](build/summary.txt), `pcf.experts.team_efficiency.changes`).

| Offense, against the champion (`ridge`) | All weeks | Weeks 1–4 | Weeks 5–9 | Rows |
|---|---|---|---|---|
| Next 3 games, every team | **+0.3%** (+0.1 to +0.6) | +0.2% (−0.6 to +1.0) | | 4,734 |
| Rest of season, every team | **+0.5%** (+0.3 to +0.8) | **+1.7%** (+0.8 to +2.6) | | 4,734 |
| Rest of season, new coach | +3.7% (+2.7 to +4.9) | **+11.1%** (+7.5 to +14.4) | +7.6% (+5.5 to +10.0) | 1,005 |
| Rest of season, new QB | +0.9% (+0.4 to +1.5) | +3.7% (+1.1 to +6.3) | +2.0% (+0.8 to +3.2) | 1,617 |
| Next 3 games, new coach | +1.9% (+1.0 to +2.8) | +2.1% (−0.4 to +5.3) | +4.2% (+2.9 to +5.7) | 1,005 |
| Next 3 games, new QB | +0.8% (+0.3 to +1.4) | +0.9% (−0.9 to +2.8) | +2.5% (+1.6 to +3.6) | 1,617 |
| Rest of season, neither | −0.1% (−0.3 to +0.0) | −0.8% (−1.1 to −0.5) | −0.6% (−1.0 to −0.2) | 2,525 |

Both variants pass every check: 9 of 9 leakage checks, 100 of 100 shuffled refits beaten, ranges holding 79.7%; the range score calls both "better" than `ridge` with the whole interval below zero.

| # | Finding | Evidence | Confidence |
|---|---|---|---|
| R11 | **A weaker pull after a new QB or coach beats the champion** on both offense forecasts: +0.3% (+0.1 to +0.6) next 3 games and +0.5% (+0.3 to +0.8) rest of season; 2020–2024 +0.4% and +0.6%. Round two found +0.3% and +0.4%: it held | summary.txt, scorecards | strong (small) |
| R12 | **The gain sits where it should: after a change, early in the season.** Rest-of-season forecasts for teams with a new head coach improve 11.1% in weeks 1–4 and 7.6% in weeks 5–9; with a new QB, 3.7% and 2.0%. The new coach matters more than the new QB | summary.txt | strong for the coach, suggestive for the QB |
| R13 | **Teams with neither change lose a little** (−0.8% in weeks 1–4 of the rest-of-season forecast). Their own prior is unchanged, so the loss comes through the forecast map and the joint fit: the map's slope on the rating is now fit on a mix of full and cut priors. A stronger pull for unchanged teams may win it back (IDEAS I40). **Tested (R14): it doesn't** | summary.txt | suggestive |
| R14 | **R13's loss can't be won back cheaply** (round three, IDEAS I40, the CEO's pick, 2026-11-13). A stronger pull for teams with neither change, tuned on 2007–2015 with the cuts (keep 1.10 × the pull, a = b = 0.25, the same cuts as P3), ties P3 on 2016–2024: +0.0% (−0.1 to +0.1) next 3 games, −0.1% (−0.1 to −0.0) rest of season. Letting the forecast map's slope differ for unchanged teams ties too: −0.0% and −0.2% (−0.4 to −0.1). Unchanged teams lose a little either way. The tuning surface is flat (2007–2015 error moves in the fourth digit). The loss is P3's small price, and P3 stays as built | [r3_keep_pull.txt](explore/r3_keep_pull.txt) (exploration harness) | strong (a tie) |
| R15 | **Mid-season QB changes don't help either** (round four, IDEAS I37, the CEO's go, 2026-11-13). This week's QB (last starter, or the top healthy depth-chart QB when the injury report rules him out: right 92.5% of the time) was used two ways, tuned on 2007–2015: counting other QBs' games for less, and P3's QB cut updated every week. The tuning picks no weight cut: every cut makes the 2007–2015 error worse. The weekly cut (a = 0.5) against P3, 2016–2024: −0.1% (−0.3 to +0.1) next 3 games, −0.1% (−0.3 to +0.1) rest of season. Even on team-weeks whose QB had started under half the games so far, a 0.25 cut gains only +0.3% / +0.4% (intervals across zero), and dropping the old QB's games costs 7.6% / 10.4%. A few games with a new QB say less than the old QB's games still say about the line, receivers and scheme. What could still help is *how good* the new QB is, which is the QB-talent expert's job, not this one | [r4_qb_switch.txt](explore/r4_qb_switch.txt), [r4_qb_switch_check.txt](explore/r4_qb_switch_check.txt) | strong (a tie) |

## The vault (2025), opened once on the champion (2026-11-14)
[build/vault.py](build/vault.py), [build/vault.txt](build/vault.txt). The champion's four forecasts (offense `change`, defense `ridge`) were validated with the vault open; each baseline's 2025 forecasts were made by the same walk-forward backtest, trained only on the seasons before. Reported as-is.

**Opened twice, the second time blind.** The first vault run (08:43) failed leakage checks 3 and 4 in 2025 (R17). The fix changed only when P3's QB flag counts in 2025, and was made before any 2025 score was read; the rerun (09:44) passes every check and is the result below. The CEO agreed to report it so, with this note (2026-11-14). 2016–2024 forecasts are identical to the last digit before and after the fix (4,734 rows each).

| Forecast | Against | 2025 | 2016–2024 | 2025, weeks 1–4 | Ranges hold, 2025 (2016–2024) |
|---|---|---|---|---|---|
| Offense, next 3 (`change`) | the league | **+21.4%** (+17.0 to +24.9) | +20.1% | +11.4% | 79.2% (79.7%) |
| | `ridge` (P3's gain) | **−0.4%** (−0.8 to −0.0) | +0.3% | −0.7% | |
| Offense, rest (`change`) | the league | **+28.3%** (+24.7 to +31.5) | +26.2% | +13.8% | 78.3% (79.7%) |
| | `ridge` (P3's gain) | **−0.7%** (−1.4 to −0.2) | +0.5% | −2.2% | |
| Defense, next 3 (`ridge`) | the league | **+18.8%** (+14.3 to +22.7) | +13.8% | +0.4% | 75.4% (79.7%) |
| | `usual` | +0.8% (−1.4 to +2.3) | +3.9% | −1.8% | |
| Defense, rest (`ridge`) | the league | **+22.4%** (+19.6 to +24.5) | +17.5% | +9.5% | **64.7%** (80.0%) |
| | `usual` | **+1.9%** (+0.3 to +3.4) | +5.2% | +3.3% | |

| # | Finding | Evidence | Confidence |
|---|---|---|---|
| R16 | **The vault holds for the ratings, not for P3.** All four forecasts beat the league's level in 2025 by more than in the backtest (+18.8% to +28.3%), and every play still beats the usual rule on defense (+0.8% / +1.9%, smaller than the backtest's). P3 loses in 2025 (−0.4% / −0.7%), within its own season-to-season spread: in 2016–2024 it lost 3 of 9 seasons over the next 3 games (worst −0.5%) and 4 of 9 over the rest of the season (worst −0.8%). 2025 had 13 new-QB and 7 new-coach teams (2016–2024: 10.9 and 6.8 a season). **The defense's rest-of-season ranges were too narrow in 2025:** 64.7%, misses on both sides (16.7% below, 18.6% above), no bias. That one season fails its group bar (70–90%), so that scorecard's coverage reads "fail"; pooled 2016–2025 it holds 78.4%. In the backtest the same forecast ran 73–89% by season | vault.txt, scorecards | strong for the ratings; P3's gain stays small and uneven |
| R17 | **From 2025, depth charts are known at kickoff**, so the week-1 QB isn't known at week 1's Saturday run (through 2024 it is, from the start of the week). P3's two flags had one known-at (the later of the two, skipping a missing side), so a view without the depth chart called the QB unchanged and the flags known, while the full view held both back: 32 week-1 rows of `change` differed between per-moment and bulk features, which checks 3 and 4 caught. Each flag now has its own known-at; in 2025's week 1 only the coach cut counts | commit 7c84e81, `test_each_flag_waits_for_its_own_facts` | strong |

## Spot-checks (the CEO's picks, 2026-11-14: R6 and R8)
[build/spotcheck_r6.py](build/spotcheck_r6.py) → [spotcheck_r6.txt](build/spotcheck_r6.txt); [build/spotcheck_r8.py](build/spotcheck_r8.py) → [spotcheck_r8.txt](build/spotcheck_r8.txt).

| # | Finding | Evidence | Confidence |
|---|---|---|---|
| R18 | **R6 holds: Elo already has most of what efficiency knows about the margin.** Their margins correlate at r 0.90 (Elo holds 81%). Alone, efficiency misses by 10.26 points a game against Elo's 10.18; together 10.15 (−0.26%, neutral). Where they differ by 3+ points (506 games) the result lands on efficiency's side 55.5% of the time: a little information, worth about 0.1 point against a 10-point miss. No week band gains. The closing spread beats both (9.91) and neither adds to it (fit on every season: 0.99 × line + 0.04 × efficiency). On game totals efficiency beats the league mean by 1.3% but adds nothing to the total line. **Use the offense/defense split (points, fantasy environment), not the margin** | spotcheck_r6.txt, 2017–2024, 2,111 games | strong |
| R19 | **R8 holds: the combination's gain is small, uneven and held by a few teams.** Over the next 3 games it ties (−0.1%) and wins 2 of 9 seasons, losing in weeks 1–9 and gaining +0.5% from week 10. Over the rest of the season it gains +0.5% and wins 6 of 9, but 2016 and 2023 (+2.3% each) carry most of it. By team, five (ARI, TEN, PHI, TB, WAS) gain 0.7% of ridge's error and the other 27 lose 0.2%. With the split luck (±0.2 points) and its cost, the simple rating stays the champion | spotcheck_r8.txt, diagnose.txt | strong |

## Hunches: what the build adds (the CEO called them, 2026-11-14)
| # | Exploration verdict | What the build found | The CEO's verdict |
|---|---|---|---|
| H41 (representativeness weights) | held | Smaller: +0.5% over the rest of the season, a tie over the next 3 games (R4) | **held** |
| H42 (DML) | held (small) | No gain over all plays equal (R3) | **failed** |
| H44 (the EPA–WPA gap in the weights) | held (small) | Inside the combination, so it rises or falls with R4 | **mixed** |
| H40, H43 | unclear, failed | Not rebuilt | unchanged |

## Where it misses
The shared miss lenses are built for player-games, so [build/misses.py](build/misses.py) ([misses.txt](build/misses.txt)) is a team-level stand-in on the champion's next-3 forecasts, 2016–2024: bias (result minus forecast) and skill against the league by group.

| # | Finding | Evidence | Confidence |
|---|---|---|---|
| R20 | **No bias overall or by week; the misses are where you'd expect.** Weeks 1–4 are the weakest (+14.4% / +10.8% against the league, against +22.0% / +16.3% from week 10). The worst offenses play a little worse than forecast (−0.008 EPA per play). Playoff teams beat their forecasts (offense +0.029, defense allows −0.020), a hindsight lens: teams that overperform make the playoffs. **Defenses under a new head coach allow +0.012 EPA per play more than forecast** (+0.006 to +0.018, 1,005 team-weeks), where P3 changes nothing (IDEAS I41) | misses.txt | strong for the shape; suggestive for the new-coach defense |

## The case against
- **The vault was opened twice.** The second run followed a fix made before any 2025 score was read, and the CEO agreed to report it; strictly, VALIDATION.md would call it spent. 2026 live is the clean test either way.
- **P3 lost on the vault** (−0.4% / −0.7%). Its 2016–2024 gain is small (+0.3% / +0.5%) and uneven (it lost 3–4 of 9 seasons), so it may be worth less than the backtest says.
- **The defense's rest-of-season ranges failed in 2025 (64.7%).** Rest-of-season results move together within a season, so one season is few independent draws; but 2019 and 2020 were also low (73%). The ranges may understate how much a whole season can shift (IDEAS I42).
- **P3's new-coach effect may be partly regression to the mean.** Teams that fire their coach often had an extreme season, which regresses anyway, so the flag may stand in for "last season was extreme". That doesn't hurt the forecast, but it changes what the flag means. Its settings came from round two's tuning on 2007–2015 and were scored here once.
- **The combination's edge is small and partly luck.** The check (R8–R10) explains the shrink: the exploration's split was lucky, and the build's per-season model refits cost it. Honestly measured it's about +0.3% / +0.9%, and the split alone moves it by about ±0.2 points. R9 (freeze the models) comes from one comparison, chosen after seeing the result, so it's a hypothesis until a rerun confirms it on the harness.
- **The settings were tuned on 2007–2015 in the exploration, with the forecast map fit on those seasons.** The scored seasons are clean, but every rung's settings came from the same tuning, so the rungs' differences are fair to each other, not to a fresh method.
- **R7's yardstick is weak.** Beating the league's mean on points is easy; the fair test is against Vegas's team total, or against the same map on `ridge`'s ratings. Not run.
- **Scorecards for `usual` and `league` weren't run on their own** (decision 0032, call 11); their rows come from the higher rungs' baselines.

## Pitfalls
- The range groups must be a features column: the first run named a column the model added itself, and every validation stopped at scoring. Groups are now `left_<horizon>`.
- Background validations writing to the same log file after a restart interleave and overwrite lines (`>>` from two processes). Read the saved histories and scorecards, not the logs.
- **From 2025, depth charts are known at kickoff,** not at the start of the week: anything built on the week's depth chart isn't available at the Saturday run in week 1 (R17). Give every input its own known-at; a combined one that skips a missing side makes per-moment and bulk features disagree.
- The experts may not import `pcf.data.tables`: the number of situation bins is repeated in `ratings.py`, with a test that the two agree.

## Not looked at
- P3 on defense (round two tuned none), and a new defensive coordinator, which the flags don't see.
- A consistency score for the published ratings themselves; the player-game miss lenses (team level only, R20).
- Points against Vegas's team totals.

## Could be improved
1. **The play weights without DML** (IDEAS I39): what gain the combination has comes from the representativeness weights, not DML. A weighted ridge needs no outcome model, no bins and no split, so no split luck. Worth a test only if the rest-of-season forecast matters (futures).
2. **If the combination ever returns:** freeze its season models (R9), split with a real hash (R10), and average over several splits (repeated cross-fitting).
3. **The season's first weeks** (IDEAS I38, the CEO's ask): P3 is the first gain there (R11, R12); a stronger pull for teams with no change ties (R14), and so do mid-season QB changes (R15). Next: the new QB's own track record (a QB-talent expert), roster turnover, or the preseason market as a prior (a new data source, needs sign-off).
4. Test R7 against Vegas's team total (R18 found nothing to add to the game's total line).
5. **The defense's rest-of-season ranges** (R16, IDEAS I42): widen them by how much whole seasons shift, judged on 2026 live.
6. **New-coach defenses allow more than forecast** (R20, IDEAS I41): a shift, not just a weaker pull.

## Don't redo
- The combination as the champion: it was weighed and set aside for its size against its cost (R8; the CEO, 2026-11-13).
- DML with the game state on EPA (R3, and the exploration's F7): EPA already holds the game state.
- The usual garbage-time rule: every play counts (R2).
- A stronger pull, or a separate forecast slope, for teams that kept their QB and coach (R14): both tie P3.
- Counting another QB's games for less, or updating P3's QB flag every week (R15): both tie P3; dropping the old QB's games hurts.

## Interface card
| | |
|---|---|
| **Inputs** | `team_game.schedule`, `team_game.efficiency` (new part, decision 0032), `team_game.pregame`, `team_game.opening_coach`, `player_game.roster`, `player_game.depth` (P3's flags) |
| **Outputs** | `outputs/team-efficiency/<variant>/`: `off_epa_next3`, `def_epa_next3`, `off_epa_rest`, `def_epa_rest` (EPA per play relative to the league, mean, q10, q50, q90); **champion: `off_<horizon>_change`, `def_<horizon>_ridge`**; published with `off_next3_change`: `off_rating`, `def_rating` (the champion's ratings, under names that stay if it changes) and their sds (a floor, decision 0032 call 9), `off_pass`, `def_pass`, `off_run`, `def_run`, `off_ssr`, `def_ssr` |
| **Level of detail** | team-game (each team's next game) |
| **Interval** | weekly, every regular-season week, from week 1 (week 1 is last season's rating, pulled toward the league) |
| **Cadence** | in_season, the Saturday run (Thursday games at the Thursday run) |
| **Known at** | each Saturday, from games known by then (play-by-play: kickoff + 1 day) |
| **How to use it** | As a feature: team strength, game script, points and fantasy environment, through the offense/defense split. Not as an Elo add-on or a margin input (R6, R18). The defense's rest-of-season ranges ran narrow in 2025 (R16) |
| **Feeds** | game script, team-strength composite, player opportunity and fantasy, pace |

## Open questions for the CEO
1. ~~Which rating ships as the champion?~~ **Answered 2026-11-13:** `ridge`, every play counted equally.
2. ~~The hunch verdicts for H41, H42 and H44~~ **Answered 2026-11-14:** H41 held, H42 failed, H44 mixed.
3. ~~The early-season work: which first?~~ **Answered 2026-11-13:** the QB or coach change (P3), built (R11–R13).
4. ~~Should P3 join the champion?~~ **Answered 2026-11-14:** yes. Offense forecasts from `change`, defense from `ridge`.

## Technical calls for veto
Decision 0032's 12 calls (the part, earlier-season models, fixed settings, the CRC-32 halves, same-week games, the team index, the per-window forecast map, rungs as variants, the target, the published ratings, the Saturday run, `usual` and `league` as baselines only, P3 as the rung `change`), and 2026-11-14's: P3 in the champion on offense only, the published ratings' stable names, and each P3 flag's own known-at. **The CEO vetoed none (2026-11-14).**
