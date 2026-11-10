# Brief: Live runs for the finished experts (`live-experts`)

**Status:** agreed (2026-11-10) · **Layer:** data and infrastructure (phase 0) · **Cadence:** in_season

## The usual way
A scheduled job pulls fresh data, loads the approved version of each model, and scores the upcoming games. It writes every forecast to a store that can't be edited, stamped with the model version and the time. It watches for inputs that go missing or drift, and grades the forecasts once results arrive against what the backtest promised. Betting shops also stamp each number against the market price at that moment and at the close.

## Analogies
- **Paper trading.** A trading strategy runs live without real money for a while, to see whether the backtest's edge survives real timing, fees and missing data. Elo against the closing line is our paper trade.
- **Weather forecast verification.** Forecasts go out on a fixed schedule and are archived as issued; forecasters are scored on the archive, never on reruns. So a forecast remade later doesn't count, and a missed week can't be filled in.

## CEO hunches
None (the CEO, 2026-11-10: "No hunches, go ahead").

## The question
Can Elo's game forecasts and the schemes-v2 trait forecasts be saved before kickoff every week, beside participation's, so the rest of 2026 gives them an honest live record?

## Why it matters
- **It's the market test.** Elo's margin, total and win chance against the closing line is the first live read on "beating the market", PCF's first measure of success.
- **It settles what the vault couldn't.** Schemes-v2 left rung 2 for pass rate and throw depth against the league to live seasons (RESULTS, Could be improved 4).
- **Downstream models need live histories** (rule e): pace, totals and player opportunity will read these forecasts as features, and from 2026 on that history can only come from the ledger.
- **Lost weeks don't come back.** About 8 regular-season weeks and the playoffs remain.

## Terms
- **Standard terms used:** [ledger row, replay, input check, range score (pinball), coverage, closing line value, as_of, known-at](../../docs/GLOSSARY.md).
- **New terms:** none.

## Builds on
| Project | What we use | Why |
|---|---|---|
| `prediction-ledger` | The scheduled run (`pcf ledger run`, Task Scheduler), write-once files in `pcf-data`, the input check, the weekly scorecard and its live-gap flag | It already does this for participation; Elo and schemes join it |
| `elo` | The final variants `margin`, `total`, `win`, `wins_next3`, `wins_rest`, and the ratings it publishes (decision 0021) | The game-level forecasts, and the ratings higher layers read |
| `schemes-v2` | The final variants `pass_oe_rung2`, `shotgun_rung2`, `depth_rung2`, `tempo_shrunk` | The trait forecasts pace and player volume will read |
| `baselines` | The no-vig closing line (`MarketMargin`, `MarketTotal`, `MarketWin`) | Elo's market yardstick |
| `odds-collection` | The collected lines | The line at our forecast's moment (later, with products) |

**Already tried:** the exploration put all nine forecasts through the live path for week 10 ([EXPLORATION.md](EXPLORATION.md)).

## Assumptions
- **The run still makes kickoff with nine more models.** Participation's five take about 25 minutes; Elo's five about 4 and schemes' four about 1.5 (exploration).
- **Closing lines arrive in nflverse's schedule after each game,** as they have every season. Tested at the first scorecard.
- **The PC is on, or can wake, at run times,** as for participation.

## Goals
1. Elo's and schemes' forecasts in every scheduled run, before kickoff, with no weekly work from the CEO.
2. Elo's ratings saved with its live rows, as they are in its backtest history, so higher layers can read them.
3. The weekly scorecard covers them: each against its own backtest (the live-gap rule), and Elo also against the closing line.
4. The collectors running again (decision 3).

## Tests
No bar in `docs/VALIDATION.md` changes.
- **Success looks like:**
  - In the first 2 live weeks, every game has Elo and schemes rows in `pcf-data` before kickoff, or its gap is explained.
  - Participation's rows still arrive before kickoff (adding models doesn't crowd them out).
  - A rerun on the same code and data matches to the last digit.
  - The scorecard shows each new model's live score against its backtest's interval, and Elo's gap to the close.
