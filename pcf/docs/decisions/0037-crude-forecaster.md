# 0037: The crude forecaster and its yardstick: variant pins, one Saturday moment, the row rule, the ladder's rule, and how a gain is read

**Date:** 2026-11-17 · **Decided by:** the CEO agreed the brief and its four calls (2026-11-15: keep team yards; play level later; only players expected to play at least one snap; yards only). The calls below are Claude's technical calls, listed for veto at merge. · **Project:** `crude-forecaster`

**Decision:**
- **The package:** `pcf.baselines.crude` (`features`, `fitting`, `model`, `yardstick`). It is a yardstick like the other baselines, so it lives beside them; phase 0, never a product.
- **48 variants**, `<target>_<horizon>_<rung>`: 4 targets (passing, rushing, receiving, team) × 3 horizons (next, next3, rest) × 4 rungs (season, lasso, trees, mix). Team yards allowed is the yards-gained forecast filed under the defense (`yardstick.allowed`), so the five targets are four forecasts and a mirror (exploration F2).

**The calls:**
1. **One variant of a project can be pinned as an input** (`"elo/margin": 1`).
   - **The problem:** every finished expert keeps several variants under one id (`outputs/<id>/<variant>/<run>/`), and the gateway read only `outputs/<id>/<run>/`. No variant has an MLflow model.
   - **The fix:** an input `"<id>/<variant>"` reads the run `registry.yaml` pins under the project: `history_runs: {<variant>: {1: <run_id>}}`. `gateway.history_run` and `contract.check_expert` (`project_of`) know the form; nothing else changes. Decision 0033's `{1: run}` form still works.
   - **The pins** (all 2016–2024, Saturday run, the runs each RESULTS.md cites or its latest final): participation `trees_week` 2abc96bc, `lasso_h3` f0da2987, `lasso_rest` 2de0578d; Elo `margin` 21082e26, `total` 417b504c; team-efficiency `off_next3_change` 0d6fc9fb (it publishes both sides' ratings); pace `plays_full` dbdb566f, `dropbacks_full` d39f53b1, `runs_full` 252161d4, `proe_shrunk` 331e6a9a, `pace_oe_shrunk` fdbdc0e5; schemes-v2 `pass_oe_rung2` 113ae2db, `shotgun_rung2` dfa8be86, `depth_rung2` b3fb56d8, `tempo_shrunk` 88ffef17.
2. **One forecast moment: the Saturday run** (Thursday games at the Thursday run). Every pinned expert was made at that run, so every input is lined up to it; this fixes the exploration's mixed Tuesday and Saturday moments (its case against).
3. **The row rule:** a player counts when participation's saved chance of a snap (`trees_week` `p_nonzero`) is at least 50%, known before kickoff. Rows where he took a snap are reported as a check, never the headline (a filter on the outcome).
4. **Positions are the exploration's:** passing QBs; rushing RBs; receiving WRs, TEs and RBs. QB rushing is left out (I67).
5. **Crude inputs average the games he played** (a stat or an offensive snap), not every rostered game as the exploration did. With the row rule, a missed game says nothing about the next one he plays; participation carries availability. A unit with no earlier games gets 0 and `no_history` = 1; week 1's season-so-far is last season's.
6. **Team yards gained = passing + rushing yards**, sack yards not taken off (the exploration's). Team volume is plays (attempts, carries, sacks).
7. **Horizons are yards per game** over the team's next 3 regular-season games, or the rest of its regular season, from this one; only complete windows are scored. A week he has no row (or no stats), on any team, counts 0.
8. **Regular season only**, in features, rows and outcomes (the exploration's). Playoff rows aren't forecast.
9. **Every rung fits the same way:** the window's earlier 80% first (the lasso picks its penalty there, the baselines' rule), its latest 20% scored for the ranges, then refit on everything. Ranges: the latest 20%'s misses at q10, q50 and q90 by position and fifth of the forecast, since yards misses grow with the forecast.
10. **The trees are xgboost** (installed for this project, `uv add xgboost`; ARCHITECTURE.md already lists it) with fixed plain settings: 300 trees, learning rate 0.05, depth 4, at least 50 rows a leaf, rows and columns subsampled 80%, 4 threads. No tuning: a yardstick is meant to change rarely.
11. **One fit per season** (`refit season`), before week 1, on every earlier row, recency-weighted (half-life 4 seasons). The exploration's walk; weekly refits would cost 17 times as much for a yardstick.
12. **The ladder's rule:** the lasso must beat the season average on the range score (90% interval above zero, paired by week); the trees must beat the lasso; the mix (the CEO's method) must beat both plain rungs. Otherwise the simpler rung is the champion, per target and horizon.
13. **How a gain is read:** the headline is the share of the crude forecast's held-out squared error removed (the exploration's unit, comparable with the noise ceiling); the range-score change is reported beside it and decides the no-noise verdict (VALIDATION.md §5). Both paired on the same rows, 90% intervals from 2,000 resamples of whole weeks.
14. **Method C is exact:** every subset of the members is fit (players: 6 members, 64 fits; teams: 5, 32). The members are the five finished experts plus a **shuffled copy**: participation's columns for players and Elo's for teams, shuffled together within each week. Its share must cover zero.
15. **Missing expert values** (a game an expert didn't forecast) get the moment's median; more than 2% missing on a moment raises.
16. **The yardstick's own noise:** each added-alone gain refit with three tree seeds (trees and mix only) and with each of 2016, 2017 and 2018 left out of training (in every fold's training), plus the two halves of the scored seasons (2019–2021, 2022–2024).
17. **SHAP on held-out rows only:** each test season's model, fit before it, explains that season's rows. Exact for the lasso, TreeSHAP for the trees, averaged for the mix. An explanation, never the test (the brief).

**Why:** the brief, as agreed, plus the exploration's findings F1–F12 and its case against.
