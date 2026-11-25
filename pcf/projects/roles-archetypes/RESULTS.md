# Results: Roles and archetypes (`roles-archetypes`)

> Written by Claude at the end of the build (2026-11-24), for the CEO's review before the merge. The odds were written first, in [BUILD.md](BUILD.md). The technical calls are in [decision 0048](../../docs/decisions/0048-roles-archetypes-build.md). The full numbers are in [build/report.txt](build/report.txt).

**Date:** 2026-11-24 · **Brief:** [BRIEF.md](BRIEF.md) · **MLflow experiment:** `roles-archetypes`, run `696a3f0b827f48549dfc9e3393655df1` ("roles-retro v1") · **Champion:** none registered (a saved history, like schemes-v2's retrospective traits; decision 0048, calls 1 and 26)

## In short

**The role table wins.** Six plain numbers per player-season (snap share, targets per pass snap, carries per run snap, target depth, run and 11-personnel tilts; and their defensive mirror), plus named roles read from them, beat the position labels by 34–63% on next season's per-snap rates. They also add a little beyond his own last-season rates on three of four targets. On the yardstick, they count on both boards: receiving +0.34%, rushing +0.74% of the squared error.

**The pooled PCA coordinates repeat and travel, and beat the labels on three of four targets (+27–43%), but they lose to the role table everywhere.** On the yardstick they count on receiving (+0.30%) and add noise on rushing (−0.90%). By the brief's tie rules, the table is the forecasting input. The coordinates ship as the shared map: description, comparables, the space other measures are read within.

**The autoencoder reconstructs more (0.90 against 0.84) but forecasts worse, so PCA stays.** The coarse named roles flip 3.8% between halves, which passes. The fine ones flip 16.3%, which fails the 14% bar.

**Scorecard:** MLflow run `696a3f0b` (metrics and the report) · **Vault:** untouched (2025; the brief) · **Versions tried:** 1 logged run. Before it, the named-role cuts were tried at medians, valleys and quantiles on 2016–2020 only (decision 0048, call 13).

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal / no noise | The coordinates' lasso beats 20 of 20 refits on targets shuffled within season and position, on all four targets. Beyond his own rates (the no-noise target), it ties on targets and tackles and adds on carries (+1.0%, interval +0.0 to +2.0) and rushes (+3.1%, +1.9 to +4.3). It never makes the forecast worse. On the yardstick's rushing board it adds noise (−0.90%); see "Where it misses" |
| Calibration and range coverage | The coordinates' 90% intervals cover 84–91% per axis (two halves inside their combined band). The named roles' "how sure" is calibrated: it said 0.98, 0.83, 0.68 and 0.47, and the label held 0.96, 0.85, 0.69 and 0.52 |
| Leakage | Every rate is shrunk toward priors from seasons up to the row's season. The spaces are walk-forward, and the forecasting tests are fit on earlier target seasons only. The package test `test_walk_never_reads_a_later_target_season` checks this. The ladder's shuffles stay within season and position (a test too). `leakage.scan_code` is clean (no random splitters) |
| Football sanity (CEO review date) | Claude's read (the 2024 top and bottom 10 per axis in the report): in tight is fullbacks and blocking TEs against slot receivers; the featured axis is Kelce, McBride, Bowers, Nabers, Jefferson, Chase; rusher or dropper is Von Miller and Will Anderson against safeties; the tackler axis is Roquan Smith and Patrick Queen. The CEO's review: pending |
| CEO spot-check (date): what was checked | Pending |

## Hunch verdicts

The brief's hunches (H99–H108) were closed by the CEO after the exploration. The build adds no new hunch. Claude's ideas carried by the build are closed in `IDEAS.md` (below).

## Terms

- **Pooled role space:** one PCA per side of the ball, fit across its positions together (offense: WR, TE, RB; defense: DL, OLB, ILB, CB, S), with no position label and no measurables. It's refit after each completed season and rotated to the last fit. The published axes, read from the 2024 fit:
  - **Offense:**
    - `oz0` in tight or split out;
    - `oz1` the ball carrier, against target depth;
    - `oz2` red zone and late downs;
    - `oz3` 12 personnel, against heavy sets;
    - `oz4` the featured target: targets per pass snap and snap share;
    - `oz5` playing time in the red zone, against middle targets.
  - **Defense:**
    - `dz0` box or coverage (the sub-package player);
    - `dz1` rusher or dropper;
    - `dz2` red zone;
    - `dz3` the tackler;
    - `dz4` the late-down tackler;
    - `dz5` playing time.
- **Role coordinates:** a player-season's six numbers in his side's space, with a 90% interval from split-half noise, shrunk toward his group's mean under 200 snaps.
- **Role table:** six usage features per side (decision 0048, call 12), shrunk toward priors from earlier seasons.
- **Named role:** one of 12 fine roles, read by explicit rules on the role table with cuts frozen on 2016–2020:
  - **Offense:** early-down back, passing-down back, blocking tight end, inline tight end, slot receiver, deep threat, outside receiver.
  - **Defense:** pass rusher, box linebacker, run defender, slot defender, base defensive back.
  - **Working names:** the names are the CEO's taste call.
- **Coarse role:** one of 5 groups of the named roles: back, in tight, split out, front, coverage.
- **How sure:** the chance that each cut his role passed would come out the same with no sampling noise, multiplied over the cuts.

## Findings

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| F1 | **A six-feature role table beats position labels on next season's per-snap usage, and beats the pooled PCA too.** Over labels: targets +48%, carries +63%, tackles +34%, rushes per pass snap +37%. Over the coordinates: +10%, +207%, +12% and +15% | Run `696a3f0b`, tests 2 and rung 2; 821 offensive and 1,725 defensive pairs, 2021–2024 | strong | WR, TE, RB; DL, OLB, ILB, CB, S; 200+ snaps both seasons |
| F2 | **The role table adds a little beyond his own last-season rates:** carries +3.7%, tackles +1.5%, rushes +2.7%; targets a tie (+1.7%, −0.8 to +3.9). The coordinates add less (carries +1.0%, rushes +3.1%), and where the table is already in, the coordinates add nothing or worse | Test 3 | medium (the table includes shrunk versions of two of his own rates) | as F1 |
| F3 | **The pooled spaces repeat held out and travel with movers:** fit on 2016–2020 and read on 2021–2024, 5 of 6 offensive and 4 of 6 defensive axes repeat at 0.5+ centred within position. Movers keep 79–93% (offense, but the red zone 42%) and 73–98% (defense). PCA beats the labels on targets (+43%), tackles (+27%) and rushes (+28%), not carries (tie) | Test 1, test 2 | strong | as F1 |
| F4 | **On the yardstick, the role table counts on both boards:** receiving +0.34% of the squared error (+0.17 to +0.51), rushing +0.74% (+0.53 to +0.97), both beating all 19 shuffled copies. The coordinates count on receiving (+0.30%, +0.18 to +0.42) and add noise on rushing (−0.90%) | Test 4; 36,125 and 10,207 board rows | strong (receiving, the table on rushing); the rushing noise's cause: see "Where it misses" | rest-of-season receiving and rushing yards, 2021–2024 |
| F5 | **Named roles: the coarse five are stable, and the fine twelve aren't stable enough.** Coarse roles flip 3.8% between a season's halves; fine roles flip 16.3% at the median group (DL 30% and OLB 34%, between run defender, pass rusher and box linebacker; CB 13%, S 9%, ILB 7%). "How sure" is calibrated. Positionless rules put 102 OLBs and 222 DL among the pass rushers, 156 DL and 247 OLB among the box linebackers, and 24 safeties among the slot defenders | Test 5 | strong | 200+ snaps, 2021–2024 |
| F6 | **Like-for-like substitutes on the pooled space: defense passes, offense doesn't quite.** The replacement is closer in role than chance: rank 0.477 on defense (0.457 to 0.496) and 0.477 on offense (0.447 to 0.510; RB 0.43, TE 0.53, WR 0.48) | Test 5, H101's design; 1,710 and 1,120 events | medium | prior-season coordinates |
| F7 | **The autoencoder fits the features better and forecasts worse.** It reconstructs 0.90–0.92 against PCA's 0.84–0.85, but loses to PCA alone on targets (−17%), tackles (−17%) and rushes (−4%). Beyond his own rates it ties three times and adds +1.1% on rushes. It doesn't repeat better (centred split-half lower on 4 of 6 offensive axes) | Rung 4, test 1 | strong | as F1 |
| F8 | **Trees on the coordinates fix the carries step and nothing else.** +44% over the lasso on carries alone (the lasso can't make the back/not-back jump), +4% on rushes. Worse on targets (−12%) and beyond his own rates on every target (−6% to −25%) | Rung 3 | strong | as F1 |

## The ladder

| Rung | Method | Result vs the rung below | Takeaway carried forward |
|---|---|---|---|
| 0 | Position labels (lasso on group dummies) | — | The bar |
| 1 | The role table and named roles (lasso) | **Better on all four targets**, +34% to +63% | The role is a few plain usage rates. Snap share and his own rates carry most of it |
| 2 | The pooled PCA per side | **Worse than rung 1 on all four** (−10% to −207%). The ladder stops here by rule k | Its axes mix the table's signal with weak features (red zone, late downs). The lasso can't make carries' step from them |
| 3 | Trees on the coordinates (run anyway, the brief's carries question) | Better than the PCA lasso on carries (+44%) and rushes (+4%), tie on tackles, worse on targets; still worse than rung 1 | The carries step is real (back or not). The table has it directly as carries per run snap |
| 4 | The autoencoder (exploratory, run anyway) | Worse than PCA on three of four alone; ties beyond his own rates | More reconstruction isn't more signal. PCA stays (rule k) |

## Where it misses

*Not a forecasting model, so the miss lenses don't apply.* Two places worth chasing:

- **The coordinates add noise on the yardstick's rushing board** (−0.90%, while their shuffled copies cost only −0.09% at best). A follow-up run (2026-11-24, scratch, not logged) rules out the rotation: the frozen 2016–2020 fit's coordinates give −0.86%, axes 4–5 alone are neutral (+0.06%), and the ball-carrier axis alone is neutral (+0.03%). The noise sits in axes 0–3 together (−0.81%). A likely cause, untested: the in-tight axis puts fullbacks and blocking tight ends beside the backs, and a linear fit on the board reads it as carries; the role table has carries per run snap directly. I133 tests it
- **Fine roles flip where the front blurs.** DL 30% and OLB 34% flip between run defender, pass rusher and box linebacker within a season. That's the rusher cut (0.041 rushes per pass snap, a valley that is shallow for DL) and the tackler cut. I134 tries a band around each cut.

## The case against

- **The role table is close to his own rates.** Two of its six features are shrunk versions of next season's targets (targets per pass snap, carries per run snap), and the third test's "own rates" are the same rates, raw. Part of the table's win over the labels (and over PCA) is just that. Beyond his own rates its gain is small (1.5–3.7%), and on targets a tie. Fair test: a table without those two features, on the yardstick (I135).
- **Test 1 fails as written for offense.** "Movers keep at least half of each component's season r" fails on the red-zone axis (42%), which also fails to repeat (centred 0.34). The other reading, only the components that repeat, passes. Claude reported the strict reading; the CEO decides.
- **The named-role cuts were chosen looking at flips on 2016–2020.** Medians, then valleys and quantiles, until the coarse roles flipped little and the fine ones stopped improving. The scored seasons weren't looked at, but the choice of cut type is a degree of freedom, and the fine roles still fail.
- **Offense's axes 4 and 5 rotate between fit windows** (congruence against the frozen fit 0.26 and 0.20), because they explain nearly the same variance. A reader of `z4` and `z5` over seasons sees slowly changing meanings even with the Procrustes chain. Step to step it holds 0.95+, but across 2016 to 2024 it drifts. (It isn't what hurts on the rushing board: the frozen fit does the same.)
- **The yardstick's gains are small and from one design.** +0.3% to +0.7% of the squared error, beside participation, on 2021–2024 only. The vault (2025) is untouched, so there's no second sample.
- **Substitutes on offense miss the bar by a hair** (0.477, interval to 0.510). With the axes scaled within position it is 0.479, the same. RB passes alone (0.43); TE doesn't (0.53).

## Pitfalls

- **The exploration's counts picked a player's group across both sides,** so a few defenders with offensive snaps (and the reverse) were placed in the other side's space (CB and ILB rows in offense's group means). Fixed in the build: the group is picked within the side (decision 0048, call 5).
- **Median cuts on features that repeat about 0.8 flip about 20% between halves.** A rule's cut belongs where few players sit: a valley, or a high quantile.
- **The role table and the own rates share columns** (snap share). The ladder's column list is deduplicated, or the lasso sees the column twice.
- **The report was first written under `src/`** (a `parents[3]` path); fixed to the project folder.

## Not looked at

- **Quarterbacks' space and rookies from measurables** (the brief's later plan).
- **The 40-yard dash:** the combine is only a raw file, not a table (decision 0048, call 25).
- **I57 (forecasting the route mix), I122 (the shrunk vacancy forecast), I49 (swap pairs):** not this build's tests. They're left open with their next home noted.
- **H108's role credit for VOE:** offered in the exploration, not rebuilt here.
- **The vault.**

