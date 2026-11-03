# Exploration: Miss lenses (`miss-lenses`)

> A first look at where the baselines miss: which tags and categories explain the most of the lasso's and ECR's errors on held-out games? The answer picks the short list of lenses every RESULTS.md looks through ("Where it misses", CEO 2026-11-03), and checks ideas I1–I3.
> Run on 2026-11-03 with [`explore/profile_misses.py`](explore/profile_misses.py) on the baselines' walk-forward histories: the lasso (2016–2024, Tuesday run, 52,472 player-games) and ECR (2022–2024, Saturday run, 13,181). The vault (2025) wasn't read.

**How a lens is scored.** A miss is actual points minus the model's projection. For each lens (a way to split player-games into groups, within each position):
- **Bias:** the share of the squared miss removed by correcting each group's average miss. The corrections are learned on even seasons and applied to odd ones, and back, so a lens with many small groups can't look good by fitting noise. Near 0 means the model is right on average in every group.
- **Spread:** the same for the size of the miss: are the misses bigger in some groups?
- **Top group:** the group with the largest average miss (200+ rows), with a 90% interval resampled by week.

**Verdict: GO, with a twist.** The lens list is short because almost nothing known before the game explains the misses (F1). The misses come from what happens in the game: how much a player plays, and how much their team scores (F2). That says more about the next experts than about tags (F6).

## Findings

| # | Finding | Confidence |
|---|---|---|
| F1 | **No tag known before the game explains more than 0.6% of either model's squared miss.** All 22 pre-game lenses (position, week, experience, age, depth, injury report, a teammate out, home, the 13 player and team tags, the opponent's backup QB) score 0.0–0.5% for the lasso and below 0.2% for ECR. Some groups are off on average (the lasso: −1.2 points for players active while questionable, +0.6 when a same-position teammate is out), but they're small groups or small misses. | strong |
| F2 | **After the game, three lenses explain most of what can be explained:** the player's snap share (lasso 8.0% of the squared miss, ECR 3.6%), their team's points (6.4%, 6.6%) and the final margin (2.3%, 2.7%). For QBs, a completion-above-expected game alone explains 10–11%. Players under 25% of snaps score 2.3 points below the lasso (1.8 below ECR); teams scoring 31+ put their players 1.9 above ECR. | strong |
| F3 | **The size of a miss depends on depth and snaps, not on tags.** Depth-chart rank explains 4.5% (lasso) and 5.4% (ECR) of the variation in miss size, snap share 7.8% and 8.7%. Every tag is under 0.4%. | strong |
| F4 | **Role changes are information the lasso lacks but ECR has (idea I3: killed for ECR).** With a same-position teammate listed Out, the lasso under-projects by 0.61 points (0.48 to 0.73, 6,642 player-games). ECR doesn't (−0.19 overall, RB +0.46 on 305). ECR's misses are no bigger after a role change: new team, first game back, backup QB starting. | strong (lasso), medium (ECR: 3 seasons) |
| F5 | **Recent form adds a little on top of the season-so-far average (idea I2: confirmed).** Weeks 5+, fit 2016–2020, scored 2021–2024: adding the last 4 games to the season average cuts the error by 0.01 (QB, WR), 0.01 (TE) and 0.04 (RB) points. The season average carries 0.52–0.67 of the weight, the last 4 games 0.14–0.31. | strong |
| F6 | **ECR's expert spread mostly tracks rank, not risk (idea I1: inconclusive).** By position, a wider spread goes with *more* coverage (WR 86.5% in the widest quarter against 78.0% in the narrowest), because deep-ranked players score little and disagree most. Within ranks 1–24, the widest spreads cover a little less (74–77% against 79–82%), on few rows (38 and 223). | weak |
| F7 | **Two lenses can't be scored this way:** season (each half sees different seasons) and position (every lens is already measured within position). They're shown as groups, not ranked. | strong |

## What this means for the brief

- **The fixed lenses can be few: position, depth, week band (before the game) and snap share, team points, final margin (after it).** Every other tag adds nothing on average (F1). The template's "at most 5 others, only when clearly off" still catches the odd group.
- **After-game lenses are diagnostic, never features.** They say *what* went differently, so they point at what to predict next. They must be labelled as such.
- **The next experts follow from F2, not from tags:** a player's share of snaps (`participation`) and their team's scoring (`team-efficiency`, `pace`, and the market's implied team totals once odds are a table). Those are the two parts of the miss that no baseline predicts well.
- **The lens check should be a function, not a notebook,** so every scorecard gets it the same way.
