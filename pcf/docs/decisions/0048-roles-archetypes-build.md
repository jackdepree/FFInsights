# 0048: roles and archetypes' build, its technical calls

**Date:** 2026-11-24 · **Decided by:** Claude (technical calls, listed for the CEO's veto at merge) · **Project:** `roles-archetypes` (the build of the agreed brief; decision 0045 holds the exploration's and the brief's calls)

## What ships, and how it's read

1. **A saved history, not a forecasting expert.** The output is a description (each player-season's coordinates, named role and role table), so it's published as a walk-forward history in the standard output columns (`as_of`, `train_end`, `cadence` = retrospective, `season`), saved under `outputs/roles-archetypes/<run_id>/history.parquet` and pinned in the registry's `history_runs` (decision 0033's way for projects without a registered model). A later model reads it with `view.output("roles-archetypes")`, and an in-season view sees a season only once it's finished (rule m). The precedent is schemes-v2's retrospective traits (a table, not an expert). The forecasting tests are evaluation code in the package, not a shipped forecast.
2. **The history holds the PCA, not the autoencoder:** the autoencoder didn't beat PCA where it mattered (rule k: the tie, or worse, goes to PCA).
3. **Its columns:** `z0`–`z5` (his side's six coordinates) with `z*_lo`, `z*_hi` (90%); `shrink_w`; `role`, `coarse`, `sure`; the role table `t0_*`–`t5_*`; `version` (the last season the fit saw); keys `gsis_id`, `team`, `season`, `side`, `group` (the depth chart's group, to report and compare only); `snaps`.

## The counts and features

4. **Read through the gateway,** a retrospective view at the end of time, one season at a time (`play.pbp`, `player_play.on_field`), cached in `<interim>/roles_archetypes/`. The counts match the exploration's exactly where the rows overlap (checked on 2019).
5. **A player's group is picked within his side** (a fix of the exploration's counts): his most common position among that side's groups. Before, a few defenders with offensive snaps (and the reverse) were placed in the other side's space. The 200+ snap rows per group are unchanged but for one CB and one ILB.
6. **Usage rates are shrunk toward priors from seasons up to the row's season** (walk-forward). The exploration pooled all seasons.

## The spaces

7. **PCA by SVD,** each axis's sign fixed so its largest loading is positive. Standardized on the fit rows (full seasons, 200+ snaps).
8. **Refits:** every completed season, on all completed seasons, rotated to the previous fit by orthogonal Procrustes on the loadings; the first fit is 2016 alone. Step to step, every axis keeps a congruence of 0.95+ (offense) and 1.00 (defense). The published axes are read from the latest (2024) fit. Offense's axes 4 and 5 explain nearly the same variance (5% each), so they rotate between fit windows: against the frozen 2016–2020 fit, the 2024 fit's axes 4–5 match at only 0.26 and 0.20 (defense 0.82–1.00), though the six together span the same space. The history's `z4` and `z5` are read from the 2024 fit's loadings, not the brief's names.
9. **The frozen fit (2016–2020) is used only for test 1,** as the brief says. Everything else, including the forecasting tests, uses the walk-forward history.
10. **Intervals:** each axis's sampling noise from the fit seasons' split halves: var(z_odd − z_even) ≈ a (1/n1 + 1/n2), so a season of n snaps has sd √(a/n), and the 90% interval is ±1.645 sd. Checked on 2021–2024: two halves fall inside their combined 90% band 84–91% of the time per axis (should be 90%).
11. **Players under 200 snaps** are placed and pulled toward their group's mean on the fit rows by w = snaps / (snaps + 200), as the brief says; w = 1 from 200 snaps. That's a step at 200 (from 0.5 to 1), kept because the brief set it; a smooth weight for everyone is the alternative.

## The role table and named roles

