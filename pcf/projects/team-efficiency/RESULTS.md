# Results: Opponent-adjusted efficiency (`team-efficiency`)

**Date:** 2026-11-13 · **Status:** building. **Champion: `ridge`, every play counted equally** (the CEO, 2026-11-13: "Ship the simple rating, every play counted equally, as the champion"). Not done: the hunch verdicts, the early-season work (I38) and the vault · **Brief:** [BRIEF.md](BRIEF.md) (agreed 2026-11-13) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** `team-efficiency` · **Technical calls:** [decision 0032](../../docs/decisions/0032-team-efficiency-build.md)

## In short
**The champion is the simple rating** (`ridge`: opponent-adjusted EPA per play on every play, counted equally, with recency and last season as a prior). The CEO chose it on 2026-11-13 over the combination, whose honest edge (about +0.3% / +0.9%, R8) is about the size of its own split luck and costs an outcome model, 14 situation bins and cross-fitting. DML alone adds nothing (R3).

PCF now rates every team's offense and defense after every game, opponent-adjusted, from a new table part (`team_game.efficiency`), and forecasts each side's EPA per play over its next 3 games and the rest of the season.
- **The big win is counting every play.** Ratings on every play, counted equally (`ridge`), beat the usual garbage-time rule (`usual`) in all four forecasts, by 3.9–7.5% of its squared error, and in weeks 1–4 too (R2). Against the league's level they remove 14–26% of the error (R1), as the exploration found.
- **The extras the exploration found mostly didn't survive the build.** DML with the game state ties all plays equal everywhere (R3). The combination (DML on plays counted by the representativeness weights) ties over the next 3 games and gains a little over the rest of the season: +0.5% pooled, against the exploration's +0.6% and +1.4% (R4). In weeks 1–4 of the next-3 forecast it's slightly worse (−0.7%). **The check:** the exploration's split was lucky, and refitting the season models every season costs the combination. Measured honestly, with the models frozen, it gains about +0.3% and +0.9% (R8–R10).
- **Elo:** the ratings still add nothing to Elo's margin (R6). They do forecast points and team fantasy points well above the league's mean (R7).

**Scorecards:** `data/outputs/team-efficiency/<variant>/<run_id>/scorecard.html`. **Numbers:** [build/summary.txt](build/summary.txt), [build/downstream.txt](build/downstream.txt).
**Vault:** closed (2025). It opens once, at validating, after the champion is chosen.
**Versions tried:** 1 per variant (the first run stopped on a bug in how ranges were grouped, before any score; fixed and rerun).

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal / no noise | The champion's publisher (`off_next3_ridge`, rerun 2026-11-13 to publish its ratings) and all 12 validated variants (`combo`, `dml`, `ridge` × side × horizon) beat 100 of 100 shuffled refits, and each beats the league's level with the whole 90% interval below zero. `ridge` beats `usual` in all four |
| Calibration and range coverage | The 80% ranges hold 79.3–80.3% for every variant. Every season and every games-left group inside the bar |
| Leakage | 9 of 9 blocking checks pass for all 12: identical at 25 cutoffs when future data is changed or deleted. No feature above \|r\| 0.9 |
| Football sanity | Best forecast offenses: 2018 Chiefs, 2018 Saints, 2023 49ers, 2024 Bills. Worst: the 2020 and 2023 Jets, 2018 Cardinals. The CEO's review is pending |
| CEO spot-check | pending |

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
| R13 | **Teams with neither change lose a little** (−0.8% in weeks 1–4 of the rest-of-season forecast). Their own prior is unchanged, so the loss comes through the forecast map and the joint fit: the map's slope on the rating is now fit on a mix of full and cut priors. A stronger pull for unchanged teams may win it back (IDEAS I40) | summary.txt | suggestive |

## Hunches: what the build adds (verdicts are the CEO's to call)
| # | Exploration verdict | What the build found |
|---|---|---|
| H41 (representativeness weights) | held | Smaller: +0.5% over the rest of the season, a tie over the next 3 games (R4) |
| H42 (DML) | held (small) | No gain over all plays equal (R3) |
| H44 (the EPA–WPA gap in the weights) | held (small) | Inside the combination, so it rises or falls with R4 |
| H40, H43 | unclear, failed | Not rebuilt |

## Where it misses
Not run yet. The miss lenses run on the champion, once it's chosen.

