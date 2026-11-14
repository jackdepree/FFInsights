# 0032: Team efficiency rates from a per-game table part, with fixed walk settings and every rung as a variant

**Date:** 2026-11-13 · **Decided by:** the CEO agreed the brief with both exploration rounds' changes and asked for the build ("I think we can agree on the brief and start the build", 2026-11-13). The calls below are Claude's technical calls, listed for veto at merge. · **Project:** `team-efficiency`

**Decision:**
- **A new table part, `team_game.efficiency`** (`pcf.data.tables.efficiency`). Per offense and game it holds the sums the ratings need:
  - all plays (count, EPA, EPA squared);
  - the usual garbage-time rule's plays;
  - passes and runs apart;
  - series and successful series;
  - per DML situation bin (win-chance band × half, 14 bins): plays, EPA less the outcome model, and the same times the offense's and the defense's representativeness weight.
  - It's known when play-by-play is (kickoff + 1 day), and it's an after-kickoff part.
- **The expert `team-efficiency`** (`pcf.experts.team_efficiency`) has 20 variants: side (offense, defense) × horizon (next 3 games, rest of season) × rung (`league`, `usual`, `ridge`, `dml`, `combo`).

**The calls:**
1. **The season's models are fit on earlier seasons only**, like pace's expected models (decision 0028).
   - **Training seasons:** up to the 10 seasons before, and never fewer than 3. The first rated season is 2002 (play-by-play starts in 1999).
   - **The models:** the EPA–WPA gap model, the outcome model, the gap's 5% tails and the kinds' weights.
   - **Caching:** cached per season and keyed by `MODEL_VERSION`. Each set is checked to have been fit only on earlier seasons before it's used.
   - **Why:** the exploration fit them once, on 2006–2015, which put 2007–2015's own seasons in their training data. 2016's models are fit on exactly 2006–2015, so the scored seasons match the exploration's setup from 2016 on.
2. **The settings are fixed** at the exploration's, tuned on 2007–2015 (half-life weeks, prior strength, pull):

   | Rung | Offense | Defense |
   |---|---|---|
   | `usual` | 16, 10, 0.5 | 16, 10, 0.5 |
   | `ridge`, `dml` | 16, 5, 0.7 | 16, 5, 0.7 |
   | `combo` | 16, 5, 0.7 | 1000, 10, 0.5 |

   - **The prior's strength is in games' worth of plays:** each measure's mean per team-game in 2006–2015 (62.6 plays; 42.9 under the usual rule; 36.1 passes; 26.5 runs; 27.6 series). The exploration took this mean over 2006–2024, a slight look at later seasons, now removed.
   - **Pass, run and series-success ratings** (published, not forecast) use the all-plays settings. Round two tuned them but didn't record them.
3. **DML's cross-fitting halves** are a checksum of the game id (CRC-32 mod 2), not polars' hash, so they don't change between library versions. The halves differ from the exploration's, so the numbers move slightly.
4. **The ratings at a moment use every game known by then,** including earlier games of the same week (a Thursday game at the Saturday run). The exploration used earlier weeks only. The same-week game goes in at full recency weight.
5. **The team index comes from the schedule,** and each season's prior is centred over the teams that played. A team with no games adds nothing, so per-moment and bulk views agree, and synthetic leagues work.
6. **The forecast map is refit in each training window:** weighted least squares of the target on 1, own rating, opponents' mean rating and home share, with the harness's recency weights. The exploration fit it once, on 2007–2015.
   - **Ranges:** the training misses' quantiles per number of games in the window (`left`).
7. **Every rung is a variant on the same features.**
   - **What `features` computes:** one function computes every rung's ratings, so each variant's baselines reuse its features and compare on identical rows.
   - **The baselines:** `combo` against `dml`, `ridge` and `league`; `dml` against `ridge` and `league`; `ridge` against `usual` and `league`; `usual` against `league`.
   - **`usual` is kept** as F1's yardstick, so the build reproduces the exploration's first finding.
8. **The target** is EPA per play over the window's games, relative to each game's weekly league mean.
   - **Which windows count:** regular season only, complete windows only. The next-3 window shrinks at the season's end, as in the exploration.
   - **When it's known:** when the last of its weeks is known.
