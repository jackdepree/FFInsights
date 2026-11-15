# Exploration: Crude forecaster (`crude-forecaster`)

> A first look at the yardstick: a deliberately simple forecast of yards that any expert's saved output can be added to, so every expert is scored the same way. Is there room for experts to add anything, and what do the CEO's hunches H50–H55 look like on a rough version?
> Run on 2026-11-15 with [`explore/first_look.py`](explore/first_look.py) (output: [`explore/first_look.txt`](explore/first_look.txt)). Rows: every rostered QB, RB, WR and TE in a regular-season game, and every team-game, 2016–2024. Forecasts for 2019–2024, each season from models fit on 2016 to the season before. The vault (2025) wasn't read.

**How to read the numbers.** "Removes X%" means the share of squared error removed, against always guessing the average (for the crude model) or against the crude model (for an expert). Intervals are 90%, from resampling whole weeks. All of it is discovery: one rough version, not through the gateway or the harness, and the 2019–2024 seasons have now been looked at once for this project.

**The rough version.** Inputs from earlier games only: the average of yards (season so far, last 4 games, last season), the season's running total, last 4 minus the season, the game-to-game spread; the same averages for attempts, first downs and touchdowns; yards per attempt. Model: a lasso and gradient-boosted trees, averaged. The trees are scikit-learn's, because xgboost isn't installed (the build installs it and compares).

**Verdict: GO.** There is plenty of room and the yardstick separates the experts clearly: participation is worth 8% to 25% of the crude model's error on player yards, the team experts 0.1% to 1.7% each, and one expert (schemes) shows nothing clear on three of four targets. Two things need the CEO's eye before the brief is agreed: team yards are barely predictable by anything (F2), and one play's yards even less (F12).

## The noise ceiling (measured first)

