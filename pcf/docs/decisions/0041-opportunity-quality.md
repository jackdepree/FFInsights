# 0041: opportunity-quality, the build's technical calls

**Date:** 2026-11-21 · **Decided by:** Claude (technical calls, listed for the CEO's veto at merge), inside the agreed brief and the CEO's calls of 2026-11-16 · **Project:** `opportunity-quality`

## The facts (layer 0 parts)

1. **Two new table parts, not a new table.** `play.xfp` (one row per play on the play spine; the chance's player, kind, expected catch, yards and touchdown, the actual ones, yards after the catch over expected) and `player_game.opportunity` (each player-game's sums, `oq_` prefix). Both are known when the play-by-play is (kickoff + 1 day). Parts keep the other builds' tables untouched (decision 0008), and `build_player_game` now ends with them.
2. **A chance** is a target (a pass with a receiver, not a sack) or a carry (a run with a rusher) by an RB, WR or TE; two-point tries are left out. QB carries aren't chances: the brief is about the work skill players are given.
3. **Expected values from the situation alone** (yard line, down, distance, goal to go, formation, tempo, quarter, clock, score, throw depth and side; run side and gap). No player, team or defense: "expected" means an average player in that spot (the brief's assumption, flagged).
4. **One model per piece of a fantasy score** (catch chance, receiving yards, target TD chance; rushing yards, carry TD chance), boosted trees with the exploration's settings. Any scoring is then a sum (`CHANCE_SCORING` in `pcf.baselines.common`), so half-PPR and standard need no refit.
5. **Fit on regular-season chances of up to 10 earlier seasons, never fewer than 3, from 2009** (td-expert's F1: earlier play-by-play lists mostly completed targets). Expected values start in 2012; player-games before then carry the counts and nulls for the expected columns. Fits are cached per season and keyed by a model version; a fit that saw its own season is refused.
6. **Every rostered RB, WR and TE gets a row** in each game with play-by-play, 0 chances when he got none, so a benched player is in the outcome (the brief's flagged assumption: players who lost their role stay in).
7. **Yards after the catch over expected** is nflverse's: `yards_after_catch − xyac_mean_yardage`, completions only.

## The forecast

8. **Reuses participation's feature code, not its saved forecasts.** Participation's saved histories cover 2016-2024, so they can't score the 2025 vault; its inputs (snap shares, depth chart, injury report, teammates out, new team, rookie) are recomputed from the same parts through the gateway. The registry's `depends_on` becomes `[grain-tables]` for this reason. Pace's team volume forecasts (in the brief's inputs) aren't used in this build: participation's inputs already carry the playing time, and pace adds a second saved history to line up; a candidate for the next rung.
9. **Next game's expected PPR points as a spike forecast** (decision 0014): the chance of at least one chance (logistic), the expected points if he gets one (lasso, penalty chosen on the latest 20% of the training window), and ranges from the latest 20%'s misses by position and size of forecast. A two-part forecast because a fifth of rostered player-games are 0.
10. **The ladder:** last 4 games' expected points (rung 0) → counts (playing time + past targets, carries, snaps) → + past expected points → + efficiency (`eff`: points over expected per chance over this season and last, shrunk toward 0 by 30 chances; past points; yards after the catch per catch; a tight-end yards-after-catch term) → trees on `eff`'s inputs. Takeaways carried up: the exploration's F7 (expected points per chance beat counts), and participation's (playing-time inputs first).
11. **The yards variants** (`eff_rec_yards`, `eff_rush_yards`): next game's expected receiving and rushing yards, the same model, for the yards-only yardstick (the brief's units).
12. **Saturday run, refit once a season** (as participation and the yardstick), test seasons 2016-2024, training from 2013 (the first season with a full year of expected values behind it).
13. **Longer horizons are direct models** (participation's reason): the average expected points per game over the team's next 3 regular-season games, and over the rest of its regular season; a week the player has no row counts 0; a row is scored only when its whole window is known. Lasso with ranges by position and size.

## The regression measure

14. **The gap** is his points over expected per chance over this season so far plus last season, measured against 0 (the average player in the same spots), weighted by chances; a row needs 20 chances behind it and 10 still to come to be scored.
15. **Method A:** one pull-back rate per position, the weighted slope of later gaps on earlier ones. **Method B:** partial pooling, k = τ²/(τ² + V), with τ² from earlier player-seasons of 30+ chances, V from the spread of one chance's points over expected by kind. **B with yards after the catch:** B plus a per-position weight on his shrunk yards-after-catch gap. All parameters come from the 6 seasons before (never the scored one).
16. **"The gap closes"** means his future gap (rest of the season) ends on the near side of half his current gap. The chance is a normal approximation from B's posterior and the future chances' noise, **then recalibrated with a Platt fit on earlier seasons' rows**, because the raw chance is overconfident (calibration slope 0.63). The recalibrated chance is the one published (B's, without yards after the catch: B with them adds noise for backs and receivers on the vault).

## Validation

17. **The no-noise target is the brief's** (next game's PPR points on targets and carries, against past points, targets, carries, snaps and position), scored 2019-2024 with the downstream model trained from 2016, because the expert's walk-forward history starts in 2016 (rule e).
18. **Fitting noise** is one training season left out (2016, 2017 or 2018) for the lasso rungs, and seeds for trees, before reading any gain under 0.5%.
19. **The downstream checks walk saved feature histories** (`downstream.py`), so a new variant costs seconds, not a feature rebuild; every row is still predicted by a model fit only on earlier rows.

## After the results

20. **The trees rung is the champion** (`eff_trees`): it beat the lasso by 1.8% of the range score through the harness, with 20 shuffles (the 20-of-20 rule) because each tree refit is slow. The horizons and the yards variants stay lasso (idea I103).
21. **The regression measure publishes method A's mean,** with B's range moved onto it and B's recalibrated chance the gap closes beside it, because B lost to A on the 2025 vault (−1.0%) and the brief's rule says the simpler method ships when the per-player rate isn't better. B's mean stays in the output for the CEO's call.
22. **Saved feature histories** (`pcf.validation.backtest.save_features`, `load_features`, `latest_history`): shared, additive. An expert's package may not read files (leakage check 1), so the readers live in the harness.
23. **The no-noise target is reported two ways:** the brief's baseline, and the same baseline with participation's playing-time inputs, since a downstream user already has those.
24. **The histories pinned in the registry** (`history_runs`): `eff_trees`, `eff_h3`, `eff_rest`, and the yards variants' walks on the saved features (`saved-features`), which have their own 20-of-20 signal tests but no scorecard.

