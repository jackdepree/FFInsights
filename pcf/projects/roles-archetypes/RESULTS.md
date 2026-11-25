# Results: Roles and archetypes (`roles-archetypes`)

> Written by Claude at the end of the build (2026-11-24), for the CEO's review before the merge. Round 2 (2026-11-25), after the CEO's answers, adds the spot-check of the rushing noise and the backlog ideas that fit (section "Round 2"). The odds were written first, in [BUILD.md](BUILD.md). The technical calls are in [decision 0048](../../docs/decisions/0048-roles-archetypes-build.md). The full numbers are in [build/report.txt](build/report.txt).

**Date:** 2026-11-24 · **Brief:** [BRIEF.md](BRIEF.md) · **MLflow experiment:** `roles-archetypes`, run `696a3f0b827f48549dfc9e3393655df1` ("roles-retro v1") · **Champion:** none registered (a saved history, like schemes-v2's retrospective traits; decision 0048, calls 1 and 26)

## In short

**The role table wins.** Six plain numbers per player-season (snap share, targets per pass snap, carries per run snap, target depth, run and 11-personnel tilts; and their defensive mirror), plus named roles read from them, beat the position labels by 34–63% on next season's per-snap rates. They also add a little beyond his own last-season rates on three of four targets. On the yardstick, they count on both boards: receiving +0.34%, rushing +0.74% of the squared error.

**The pooled PCA coordinates repeat and travel, and beat the labels on three of four targets (+27–43%), but they lose to the role table everywhere.** On the yardstick they count on receiving (+0.30%) and add noise on rushing (−0.90%). By the brief's tie rules, the table is the forecasting input. The coordinates ship as the shared map: description, comparables, the space other measures are read within.

**The autoencoder reconstructs more (0.90 against 0.84) but forecasts worse, so PCA stays.** The coarse named roles flip 3.8% between halves, which passes. The fine ones flip 16.3%, which fails the 14% bar.

**Round 2 (2026-11-25):** the CEO approved the twelve role names, read test 1 as the repeating components (so it passes), shipped the fine roles as leans with "how sure", and vetoed none of decision 0048's calls. The spot-check found the rushing noise is mostly a floor that any six signal-free columns pay on that board (about −0.5%), plus the fullbacks' extreme coordinates. No fix of the coordinates beats the role table there. Of the eight backlog ideas tested, six held in full or where the idea placed them, one held in part (I132) and one failed (I134, the band). The role table also makes better like-for-like substitutes (0.44 on both sides). Without his own rates, it still counts on both yardstick boards. And it adds to a receiver's route-mix forecast.

**Scorecard:** MLflow run `696a3f0b` (metrics and the report) · **Vault:** untouched (2025; the brief) · **Versions tried:** 1 logged run. Before it, the named-role cuts were tried at medians, valleys and quantiles on 2016–2020 only (decision 0048, call 13).

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal / no noise | The coordinates' lasso beats 20 of 20 refits on targets shuffled within season and position, on all four targets. Beyond his own rates (the no-noise target), it ties on targets and tackles and adds on carries (+1.0%, interval +0.0 to +2.0) and rushes (+3.1%, +1.9 to +4.3). It never makes the forecast worse. On the yardstick's rushing board it adds noise (−0.90%); see "Where it misses" |
| Calibration and range coverage | The coordinates' 90% intervals cover 84–91% per axis (two halves inside their combined band). The named roles' "how sure" is calibrated: it said 0.98, 0.83, 0.68 and 0.47, and the label held 0.96, 0.85, 0.69 and 0.52 |
| Leakage | Every rate is shrunk toward priors from seasons up to the row's season. The spaces are walk-forward, and the forecasting tests are fit on earlier target seasons only. The package test `test_walk_never_reads_a_later_target_season` checks this. The ladder's shuffles stay within season and position (a test too). `leakage.scan_code` is clean (no random splitters) |
| Football sanity (CEO review date) | Claude's read (the 2024 top and bottom 10 per axis in the report): in tight is fullbacks and blocking TEs against slot receivers; the featured axis is Kelce, McBride, Bowers, Nabers, Jefferson, Chase; rusher or dropper is Von Miller and Will Anderson against safeties; the tackler axis is Roquan Smith and Patrick Queen. The CEO, 2026-11-25: "I think the 12 role names work great!" (names and roles approved) |
| CEO spot-check (date): what was checked | 2026-11-25, the CEO's pick: the rushing noise (section "The spot-check"). A floor of about −0.5% that signal-free columns pay on that board, plus the fullbacks; no fix beats the role table |

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
  - **The names** were approved by the CEO (2026-11-25: "I think the 12 role names work great!").
- **Coarse role:** one of 5 groups of the named roles: back, in tight, split out, front, coverage.
- **How sure:** the chance that each cut his role passed would come out the same with no sampling noise, multiplied over the cuts.
- **A lean:** a fine role published with its "how sure", to be read as a tilt rather than a fact (the CEO, 2026-11-25: "Yes ship roles as leans with a certainty score"). At 0.9+ it held 96% of the time; below 0.6, about half.

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
| F9 | **On the rushing board, any six signal-free columns that are constant within a player-season cost about 0.5%.** 19 copies of the coordinates, shuffled within season and group, cost −0.48% on average (−1.03 to +0.02); copies of the role table −0.53%. On the receiving board (3.5 times bigger), −0.04% to −0.10% | Round 2's spot-check, 19 copies per input | strong | The crude forecaster's rushing rest-of-season board (backs only), beside participation |
| F10 | **The coordinates' rushing loss is that floor plus the fullbacks.** They sit 0.43 below their own copies (beating 3 of 19). With last season's non-carriers set aside, −0.13% (−0.44 to +0.16), above 18 of 19. It isn't one season (2019 38% of the loss, 2021 35%) or one kind of back (early-down 55%, passing-down 43%). The weak axes hurt most alone: red zone −0.52%, 12 personnel −0.33%; in tight helps (+0.19%) | The spot-check | strong (the floor); medium (the fullbacks' share) | As F9 |
| F11 | **Without his own target rates, the role table still counts on both boards:** receiving +0.23% (+0.14 to +0.32), rushing +0.88% (+0.67 to +1.11), both beating 19 of 19 copies. It still beats the labels on targets (+28%), but only ties on carries (+4.3%). Beyond his own rates, it ties on both. So the table's yardstick worth isn't his own rates. Its carries win over the labels is the shrunk carry rate | I135 | strong | Offense, 4 features: snap share, target depth, run and 11-personnel tilts |
| F12 | **Like-for-like substitutes are clearer on the role table:** the replacement ranks 0.436 on offense (0.404 to 0.466; RB 0.34, TE 0.42, WR 0.49) and 0.440 on defense (0.415 to 0.464; OLB 0.38), against 0.477 on the pooled space | I136, H101's design, 1,120 and 1,710 events | strong | Prior-season tables, standardized |
| F13 | **A hysteresis band doesn't fix the fine roles.** The smallest band that worked on 2017-2020 (0.5 sd) gives 14.05% on 2021-2024 (the bar is 14%; DL 26%, OLB 31%). It ties the plain labels on forecasts. The front's fine roles are blurred, not just noisy | I134 | strong | Fine roles, 200+ snaps |
| F14 | **A newcomer's role leans a little toward the player he replaced:** last season's group average, moved 15% toward the departed player, cuts the squared distance 1.7% (+0.3 to +3.1), beating 20 of 20 placebo vacancies. Moved 25% toward the team's usual role, 1.1%. On the role table, ties | I122, 393 newcomers | medium (small) | WR, TE, RB filling a top player's vacancy |
| F15 | **The passing-down role is paid for edge players.** The team-adjusted 3rd-and-4th-down share adds 5.4% (lasso) to 5.8% (trees) to a next-contract model for DL and OLB, beating 20 of 20. Over all positions it adds 3.6% on the lasso, and ties on the stronger trees | I43, 4,779 veteran contracts signed 2019-2024 | medium | Share of the cap, from the season before |
| F16 | **A receiver's route mix is his, and the role table adds to it:** the vertical share of his targeted routes repeats at r 0.51; his own past share beats the position's mix by 18.6% (+11.5 to +25.0); the role table adds 9.1% beyond it (+6.2 to +12.0, beating 20 of 20) | I57, 1,101 WR and TE pairs (567 scored) | strong | 20+ targeted routes both seasons; routes are post-season data |
| F17 | **Measurables place a rookie receiver on the in-tight axis** (slot or outside): +15.8% over the position mean (+5.2 to +25.2), beating 20 of 20. Not his ball-carrier axis (a tie), and not TEs or RBs (55-58 rookies, ties) | I132, 190 rookies 2017-2024 | medium | First season, 200+ snaps; the 40, height, weight, vertical, shuttle, draft slot |

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