| Target | Rows scored | Average | Crude model removes | Hindsight average removes | With every expert added |
|---|---|---|---|---|---|
| Passing yards (QBs) | 8,111 | 95.2 | 61.2% | 60.3% | 71.1% |
| Rushing yards (RBs) | 13,102 | 22.8 | 42.3% | 44.9% | 48.8% |
| Receiving yards (WR, TE, RB) | 42,981 | 18.0 | 40.3% | 41.6% | 45.3% |
| Team yards gained (= the opponent's yards allowed) | 3,198 | 359.1 | 7.5% | 5.5% | 9.3% |

- **The hindsight average** is each player's (or team's) average over the *other* games of the same season: what you'd know about him with the whole season in hand, and nothing about the week. The crude model already matches it. So the room that is left is not "know the player better"; it is **what changes week to week** (who plays, how much, against whom), which is what the experts are for.
- **It is not a true ceiling.** Adding every expert goes past it on all four targets. A real upper bound (for example, the forecast if the actual snaps were known) wasn't measured; participation#F5 put that at 14% of the lasso's fantasy-point miss.
- **Fitting noise: not measured.** Three seeds of the trees gave identical results, because these trees have no randomness as configured. That says nothing about noise from row order or resampled training seasons. The build measures it properly (seeds with subsampling on, VALIDATION.md §5).
- **Most player rows are easy zeros.** Passing yards "removes 61%" largely by knowing who the backup is: among QBs who took a snap it removes 29%. Every number is reported for all rostered players; the build needs a rule for which rows count (participation#F6).

## Findings

| # | Finding | Confidence |
|---|---|---|
| F1 | **Player yards are predictable from crude inputs; the model matches the hindsight average.** 61% (passing), 42% (rushing), 40% (receiving) of squared error removed. | strong |
| F2 | **Team yards are barely predictable: 7.5%.** The offense's own past removes 5.6%, the defense's past 1.1%, both 7.5%. Yards gained is mostly the offense's; "yards allowed" is the same number seen from the other side, so the five targets are four different forecasts plus a mirror. | strong |
| F3 | **The lasso and the trees are level for players; the trees hurt for teams.** Lasso, trees, mix: passing 60.5 / 60.2 / 61.2%; rushing 42.5 / 40.5 / 42.3%; receiving 39.8 / 39.9 / 40.3%; team 9.0 / 2.8 / 7.5%. The mix earns its place only narrowly for passing and receiving; for team yards the lasso alone is better (rule k). | medium: one setting of the trees |
| F4 | **H51: past yards carry almost all of it.** Yards-only inputs give 98–100% of what the full crude model explains (passing 60.7 of 61.2; rushing 42.2 of 42.3; receiving 39.7 of 40.3). First downs add 0.1 to 0.2 points, nothing clear; attempts and touchdowns add the remaining 0.1 to 0.6. | strong |
| F5 | **H52: receivers aren't the easiest.** Among players who took a snap: QBs' passing yards have the smallest typical miss (0.36 of their average), RBs' rushing 0.60, WRs' receiving 0.65, TEs' 0.74, RBs' receiving 0.86. By share removed: RB rushing 41%, TE receiving 39%, WR receiving 35%, QB passing 29%, RB receiving 22%. Wide receivers are in the middle on both. | strong |
| F6 | **H50: participation adds the most to player yards by far; opponent-aware experts lead only for team yards.** Shapley share of the crude model's error removed: participation 24.5% (passing), 10.1% (rushing), 8.3% (receiving). Elo 0.47 / 0.39 / 0.12%, all clear of zero. Team efficiency 0.20 / 0.53 / 0.04% (clear for passing and rushing). For team yards: Elo 1.13% (0.51 to 1.75), efficiency 0.52% (0.06 to 0.97), pace 0.20% and schemes 0.14% (neither clear). | strong for the order; medium for the small ones |
| F7 | **The two readings agree, and the overlap is where expected.** "Added alone" and the Shapley share differ little for participation (24.8 against 24.5%) and by about half for Elo and efficiency on passing and team yards (Elo alone 1.70% on team yards, share 1.13%): those two carry some of the same thing. Method C costs 32 fits per player target and took about 20 minutes for everything. | strong |
| F8 | **Schemes add nothing clear, and pace slightly hurts receiving yards.** Schemes: share −0.01% to +0.14%, no interval clear of zero. Pace on receiving yards: −0.06% (−0.12 to −0.00). | medium |
| F9 | **H53: split by kind of expert.** All experts together improve attempts far more than yards per attempt (passing +29.0% against +2.4%; rushing +16.5% against +2.7%; receiving +13.6% against +0.4%), and that is all participation, which does nothing for efficiency (−0.1 to −0.2%). The opponent-aware experts go the CEO's way: Elo and team efficiency improve yards per attempt more than attempts (passing: efficiency expert +2.37% against +0.53%, Elo +2.16% against +1.17%; rushing: +1.70% against +0.28%). Yards per attempt itself is nearly unpredictable from a player's past (crude removes 3.4%, −0.7%, 5.1%). | medium: efficiency is scored only on games with enough attempts (15 passes, 8 carries, 4 targets), a filter on the outcome |
| F10 | **H54: recent games carry forward for players, not for teams.** The last-4 inputs add 5.5% (4.2 to 6.9) for passing, 1.8% (1.1 to 2.5) rushing, 1.0% (0.7 to 1.3) receiving, and 0.1% (−0.5 to +0.7) for team yards. | medium: for a player, "recent" is mostly a changed role (who starts now), not a hot streak; it wasn't tested with participation already in, where it should shrink |
| F11 | **H55: the spread repeats, mostly because it grows with the average.** Raw, odd against even weeks: rushing 0.61, receiving 0.58, passing 0.31; season to next season 0.59, 0.67, 0.16. With the average taken out: 0.23, 0.16, 0.30 (odd against even) and 0.20, 0.14, 0.14 (season to season), all clear of zero, all under 0.3 across seasons. As an input it does nothing for the middle (−0.05 to +0.21%, none clear) and relates weakly to the size of the miss (r 0.05 to 0.14), so any use is in the range. | medium: correlations computed directly, not with `pcf.validation.consistency` |
| F12 | **One play's yards: about 2% is explainable before the snap.** The situation (down, distance, field position, clock, score, formation) removes 2.06%; both teams' yards per play so far brings it to 2.24%; knowing run or pass, 3.24%. | medium: one model, fit 2016–2021, scored 2022–2024 |

## The hunches

| # | Hunch | Verdict | Real? | Pays? | CEO said | Claude said |
|---|---|---|---|---|---|---|
| H50 | Opponent-aware experts add the most | **partly**: failed for player yards, held for team yards (F6) | partly | yes, small: Elo 0.1–1.1%, efficiency 0.0–0.5% | 60% there'd be signal: there is | team 60%: happened; player 25%: didn't |
| H51 | Past yards and first downs carry most of the explained variance | **held**, and by more than either of us said: 98–100%, nearly all of it yards (F4) | yes | first downs: no | about 50% | 70% that the share tops 70%: yes; first downs under 2%: yes |
| H52 | Wide receivers' yards are the easiest to predict | **failed** (F5) | no | not a forecast | 60% | 20%; QB smallest miss and RB rushing largest share among those playing: both happened |
| H53 | Experts improve efficiency more than volume | **unclear**: no for all experts together, yes for the opponent-aware ones (F9) | partly | efficiency gains 0.9–2.4% of a small thing | 60% | 25%: right overall, wrong about Elo and efficiency |
| H54 | Recent games carry forward | **held** for players, failed for teams (F10) | yes for players (likely role, not form) | yes: 1.0–5.5% | 40% | 60% detectable: yes; "small": wrong, it's the largest crude input after the averages |
| H55 | Boom-or-bust is a lasting trait | **held, weakly** (F11) | yes, weak: 0.14–0.20 season to season once the average is out | no for the middle; not tested for the range | 70% | 80% repeats: yes; 40% above 0.3: no |

Retro pattern check: P1 (ownership, who plays) predicted participation would dominate, and it did. P2 (team-level matchups fail) didn't predict that Elo and efficiency would clear zero on three targets; they did, by small amounts. P7 (real isn't the same as useful) fits H55.

