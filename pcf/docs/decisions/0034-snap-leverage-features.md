# 0034: Snap leverage downscaled to feature engineering: a post-season usage part, the forecasts retired

**Date:** 2026-11-14 · **Decided by:** the CEO's rule ("if it fails the no noise target then we will downscale this project from an expert to simply an investigation and feature engineering") and pick ("(a) Part + usage part", 2026-11-14), after the build failed the no-noise target (RESULTS R1–R3). The calls below are Claude's technical calls, listed for veto at merge. · **Project:** `snap-leverage`

**Decision:**
- **`play.leverage` stays** as decision 0033 built it.
- **A new post-season table part, `player_game.leverage_usage`**, built from true participation (`player_play.on_field`) × `play.leverage` × `play.pace`. Columns:
  - `lev_side`, `lev_snaps`: the side he played most, and his snaps there;
  - `lev_snap_share`, `lev_share`, `lev_hs_share`;
  - `lev_role_gap`, the passing-down role gap;
  - `lev_trust_oe`, trust over expected.
  - It covers 2016–2025, about 20,000 player-games a season.
- **The usage functions move to `pcf.data.usage`**, so the table build and any later live model share one version.
- **The nine forecast variants leave the package** (`pcf.experts.snap_leverage` is removed). Their scorecards and histories stay in MLflow and `data/outputs/snap-leverage/` as the investigation's record. The last commit with them is 892d39c.

**The calls:**
1. **The part is post-season only, and an after-kickoff part** (rule m), like `on_field_pace`. It's known when participation is: the day after the Super Bowl. An in-season model sees it only for finished seasons.
2. **One row per player-game, on the side he played most** (`player_game`'s keys are player and game). A player on both sides keeps the side with more snaps; a tie goes to the first side alphabetically (defense).
3. **The columns carry a `lev_` prefix,** since no column may come from two parts.
4. **`pcf.data.usage`, not `pcf.data.tables`.**
   - **Why:** models may not import table builders (leakage check 1).
   - **What it allows:** a live model can compute the same measures from participation-live's map through its own declared inputs, as the build did.
   - **The precedent:** `pcf.data.standings` lives there for the same reason.
5. **The registry entry becomes phase 0** (data and features, like `tag-tables`). It depends only on `grain-tables`, and the interface block says how to use the parts and what not to redo.
6. **The harness keeps `first_read`** (decision 0033, call 10). It's general, tested and harmless, and any future model that reads the play-by-play can use it.
7. **No consistency rerun.** The measures are the exploration's, from true participation, and already have rows in `CONSISTENCY.md` (F3–F5). The map's versions got their own row (R9).

**Why:** the CEO's rule and pick. The contract signal (+1.7% from the role gap, F10) came from true participation, and contract work runs between seasons, where post-season data is allowed.
