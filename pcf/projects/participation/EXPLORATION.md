# Exploration: Participation and snaps (`participation`)

> A first look at PCF's first expert: is a player's share of their team's offensive snaps predictable before kickoff, and would knowing it fix the fantasy baselines' misses? It follows from miss-lenses#F2: playing time is the largest part of the misses that no baseline predicts.
> Run on 2026-11-03 with [`explore/profile_participation.py`](explore/profile_participation.py) on the built tables. Rows: every rostered QB, RB, WR and TE with an earlier game, 2013–2024 (101,780 player-games). Fit on 2013–2020, scored on 2021–2024. The vault (2025) wasn't read.

**Two information sets:**
- **Tuesday:** earlier games' snap shares (last game, last 3, last 8, season so far), games played, this week's depth chart, new team, rookie.
- **Saturday:** Tuesday's, plus the week's injury report (game status, practice) and how much share the same-position teammates listed Out or Doubtful usually take.

**Verdict: GO.** Snap share has strong signal, and the injury report adds a lot (F2, F3). The catch is what it's worth downstream: a predicted share fixes 2.4–3.0% of the lasso's squared miss, but only 0.3–0.6% of ECR's (F5). FantasyPros' experts already know who will play and how much. **This expert makes box-score models catch up with ECR on playing time; it won't beat ECR by itself.**

## Findings

| # | Finding | Confidence |
|---|---|---|
| F1 | **Snap counts cover every rostered skill player from 2013,** but a share needs a status. Game statuses (active or inactive) start in 2019; before that, a player with no snap-count row didn't play. 16.5% of rostered QB/RB/WR/TE player-games are inactive, and 8.1% are active with no offensive snap. Shares are two-humped: 52% of QB rows are 0 (backups), and 36% are over half. | strong |
| F2 | **The injury report decides who plays.** Predicting active or not: AUC 0.81 on Tuesday's information, **0.92 with Saturday's** (Brier 0.079 → 0.053; 12.6% inactive). | strong |
| F3 | **Snap share is predictable, more so by Saturday.** Share of variance explained, 2021–2024: the last-3-games average 0.53–0.60; a gradient-boosted model on Tuesday's information 0.62–0.71; on Saturday's **0.69–0.76** (QB 0.76, RB 0.70, WR 0.72, TE 0.72). A linear model sits in between. | strong |
| F4 | **Because shares are two-humped, the mean is a poor summary.** Last game's share has a lower absolute error than the boosted model at QB (12.1 vs 14.1 points of share on Tuesday), since a backup's 0 is usually 0 again. A model of the mean wins on squared error and loses on absolute error. The honest output is a probability of playing plus a share if active, with ranges. | strong |
| F5 | **A pre-game share fixes some of the lasso's misses and almost none of ECR's.** Share of the squared miss removed by a correction on the snap share, learned on other seasons, 2021–2024: lasso 2.4% (Tuesday), 2.9% (Saturday), 14.4% if the actual share were known; ECR 0.3%, 0.6% and 9.4%. What ECR misses about playing time happens *during* the game (injuries, blowouts, game plans), not before it. | strong |
| F6 | **Rows to predict need a rule.** 12% of rostered skill players never play an offensive snap in a season (third QBs, practice-squad call-ups). Predicting them is easy and inflates scores; scoring should weight or filter them consistently. | medium |

## What this means for the brief

- **Predict a player's offensive snap share for the next game, with a probability of being active**, for every rostered QB, RB, WR and TE (F1, F4).
- **Run on Saturday,** after the injury report (F2, F3). A Tuesday version is a variant if a product needs it.
- **Climb the ladder:** last-3 average → lasso → boosted trees (F3).
- **Set expectations:** its downstream value is for box-score models and as a building block (vacated opportunity, game simulator), not to beat ECR alone (F5). The no-noise test should name the lasso's fantasy points as its downstream target.
