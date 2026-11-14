# 0033: Snap leverage as a shared play part, usage from the morning-after map, nine variants on the same trees

**Date:** 2026-11-14 · **Decided by:** the CEO agreed the brief and its open questions ("1c, 2 yes, if it fails the no noise target then we will downscale this project from an expert to simply an investigation and feature engineering", 2026-11-14). The calls below are Claude's technical calls, listed for veto at merge. · **Project:** `snap-leverage`

**Decision:**
- **A new table part, `play.leverage`** (`pcf.data.tables.leverage`): each snap's leverage before the snap. It's known when play-by-play is, and it's an after-kickoff part. Any project can read it.
- **The expert `snap-leverage`** (`pcf.experts.snap_leverage`) has 9 variants: 3 targets × 3 rungs.
  - **Targets:** leverage share over the next 3 games, leverage share over the rest of the regular season, snap share over the next 3 games.
  - **Rungs:** `plain`, `lev`, `full`.

**The calls:**
1. **Leverage is fit on earlier seasons only**, like `play.pace` (decision 0028).
   - **The model:** gradient-boosted trees of WPA² on the situation before the snap: quarter, clock, score margin, down, distance, field position, both teams' timeouts, and the win chance going in.
   - **Training seasons:** up to the 10 seasons before, never fewer than 3, regular season only. The fits are cached per season, keyed by `MODEL_VERSION`, and checked to have seen only earlier seasons.
   - **Leverage** is the spread (the model's square root) over its mean on the training snaps, so 1.0 is an average snap.
   - **High stakes** is a fixed cut: the training snaps' 80th percentile. The exploration cut each season at its own 80th percentile, which looks ahead in season.
   - **Snaps:** runs, passes, kneels and spikes with a win chance, every season type; two-point tries are left out.
   - **The part covers 2002–2026.** Its quality matches the exploration's: it correlates 0.555 with the actual swing in 2016 and 0.559 in 2024.
   - **Disclosed:** a sanity check of the rebuilt part also printed 2025's figure (0.574) by mistake. That is the leverage part's quality, not a forecast score, and no setting was chosen from it. The vault's forecasts are untouched.
2. **A pinned version with no MLflow model reads the run the registry pins.**
   - **The problem:** participation-live has no registered model, so `view.output` had no version to read.
   - **The fix:** `registry.yaml` gives it `history_runs: {1: 6f13a56965644245a9c06384f0959448}`, its final map run (8.6 million rows, 2019–2024; the run RESULTS cites). `gateway.history_run` tries MLflow first and falls back to this pin.
   - **Why:** the pin is reviewed and merged like code, so the handoff stays versioned (rule e) without registering a model the project never registered.
3. **Usage comes from the map, each snap counted by its on-field chance** (`usage.usage`; the brief).
   - Per player-game and side: leverage share, high-stakes share, the passing-down role gap (high-stakes share minus snap share), and trust over expected.
   - **Trust over expected:** his high-stakes snaps beyond his on-field rate in each fifth of the expected pass chance (`pcf_xpass`, fixed fifths), over his side's high-stakes snaps.
   - **Missed games:** a rostered game he missed counts 0 for the shares, and the role and trust measures are left empty for it.
4. **The plain rung uses the official snap counts, not the map's snap share.**
   - Its features: last game, last 3, season to date, last season, games so far, position group, first-year player.
   - **Why:** that's the yardstick anyone would use, so the no-noise test asks whether the leverage measures add anything beyond it.
5. **Last season's shares were added** (`snap_prev`, `lev_prev`). The exploration's rows started after a player's first game; the expert also forecasts week 1.
   - In 2019 `lev_prev` is empty (the map starts in 2019). A fit leaves out any column with no values in its window.
6. **Every rung is the same trees**, so a comparison changes only the features.
   - The trees are the exploration's (F6): 250 iterations, learning rate 0.06, 31 leaves, at least 100 rows a leaf.
   - **Changed from the draft:** the brief's draft said rung 1 would be ridge regression. With every rung on the same model, the no-noise verdict tests the features alone. The exploration's linear check agreed with the trees.
   - **Ranges:** refit without the latest 20% of the window, and take those rows' misses at q10, q50 and q90 by position group, clipped to 0–1 (participation's way).
   - **Baselines:** `full` against `lev` and `plain`; `lev` against `plain`.
7. **The targets:**
   - **Snap share:** from the official snap counts, known when the window's last game's counts are.
   - **Leverage share:** from nflverse's true participation × `play.leverage`. It's known after the season (post-season only, rule m), so in-season fits train on earlier seasons only.
   - **Windows:** the team's games from this one on; the next-3 window needs 3 games left. A week he has no row, on any team, counts 0. Only complete windows are scored.
   - **The map never trains on true participation** (rule e). True participation is the outcome, not an input.
8. **The scored seasons are 2020–2024.**
   - `first_train` is 2019, the map's first season, so 2020 is fit on 2019 alone. The brief's draft said 2021–2024; scoring 2020 adds a season at the cost of a thin first fit.
   - **The vault is 2025**, opened once, at validation.
9. **Run settings:** `--refit season --shuffles 20` (participation's), one process per variant.
10. **An expert may declare `first_read`**, the earliest season it reads, and the harness's default gateway then holds only the seasons from it on (`gateway.for_expert`).
    - **Why:** every view of `play` includes its spine, the 373-column play-by-play (2.7 GB for all seasons), and the leakage checks copy whole parts.
    - snap-leverage reads from 2018 (last season's shares for 2019). No other expert declares it, so nothing else changes.
11. **Not live yet.**
    - **Why:** participation-live's map isn't made in the weekly run, so snap-leverage can't forecast 2026's games yet.
    - **What it needs:** the map added to the ledger run, which needs the CEO's approval.

**Why:** the brief, as agreed, plus the exploration's findings F1–F11.
