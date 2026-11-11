# Results: Live runs for the finished experts (`live-experts`)

**Date:** 2026-11-10 · **Brief:** [BRIEF.md](BRIEF.md) (agreed 2026-11-10: 1A, 2A, 3A) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **Status:** built; validating until the first 2 live weeks are in (the brief's tests)

## In short
From the next scheduled run on `main`, the ledger forecasts 18 models before every kickoff: participation's five as before, then Elo's five (margin, total, win chance, wins in the next 3 games and the rest of the season) and schemes-v2's four traits, each trait with its season-to-date average as a yardstick. Elo's live rows keep its ratings, and `pcf ledger score` now sets Elo against the closing line. A full trial at Saturday's moment of week 10 covered all 13 games in about 20 minutes. While GitHub Actions is locked, the odds and nflverse collectors run from this PC; their first runs reached `pcf-data` on 2026-11-10. Nothing has run live yet.

## What's built
- **`pcf.validation.live.MODELS`:** 18 models, participation first (a test keeps it first).
- **Published columns in live rows and ledger files** (`Run.write(publishes=...)`): Elo's 13 rating columns ride with its margin forecasts; a missing one is refused.
- **The scorecard:** pinned backtests for all 13 new models (four new: the season-to-date yardsticks, 2016–2024); `close_card`, Elo's margin and total (average miss, points) and win chance (log loss) against nflverse's closing line on the same games.
- **One retry for a failed refresh** in the ledger's pull (decision 0027, call 5).
- **The PC collectors:** `ops/collect-run.ps1` and `ops/register-collector-tasks.ps1` (decision 0027, calls 6–7).
- **The replay of 2026 weeks 1–9** for the 13 new models, in `pcf-data/replay/` (never counted).

## Findings
**R1. All 18 models make kickoff with room to spare.** Full trial, fresh pull, Saturday noon of week 10 ([`explore/full_trial.py`](explore/full_trial.py)):

| Part | Time |
|---|---|
| Pull (refresh and the live season's tables) | 13 s |
| Participation's five | 14.4 min (trees_week 3.9) |
| Elo's five | 3.2 min |
| Schemes' eight | 2.3 min |
| **All 18** | **19.9 min** |

Every model wrote rows for all 13 due games (408 player rows for participation, 13 game rows for Elo's game forecasts, 26 team rows for the rest).

**R2. The input check is clean for the new models after a fresh pull.** The exploration's snap-share flags on Elo were stale data. Participation's injury inputs are flagged in this trial only because Saturday's report doesn't exist on a Tuesday.

**R3. Elo's live forecasts look like football.** Before the refresh, its week-10 margins matched the current spread at r 0.94, 1.4 points apart on average (EXPLORATION). After it, they moved with week 9's results (BUF at NYJ: Bills by 8.8, then 10.8).

**R4. The collectors run from the PC.** Odds: 29 ESPN games caught up, The Odds API's lines for 27 games (428 credits left this month). nflverse: 10 change-log entries. Both pushed as `pcf-collector-pc`. The first nflverse attempt failed because nflverse replaced its schedule file mid-download; the retry 15 seconds later worked (R5).

**R5. A refresh can fail for a moment, and the ledger's would have stopped the run.** The same download sits under the ledger's pull, so one mismatch at Thursday noon would have cost every forecast that run. Both now retry once after a minute.

**R6. On the replay of 2026 weeks 1–9 (not a record), no model is worse than its backtest's range, and Elo is about as far behind the close as it was in its backtest.** (`pcf ledger score --replay`, 136 games)

| Elo against the close | Measure | Elo | Close | Behind | Backtest, 2016–2024 (elo#F2) |
|---|---|---|---|---|---|
| Margin | average miss, points | 9.77 | 9.49 | 0.28 | 0.27 |
| Total | average miss, points | 11.10 | 10.60 | 0.50 | 0.30 |
| Win chance | log loss | 0.635 | 0.622 | 0.012 | 0.019 |

- 12 of the 13 new models can be scored so far (wins over the rest of the season waits for the season's end). None is worse than its backtest's 90% interval for 9 weeks; tempo is better than its interval (59.3 against 59.7–72.7 on the range score ×100). The schemes finals beat their season-to-date yardsticks here too (pass rate over expected 2.15 against 2.36).
- It's a replay, made today with today's data, so it says the pipeline scores correctly and nothing looks broken. It is not evidence of live skill.

## Spot-check before merge (the CEO's pick: Elo against the close, 2026-11-10)
Recomputed by hand from the raw replay files and nflverse's raw schedule, with none of pcf's scoring code:
- **The numbers match.** Margin 9.766 against the close's 9.485 (0.280 behind) and total 11.100 against 10.596 (0.504 behind), both to the last digit. Win chance 0.635 against 0.623 (0.012 behind) by hand, where `close_card` reads 0.6346 against 0.6223 on 135 games. The one game apart is the week 5 tie (NYG 27, WAS 27): the scorecard leaves ties out of win chance, as Elo's backtest does.
- **The line's direction is right.** A positive `spread_line` means the home team is favored (SEA −166 at +3.0 in week 1), the same direction as Elo's margin and the result (home minus away).
- **Every game is there, and every forecast came before its game.** All 136 finished games of weeks 1–9, each forecast at least 8 hours before kickoff; the 9 Thursday games were forecast at Thursday noon.
- **Six games walked through,** one every few weeks. In week 1, ARI won 26–14 at LAC: Elo had LAC by 6.0 and missed by 18.0, while the close had LAC by 8.5 and missed by 20.5. Elo and the close are usually a few points apart and both miss big upsets.

## Case against
1. **Nothing has run live.** Every number above is a trial at a future moment with Tuesday's data. The first real test is Thursday 2026-11-12 (participation only, unless this merges first) and Saturday 2026-11-14.
2. **Thanksgiving is the tightest run.** On Thursday 2026-11-26 the first game (CHI at DET) is at 13:00, so the noon run waits for the injury file until 12:15 at the latest, then takes about 20 minutes: participation done by about 12:30, Elo and schemes by about 12:36. That leaves about 25 minutes. A slow pull or a slower PC could push the last models past kickoff; their rows would be left out, and the record would say so.
3. **Eight weeks can't say much about Elo against the market.** Elo was 0.27 points behind the close on margins over 2016–2024. With about 110 live games, the live gap's own noise is several times that, and `close_card` has no interval yet. It's a running record, not a verdict, until a season or more is in.
4. **The new yardsticks' backtests are lighter.** They ran with 20 shuffled refits, not 100. They're yardsticks, not candidates, but their scorecards are less thorough than the finals'.
5. **The PC collectors depend on the PC.** If it's off or asleep and can't wake, a run is missed, and The Odds API's props for that window are lost. GitHub's collectors didn't have that weakness.
6. **The replay isn't a record.** Weeks 1–9 were remade today with today's data, cut by the known-at rules. Weeks 1–8 have no first-seen proof for injuries (prediction-ledger, decision 2).

## Interface card
| | |
|---|---|
| **Inputs** | Each model's own inputs, through the gateway, at the run's moment |
| **Outputs** | Per run, in `pcf-data/ledger/<season>/<run>/`: one file per model (`<project>__<variant>.parquet`), standard output plus kickoff, record, commit, data pull time; Elo's margin file adds its 13 rating columns. `pcf ledger score` writes the scorecard and `_close` (Elo against the closing line) to `data/ledger/scorecards/` |
| **Level of detail** | player-game (participation), game (Elo's margin, total, win), team-game (Elo's wins, schemes) |
| **Cadence** | in_season: Tuesday 10:00, Thursday and Saturday noon Eastern (the ledger task) |
| **Known at** | each run's moment; rows for games already kicked off are left out |
| **How to use it** | Higher layers read the counted rows (`ledger.read`) as the live part of each model's walk-forward history |
| **Feeds** | the scorecards; later, pace, totals and player opportunity |

## Technical calls (for veto at merge)
Decision 0027's seven calls:
- participation first;
- live rows keep what an expert publishes;
- each new model's backtest pinned, with new 2016–2024 backtests for the four yardsticks;
- Elo set against nflverse's close after the game, in Elo's own measures;
- one retry for a failed refresh;
- the PC collectors copy the Actions jobs (30 minutes later on Tuesday and Saturday, their own clone, the key never logged);
- they stand down once GitHub's collector pushes again.

## Open questions for the CEO
None. The tasks for the PC collectors are registered after the merge (they run the copy of `main`).