- **Failure looks like:** runs miss kickoff for the new models more than 1 week in 4 for reasons we can't fix.
- **The live-gap rule (already agreed):** after at least 4 live weeks, a model is flagged if its live score is outside its backtest's 90% interval on the worse side.
- **Seasons:** live from 2026 week 10. Training on 2025 is fine; scoring it isn't (participation's rule).

## Inputs and outputs
- **Inputs:** what each model already reads, through the gateway, at the run's moment.
- **Outputs:** one file per model per run in `pcf-data`: Elo per game (margin, total, win chance) and per team-game (wins in the next 3 games and the rest of the season); schemes per team-game (four traits); each with mean and q10, q50, q90 (win chance: mean only), `as_of`, kickoff, model, commit and training cutoff. The scorecard gains their rows.

## How it will be used
- **Now:** the honest test of Elo against the market, and of schemes' live-only questions.
- **Later:** the saved forecasts are the walk-forward history pace, totals and player opportunity train on.

## Decisions (CEO, 2026-11-10: 1A, 2A, 3A)

**1. What goes in the ledger?** *(why it matters: whatever isn't logged now has no live record later, but every extra model is one more chance of a lucky-looking winner)*
- **A. The nine final forecasts, with yardsticks that cost nothing extra (chosen).** Elo's five finals, scored after each game against the closing line (already in our tables, so no extra rows); schemes' four finals, plus each trait's season-to-date average as its simple comparison, as `last_game` is for participation.
- **B. Elo's margin, total and win chance only.** The market test, and nothing else. Simplest, but schemes' live questions and the long-horizon wins forecasts get no record.
- **C. Every variant we've built (tempting, bad).** It looks thorough, but with 40-odd variants one will look good by luck, and the anti-traits are retired.

**2. What about 2026 weeks 1–9?**
- **A. Replay them once, in a separate file marked as a replay (chosen)**, as for participation: an early read now, never counted as a record.
- **B. No replay.** The cleanest record, but no read until 4 live weeks are in (early December).
- **C. Put them in the ledger as if live (tempting, bad).** A longer-looking record that isn't one.

**3. The collectors have been down since 2026-11-05 (GitHub's billing lock).** *(why it matters: The Odds API's prices and props, and the line at any moment, are lost for every week they're down; ESPN's open and close can be backfilled later)*
- **A. Run both collectors from this PC, on their usual days, until GitHub is unlocked (chosen; the CEO's approval of the scheduled task and of the sign-off).** One more scheduled task, using the key already in `pcf/.env`. It changes where collectors run (decision 0005) for now, so it needs your sign-off.
- **B. Wait for GitHub Support.** Nothing to set up, but each week waiting is lost.
- **C. Clear the billing issue on GitHub's side.** Only you can do this; it can go with A or B.

## Technical calls (Claude's, listed for veto)
- Participation runs first, then Elo, then schemes, so a slow run never costs participation its kickoff.
- Live rows carry each model's published columns (Elo's ratings), as its backtest history does.
- The scorecard pins each new model's validated backtest, as it does for participation.
- Elo's market comparison uses nflverse's closing lines, not our collectors; the ledger's `market_*` columns stay empty until a product brings the line at its moment.

## Plan
Time box: one session. No model ladder: this is infrastructure.
1. The CEO's decisions above.
2. Add the models to `live.MODELS`, carry published columns, pin the backtests, add Elo's closing-line comparison to the scorecard; tests.
3. A full trial run (refresh, all fourteen models, not pushed) for timing.
4. Merge to `main` (the scheduled run uses `main`), with the CEO's approval. **To make Saturday 2026-11-14's run,** the merge is needed by Saturday morning; Thursday's single game will most likely be participation only.
5. The replay (decision 2), and the collectors (decision 3).
