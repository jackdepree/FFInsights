# 0046: vacated opportunity's exploration and brief, their technical calls

**Date:** 2026-11-24 · **Decided by:** Claude (technical calls, listed for the CEO's veto at merge) · **Project:** `vacated-opportunity`, and its two experts `vacated-live` and `vacated-offseason` (exploration and brief; nothing ships)

## The counts

1. **The groups and top k:**
   - WR 2, TE 1, RB 1 (with FB), OL 5, DL 3, by snaps in the group;
   - the roster's DL only, so edge rushers listed as LB are not in it.
2. **An absence:** a team game between a top player's first and last game for that team in which he had no snap (the exploration). In the build, live, it's an expected absence read from the Saturday run's report (call 10).
3. **A departure:** in the exploration, a top player with no snap for the team in s + 1. In the build, he isn't on its week-1 roster, which is known before the season (call 11).
4. **Pressure:** the rate over dropbacks with the flag or a sack, a sack counted as a pressure (F34).

## The tests

5. **Intervals are 90% team Poisson bootstraps,** 2,000 draws.
6. **The plus-minus:**
   - fit on seasons up to s, each share demeaned within his player-season;
   - the pooled part (per pair of groups) and the pair part (per same-group pair) share one ridge penalty, chosen by 5-fold cross-validation on 2016;
   - forecasts clipped to [0, 1].
7. **The weekly walk-forward:** the pooled part from fits up to s − 1; the pair part from this season's earlier weeks, fit on the residual.
8. **Role distance (H111):** Euclidean over roles' 6 pooled coordinates, scaled by its median, before exp(−d).
9. **I125's intake flag, known in the offseason:** a newcomer at the group who was a top player at his group elsewhere last season, or a pick 1–64 rookie. The CEO confirmed it for the build (2026-11-24: "Yes a preseason flag is good enough").
   - Two calls were reported after the pre-registration, not as verdicts: the hindsight flag's leak check, and H110's "he left" side bet without the count of departures.

## The brief (for the build)

10. **The live absence input is an expected absence:** (1 − his chance of playing) × his share to date. The chance comes from availability once built, and from the report's Out (0) and Doubtful until then. The hindsight version is reported as the ceiling.
11. **The offseason backtest runs on the week-1 roster only.** The free data has no historical March or April rosters, so the runs after free agency and the draft are live only.
12. **The ridge's penalty grid is extended below 1** (the exploration chose the grid's edge). It's chosen by cross-validation within the training seasons.
13. **Shares from 2013** (when snaps begin); the lines' pressure from 2016; scored 2017–2024; the 2025 vault is untouched.
14. **The shuffled null:** absences shuffled across games within the team-season (live); departures shuffled across team-seasons (offseason). 19 copies each.
15. **The choice model (method 3, the CEO, 2026-11-24) is fit on completed seasons only.** It reads who was on the field each play, which is known only after the season (rule m), so its diversion ratios feed both experts as a prior.

## Data path

16. **The exploration's scripts read the main checkout's data through `PCF_DATA_DIR`** (the worktree has no `data/`). Its interim tables are in `<interim>/vacated/`. No config changed.
