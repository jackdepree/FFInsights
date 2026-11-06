# Brief: Prediction ledger (`prediction-ledger`)

**Status:** draft, 2026-11-06 · **Layer:** data and infrastructure (phase 0) · **Cadence:** in_season

## The question
Can we keep a permanent record of what PCF forecast before each game, made and saved automatically, so we can check how it really does on games it hasn't seen?

## Why it matters
- **It's the only honest test left.** `trees_week`'s inputs were chosen on the same seasons they were tested on (RESULTS, case against 10). A forecast saved before kickoff can't have that problem.
- **Lost weeks don't come back.** A forecast recreated later is never quite the one we'd have made. About 9 regular-season weeks and the playoffs remain in 2026.
- **It builds the track record** any public product would need, and it's where closing line value gets measured once products join.

## Terms
- **Standard terms used:** [range score (pinball), MAE, coverage, known-at, as_of, closing line value](../../docs/GLOSSARY.md).
- **New terms:**
  - **Ledger row:** one forecast for one player and game, with the exact model and data behind it. Never changed once written.
  - **First seen:** the moment our own pull first held a row of a source. It's proof of when we had it, where the source gives no date.
  - **Input check:** at each run, how often each input is filled compared with the backtest. It catches inputs that have gone missing live.
  - **Replay:** a forecast remade later for a game already played. It's useful, but it's not a record, and it's never counted as one.

## Builds on
| Project | What we use | Why |
|---|---|---|
| `validation-harness` | The contract, `as_of` gateway, moments (decision 0010), scores, live-gap rule (VALIDATION §1, §9) | Live forecasts must follow the same rules as the backtest |
| `participation` | The four champions and their backtest scores | The first forecasts, and what live results are compared with |
| `timeline` | The injury known-at rule (timeline#F4) | This is the rule to fix |
| `data-layer` | `pcf refresh`, and daily snapshots in `pcf-data` | Fresh data, and our proof of first seen |
| `odds-collection` | The private `pcf-data` repo and its push pattern | Where the ledger lives |

**Already tried:** the exploration ran a real forecast for week 9. The path works, and it found the injury problem ([EXPLORATION.md](EXPLORATION.md)).

## Assumptions
- **Injury reports reach nflverse before the Saturday noon run.** Seen by 13:31 Eastern once. Tested on the first live Saturday.
- **This PC is on, or can wake, at run times, with the CEO logged in.** A missed run leaves a gap, and the record says so.
- **A model refit each run scores about like one refit each season,** as validated. It has fresher data, so if anything it should do a little better. The live-gap check would catch the opposite.
- **Fill-in roster rows are good enough for the Wednesday run** when this week's rows haven't landed. Those rows are marked.

## Goals
1. **Fix the injury rule first,** so live forecasts see what the backtest saw.
2. **A forecast for every game, saved before kickoff,** with no weekly work from the CEO.
3. **Nothing can be changed or backdated.** Each run writes its own file, nothing is ever overwritten, and a forecast after kickoff is refused.
4. **Every row can be traced:** model, code commit, training cutoff and data pulled.
5. **A weekly score against the backtest,** using the live-gap rule that already exists.

## Tests
No bar in `docs/VALIDATION.md` changes. The specific ones:
- **Success looks like:**
  - The injury check passes: reports appear for about 7–10% of rows at the Saturday moment in 2026, against 0 now, and all future-data checks still pass.
  - In the first 2 live weeks, every game has rows pushed to `pcf-data` before kickoff, or its gap is explained.
  - Tests show a second write to the same run, or a write after kickoff, is refused.
  - Rerunning a run on the same code and data matches to the last digit.
  - A scorecard appears each week, with range score, average miss and coverage against the backtest.
- **Failure looks like:**
  - Runs miss more than 1 week in 4 for reasons we can't fix: move where it runs.
  - The fix can only work by showing data before we could have had it: stop, and bring it back to the CEO.
- **The live-gap rule (already agreed):** after at least 4 live weeks, a model is flagged if its live score is outside its backtest's 90% interval on the worse side.
- **Seasons:** live from 2026, week 10. The 2025 vault stays closed: training on it is fine, scoring it isn't.

## Inputs and outputs
- **Inputs:** what each model already reads, through the gateway; `pcf refresh` at run time; our snapshots for first seen.
- **Outputs:**
  - One file per run in the private `pcf-data` repo, at player-game level, per model: mean, q10, q50, q90 and the spike parts, as_of, kickoff, model, commit, training cutoff, data pull time, and input-check results. Empty market columns are ready for products.
  - A weekly scorecard on the PC.
  - Failed runs show as a Windows notice, and a small GitHub Action checks for new rows, as a backup.

## How it will be used
- **Now:** the real test of `trees_week`. If it holds up, we trust it, and if not, we find out why.
- **Later:** every champion joins, and products add market lines so closing line value can be measured. It's also the honest record behind anything public.

## Plan
Time box: 2–3 sessions. No model ladder, as this is infrastructure.
1. Fix the injury rule, with the input check as a shared tool.
2. `pcf.core.ledger`: write-once files, refusal after kickoff, rows that can be traced.
3. A live run that reuses the harness's fit and predict, and pushes to `pcf-data`.
4. The weekly scorecard.
5. Task Scheduler, with one approval from the CEO, plus the backup check.

**First counted forecast:** Wednesday 2026-11-11, 16:00 Eastern, for week 10's Thursday game. Sunday's games follow at Saturday noon.

## Decisions for the CEO

**1. What goes in the ledger?**
- **A. All four participation champions plus `last_game` as a yardstick (recommended).** It tests every horizon we'd hand to higher layers, and a simple comparison shows whether the gain survives live. New champions join with one line.
- **B. Next-game `trees_week` only.** The simplest, but the other horizons have no live record when fantasy needs them.
- **C. Every variant we've built (tempting, bad).** It looks thorough, but with enough variants one will look good by luck, and we'd be picking winners after seeing results.

**2. What about weeks 1–8 of 2026?**
- **A. Replay them once, in a separate file marked as a replay (recommended).** These seasons weren't used to pick the inputs, so it's a useful early read: 8 weeks now, instead of waiting until week 13. It does use up 2026's early weeks as unseen data, and weeks before 2026-10-31 have no first-seen proof, so they use a fallback rule.
- **B. No replay.** The cleanest record, but no read on 2026 until 4 live weeks are in.
- **C. Put them in the ledger as if live (tempting, bad).** It looks like a longer track record, but it wouldn't be a real one, and that would undermine the whole ledger.

**3. Injury rule: for information, it's a technical call unless you object.**
- **Recommended:** a report counts as known when we first saw it in a pull. For rows before our snapshots began (the 2025 vault and 2026 before 2026-10-31), a fallback measured on 2021–2024's real timestamps, with its too-early rate logged.
- **Rejected:** simply moving the rule to noon the day before. That's the old rule, and it was too early for 6–7% of reports (timeline#F4).