## The case against
- **P3's new-coach effect may be partly regression to the mean.** Teams that fire their coach often had an extreme season, which regresses anyway, so the flag may stand in for "last season was extreme". That doesn't hurt the forecast, but it changes what the flag means. Its settings came from round two's tuning on 2007–2015 and were scored here once.
- **The combination's edge is small and partly luck.** The check (R8–R10) explains the shrink: the exploration's split was lucky, and the build's per-season model refits cost it. Honestly measured it's about +0.3% / +0.9%, and the split alone moves it by about ±0.2 points. R9 (freeze the models) comes from one comparison, chosen after seeing the result, so it's a hypothesis until a rerun confirms it on the harness.
- **The settings were tuned on 2007–2015 in the exploration, with the forecast map fit on those seasons.** The scored seasons are clean, but every rung's settings came from the same tuning, so the rungs' differences are fair to each other, not to a fresh method.
- **R7's yardstick is weak.** Beating the league's mean on points is easy; the fair test is against Vegas's team total, or against the same map on `ridge`'s ratings. Not run.
- **Scorecards for `usual` and `league` weren't run on their own** (decision 0032, call 11); their rows come from the higher rungs' baselines.

## Pitfalls
- The range groups must be a features column: the first run named a column the model added itself, and every validation stopped at scoring. Groups are now `left_<horizon>`.
- Background validations writing to the same log file after a restart interleave and overwrite lines (`>>` from two processes). Read the saved histories and scorecards, not the logs.
- The experts may not import `pcf.data.tables`: the number of situation bins is repeated in `ratings.py`, with a test that the two agree.

## Not looked at
- P3 on defense (round two tuned none), and a new defensive coordinator, which the flags don't see.
- The vault, the miss lenses, a consistency score for the published ratings themselves.
- Points against Vegas's team totals.

## Could be improved
1. **The play weights without DML** (IDEAS I39): what gain the combination has comes from the representativeness weights, not DML. A weighted ridge needs no outcome model, no bins and no split, so no split luck. Worth a test only if the rest-of-season forecast matters (futures).
2. **If the combination ever returns:** freeze its season models (R9), split with a real hash (R10), and average over several splits (repeated cross-fitting).
3. **The season's first weeks** (IDEAS I38, the CEO's ask): P3 is the first gain there (R11, R12). Next: a stronger pull for teams with no change (I40), then roster turnover, mid-season QB changes (I37), or the preseason market as a prior (a new data source, needs sign-off).
4. Test R7 against Vegas's team total.

## Don't redo
- The combination as the champion: it was weighed and set aside for its size against its cost (R8; the CEO, 2026-11-13).
- DML with the game state on EPA (R3, and the exploration's F7): EPA already holds the game state.
- The usual garbage-time rule: every play counts (R2).

## Interface card
| | |
|---|---|
| **Inputs** | `team_game.schedule`, `team_game.efficiency` (new part, decision 0032) |
| **Outputs** | `outputs/team-efficiency/<variant>/`: `off_epa_next3`, `def_epa_next3`, `off_epa_rest`, `def_epa_rest` (EPA per play relative to the league, mean, q10, q50, q90); **champion: `<side>_<horizon>_ridge`**; published with `off_next3_ridge`: `off_ridge`, `def_ridge` and their sds (a floor, decision 0032 call 9), `off_pass`, `def_pass`, `off_run`, `def_run`, `off_ssr`, `def_ssr` |
| **Level of detail** | team-game (each team's next game) |
| **Interval** | weekly, every regular-season week, from week 1 (week 1 is last season's rating, pulled toward the league) |
| **Cadence** | in_season, the Saturday run (Thursday games at the Thursday run) |
| **Known at** | each Saturday, from games known by then (play-by-play: kickoff + 1 day) |
| **How to use it** | As a feature: team strength, game script, points and fantasy environment. Not as an Elo add-on (R6) |
| **Feeds** | game script, team-strength composite, player opportunity and fantasy, pace |

## Open questions for the CEO
1. ~~Which rating ships as the champion?~~ **Answered 2026-11-13:** `ridge`, every play counted equally.
2. **The hunch verdicts for H41, H42 and H44** in light of the build (table above).
3. ~~The early-season work: which first?~~ **Answered 2026-11-13:** the QB or coach change (P3), built (R11–R13).
4. **Should P3 join the champion?** Offense would forecast from `change` (`ridge` plus the weaker pull); defense stays `ridge`.

## Technical calls for veto
Decision 0032's 12 calls (the part, earlier-season models, fixed settings, the CRC-32 halves, same-week games, the team index, the per-window forecast map, rungs as variants, the target, the published ratings, the Saturday run, `usual` and `league` as baselines only), plus P3 deferred.
