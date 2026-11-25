# 0047: availability's build, its technical calls

**Date:** 2026-11-24 · **Decided by:** Claude (technical calls, listed for the CEO's veto at merge) · **Project:** `availability` (build; brief agreed 2026-11-24, all three methods) · Plan and odds: [`projects/availability/BUILD.md`](../../projects/availability/BUILD.md) · Results: [`projects/availability/RESULTS.md`](../../projects/availability/RESULTS.md)

## The tables (layer 0, additive)

1. **A new table, `roster_week`** (spine part `status`), one row per player on a team's 53 or a reserve list for each of its regular-season games, 2016 on. `player_game`'s spine leaves reserve lists out, so an injured-reserve stint was invisible. Known at the start of the week, like `player_game`'s spine (the weekly roster's own rule). When a player is listed twice in a week, the active row wins.
2. **Health reserve lists are `RES`, `PUP` and `RSN`** (injured reserve, physically unable to perform, non-football injury or illness, read from the status's description). `R02` (reserve/retired) is left out. Suspensions, exempt, practice squad, `RSR` and others are not health. `RSN`'s reading comes from its description; it was not checked against news.
3. **A new part, `player_game.injured`** (2013 on): the first play each player is named "was injured during the play", and how many times, matched by standardized team, jersey and last name (decision 0044 call 1). Known the day after the game. Unmatched names are dropped.

## The definitions

4. **Listed means a game status (Questionable, Doubtful, Out) or a limited or no-practice day.** A full practice with no game status isn't listed.
5. **The states:** healthy (on the 53, not listed), listed (Questionable or no status), out (Out or Doubtful), reserve, and off (no roster that week; absorbing when rolling forward). This week's state uses this week's final report, known at the Saturday run.
6. **Training rows start in 2016, not 2013** (the brief said training from 2013). Before 2016 there are no weekly statuses, so reserve stints can't be told apart and players on a season-long list show up with their season-end status. A player's record (snaps, reports, in-game injuries) still starts in 2013.
7. **Snap-weighted games lost:** before a player's first game of a season, last season's mean share; with neither, his position's mean share last season. Decision 0044 call 11 said the depth-chart rank's average share; the position's mean is simpler, and the rank is often missing for reserve players. Offense (QB, RB, WR, TE, OL) and defense (DL, LB, DB) are summed apart; specialists are left out.
8. **Proneness:** named in-game injuries per scrimmage snap over his position's rate, shrunk by credibility Z = n_exp / (n_exp + 2) (decision 0044 call 6), with a repeat flag for the same body part.

## The models

9. **Every model refits once per season,** with the harness's recency weights (half-life), walk-forward, scored 2017-2024 (2017 trains on 2016 alone).
10. **Next game's health-absence models fit on listed rows only.** An unlisted player's health absence is about 0.2% (an injury after the report, or a late listing); those rows get the training rate of unlisted rows.
11. **Penalties and settings:** the plain logistic's C is 0.3; the lasso's C is picked from a grid on the pool's latest 20%; trees are scikit-learn's histogram boosting (200 rounds, learning rate 0.06, 15 leaves, 80 rows a leaf), the same settings everywhere.
12. **The two-part horizons** (method 1): a lasso logistic for any health absence in the window, times a ridge on the share of the window if any; the count if any is drawn from the empirical shares in the predicted share's bin, from the latest 20% of training.
13. **The chain** (method 2): a multinomial logistic for each state's moves (to healthy, listed, out, reserve, off), with weeks in the state bucketed 1, 2, 3, 4+, and a logistic for whether a listed or out week is an absence. It's rolled forward exactly (state × weeks-in-state × count) over the window.
14. **The hidden health state** (method 3): four hidden states per position group, two observed symbols each week (the report with snaps, eight kinds; practice, four kinds), fit by Baum-Welch (30 rounds), filtered through this week's partial report and rolled forward.
15. **The active stack** uses participation's `active` from its pinned walk-forward history (run `1a5406548afa4be181c2e88b9fa3b987`), and kept share uses participation's `trees_week` (run `2abc96bcab5047f5b7d505416f538b0f`). Both are lined up as each row's latest output made by its moment (rule e).
16. **`active_gated` was added after the first walk.** The stack helped listed players and cost unlisted ones, so the gated version fits and uses the stack on listed players only. It was added after seeing a result, so it counts as a discovery, not a confirmation.

## The scoring

17. **The build's comparisons run on one saved feature history** (every Saturday and Thursday moment, 2016-2024, from the gateway), through the harness's own `backtest.walk` and the paired comparison by whole weeks. The shipped variants also go through the harness's full validation (`run forecast`), which rebuilds the features itself.
18. **Games played for any reason:** his rate of playing when healthy, (games played + 4 × 0.9) / (games not health-absent + 4), this season so far, times the share of the window he isn't health-absent. The prior and its weight mirror I60's crude forecast. Its range comes from the health count's range only.
19. **On the yardstick, availability's columns start in 2017,** so the boards' training rows start in 2017 for both the base and the new forecast. I60's crude columns go in the base beside participation, so the gain is what availability adds beyond them.
20. **The vault (2025) stays closed** (the build chat: "Don't open the vault (2025) unless the brief says to"). Opening it once is a yes/no for the CEO.