- **The coordinates add noise on the yardstick's rushing board** (−0.90%). The rotation is ruled out: the frozen 2016–2020 fit gives −0.86%. The spot-check (round 2, below) found the cause. Part is a floor of about −0.5% that any six signal-free columns pay on that board (F9). The rest is the fullbacks' extreme coordinates (F10). Rushing reads the role table or the fine back roles instead
- **Fine roles flip where the front blurs.** DL 30% and OLB 34% flip between run defender, pass rusher and box linebacker within a season. That's the rusher cut (0.041 rushes per pass snap, a valley that is shallow for DL) and the tackler cut. A band around each cut (I134) still leaves DL at 26% and OLB at 31% (F13): the blur is real, so these leans need their "how sure"

## The case against

- **The role table is close to his own rates.** Two of its six features are shrunk versions of next season's targets (targets per pass snap, carries per run snap). Part of the table's win over the labels on carries is just that: without them it ties (+4.3%; F11). On the yardstick, though, the table without them still counts on both boards (I135), so its downstream worth isn't his own rates.
- **Test 1 passes only on the reading settled after the result.** As written ("movers keep at least half of each component's season r"), offense failed on the red-zone axis (42%), which doesn't repeat anyway (centred 0.34). The CEO then read it as the repeating components (2026-11-25: "I think movers keep only the parts that repeat"), and on that reading offense passes (79–93%). The reading was settled after the result was seen, at the CEO's call.
- **Round 2 ran many tests on one sample** (eight ideas, about 25 comparisons, all on 2016–2024). Each has its 20 shuffles, but with that many, one false "counts" is plausible. The smallest results (I122's +1.7%, I43's overall lasso +3.6% against a tie on trees) are the ones to doubt first.
- **The spot-check's floor is a guess about its cause.** That signal-free columns cost about 0.5% on rushing is measured. That the board's penalty choice causes it is untested (I137).
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
2. **The front's fine roles** need a better pass-rush measure than sacks and hits per pass snap: the band didn't fix them (I134, killed).
3. **The yardstick's rushing floor** (I137): picking the board's penalty on whole held-out seasons may remove the cost that signal-free columns pay.
4. **Like-for-like comparables from the role table** (I136 held): vacated-offseason should read the table, not the space.

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
| **How to use it** | **As a forecasting input, the role table** (`t*_`): it beats labels and the coordinates and counts on both yardstick boards, even without his own rates (F11). It is also the space for like-for-like comparables (F12) and a receiver's route mix (F16). **The coordinates** (`z*`) are a shared map: description, the space other measures are read within, and an input for receiving only, **never for rushing** (F10). Use `coarse` freely. **The fine `role` ships as a lean, read with `sure`** (the CEO, 2026-11-25): it flips 16% (the front 26–34%), and at 0.9+ it holds 96%. For rushing, the two fine back roles count on their own (+0.45%). Under 200 snaps, read `shrink_w` |
| **Feeds** | skill-over-expected (the role table, I113), vacated-offseason (like-for-like on the role table, H101 and I136; the vacancy blend, I122), VOE (role credit, H108), availability (deep-target receivers), crude-forecaster (the role table), contract-motivation (the passing-down share for DL and OLB, I43), a later rookies' expert (measurables for receivers' in-tight axis, I132) |

