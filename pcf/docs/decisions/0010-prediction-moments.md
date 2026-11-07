# 0010: Prediction moments are the weekly runs

**Date:** 2026-11-02 · **Decided by:** CEO (1C in the `validation-harness` brief), Claude (the times and the fallback)

**Changed 2026-11-06:** the Wednesday 16:00 run moved to Thursday 12:00 (CEO; [decision 0016](0016-thursday-run.md)). The text below is as decided on 2026-11-02.

**Decision:** The three weekly runs are named prediction moments: **Tuesday 10:00, Wednesday 16:00 and Saturday 12:00 Eastern**, on those days inside each week window. A model declares its `run`. Each game is predicted at the latest run before its kickoff that the model may use: its own run and the earlier ones. So a Saturday model predicts Thursday games at the Wednesday run, never after kickoff. A week that starts mid-week (2010 and 2020–21 Tuesday games, the Friday-start week 1 of 1999–2001) can have no allowed run before a game. Its moment is then 10:00 ET on the window's first day (`fallback`). Retrospective models predict a season at 10:00 ET on the first day of its week-1 window; offseason-events models at the start of the event's phase. The code is `pcf.data.timeline.moments`.

**Why:** a moment decides what a model may use. The exploration found that a Tuesday 10:00 moment can't see last Monday night's stats, which are known 24 hours after kickoff (validation-harness#F2). It also can't see the week's closing lines, known at kickoff (#F3). Backtesting each model at the moment its product is used makes the backtest match live use. Waivers use Tuesday; Sunday start/sit and props use Saturday.

**Alternatives:**
- Tuesday only. It's the earliest, but the two Monday-night teams are a game behind in every feature.
- Wednesday only. Last week is complete, but it comes after many waivers run.
- Counting Monday night as known by Tuesday morning (rejected): it's unproven. If nflverse publishes late, live results are quietly worse than the backtest.

**Revisit if:** `weekly-run` changes the run times, or the live ledger shows nflverse stats reliably arrive before Tuesday 10:00. A tighter known-at rule would then let Tuesday see Monday night.