## Could be improved

1. **Feed the role table, not the coordinates, to the yardstick and skill-over-expected.** It is the forecasting input (F1, F4).
2. **A hysteresis band for the fine roles** (I134): keep last half's label unless he moves clearly past the cut. Aimed at DL and OLB flips.
3. **Find why the coordinates add noise on rushing** (I133): the fullback reading above, by dropping fullbacks or adding carries per run snap beside the axes.
4. **Substitutes measured with the role table** rather than the pooled space (I136): it may pass where the space misses on offense.

## Don't redo

- **The autoencoder at this size.** It reconstructs more and forecasts less (F7). A nonlinear method should be tried only with a target to fit, not a reconstruction.
- **Trees on the coordinates beyond his own rates** (−6% to −25%).
- **Median cuts for named roles.**

## Interface card

Also in this project's `interface` block in `registry.yaml`.

| | |
|---|---|
| **Inputs** | `play.pbp`, `player_play.on_field` (post-season), through the gateway |
| **Outputs** | `outputs/roles-archetypes/<run_id>/history.parquet` (run `696a3f0b`, pinned in `history_runs`), per player-team-season 2016–2024 (14,065 rows). Columns: keys `gsis_id`, `team`, `season`, `side`, `group`; `snaps`; `z0`–`z5` with `z*_lo`, `z*_hi` (90%); `shrink_w`; `role`, `coarse`, `sure`; the role table `t0_*`–`t5_*`; `version`; `as_of`, `train_end`, `cadence` |
| **Level of detail** | player-team-season |
| **Interval** | once a season, after participation's release |
| **Cadence** | retrospective |
| **Known at** | after the season's last game plus participation's release; an in-season model reads it only from completed seasons, as a prior (rule m) |
| **How to use it** | **As a forecasting input, the role table** (`t*_`): it beats labels and the coordinates and counts on both yardstick boards. **The coordinates** (`z*`) are a shared map: comparables, the space other measures are read within, and an input for receiving only. Use `coarse` freely. Use the fine `role` with `sure` (it flips 16%; 0.9+ holds 96%). Under 200 snaps, read `shrink_w` |
| **Feeds** | skill-over-expected (the role table, I113), vacated-offseason (like-for-like, H101), VOE (role credit, H108), availability (deep-target receivers), crude-forecaster (the role table) |

## Open questions for the CEO

1. **Role names (taste):** are the 12 working names right? Early-down back, passing-down back, blocking tight end, inline tight end, slot receiver, deep threat, outside receiver; pass rusher, box linebacker, run defender, slot defender, base defensive back. Would you split or merge any (for example, a "move tight end", or an "edge" that is both DL and OLB)?
2. **Test 1's reading:** did "movers keep at least half of each component's season r" mean every component, or only the ones that repeat? Offense fails the first reading on the red-zone axis alone.
3. **Fine roles:** ship them as leans with their "how sure" (the coarse five pass), or hold them back until a hysteresis band (I134) gets them under 14%?
4. **The spot-check:** which decision or finding do you want walked through in depth?
