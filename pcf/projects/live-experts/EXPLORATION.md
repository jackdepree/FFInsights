# Exploration: live runs for the finished experts (`live-experts`)

**Date:** 2026-11-10 · **Time box:** a light exploration (infrastructure) · **Verdict: GO.** The collectors' outage is a separate problem for the CEO · **Script:** [`explore/first_look.py`](explore/first_look.py)

## The question

Can Elo and the schemes-v2 trait forecasts join the scheduled ledger run this season, with no weekly work from the CEO? What stands in the way?

## The answer in one paragraph

It mostly works already. All nine final forecasts (Elo's five, schemes' four) go through the ledger's live path for week 10 with no code changes: every one of the 14 games gets its rows, in 22–53 seconds a model, about 6 minutes for all nine. Elo's margins agree with the current spread at r 0.94, 1.4 points apart on average. What's missing is small: the models aren't on the ledger's list, Elo's ratings aren't kept with live rows, and the scorecard doesn't know their backtests. Separately, **both GitHub collectors have been down since 2026-11-05 and still are,** so The Odds API's prices and props for weeks 9–10 are already lost.

## What we measured

| Check | Result |
|---|---|
| The scheduled ledger run | Registered as "PCF ledger run": Tuesday 10:00, Thursday and Saturday noon Eastern, in its own copy of the repo that always holds the latest `main`. Ran today at 10:00 with nothing due (exit 0). Forecasts participation only (`live.MODELS`) |
| What's in `pcf-data` | No live run yet: the first counted forecast is Thursday 2026-11-12. One replay (2026 weeks 1–8, participation) |
| Elo and schemes through the live path, week 10 | Works with no code changes. Thursday noon: 1 game; Saturday noon: 13 games. Elo's margin, total and win: one row per game; its wins forecasts and schemes' traits: one per team. Nothing missing, nothing failed |
| Time per model | Elo 43–53 s each (it replays every season's ratings from 1999), schemes 22–23 s each, fitting under 0.1 s: about 6 minutes for all nine, on top of participation's roughly 25 |
| Football sanity | Elo's margin against nflverse's current spread for the 13 games with one: r 0.94, average gap 1.4 points (e.g. JAX at TEN: Elo −11.9, spread −10.0) |
| The scorecard | `ledger_score.BACKTESTS` pins one backtest per model; only participation's five are pinned. Elo's and schemes' saved backtests exist (`outputs/elo/<variant>/`, `outputs/schemes-v2/<variant>/`) |
| Closing lines for Elo | In our tables already: nflverse's schedule carries each game's closing spread, total and moneylines (`game` table), which is what Elo's market yardsticks use. No collector needed for "against the close" |
| The line at our forecast's moment | Needs our own collectors (The Odds API, ESPN), which have stopped (finding 1) |

## Findings

**1. Both GitHub collectors have been down since 2026-11-05 (the billing lock), and still are.** Every scheduled run of `collect-odds` and `snapshot-nflverse` since then has failed; the last odds snapshot in `pcf-data` is 2026-11-03 and the last nflverse snapshot 2026-11-04. What that loses, and what it doesn't:
- **Lost for good:** The Odds API's prices and props (FanDuel, anytime TD) for weeks 9–10 so far, and the line at any given moment.
- **Recoverable:** ESPN keeps each game's opening and closing lines, so its backfill can fill the gap once a collector runs again. nflverse's own schedule keeps the closing lines.
- **Also stopped:** the nflverse snapshots, which are the ledger's proof of when we first had a file (prediction-ledger, "first seen"), and the backup check that emails the CEO when a ledger run is missing.

The ledger run itself doesn't depend on GitHub Actions: it runs on this PC and pushes with git.

**2. The live path already handles game and team-game rows.** The ledger writes whatever keys an expert declares (`game_id`, or `game_id` and `team`), and checks win chances as probabilities. Three small gaps:
- **The list:** `live.MODELS` names participation's five only.
- **Elo's ratings:** its backtest history keeps the ratings it publishes for higher layers (decision 0021), but the live path and the ledger's files keep only the standard output, so live rows lose them (the registry already says "Live runs don't carry the ratings yet").
- **The scorecard:** `ledger_score.BACKTESTS` has no pinned backtest for Elo or schemes, so it would skip their rows. Nor does it compare Elo with the close.

**3. The input check flags the snap-share inputs on Saturday** (`share_diff`, `share_missing`) for Elo's margin, total and win. That's expected here: the trial didn't refresh, so week 10's rosters and injury reports weren't in. A real run refreshes first; the first live Saturday will show whether the flag stays.

**4. Forecasts are trained only through week 9's Thursday game** (`train_end` 2026-11-07), for the same reason: this PC's tables were built before week 9's Sunday games. Again a trial limit, not a live one.

## Assumptions and limits

- The trial used the data already on this PC (pulled before 2026-11-10), not a fresh pull, so its week-10 rows are what a run would make with slightly older data.
- It timed each model alone; the scheduled run does them one after another with one data pull.

## Go or no-go

**GO.** The work is a short list (finding 2), and a run adds about 6 minutes. Two things are the CEO's: which forecasts go in, and what to do about the collectors (finding 1). Both are in the brief.