## Round 2 (2026-11-25): the CEO's answers, the spot-check and the backlog

### The CEO's answers

Word for word: "I think the 12 role names work great! I think movers keep only the parts that repeat. Yes ship roles as leans with a certainty score. Can you spot check the rushing noise? No vetoes from me. Make sure to check the backlog of ideas and test the ones that fit into both of these builds, please."

- **Role names:** the twelve stand.
- **Test 1:** re-scored on the CEO's reading (movers keep half of each repeating component's season r): **offense passes.** Its five repeating axes keep 79–93%, and the red-zone axis doesn't repeat (centred 0.34). Defense already passed. This was settled after the result, at the CEO's call. The run's code now prints this reading (decision 0048, call 33).
- **Fine roles:** they ship as leans with "how sure", beside the five coarse roles (interface card).
- **Decision 0048:** no vetoes.

### The spot-check: the rushing noise (the CEO's pick)

**The question:** on the yardstick's rushing board, beside participation, the coordinates cost −0.90% while the role table adds +0.74%. What drives the loss? Does it come from one position or one season? Does a fix stay simpler than the table? The odds were written first (BUILD.md, round 2). The scripts are `explore/build2_rushing.py` and `explore/build2_rushing_copies.py`.

**The rows:**
- The rushing rest-of-season board is running backs only: 15,383 rows, 10,207 of them scored (2019–2024), covering 969 back-seasons.
- Each row's prior is last season's main-team coordinates.
- 1,919 scored rows (rookies and newcomers) have no prior and get the column's median.
- 68 player-seasons (915 rows) were non-carriers last season: fullbacks and backs who played like tight ends, named blocking or inline tight end.

