# Results: Participation and snaps (`participation`)

**Date:** 2026-11-03 · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** `participation` · **Champions:** `trees_spikes` (next game, from 2026-11-04, F25; before that `trees`), `active` (chance of being active), `lasso_h3` (next 3 games), `lasso_rest` (rest of the season). None registered as a model yet: see the case against, point 6.

## In short
PCF's first expert works. Before each game it forecasts each rostered QB, RB, WR and TE's snap share, explaining 74% of the variance against 58–59% for the last game or last 3 games, and cutting the pinball loss by a quarter. It beats its shuffled self 20 of 20 times and improves the lasso's fantasy points, and slightly improves ECR's. Boosted trees win for the next game; the simpler lasso wins or ties for longer horizons. **Two checks miss their bars narrowly, as written:** next-game range coverage (85.3%, bar 75–85%) and the active probability's slope (0.89, bar 0.9–1.1). The first is arithmetic, not a bad forecast: a perfect one would score 85.8% (F13). Judged part by part it passes (F22). Fixing the two real misses that showed, at QB and Questionable (F23), gave a new champion, `trees_spikes` (F25).

**Scorecards:** `outputs/participation/<variant>/<run_id>/scorecard.html` (also in MLflow, except `trees_spikes`' run `no-mlflow-2026-11-04`: see the case against, point 9) · **Vault:** not opened · **Versions tried:** 2 for `trees`, `active`, `lasso_h3`, `lasso_rest` (the first without a signal test)

All scores are in points of share (0–100), on the rows every rung of that horizon scores, 2016–2024, `--refit season`.

| Check | Result |
|---|---|
| Signal (20 of 20 shuffled refits) | **Pass, all four champions:** next game 3.6 against 8.3–8.4 for the shuffled model; active log loss 0.216 against 0.436–0.449; next 3 games 4.1 against 7.8; rest of season 4.4 against 7.2–7.3 |
| No noise, downstream (D6) | **Pass, "adds value":** the lasso's fantasy points, pinball −0.0209 (−0.0233 to −0.0185), 52,522 rows, 193 weeks (F15) |
| Each rung beats the one below | **Pass, and the rule picked the champions** (the ladder below). `last3` lost to `last_game`, so both stayed as rung 0 per the brief |
| Chance of being active within 3 points | **Pass:** 0.79 points. **The harness's slope bar is a narrow miss:** 0.89, bar 0.9–1.1 (F12) |
| Coverage 75–85% overall, 70–90% per position | **Next game: narrow miss as written,** 85.3% (F13). Per position pass, 83.5–86.9%. Players who hadn't played recently, 91.5%, also over the 70–90% bar: mostly easy zeros. Next 3 games 79.9%, rest of season 80.1%: pass (but see F14) |
| Leakage | **Pass:** 9 of 9 blocking checks on every variant, identical at 25 cutoffs. Nothing from the game-day active list |
| Football sanity (CEO review: pending) | Rule q10 ≤ q50 ≤ q90 has 0 violations. The top 20 predictions are all QBs at 99%+, and the bottom 20 all QBs at 0: starters and backups. Details in F16 |
| CEO spot-check | Done 2026-11-04: the coverage miss. See below |

## Terms
As in the brief, now in `docs/GLOSSARY.md`: **active**, **two-part prediction**, **horizon**. Changed since the brief:
- **The spike is "no offensive snap", not "inactive".** The two-part model's first part is the chance of taking an offensive snap, because the outcome says only that: 8% of rows are active with no snap (F1). The chance of being active is its own variant, `active` (D3, updated).
- **Played recently:** took an offensive snap in the last 8 games (D7).

## Findings
Exploration findings F1–F9 are in [EXPLORATION.md](EXPLORATION.md). These continue from them.

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| F10 | **Next game: the model beats recent averages by a wide margin, and trees beat the lasso by a little.** Pinball, R²: last game 4.727, 0.582; last 3 4.876, 0.588; lasso 3.657, 0.736; **trees 3.604, 0.743.** Lasso vs last 3 −1.219 (−1.276 to −1.165); trees vs lasso −0.053 (−0.073 to −0.032). Players who played recently: trees 3.742, 0.732 (QB 3.564/0.774, RB 3.334/0.672, WR 4.126/0.706, TE 3.682/0.702). Trees won clearly in 5 of 9 seasons and tied in 4, and never lost. | `explore/compare_rungs.py`, 77,767 rows | strong | every position, 2016–2024 |
| F11 | **Career share doesn't earn its place in trees.** With it, pinball +0.005 (−0.001 to +0.011), a tie, so the simpler model stands. On players back after missing 4+ games (763 rows), career does *worse*: 5.997 against 5.946. F9's gain was against a simple model, and doesn't survive the harness. What helps those players is the absence-skipping averages: back after 1–3 games missed, trees 5.485 against last game's 12.488; after 4+, 5.946 against 9.971. | `trees_career` scorecard | strong | CEO question, D5 |
| F12 | **The chance of being active is sharp and close to calibrated, with a data break in 2019.** AUC 0.932, Brier 0.0607, calibration error 0.79 points (bar 3), slope 0.89 (bar 0.9–1.1, a narrow miss). The worst bins are off by 4.3 points (said 15.5, was 19.8; said 75.4, was 71.1). Split at the break: 2019–2024, with real game statuses, error 0.84 and worst bin 5.1; 2016–2018, where "active" can only mean "has a snap row", error 2.49 and worst bin 17.5. Listed Out, it says 5.8% and 3.1% play; Doubtful 8.0% and 3.8%; Questionable 72.4% and 69.7%. | `active` scorecard | strong | every position |
| F13 | **A forecast with a spike at 0 *should* cover about 85%, not 80%, so the coverage bar doesn't fit it.** Where q10 is above 0 (43,505 rows), the range holds 80.7%, with 9.8% below and 9.5% above: almost exact. Where q10 is 0 (35,912 rows), nothing can land below it, so it should hold 90%; it holds 90.8%. Drawing results from each row's own forecast, a perfect forecast would score 85.8%; ours scores 85.3%, a gap of −0.6 (−1.0 to −0.2). (Corrected 2026-11-04: this first said 84.5%, from a rough blend.) "43.4% above q50" (bar 45–55%) is the same effect: 20% of results tie exactly at q50. Where q50 is above 0, 49.9% land above it and 48.6% below. | a split of the `trees` history | strong | any outcome with a spike |
| F14 | **The long horizons' 80% coverage hides two errors that cancel.** Where q10 is above 0: next 3 games hold 73.4%, with 15.1% below q10 and 11.4% above; rest of season 74.4%, 15.0% and 10.6%. Where q10 is 0: 92.8% and 91.9%. Unlike the next-game model, these don't use a spike, so they understate the downside: a player's window can collapse through an injury or a release. **Use the horizons' means with confidence, and their q10 with caution.** | a split of the histories | strong | `lasso_h3`, `lasso_rest` |
| F15 | **The expert's share helps the lasso's fantasy points, and slightly helps ECR's.** Lasso with and without, 2016–2024: pinball 1.4678 vs 1.4887 (−0.0209, −0.0233 to −0.0185), MAE 4.408 vs 4.483, "adds value". ECR recalibrated with and without, 2023–2024: 1.4047 vs 1.4101 (−0.0053, −0.0091 to −0.0017), MAE 4.188 vs 4.210, "better", on 8,534 rows and two seasons. On the 13,063 rows all three score, 2022–2024: ECR 1.3849, lasso with the share 1.4387, lasso 1.4561. **The share closes a quarter of the lasso's pinball gap to ECR, and 59% of its MAE gap** (MAE 4.253, 4.304, 4.377). | `explore/no_noise.py` | strong for the lasso; suggestive for ECR | QB, RB, WR, TE |
| F16 | **The forecast behaves like football.** Starters listed Out: chance of playing 5–8%, predicted share 2–3%, actual 0. 2021–2024, QB1s: said 84.8, were 84.7. QB2s: said 12.6, were 12.9. WR1s: said 67.3, were 67.7. WR2s: said 30.4, were 29.6. | a join of the histories with report and depth | strong | every position |
| F17 | **Longer horizons favor the simpler model.** Next 3 games: season-to-date 4.557, 0.584; **lasso 4.125, 0.701**; trees 4.136, 0.698 (tie). Rest of season: season-to-date 4.881, 0.448; **lasso 4.374, 0.617**; trees 4.525, 0.590 (worse by 0.151). Probably trees overfit once single-game details stop mattering; I didn't test why. | `explore/compare_rungs.py`, 66,608 and 75,865 rows | strong | every position |
| F18 | **Counting cut players as 0 lowers the long-horizon scores, honestly.** Rest of season, played recently, lasso R²: QB 0.630, RB 0.545, WR 0.567, TE 0.559, against 0.67–0.68 in F8, which let a cut player leave the window. Those are the same players whose futures matter to a dynasty or rest-of-season product, so these are the numbers to trust. | `lasso_rest` scorecard | strong | D9 |
| F19 | **Rookie and new-team tags aren't Saturday information.** They're known only 1 hour before kickoff. Daily depth charts (2025+) are known at kickoff. Features compute these from earlier information, or fall back to the last known chart. | `features.py`, the gateway's refusals | strong | every expert at the Saturday run |
| F20 | **What the lasso keeps.** Fit once on 2013–2024, next game, it keeps 29–32 of 49 inputs per position, led by last game's share, the active-only averages, depth and teammates' absences. Plain career share is dropped everywhere; career share for players back from an absence is kept at every position, with small weights. A few box-score averages are kept, at a third or less of last game's weight. All four positions chose the grid's smallest penalty, because the grid was built for fantasy points. A grid 100 times lower barely changes anything and no champion changes: next game −0.002, next 3 −0.007, rest of season −0.002; trees still beat the lasso at next game (−0.060), tie at 3 games and lose over the rest of the season ([`explore/penalty_grid.py`](explore/penalty_grid.py)). The saved runs keep the original grid. | a one-off fit on 2013–2024 | suggestive | D5 |
| F21 | **The room a player joins matters, and career share doesn't explain it** (CEO question, discovery only, not yet through the harness). Non-QB movers with a usual share of 60%+, first 4 games on a new team: into an evenly shared room the next-game trees say 55.2, actual 50.9 (+4.3, 2.6 to 6.1; 581 rows, 160 players); behind one clear leader +1.0 (−0.9 to 2.8); into a thin room +4.6 (0.6 to 8.9), which a crowding story doesn't predict. Regulars already in the room are over-projected when a high-share player arrives: TE +5.1, WR +1.9, RB +2.0, against about 0 otherwise; QB no difference. Learning the movers' miss from earlier seasons, 2019–2024, room inputs beat a plain correction by −0.25 absolute error (−0.33 to −0.16) at next game, −0.13 at 3 games and −0.07 (a tie) over the rest of the season. Career share: 0.00, −0.05, −0.07, all ties. Movers are 8% of rows. | [`explore/new_team_room.py`](explore/new_team_room.py) | suggestive | I9, the vacated-snaps rung |
| F22 | **Judged part by part, the next-game forecast passes** (CEO's idea, spot-check, 2026-11-04). Part 1, the chance of exactly 0 snaps: AUC 0.933, error 0.97 points, slope 0.938; 2019–2024 error 0.53, slope 0.978; 2016–2018, without game statuses, error 2.31, slope 0.861. Part 2, the share on rows where they played (59,788): the range holds 79.7% (79.2–80.2), with 10.2% below, 10.1% above and 50.0% above q50; R² 0.716. The whole forecast also passes: results land evenly within it, each decile holding 9.6–10.2%. Weakest group: players who hadn't played in 8 games, AUC 0.766, slope 0.77. | [`explore/coverage_deep_dive.py`](explore/coverage_deep_dive.py) | strong | how spike forecasts are judged |
| F23 | **Two real misses sit under the 85.3%.** QBs have a second spike: 64% of QBs who played took exactly 100% of snaps, and 88% of their results above the range are exactly 100%, so their range holds 75.7% (74.7–76.8), with 57.1% above q50. QB coverage is 4.3 points short of what their forecasts promise (86.9%, against 91.2%), while the other positions are within 1. Players listed Questionable who play hold 73.6% (72.0–75.2), with 14.3% below and 12.1% above: the residuals depend on position and size, not on injury status. | same | strong | QB forecasts, Questionable forecasts |
| F24 | **A spike at 0 alone won't fix the long horizons.** Of the rows below q10 where q10 is above 0, only 25.5% (next 3) and 18.5% (rest of season) are exactly 0; about half are under half of q10. Most are partial: missing some games of the window. They need games played × share per game. | same | strong | a next rung for the horizons (F14) |
| F25 | **`trees_spikes` becomes the next-game champion** (2026-11-04). It beats `trees` on pinball by 0.021 (0.017 to 0.025), almost all at QB (0.138, 0.113 to 0.164); RB and TE tie, WR is worse by 0.004. Signal 20 of 20, all 9 blocking leakage checks pass, and judged part by part it passes every bar, where `trees` failed one: players who hadn't played recently hold 69.3%, under the 70% group bar (now 71.9%). The cost is a slightly worse mean: MAE 11.855 against 11.835 (QB 11.476 against 11.354), R² 0.742 for both. It still improves the lasso's fantasy points, −0.0205 (−0.0229 to −0.0181), against −0.0209 for `trees`, and recalibrated ECR's, −0.0052 (−0.0089 to −0.0015). | [`explore/parts_ladder.py`](explore/parts_ladder.py), `explore/no_noise.py trees_spikes` | strong | every use of next-game share |
| F26 | **QBs' new numbers are mostly arithmetic again, now at the top.** With the third part, their range holds 88.5% with only 12.0% above q50. If each forecast were exactly true, those would be 90.7% and 11.6%: a result of exactly 100% can't land above a q50 of 100%. Where q50 is below 100%, 51.6% land above it. On games neither 0 nor every snap, the range holds 76.7%. The chance of every snap is a narrow miss: error 3.71 points, slope 0.889 (bars 3 and 0.9–1.1), and it's low at 30–50%. Boosted trees were far worse (7.13, 0.671), so it uses a logistic model. | [`explore/qb_every_snap.py`](explore/qb_every_snap.py) | strong | QB forecasts |
| F27 | **Own residuals fix Questionable players' range, not their whole forecast.** Their range on games played moves from 73.5% to 79.1%, but pinball ties (+0.020, −0.006 to +0.046). The bigger gap is the chance of playing: slope 0.704 and error 3.80 for Questionable players, far below the 0.938 overall. | `explore/parts_ladder.py` | strong | Questionable forecasts, `injury-fatigue` |

## The ladder

| Rung | Method | Result vs the rung below | Takeaway carried forward |
|---|---|---|---|
| 0 | Last game, last 3, last 3 active | Last 3 is worse than last game (+0.149): recent form is one number, and a backup's 0 is usually 0 again | Averages alone miss absences and depth changes |
| 1 | Two-part lasso, per position, with box scores and career | −1.219 vs last 3 | Absence-skipping averages, depth and the injury report carry it. Offering everything was safe: the lasso drops what doesn't earn its place |
| 2 | Two-part boosted trees, without box scores (F7) | −0.053 vs the lasso at next game; a tie at 3 games; worse for the rest of the season | Interactions help for one game, not for long windows |
| 2b | Trees with career share | +0.005: a tie, so the simpler model stands | Career doesn't earn its place in trees |

## Where it misses
Lens list 2026-11-03, measured 2026-11-04 UTC, `trees`, 79,417 player-games, 2016–2024. A miss is actual minus predicted, in points of share.

| Lens | Group | Rows | Average miss | 90% interval | Idea |
|---|---|---|---|---|---|
| position | WR | 29,208 | −0.52 | −0.68 to −0.37 | |
| depth | unlisted | 6,426 | −3.32 | −4.30 to −2.51 | I10 |
| week | 10–14 | 21,061 | −0.41 | −0.57 to −0.25 | |
| snap_share (after) | 75%+ | 16,821 | +12.91 | +12.62 to +13.24 | Grouping by the outcome: see below |
| team_points (after) | 31+ | 17,430 | −0.55 | −0.70 to −0.43 | |
| margin (after) | won by 14+ | 13,641 | −0.44 | −0.61 to −0.29 | |
| qb_efficiency (after) | false | 2,444 | +12.27 | +11.34 to +13.18 | Grouping by the outcome: only QBs who played have one |
| *tag* | active while questionable | 1,867 | +7.91 | +6.30 to +9.45 | Grouping by the outcome: see below |
| *tag* | first game back | 1,376 | +3.07 | +1.69 to +4.85 | Same |
| *tag* | backup QB start | 12,242 | +0.71 | +0.42 to +0.98 | |
| *tag* | off a bye | 5,302 | −0.71 | −1.08 to −0.34 | I11 |
| *tag* | rookie | 13,403 | +0.54 | +0.11 to +0.97 | I5 |

**How to read the two big numbers.** The snap-share lens explains 24% of the squared miss, but it groups by the answer: of course players who ended up over 75% were under-predicted. The same goes for "active while questionable": the tag fires only for those who played, while the forecast includes the chance they sit. Across **all** Questionable rows (4,075), the model is 2.1 points too *high* (said 36.9, were 34.8). The only large miss a model could use is **unlisted players, 3.3 points too high.** It's largest in 2016 (said 17.3, were 6.6, on 777 rows), and 0.5–3.3 points in the other seasons.

Long horizons show the same list: unlisted −3.99 (next 3) and −3.55 (rest of season); questionable +6.55 and +4.34; first game back +4.41 and +3.78. Rest of season also flags "revenge game" (−1.85), which has no football reason to matter to a season's average. With about 20 tags scanned, that's a reminder of how chance looks.

## The case against
1. **The gain over ECR is thin.** It's two seasons, with ECR put through a linear correction per position, and −0.005 pinball is about 0.4%. F5 predicted roughly this. Treat "better" as "not noise", not as an edge over ECR.
2. **Trees beat the lasso by 0.053, about 1.4%,** with no search over their settings. They tied in 4 of 9 seasons, and the trees' win is largest in recent seasons, which fits the data improving in 2019 but could also be luck. If a product wants a simple explainable model, the lasso gives up very little.
3. **The history before 2019 has a different target.** No game statuses exist then, so "active" means "has a snap row", and "absence" means "no snap row", which is partly a different thing (active with no snap). Those seasons train every model, and the 2016–2018 calibration is visibly worse (F12). I didn't test training only on 2019+.
4. **The live path isn't exercised.** 2025+ has daily depth charts with a fallback to the last known one, and injury reports with no `date_modified`, using the noon-the-day-before rule. Everything scored here is 2016–2024, with weekly charts. Tests cover the logic; the numbers don't. The vault will be the first real test.
5. **Refit once a season.** Live, the weekly run could refit weekly. I expect little change, and it would make the signal test much slower, but I haven't measured it.
6. **One definition-of-done box isn't ticked: no champion is registered in MLflow.** The harness logs attempts, checks and scorecards, but nothing yet saves a fitted model: `tracking.log_model` takes only one scikit-learn estimator, and this expert is a dictionary of per-position parts across four variants, under a registry that holds one `champion` number per project. Nothing loads a registered model yet. The saved walk-forward histories, which are what rule e says higher layers read, are there. This is the first project to meet this gap, so I'd build it with the weekly run, the first thing that needs it. It's the CEO's call whether that's acceptable (open question 2).
7. **Ranges on the horizons are the weak spot** (F14). A product quoting a floor for a player's rest of season would quote one that fails about 15% of the time, not 10%.
8. **No-noise uses a re-made history.** `explore/no_noise.py` walks the expert forward from 2014 so the lasso has training rows; it isn't reading the saved run, which starts in 2016. The rows it shares with that run should match, but it's a separate run from the scorecards'.
9. **The part-by-part fixes (2026-11-04) have their own weaknesses.** The rule that `trees_spikes` passes was written after seeing `trees`' results, and that's forking paths: only the vault or live weeks can confirm it. It passes the q50 bar only narrowly (45.5%), because of QBs' arithmetic (F26). Its mean is slightly worse (F25). The harness doesn't judge the chance of every snap, which narrowly misses (F26). Its run isn't in MLflow, because Windows is blocking a pandas file that MLflow needs. 44 harness tests can't load for the same reason, including `test_validate.py`, so the changes to `validate` and the scorecard rest on new tests elsewhere. Rerun `pcf backtest participation --variant trees_spikes --shuffles 20 --refit season` and the full tests once the block clears.

## CEO spot-check (2026-11-04): the coverage miss

The CEO chose F13 and asked what happens if the chance of exactly 0 snaps and the share if they play are predicted separately. That is how the next-game forecast is already built (brief D3), but its ranges blended the two and the scorecard judged only the blend. So the check judged each part. The script refit the walk-forward to capture the parts; the refit matches the saved history exactly.

- **The rows.** Of 79,417: 53.5% have q10 above 0 and a result above 0 (82.7% inside); 1.3% have q10 above 0 and a result of 0 (all below the range); 16.9% have q10 of 0 and a result of 0 (all inside); 21.6% have q10 of 0, q90 above 0 and a result above 0 (81.9% inside); 6.7% have a range of 0 to 0 (96.6% inside).
- **What would a perfect forecast score?** Drawing results from each row's own forecast gives 85.8%, above the bar. The earlier 84.5% was a rough blend, and F13 now says so. Ours is 85.3%, a gap of −0.6 (−1.0 to −0.2). So the written bar fails a perfect forecast.
- **The alternative: is the blend hiding something?** Yes, two things (F23). QBs are 4.3 points short of what their forecasts promise, and Questionable players' ranges are too narrow. Every other position is within 1 point. Bins of 2–20% chance of 0 are 1.7–2.9 short, with the chance of 0 2–3 points low at 10–50%, mostly from 2016–2018.
- **What would change the answer?** A large gap between actual and promised coverage, or a lopsided landing pattern. Neither appears overall, in any season (gaps −2.3 to +1.3), or at RB, WR or TE. Removing the 0-to-0 rows gives 84.5% against 85.0%.
- **Verdict.** The miss is arithmetic, and the forecast is sound where it's used most, with QB and Questionable exceptions to fix. The bar and the scorecard are unchanged: it still says "fail" until the harness can judge parts.

## Pitfalls
- **A share of 0 after an absence is a trap.** An inactive game reads as a lost role in any simple average: last game's pinball for a player returning from 1–3 games is 12.5, against 5.5 here.
- **Blank isn't 0 in cumulative sums.** `cum_sum` went null after an absence, blanking career share on exactly the rows it was for (fixed).
- **Tags that look pre-game can depend on the game.** "Active while questionable" is listed as a pre-game lens but fires only if the player played. Don't read it as a bias in a model that forecasts whether they play.
- **A penalty grid doesn't travel between outcomes.** The lasso's grid was built for fantasy points, on a scale of tens, and shares run 0–1, so every position chose its smallest value. It didn't matter here (F20), but check for a choice at the edge of a grid.
- **`Path.write_text` defaults to the Windows encoding** and emptied a source file on a `→`. Write bytes encoded as UTF-8.
- **An abstract base with `quantity` gets picked up as a model** by `find_all`. Put `quantity` on the concrete classes.
- **`compare` needs a `step` column,** which saved histories don't have. The week comes from the game id.

## Not looked at
- **Routes, and defensive or special-teams snaps.** The registry's old summary mentioned routes, but they're post-season only (rule m). Routes belong in a retrospective expert.
- **A Tuesday variant** (D2).
- **Training only on 2019+,** the era with real statuses (case against, 3).
- **Teams' two-QB and committee backfields as their own thing.** Trees see them only through depth and shares.
- **Trades and new teams** (idea I9): the model doesn't know the role a player walks into.
- **Weekly refits, and tuning the trees.**
- **The vault (2025).**

## Could be improved
1. **A spike for the horizons' ranges,** so q10 reflects injury and release risk (F14).
2. **A vacated-snaps input** (I9), the natural next rung for new-team players and teammates of the injured.
3. **Model games played × share per game at long horizons** (F24). Done 2026-11-04: judging next-game forecasts part by part, saving the parts, the QB's third part and Questionable players' residuals (decision 0014, F25).
4. **Save a walk-forward history from 2014,** so downstream models needn't remake it.
5. **Recalibrate `active` and the chance of a snap,** especially at Out and Doubtful, where `active` says about twice the rate seen, and for Questionable players (F27). Recalibrating the chance of every snap would close its narrow miss too (F26).
6. **Give shares their own penalty grid** when these models are next rerun: a tiny gain, for free (F20).

## Don't redo
- Don't add career share to next-game trees (F11), or box scores (F7) without a new reason.
- Don't roll the next-game forecast forward for long horizons (D9).
- Don't use trees for rest-of-season without a new reason (F17).
- Don't use the game-day active list as an input (D8).
- Don't read `active while questionable` or the snap-share lens as biases (Where it misses).

## Interface card
Also in `registry.yaml`.

| | |
|---|---|
| **Inputs** | `player_game` parts snaps, game_status, depth, injury, stats (through the gateway); `game` schedule for the horizons |
| **Outputs** | `pcf.experts.participation` variants, walk-forward histories in `outputs/participation/<variant>/<run_id>/history.parquet`: `trees_spikes` (next game's share), `active` (`p_active`), `lasso_h3`, `lasso_rest`, each with `mean`; shares with `q10`, `q50`, `q90`. The next game also has `p_nonzero`, the chance of an offensive snap, and `if_nonzero_mean`, `_q10`, `_q50`, `_q90`, the share if they take one (decision 0014) |
| **Level of detail** | player-game; for the horizons, the row is the game the window starts on |
| **Interval** | 2016–2024 reported, from each team's first game; every rostered QB, RB, WR, TE |
| **Cadence** | in_season |
| **Known at** | the Saturday run, 12:00 Eastern (decision 0010). A horizon's outcome is known when the window's last game is |
| **How to use it** | As a feature for fantasy points: `share`, and `share × points`. Read saved histories, never refit (rule e). Trust the means; treat the horizons' q10 as too high (F14). Filter or flag `played_recently` when scoring. A share is 0 for players who don't take a snap: use `active` for whether they play |
| **Feeds** | `opportunity-quality`, `vacated-opportunity`, `injury-fatigue`, `roles-archetypes`, `player-opportunity`; `career-snaps` (idea) |

## Open questions for the CEO

Answered 2026-11-04: the CEO approved the merge, including no registered champion yet (2), and the sanity list looks fine (3). On (1), the CEO proposed judging the two parts separately (F22); the bar isn't changed yet, and the scorecard says "fail" until the harness can do that.

1. **Next-game coverage, 85.3% against a bar of 75–85%: accept it, and judge spike forecasts by what the spike implies?** F13 shows a perfect forecast would score 85.8%. I recommend yes: the bar stays for ordinary forecasts, and spike forecasts are judged separately on rows with q10 above 0. Changing a bar is your call, so I haven't touched it. The scorecard still says "fail".
2. **Merge without a registered champion, and build it with the weekly run?** Case against, point 6. I recommend yes.
3. **Football sanity review:** the scorecard lists the top and bottom 20 by prediction. Anything that looks off to you?