12. **The role table, six features per side:** offense snap share, targets per pass snap, carries per run snap, target depth, the team-adjusted run share and 11-personnel share (H107's table); defense snap share, rushes per pass snap, tackles per snap, tackle depth, the team-adjusted 11-personnel and 3rd-down shares (one per defensive axis that repeats; passes defensed left out, at 0.12 within a season).
13. **Named roles are explicit rules on the table's features,** read in order, positionless (no rule reads the depth chart). Ten cuts, set once on 2016–2020 and frozen: at a valley (the thinnest point of the feature's smoothed distribution, so few players sit near it) where there is one, or at a stated quantile (the backs' and tight ends' run tilt at the median, the slot cut at the 80th percentile of split-out players, the tackler cut at the 67th of the front). The cuts were picked while looking at flips on 2016–2020 only; 2021–2024 was scored once.
14. **Twelve fine roles, five coarse ones.** Offense: early-down back, passing-down back (back); blocking tight end, inline tight end (in tight); slot receiver, deep threat, outside receiver (split out). Defense: pass rusher, box linebacker, run defender (front); slot defender, base defensive back (coverage). **The names are working names: naming is the CEO's taste call.**
15. **How sure:** for each cut a rule passed, the chance his true value is on the same side, from that feature's split-half noise at his snaps; the product over the cuts. Calibrated on 2021–2024 (said 0.98, held 0.96; said 0.83, held 0.85; said 0.68, held 0.69; said 0.47, held 0.52).

## The exploratory method

16. **The autoencoder:** p → 16 → 6 → 16 → p, tanh, full-batch Adam (rate 0.01, weight decay 0.0001), 1,500 epochs, on the PCA's standardized features and fit rows. Its codes are standardized and rotated to the PCA's coordinates on the fit rows (orthogonal Procrustes), so the two compare axis for axis. Three seeds, averaged after alignment. It reconstructs 0.90 of the variance against PCA's 0.84 (offense) and 0.91 against 0.85 (defense).

## The tests

17. **The ladder's models:** the lasso (the shared `pcf.baselines.lasso.fit_lasso`) on a standardized target, its penalty chosen inside each window (fit on the earlier target seasons, scored on the window's last); trees are scikit-learn's histogram boosting with fixed settings (300 rounds, rate 0.05, 15 leaves, 20 rows a leaf, no early stopping).
18. **Rows:** consecutive-season pairs with 200+ snaps both seasons; inputs from season s's main team (most snaps), the target from season s + 1's totals across teams. Walk-forward by target season: each is fit on earlier target seasons only, scored 2021–2024.
19. **Intervals:** 90%, Poisson draws over players (2,000), for the ladder; over team-seasons for substitutes.
20. **Signal:** the coordinates' lasso against 20 refits on targets shuffled within target season and position (VALIDATION §5, retrospective); it must beat all 20.
21. **The yardstick:** `score_input` on the receiving and rushing rest-of-season boards beside participation, the prior being the previous season's main-team values (missing: the column's median). The 19 copies are shuffled **within season and position** (the brief), not the yardstick's own within-week copies: each copy moves a player's whole prior to another player of the same season and group.
22. **Substitutes:** H101's design on the build's walk-forward prior-season coordinates (the pooled space, raw axes), as the brief's test 5 says. A sensitivity with each axis scaled within position is reported beside it, not as the verdict.
23. **Test 1's mover clause is read as written** ("movers keep at least half of each component's season r"): offense fails it on one axis (the red zone, oz2, kept 42%), the axis that doesn't repeat anyway. The other reading (each of the repeating components) passes. The CEO decides which reading the brief meant.

## Not done here

24. **The vault stays closed** (the brief: "the vault is 2025, untouched"). Opening it means building 2025's counts; the CEO decides, as for the crude forecaster.
25. **Measurables beside the space** are height, weight and draft slot from the roster. The 40 isn't in the tables (the combine is a raw file only), so it isn't published; a `player` combine part is a separate data task.
26. **No MLflow model is registered** (no project has one); the run is logged as an attempt with its metrics and report.