**What drives it, in three parts:**
1. **A floor that any six player-constant columns pay on this board** (F9). 19 signal-free copies of the coordinates, shuffled within season and group, cost −0.48% on average (−1.03 to +0.02). Copies of the role table cost −0.53%. On the receiving board, which is 3.5 times bigger, copies cost only −0.04% to −0.10%. So on rushing, "no signal" reads about −0.5%, not 0. My untested guess is in I137: the board's penalty is picked on the latest 20% of each training window. That 20% shares player-seasons with the other 80%, so a column that is constant within a player-season can fit his own leftover error.
2. **The coordinates sit 0.43 below their own copies:** they beat only 3 of 19, so they're worse than signal-free. That part is the fullbacks.
   - Set last season's non-carriers' coordinates aside (missing, so the median) and the coordinates rise to −0.13% (−0.44 to +0.16), above 18 of 19 copies.
   - Their extreme in-tight and red-zone coordinates are leverage points: the board's straight-line fit learns a slope from them that doesn't hold for backs.
   - Adding carries per run snap beside the axes does about the same (−0.25%).
3. **The axes that hurt alone are the weak ones:**
   - the red-zone axis (oz2, the one that doesn't repeat) costs −0.52% on its own;
   - the 12-personnel axis costs −0.33%;
   - the in-tight axis helps (+0.19%, +0.08 to +0.31);
   - the ball-carrier axis is neutral (+0.03%).

**One position or season?** One position by construction: the board is backs only. Otherwise no:
- **Not one kind of back:** early-down backs carry 55% of the loss, passing-down backs 43%.
- **Not one season:** 2019 carries 38% (the first scored season, trained on three seasons) and 2021 35%, while 2024 is slightly positive.
- **By player, it looks like noise:** half the back-seasons are hurt. The ten worst carry 76% of the net loss; they are backs with extreme coordinates, such as Mixon 2019, Ogunbowale 2020 and Barkley 2019.

**Does a fix stay simpler than the table?** No fix of the coordinates beats it.
- The best fix (fullbacks set aside) ties at −0.13%.
- The table counts at +0.74%, and without his own rates at +0.88%.
- The two fine back roles as dummies (early-down, passing-down) count too: +0.45% (+0.30 to +0.60), beating 19 of 19. The step works where the straight line doesn't. "Is a back" alone doesn't (−0.03%).

**The other reading, and what would change the answer.** The other reading is that the coordinates hold real rushing information the board can't use. The evidence is against it: even fixed, they don't count, since they tie and stay below the 19th copy. What would change the answer is a board whose penalty is picked on whole held-out seasons (I137). If the copies' cost fell to about zero there and the fixed coordinates stayed near −0.1%, the verdict would be "no signal, no harm" rather than "noise".

**What it changes:**
- The interface card says rushing reads the role table or the fine back roles, never the coordinates.
- Every rushing-board result should be read against its copies' mean, not against zero.

### The backlog ideas that fit (odds in BUILD.md and IDEAS.md, written first)

| Idea | Result | Verdict |
|---|---|---|
| I133, the rushing noise | The fullbacks are part of it. The board's floor is the rest (above) | Held (killed as a cause; the finding is F9 and F10) |
| I134, a band for the fine roles | 14.05% at the median group, against the 14% bar (DL 26%, OLB 31%); ties on forecasts | Failed: killed |
| I135, the table without his own rates | Counts on both boards (+0.23%, +0.88%). Beats the labels on targets (+28%), ties on carries | Held: graduated (F11) |
| I136, substitutes on the role table | 0.436 offense, 0.440 defense, against 0.477 on the space | Held: graduated (F12), to vacated-offseason |
| I122, the shrunk vacancy forecast | Moving 15% toward the departed player gives +1.7% on the coordinates, beating 20 of 20 placebos; ties on the table | Held, small: graduated (F14), to vacated-offseason |
| I43, the passing-down role in contracts | DL and OLB: +5.4% lasso, +5.8% trees (20 of 20). Overall: lasso +3.6%, trees a tie | Held where the idea placed it: graduated (F15), to contract-motivation |
| I57, the route mix forecast | His own share +18.6%; the role table adds +9.1% (20 of 20) | Held: graduated (F16), to a later receivers' route expert |
| I132, the combine beside the space | WR in tight +15.8% (20 of 20); the WR ball-carrier axis, TEs and RBs tie | Held in part: graduated (F17), to the rookies' expert (the combine table part first) |

**Not tested here, and why:**
- **I23** (receiver depth fit) and **I79** (the per-position map) belong to skill-over-expected: efficiency per target, read within role.
- **I49 and I9** (who inherits an absent player's snaps) belong to vacated-live: in-season snaps.
- **I91** is already closed.

The role table is the input all of them should use.

## Open questions for the CEO

1. **The merge:** may I merge roles-archetypes into main?
2. **I137, the yardstick's rushing floor:** testing it means changing how the shared crude forecaster picks its penalty, so other projects' yardstick numbers would move a little. Should it be its own small task now, or wait for the next retro?
3. **A football question for later:** for DL and OLB, is "pass rusher" against "run defender" a real split within a season, or one job (an edge) whose snaps change by down? The fine roles flip 26–31% there even with a band, and contracts pay for the passing-down share in exactly those groups (F15). Your instinct decides whether a later build chases a better pass-rush measure or merges them.

## At the merge (2026-11-25)

The CEO, word for word: "Yes you can merge roles and archetypes into main. Keep i137 for the next retro. I think those are two distinct roles, we should distinguish between a player that is asked to defend runs and a player that is asked to rush the passer. Those roles can be very similar and have similar outcomes, but we should still try in the future to investigate."

- **I137** waits for the next retro (it would shift every project's yardstick numbers).
- **Pass rusher and run defender** stay two distinct roles for DL and OLB, even where their outcomes look alike. A later build investigates the split (a better pass-rush measure, not a merge of the two roles).