9. **Published for higher layers** (on `off_next3_combo`, decision 0021's mechanism): each team's combination ratings with their sds, and its pass, run and series-success ratings.
   - **The sd** is the ridge's own posterior sd under its prior, treating plays as independent. It leaves out the prior's own error, so it's a floor, not a calibrated interval. The forecast ranges are the validated uncertainty.
10. **The Saturday run.** Thursday games are predicted at the Thursday run, as pace does.
11. **`usual` and `league` are scored as baselines, not validated on their own.** Their histories come from the `ridge`, `dml` and `combo` runs' baselines, which reuse the same features on the same rows (`validate.baseline_history`), so the ladder reads the same. What's skipped is their own shuffled-signal, leakage and calibration checks: nothing ships from the floor or the yardstick. It saves about two hours of the four.
12. **P3, the weaker pull after a new QB or head coach, is built as the offense-only rung `change`** (the CEO chose it as the first early-season work, 2026-11-13; it had been deferred for the core's results).
    - **The flags** (`team_efficiency.changes`): new QB = the week-1 depth chart's QB1 isn't last season's most-started QB (`team_game.pregame.qb_id`, rather than round two's main passer by dropbacks from play-by-play: the same answer on 98% of team-seasons, from a team-game part). New coach = the opening coach isn't the coach of last season's final regular-season game. Known when both this season's facts are (the start of week 1); before that, no change.
    - **The settings** are round two's, tuned on 2007–2015: a = b = 0.25 on offense, none on defense, so there are no `def_*_change` variants.
    - **Inputs grow** by `team_game.pregame`, `team_game.opening_coach`, `player_game.roster` and `player_game.depth` for every variant, since the features are shared.
    - **Kept in the expert, not the shared package,** until a second user (I37's in-season QB changes) needs it.

**Alternatives:**
- **Reading play-by-play in the expert:** about 2.7 GB in memory, once per moment. The part is 13,000 rows.
- **Tuning the settings inside each training window:** the honest nested version. It costs 48 walks per window, and the exploration found the settings flat across seasons.
- **One variant per side and horizon with the rung as a setting:** fewer scorecards, but the ladder couldn't be read off the baselines.

**The champion (the CEO, 2026-11-13): `ridge`, every play counted equally.** The published ratings (call 9) move to `off_next3_ridge`: `off_ridge`, `def_ridge` and their sds, with pass, run and series success. `dml` and `combo` stay as validated variants, not used downstream. The two revisions below were found by the check and **not applied**, since the champion uses neither the season models nor the split; they apply if the combination returns (RESULTS, "Could be improved" 2):
- **Call 1:** freeze the season models. Fit them once on 2006–2015 and use them for every season from 2016 on, including the vault and 2026; 2002–2015 keep models fit on earlier seasons only, for the priors. Refit only on purpose, as a new `MODEL_VERSION`. Why: refitting each season cost the combination about +0.3 / +0.4 points (R9), probably because a moving yardstick puts each season's ratings on a different scale from last season's prior.
- **Call 3:** split with blake2b, not CRC-32. CRC-32 is linear, so its last bit is a parity of the game id's bits, not a random half (R10). It didn't change the result.

**2026-11-14: P3 joins the champion, and the vault.**
- **P3 in the champion, offense only** (the CEO: "Ok, let's rerun the validation and start to close out this expert", answering whether P3 joins). Offense forecasts from `change`, defense from `ridge` (P3 has no defense cut).
- **The published ratings get stable names:** `off_rating`, `def_rating` and their sds (offense from `change`, defense from `ridge`), on `off_next3_change`, with pass, run and series success. A later champion changes what fills them, not what readers ask for. A test holds them equal to the champion's rungs.
- **Each P3 flag has its own known-at** (`changes.season_changes`: `qb_known_at`, `coach_known_at`). The shared one (the later of the two, skipping a missing side) failed 2025's leakage checks 3 and 4: from 2025 the depth chart is known at kickoff (RESULTS R17). A flag not known yet now waits. 2016–2024 forecasts didn't move.
- **The vault** opened on the champion's four forecasts with `--open-vault`; scored apart by `build/vault.py`. Opened twice: the first run failed checks 3 and 4, fixed before any 2025 score was read; the CEO agreed to report the rerun with that note.
- **The CEO vetoed none of the calls above or calls 1–12 (2026-11-14).**
- **The weekly ledger** (the CEO: "1 yes. 2 yes.", approving the merge and the ledger): the champion's four forecasts join `live.MODELS`, plus `off_next3_ridge` and `off_rest_ridge` as P3's yardstick, since P3 lost a little on the 2025 vault and 2026 live is the next honest test (a technical call). Each adds about 3.3 minutes of live features to a run, about 20 minutes for the six.
