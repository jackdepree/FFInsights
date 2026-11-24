# 0045: roles and archetypes' exploration and brief, their technical calls

**Date:** 2026-11-24 · **Decided by:** Claude (technical calls, listed for the CEO's veto at merge; the CEO approved: "Yes I approve, you may merge") · **Project:** `roles-archetypes` (exploration and brief; nothing ships)

## The counts

1. **Personnel is counted from who's on the field** (RBs and TEs on the offense), not parsed from participation's string, which has variants and is missing on 23% of plays in 2016–2022.
2. **A player's group is his most common depth-chart position's group for the team-season:**
   - WR; TE; RB (with FB);
   - DL (DE, DT, NT); OLB; ILB (with MLB); CB; S (FS, SS).
3. **The 32 kinds of play:** pass or run (by `qb_dropback`) × early or late down × personnel (11, 12, heavy, other) × red zone or not.
4. **Shrinkage:** rates are pulled toward the group's pooled rate by a prior of 100 snaps (10 targets or tackles for per-event means), and on-rates are smoothed by +1/+2.

## The tests

5. **Intervals are Poisson-bootstrap draws:**
   - over players (consistency, H99, H107, I124);
   - over team-seasons (H101, H102, H103);
   - over teams (H104, H105);
   - over game-weeks (H106).

   A gain counts when its 90% interval clears 0.
6. **H102's label (M1) was fitted on 2016–2020 and used as its target in 2018–2020's training seasons.** The inputs are point-in-time; the label isn't. That's acceptable for the exploration only.
7. **H108's ridge penalties were chosen once, by 5-fold cross-validation on 2016:** plain 1,000, by responsibility 30, by latent identity 1,000.
8. **The obvious-input check on defense** (I124, beyond his own last-season rate) was added after the pre-registration and is reported, not a verdict.

## The brief (for the build)

9. **Each side's PCA is refit after every completed season** on all completed seasons. The new axes are rotated to the last fit (Procrustes), so a coordinate keeps its meaning. Season s's coordinates come from a fit on seasons up to s.
10. **The team-adjusted own-snap shares and the on/off tilts both stay inside the space.** H99 failed them as a stand-alone measure, not as inputs.
11. **Fit on 200+ snaps;** players under 200 are placed and shrunk by snaps / (snaps + 200).
12. **Measurables stay outside the space** (they repeat by construction).
13. **Named-role rules are set on the 2016–2020 fit and frozen** for scoring.
14. **Trees are a rung** (not in the exploration), for H107's carries step.
15. **Rookies' starting coordinates** (measurables and draft slot) come at the draft, an offseason event, so by rule m they register as their own small expert when built.

## Data path

16. **The exploration's scripts read the main checkout's data through `PCF_DATA_DIR`** (the worktree has no `data/`). Its interim tables are in `<interim>/roles/`. No config changed.