## The case against this exploration

- **The experts' outputs weren't lined up in time.** Each was read from its saved walk-forward history, made on its own day of the week (Tuesday or Saturday). Participation's Saturday forecast knows the injury report; the crude inputs don't. Part of participation's 8–25% is "the injury report", not "the expert". The build fixes the moment for every input.
- **Easy zeros flatter everything.** Third QBs and inactive players are most of the rows and most of participation's gain. Among players certain to play, every number above would be smaller and the order might change.
- **One version, six seasons, looked at once.** Small gains (schemes, pace, the 0.1–0.5% ones) are inside what a different tree setting could move; retro pattern P8 says gains under 0.3% in an exploration don't survive a build.
- **Yards aren't the products.** Nothing here says what an expert is worth for fantasy points, touchdowns or margins.
- **Longer horizons weren't run** (next 3 games, rest of season), though the CEO asked for them. They are in the brief's plan, not in these numbers.

## What this means for the brief

- **Keep the CEO's design; it works as a yardstick** (F1, F6): crude inputs, lasso and trees, experts added as inputs, read by methods A and C.
- **Fix one forecast moment** and line every expert's output up to it (the case against).
- **Report two row sets:** all rostered players, and players expected to play, so the easy zeros can't carry a result (F5, noise ceiling).
- **Team yards: the CEO's call.** At 7.5% explained, the team-level yardstick has little to work with, though it did rank Elo above efficiency above the rest (F2, F6). Options are in the brief.
- **Play level: the CEO's call.** About 2% of one play's yards is explainable (F12).
- **The model:** install xgboost and compare lasso, trees and the mix per target; for team yards the lasso alone leads (F3).
- **Measure fitting noise properly** before reading any gain under 0.5%.
