# 0050: vacated opportunity's build, its technical calls

**Date:** 2026-11-25 to 2026-11-26 · **Decided by:** Claude (technical calls, listed for the CEO's veto before the merge) · **Project:** `vacated-live` and `vacated-offseason` (the build of the agreed brief, `projects/vacated-opportunity/BRIEF.md`; decision 0046 holds the exploration's and the brief's calls)

Code: `pcf.experts.vacated_opportunity` (`data`, `rates`, `live`, `ladder`, `choice`, `offseason`, `report`, `run`). Reports: `projects/vacated-opportunity/build/`. The odds for every idea and test were written in `build/PREREG.md` before their results.

## Inputs

1. **Read through the gateway once and cached** (`<interim>/vacated_build/`): player-games 2013-2024 in the five groups (decision 0046, call 1), team-games with the head coach at kickoff, the final injury report, `roster_week` (2016 on) and the pinned histories `availability/next_logit`, `participation/trees_week`, `participation/lasso_rest`, `opportunity-quality/eff_trees`, `opportunity-quality/eff_rest` and `roles-archetypes` (all version 1). **The 2025 vault stays closed** (the CEO, 2026-11-25): nothing reads a season after 2024.
2. **A player-game's team is part of its key.** A player traded to his next opponent appeared twice in a game; the walk joins on team and, from 2016, keeps only players on that week's `roster_week`.

## vacated-live: the chance he plays (Saturday knowledge)

3. **`p_play` for a top player, in order:** 0 if he isn't on his team's `roster_week` that week, or is on a reserve list (2016 on; reserve players aren't in availability's history, so they used to fall to the report); else availability's walk-forward chance (1 − `p_health_absent`), used only if its `as_of` is at or before kickoff; else the final report's status at rates measured on 2013-2016's top players, never scored: no status 0.944, Probable 0.990, Questionable 0.730, Doubtful 0.005, Out 0 (the brief).
4. **Expected absence** = (1 − `p_play`) × his share to date (decision 0046, call 10). The hindsight version (1 if he missed the game) is walked beside it as the ceiling.

## vacated-live: the forecast

5. **No change (the bar):** a teammate's mean share over his earlier games of the season in which every current top pool-mate played; all his earlier games if there are none.
6. **The pooled rates:** a ridge without intercept on player-game shares demeaned within player-team-season (scipy `lsqr`, damp = √alpha), one rate per pair of groups (`A>B`), refit after every completed season on all completed seasons (rule m). Target and carry share are pooled across the three skill groups. The penalty is chosen by a time-ordered inner split (fit on all but the last training season, score the last), on the grid 0.03-30 (decision 0046, call 12).
7. **The pair part (I49):** each week, a ridge on this season's earlier games, fit on what the pooled part leaves, with absences known by then. Its penalty is chosen per season from earlier seasons' scored rows.
8. **Rows:** every rostered player in the groups with an earlier game for the team that season, forecast whether or not he then plays. **Scored only on games he played**, where his group had an expected absence (snap) or his pool did (targets, carries). Forecasting only players who played had leaked who sat into the yardstick (its zero-fill), which overstated it (receiving +0.37% → +0.25%).
9. **The champion is rung 3, pooled + pair.** Team and head-coach rates (the structured rung, H37) lose to one rate per pair of groups (−0.3% to −0.7%), so they don't ship. Trees on the residual gain (+17.6% snaps), but almost all of that fixes no change's late-season low bias: their absence inputs add +3.2% / +0.8% / +1.5% and nothing beside participation (I161). So trees don't ship (rule k).
10. **Ranges:** walk-forward residual quantiles per cell (group | expected absence above 0.02 | no change's tercile), each widened by his swing (I14: his to-date SD shrunk toward the group's with 20 games' weight). This beats the plain ranges' range score on all three shares.

## Validation

11. **Intervals:** a team Poisson bootstrap (2000 draws) on the share of the reference's squared error a forecast removes.
12. **The shuffled null, vacated-live:** absences remapped across games within each team-season (training absences and the walk's), and every refit redone, 19 copies. **vacated-offseason:** each season's departure lists moved to another team of the same season, no change kept.
13. **The obvious-input check:** a walk-forward least-squares stack on earlier seasons: the incumbent (participation's next-game share if he plays for snaps; opportunity-quality's expected points for targets and carries; their rest-of-season versions offseason), then the incumbent plus the expert's change.
14. **The yardstick:** next-game boards for vacated-live (the change, 0 where none). For vacated-offseason, the rest-of-season boards scored on each team's first game of the season.

## The choice model (method 3)

15. **A nested logit**, fit on each completed season's targets (and, apart, carries): the choice set is the WR, TE and RB on the field (`player_play.on_field`, retrospective; rule m), plus an outside option (anyone else, or a QB run) at utility 0. Nests are the groups. Each player-season has a pull, ridge-penalized at τ = 1. It is fit by L-BFGS with an analytic gradient (checked against finite differences, also in the tests). Each nest's λ comes from a coordinate search over 0.25, 0.4, 0.55, 0.7, 0.85 and 1.0.
16. **In season:** the prior λ is the mean of the completed seasons' fits. Each player's pull is backed out from his no-change share and snap share on a representative play, where he is on the field with chance equal to his snap share (a BLP-style contraction). The expected on-field change (the snap forecast times the chance he plays) gives the new shares. **Offseason:** the departed players' snaps go to 0 and the stayers' to the snap plus-minus. Carries' λ sat at the grid's floor in every season, so the carry fit is a boundary solution and shouldn't be read as a nest effect.

## vacated-offseason

17. **The event is the week-1 roster** (the brief: March and April rosters aren't in the free data). **Departures** are last season's top players not on the team's 53 at week 1; a reserve list at week 1 counts as gone. **Stayers** are players of the group who played for the team in season s and are on its 53.
18. **The intake flag:** a newcomer on the 53 at the group who was a top player at the same group elsewhere in s, or a rookie picked 1-64 (the CEO, 2026-11-24: "a preseason flag is good enough").
19. **The rates are vacated-live's,** fit through season s (pooled), plus season s's own pair part, since the departure comes after the season.
20. **The gate:** the plus-minus where the group was left empty, and for the lines; no change where a top player came in at a skill group.
21. **The shrink (I165):** the change (plus-minus minus no change) scaled by a slope through the origin of (actual − no change) on it, fit on earlier pairs only (the 2015→2016 pair warms up). The skill groups left empty and the lines get separate slopes, per measure.
22. **The champion, per measure (rule k):** of no change, the gated plus-minus and the shrunk one, the most complex that beats every simpler one over all stayers with an interval above 0. That gives the shrunk forecast for snap and target share, and no change for carry share.
23. **Ranges:** residual quantiles around the champion from earlier pairs, per cell (group | intake | the plus-minus moves it by more than 0.02). A cell needs 30 rows, or the pooled quantiles are used.
24. **I126 / I136, like-for-like:** distance on roles' six standardized table features (season s), a kernel exp(−d / median d) normalized to mean 1. The extra Σ (departed share × (kernel − 1)) is fit walk-forward on the plus-minus's residual.

## The saved histories

25. **vacated-live** (`outputs/vacated-live/67156fc95db64f99b3880e5ed70a86cf/`):
    - `history.parquet`, one row per player-game and quantity (`snap_share`, `target_share`, `carry_share`): mean (pooled + pair), q10/q50/q90 (swing ranges), `no_change`, `change`, `pooled_change`, `expected_absent`, `drivers`, `played`;
    - `as_of` is the Saturday run's moment; `train_end` is the previous week's last kickoff + 4 hours (week 1: as_of − 150 days);
    - beside it, `unclaimed.parquet` (each team-game-group's vacated, absorbed and unclaimed share) and `rates.parquet` (the pooled rates per refit).
26. **vacated-offseason** (`outputs/vacated-offseason/8e8a9eb07789454ba63555f84a432b57/history.parquet`):
    - one row per stayer-team-season and quantity: mean (the champion), q10/q50/q90, `champion`, `no_change`, `plus_minus`, `change` (gated minus no change), `intake`, `departed_share`, `last_season`;
    - `as_of` is the season's retrospective moment (10:00 ET on the first day of the week-1 window); `train_end` is the end of season s's Super Bowl week.
