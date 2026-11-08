# 0021: Elo's season pull is 0.4, and Elo saves its ratings for higher layers

**Date:** 2026-11-07 · **Decided by:** the CEO asked for both ("we will apply that rate"; "save the ratings as outputs the other models can read"); Claude made the technical calls below, listed for veto at merge · **Project:** `elo`

## 1. The pull between seasons: 0.5 → 0.4

**The CEO's question:** how much does a team's strength carry from one season to the next? Use that rate.

**What was measured** (`projects/elo/explore/carryover.py`, regular seasons 2002–2024):

| This season → next season | Share kept (slope) | Correlation |
|---|---|---|
| Mean margin → mean margin | 0.42 | 0.41 |
| Schedule-adjusted margin → schedule-adjusted margin | 0.45 | 0.45 |
| Elo's end-of-season rating → next season's schedule-adjusted margin | 0.65 (0.68 in 2002–15, 0.60 in 2015–24) | 0.46 |
| Elo's end-of-season rating → next end-of-season rating | 0.59 | 0.58 |

A raw season result keeps about 0.42–0.45 of itself, so it needs a pull of about 0.55. Elo's end-of-season rating keeps more, 0.60–0.68, because the walk has already smoothed out part of the season's luck. The rate that applies to our rating is therefore a pull of 0.32–0.40.

The walk's own forecasts (rating only, mean miss on the home margin):

| Pull | 2002–15 weeks 1–4 | 2002–15 all | 2016–24 weeks 1–4 | 2016–24 all |
|---|---|---|---|---|
| 0.3 | 10.949 | 10.834 | 10.148 | 10.189 |
| **0.4** | 10.905 | 10.812 | 10.148 | **10.173** |
| 0.5 (before) | **10.892** | **10.809** | 10.187 | 10.178 |
| 0.6 | 10.910 | 10.819 | 10.251 | 10.199 |

**Decision:** pull 0.4. It's the one value both measures support: the carryover slope says 0.32–0.40, and the forecasts say 0.4–0.5. The difference is tiny either way: 0.003–0.005 points over a season, and 0.04 points in weeks 1–4 of recent seasons. The offense and defense pull stays at one third, since the question was about the rating.

**Caveat (in RESULTS' case against):** the old exploration picked 0.5 on 2002–2015 alone. 0.4 leans partly on 2016–2024, which are the reported seasons. That's a mild peek, worth at most 0.005 points.

## 2. The ratings are saved with the margin's walk-forward history

**Decision:**
- **A new contract attribute, `Expert.publishes`.** It lists feature columns that get saved in the walk-forward history next to the forecast, in `history.parquet`. Higher layers read them through the same gateway call as the forecasts (`view.output("elo")`), under the same timing and vintage rules.
- **What Elo's margin variant publishes, per game:**
  - home field;
  - each team's rating, offense and defense, as they stood at the forecast's moment;
  - whether each team's usual QB is out;
  - each team's same-team share.

**Why these choices:**
- **Ratings are made without fitting**, from results known by the moment. So they're walk-forward by construction (rule e), and the leakage checks already compare them across per-moment and bulk runs.
- **They go in the history file** rather than a separate one, so a higher layer gets them with no new storage, no second gateway path and no second vintage check.
- **Only the margin variant carries them.** All variants share the same features, so one copy is enough.

**Shared-code change (for veto):** leakage check 3's future world now scrambles every value column of an upstream output except ids and metadata. Before, it scrambled only the forecast columns, which would have let a published feature from the future pass unchanged. A test covers it.

**Not yet:** the live run (`pcf ledger run`) writes only forecasts. When a higher layer needs this week's ratings live, the live run publishes them too.

**Alternatives:**
- A separate `features.parquet` with its own gateway call. Same data, but twice the plumbing.
- Every rating as its own forecast row (`quantity = elo_rating`). This was the tempting option, rejected: a rating isn't a forecast with a range, and the standard schema's range columns would be empty or invented.
