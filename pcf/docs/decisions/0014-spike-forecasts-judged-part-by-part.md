# 0014: Spike forecasts save and are judged by their two parts

**Date:** 2026-11-04 · **Decided by:** the CEO (the idea and the go-ahead), Claude (how it's built)

**Decision:**
- **An expert marks an amount with a pile of results at exactly 0 as `spike = True`.** Its `predict` also returns `p_nonzero` and `if_nonzero_mean`, `_q10`, `_q50`, `_q90`, and they're saved with the history, so higher layers can read each part. The mean must equal `p_nonzero × if_nonzero_mean`, and `check_output` enforces it.
- **The harness judges each part against its existing bar** (`calibration.spike_report`, VALIDATION.md §7). The chance of a result above 0 is judged as a probability. The range and q50 are judged on rows where the result was above 0. The blend's coverage is reported, not judged. No bar's number changed.
- **`trees_spikes` adds a third part where exactly 100% is common:** a position gets it if 20% or more of its on-field games in the training window are every snap, in practice only QBs. It uses a logistic model, because boosted trees were badly overconfident here (slope 0.67, against 0.89). The chance of every snap isn't saved or judged by the harness yet.
- **Players on the injury report get their own residuals** in `trees_status` and `trees_spikes`, falling back to all listed players, then to everyone at that size, when a size has under 30 rows.

**Why:** a result of exactly 0 counts as inside any range starting at 0, so a perfect blended forecast covers 85.8% and fails the 75–85% bar (participation#F13). Judging the blend hid two real misses (F23), and the saved history didn't let higher layers tell "may not play" from "plays a small role".

**Alternatives:**
- *Widen the bar for spike forecasts.* The simplest change, but it would still hide misses inside the blend, and the right bar would differ with how often each forecast is 0.
- *Judge only rows with q10 above 0* (first proposed in `participation` RESULTS). Those rows can still hold a result of 0, and it says nothing about the chance of 0.
- *A separate expert per part.* The harness would judge them as ordinary models, but the parts would have separate histories that could drift apart, and they'd fill the registry with near-copies.
- *Direct quantile models for the share.* They might handle both misses at once, but they cost three fits per position and season, and the mixture needs every level. Worth trying if the simple fixes stop being enough.

**Later (2026-11-05):** `trees_top` adds to `trees_spikes`: games that aren't every snap stay below 100%, and the chance of every snap is recalibrated with isotonic regression on the latest 20% of each training window, as residuals are. Platt scaling was worse (QB pinball +0.027) and fitting the part with trees was overconfident. QB's range then holds 90.7%, over the 90% group bar, and a true forecast would hold 90.2% (F28). The bar stays as written, and the CEO accepted the miss.

**Not covered:** the long horizons. Their misses are mostly partial, from missed games rather than exact zeros (F24), so they need games played × share per game.
