# Results: Participation inference, second edition (`participation-late`)

**Date:** 2026-11-12 · **Status:** validating; the CEO's spot-check done (the leakage check), waiting on vetoes and merge approval · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** `participation-late` · **Technical calls:** [decision 0031](../../docs/decisions/0031-participation-late.md) · **Code:** `pcf.experts.participation_late` (reuses `pcf.experts.participation_live`)

## In short
**A second edition of the map, made once FTN's charting is out.** Every game of 2023–2024 is rebuilt about two weeks after kickoff, each season trained on the three before. It uses the morning-after map's model plus FTN's counts per play: the backfield, the box, pass rushers, blitzers, motion, play action and screens. It is saved as its own output (`participation-late`), so the morning-after map is never rewritten.

What it gets right:
- **It's a little better on every measure, in both seasons.**
  - Log loss on open spots is 0.34% lower on offense and 0.19% lower on defense (R1).
  - The likeliest lineup gets 0.15 points more of the open spots right on offense and 0.09 on defense.
  - The whole 11 is right on 24.0% of offensive plays, against 23.7%.
- **It moves the map without overturning it.** A chance moves 1.2 points on average, and 12.6% of play-sides get a different likeliest lineup (R2).
- **The weights read like football** (R3). More in the backfield raises a back's chance most. A loaded box raises linemen, tight ends and the front seven and lowers receivers and defensive backs least. Screens raise backs and lower tight ends.
- **Calibration and certainty hold.** Calibration error is 1.06 points (offense) and 0.76 (defense), inside the bar. Each play's certainty stays honest within 1 point (R4).
- **Nothing leaks.** Sample games rebuilt from a view at their late `as_of` match the season run exactly (gap 0.0), and a view at the morning after holds none of the game's FTN rows (0) (R5).

**The CEO's hunch H39 failed:** the next game's snap counts add nothing (0.00%, participation-late#F1). They stay out.

**The gain is small.** FTN's counts lean toward personnel without fixing it. Knowing each play's personnel would be worth 4–6 points (participation-live#R11); FTN gives about a twentieth of that.

**Scores:** [build/backtest.txt](build/backtest.txt) (pooled, by season, by position group, certainty, the FTN weights) and [build/shuffled.txt](build/shuffled.txt) (the no-noise check). MLflow run `2a30b3e5b03d43b1b80ee7e82d8c4e69` (1,779 s).

**Vault:** closed; 2025 is untouched. 2022 can't be tested (FTN starts there, so there's nothing earlier to learn its weights from).

**Versions tried:** three in the build (the morning-after map refitted, the late edition trained on three seasons, the late edition trained on FTN's seasons only), after the exploration's three (H39's next game, the previous game, FTN).

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal / no noise | Yes. The late edition beats the morning-after map in both seasons and on both sides (log loss −0.38% / −0.30% offense, −0.16% / −0.21% defense). With FTN's counts shuffled across plays, the same model scores like the morning-after map (within 0.0001 in every season and side), so the gain is FTN's, not the extra inputs' (R6). By position group, log loss improves in 7 of 8 groups; the offensive line is 0.1% worse (R7) |
| Calibration | Inside the 3-point bar: 1.06 points (slope 1.06) on offense, 0.76 (slope 1.05) on defense, against 1.05 and 0.77 for the morning-after map |
| Uncertainty | The chances are the uncertainty (each cell's chance of being on). Each play's `certainty` is honest within 1 point: 88.0% expected against 89.0% right on offense, 82.5% against 83.2% on defense (R4) |
| Leakage | Point-in-time gap 0.0 on sample games rebuilt from a view at their late `as_of`; 0 FTN rows visible at the morning after; every `as_of` is at least 14 days after kickoff and every `train_end` before kickoff (R5) |
| Football sanity | Every play has 11 a side in both lineups. The snap-matched lineup keeps 99.2% of players within one play of their snap count. The FTN weights point the football way (R3). The CEO's review: pending |
| CEO spot-check | Done (2026-11-12): the leakage check, five doors and a control; no leak found (The CEO's spot-check: the leakage check) |

## Hunch verdicts
From the exploration ([explore/late_inputs.py](explore/late_inputs.py) → [late_inputs.txt](explore/late_inputs.txt)). Copied into [`HUNCHES.md`](../HUNCHES.md).

| # | Hunch | Verdict | Evidence, with its size |
|---|---|---|---|
| H39 | "add the snap counts for the next game, and then we just predict the past game" | **failed** | Each player's snap share in his team's next game, as a change from this game's: +0.00% log loss on offense, +0.01% on defense, in both held-out seasons. The previous game's: +0.02% / +0.01%. This game's own snap count already fixes how many snaps he played; next week's only says where his role is heading (participation-late#F1). Claude expected a small gain (under 0.5%) |

## Terms
New in `docs/GLOSSARY.md`: **edition (vintage)**, a map of the same games made at a later moment with more evidence, kept beside the earlier one rather than replacing it.

## Findings
Numbered R1–R7 so they don't clash with the exploration's F1–F3. Cite as `participation-late#R1`.

**R1. FTN's counts make the map a little better, in both seasons.** Pooled 2023–2024, the morning-after map against the late edition:

| | Offense: morning after | Offense: late | Defense: morning after | Defense: late |
|---|---|---|---|---|
| Log loss, open spots | 0.4078 | 0.4065 (−0.34%) | 0.4688 | 0.4679 (−0.19%) |
| Open spots right, likeliest | 75.83% | 75.98% | 74.26% | 74.35% |
| Share of the 11 right, likeliest | 88.91% | 88.98% | 83.12% | 83.18% |
| Whole 11 right, likeliest | 23.72% | 24.01% | 10.35% | 10.44% |
| Open spots right, snap-matched | 71.82% | 72.01% | 70.27% | 70.32% |

By season: offense −0.38% (2023) and −0.30% (2024), defense −0.16% and −0.21%. The gain is a little smaller than the exploration's (0.41% / 0.26%) because the exploration's comparison was trained on FTN's seasons only, which costs the morning-after map a little (participation-late#F3). Confidence: strong (both seasons, both sides, same direction).

**R2. It moves the map, but not much.** A cell's chance moves 1.2 points on average; 12.6% of play-sides (12.0% in 2023, 13.2% in 2024) get a different likeliest lineup. The rest of the map stands as the morning after left it.

**R3. The weights read like football** (the 2024 fit, per position group, on the chance of being on before balancing to 11):
- **Backfield count:** backs +0.49 (the highest), quarterbacks +0.35, linemen +0.21, receivers +0.14, tight ends −0.06. Two in the backfield means another back, not another tight end.
- **Box count:** linemen +0.49, quarterbacks +0.46, tight ends +0.37, receivers +0.13 (the lowest on offense). On defense: linebackers +0.30, the defensive line +0.28, defensive backs +0.16. A loaded box means heavy personnel on both sides.
- **Pass rushers:** linebackers +0.19 and the defensive line +0.15, against defensive backs +0.07.
- **Screens:** backs +0.31, tight ends −0.13. **Motion:** receivers +0.13 and defensive backs +0.13, tight ends −0.01.
- **Play action** is negative for every group (−0.07 to −0.64). Because the chances are balanced to 11 a play, a shift shared by every group cancels; only the differences matter (tight ends −0.07 against receivers −0.37: play action leans to tight ends).

**R4. Calibration and certainty hold.** Calibration error is 1.06 points on offense (1.05 before) and 0.76 on defense (0.77), slopes 1.06 and 1.05. The certainty sorts offensive plays from 80.5% right (the least certain tenth) to 95.7% (the most), and the expected share matches the true share within 1.3 points in every tenth (within 1 point overall, a little under-confident).

**R5. Point in time is clean.** Four sample games of 2024 rebuilt from a view at each one's late `as_of` match the season run exactly (gap 0.0). A view at each game's morning after holds none of its FTN rows (0). Every saved row's `as_of` is 14 days or more after kickoff (median 15), and every `train_end` is before kickoff. The three last games of each season (the conference championships and the Super Bowl) wait for the next season's first run, about 7 months, because the weekly runs stop after the season (Pitfalls).

**R6. The gain is FTN's, not the extra inputs'.** With FTN's counts shuffled across plays within each season, the same model scores exactly like the morning-after map: offense 0.4112 and 0.4046 (2023, 2024) against 0.4111 and 0.4045 without FTN and 0.4096 and 0.4033 with the real counts; defense 0.4680 and 0.4695 against 0.4681 and 0.4696, and 0.4673 and 0.4685 with the real counts ([build/shuffled.txt](build/shuffled.txt)). Eight more inputs with no signal cost and gain nothing; the real counts gain in every season and side.

**R7. By position group, 7 of 8 get better log loss.**
- Gains: tight ends (0.4844 → 0.4821), backs (0.3557 → 0.3541), receivers (0.4491 → 0.4476), quarterbacks (0.1407 → 0.1392), defensive backs (0.3690 → 0.3669), linebackers and the defensive line by a hair.
- The offensive line is 0.1% worse (0.3332 → 0.3336), though its open spots right go up (82.5% → 82.6%). Linemen barely rotate, so there's little for FTN to tell.
- The likeliest lineup's open spots right go up in 6 of 8 groups; receivers (77.86% → 77.79%) and defensive backs (83.03% → 83.01%) dip by a hair while their log loss improves.

**Training on three seasons ties training on FTN's seasons only** (0.4065 against 0.4067 on offense, 0.4679 against 0.4678 on defense). The exploration's 0.15% cost of FTN's seasons alone is recovered by adding FTN. Decision 0031's call 4 (three seasons, FTN marked missing) stays: as FTN's history grows, the two converge anyway.

## The CEO's spot-check: the leakage check (2026-11-12)
The CEO picked the leakage check. Script: [build/spot_leakage.py](build/spot_leakage.py) → [spot_leakage.txt](build/spot_leakage.txt).

**The question.** Could the late edition, or anything built on it, use something it couldn't have known at its moment? A leak could come in through five doors:
1. FTN's charting reaching the backtest early.
2. The backtest computing a game from end-of-time data while dating it earlier.
3. A higher layer reading the late edition before it existed.
4. Training on the test season or on anything after it.
5. The answer key (the true participation) reaching the inputs.

**1. One game through time.** Dolphins at Rams, week 10 of 2024 (Monday night, kickoff 01:15 UTC on Tuesday, November 12). What a view holds at each moment:

| Moment | FTN plays visible | Morning-after rows a higher layer sees | Late rows a higher layer sees |
|---|---|---|---|
| Kickoff | 0 | 0 | 0 |
| The morning-after edition's `as_of` (Thursday, November 14) | 0 | 4,570 | 0 |
| Kickoff + 7 days | 0 | 4,570 | 0 |
| Kickoff + 14 days − 1 second | 0 | 4,570 | 0 |
| Kickoff + 14 days | 159 (all of them) | 4,570 | 0 |
| The late edition's `as_of` (Tuesday, November 26) | 159 | 4,570 | 4,570 |

FTN's rows appear at exactly 14 days, and the late edition only once it's made. A higher layer reading the game before November 26 sees the morning-after map and nothing else.

**2. The 14-day line, every game.** At 139 moments (every weekly run of 2023–2024, plus each game's late `as_of`), for all 570 games:
- **Early:** 0 times did a game's FTN rows show before kickoff + 14 days.
- **Complete:** 0 games were missing any FTN rows at their own late `as_of`. So the backtest, which reads FTN once at the end of time, used exactly what was known then.
- **The gap:** from FTN's known-at to the late `as_of` is 13 hours at least, 45 hours typically, and 205 days at most (the Super Bowl, which waits for next September's first run). It's never negative.
- Every game has FTN charting.

**3. Rebuilds, with a control.** 12 games (5 random games and the Super Bowl in each season) rebuilt from a view at their late `as_of`, then again from a view one second before FTN's known-at:
- **At the late `as_of`:** the largest gap to the season run's chances is 0.000000 in all 12, over 4,462–6,436 FTN-charted cells a game, with no cell unmatched.
- **One second early (the control):** no charted cells, and the chances differ from the season run's by 12–19 points at most (1–2 points on average across open cells). The check would catch FTN arriving early or missing.

**4. Training.** Each season's late model is fitted on the three seasons before it, never its own:
- **2023:** trained on 2020–2022 (FTN charts 0%, 0% and 99.7% of rows: marked missing before 2022). The last training game's FTN was known on 2023-02-26, before the first 2023 kickoff (2023-09-08).
- **2024:** trained on 2021–2023 (0%, 99.7%, 96.7% charted). The last training game's FTN was known on 2024-02-25, before the first 2024 kickoff (2024-09-06).

**5. The answer key.** The late edition's inputs view refuses `player_play` (the true participation): `UndeclaredInput`. The morning-after map's inputs don't declare FTN, so the first edition can't read it whatever the dates say.

**What would change the answer:**
- **FTN's real timing in history.** The 14 days is a rule, not a record: FTN's `date_pulled` shows later re-pulls, not first release (DATA_SOURCES.md). DATA_SOURCES.md puts FTN about 1–2 weeks behind the games, so 14 days sits at the cautious end. If FTN had been later than 14 days in some past week, the backtest would have used it a few days early. That's a timing optimism, not a leak of results. Live, the known-at is our own fetch time, so it can't be early.
- **A higher layer reading the files directly.** The gateway is what hides the late edition before its `as_of`. Code that opened `history.parquet` itself would skip that. Rule c already forbids it; every model reads through the gateway.
- **The rebuild covers 12 games of 570.** Door 2 for FTN is checked on all 570 (part 2). The other inputs are participation-live's, already checked (participation-live#R8).

**Verdict: no leak found.** Each door is closed, and the control shows the checks can fail.

## The ladder
| Rung | Method | Result vs the rung below | Takeaway carried forward |
|---|---|---|---|
| 0 | the morning-after map (participation-live's sequence rung, refitted on the same seasons) | — (participation-live#R1: beats its shuffled self by 5.1–5.5%) | everything: grid, history, chain, balancing, lineups, certainty |
| 1 | + the next game's snap counts (H39, exploration) | +0.00% / +0.01%: no gain | dropped (F1) |
| 2 | + FTN's counts per play | −0.34% / −0.19% log loss | the champion |

The ladder stops at rung 2: the next step (a tree rung, or FTN inside the position mix) is in Could be improved.

## Where it misses
The same lenses as participation-live's (its RESULTS "Where it misses"): the late edition shifts them by tenths of a point and changes none of them. The biggest misses are still backs, tight ends and the defensive line (log loss 0.35, 0.48, 0.55), where rotation is heaviest and FTN's counts only lean.

## The case against (2026-11-12, written before asking to merge)
1. **The gain is small.** A third of a percent of log loss and 0.15 points of open spots. A higher layer will barely notice. If a second output and a second run each week aren't worth that, the morning-after map alone would do.
2. **Two test seasons only.** FTN starts in 2022, so only 2023 and 2024 can be tested, and 2023's FTN weights come from one season. Both seasons agree in direction and size, but two is thin.
3. **The offensive line is a hair worse** (0.1% log loss). It's small and the open spots go the other way, but "doesn't add noise" holds for 7 of 8 groups, not 8.
4. **FTN's charting is unchecked.** Its counts are a charter's judgement (who is "in the box"); any systematic charting error enters the map. About 3% of plays aren't charted and get the morning-after treatment.
5. **Live timing is our own fetch, not history's 14 days.** In history FTN's known-at is 14 days after kickoff. Live, a game waits until our weekly fetch has its rows; if FTN's free release is late or stops, the late edition simply doesn't appear (the morning-after map stays).
6. **The late edition is only for uses that can wait.** A model that runs before next week's game can't use it for last week's game until 14 days have passed; using it earlier is a leak (rule c). The `as_of` column enforces that only if downstream code reads it.
7. **Versions tried, on the test seasons:** the exploration's three variants and the build's three. FTN's column set wasn't tuned (it's every count FTN has), so selection on test seasons is light.

## Pitfalls
- **FTN's fill must touch only the feature columns.** Filling nulls across the whole frame turned `play_id` into a float and broke the join (fixed in `ftn.features`).
- **The weekly runs stop after the season.** The last three games' late edition waits for the next season's first run (R5). Harmless for in-season use; a retrospective model that wants them sooner should read FTN's charting in the retrospective view instead.
- **A shift shared by every group means nothing** (R3, play action). Read the FTN weights as differences between groups.

## Not looked at
- **The 2025 vault.** It opens once, at the final check.
- **2022** (no earlier FTN season to learn from).
- **FTN's other columns** (formation details, the QB's drop, pass-rusher alignment): the counts were enough for a small first gain.
- **A third edition** (later still, e.g. from the season's final participation data): that is participation's retrospective answer key, not an in-season edition.

## Could be improved
1. **FTN inside the position mix.** Today FTN's counts move each player's chance; the position mix (how many backs and tight ends) is still the summed chances. A backfield count of two could shape the mix directly, with its uncertainty.
2. **A live fetch of FTN's charting** each week, logging when each game's rows first appear, so the live known-at is measured rather than assumed.
3. **Per-group interactions** (box count by down and distance): a tree rung.
4. **FTN's other columns** (Not looked at).

## Don't redo
- **The next game's snap counts as an input** (F1, H39): nothing, in both seasons.
- **Folding FTN into the morning-after map** (decision 0031, alternatives): a backtest would see FTN two weeks early.
- **Fixing each play's personnel from FTN's counts:** two in the backfield means two backs on only 35% of plays (BRIEF, first look).

## Interface card
Also in this project's `interface` block in `registry.yaml`.

| | |
|---|---|
| **Inputs** | everything participation-live reads (`play.pbp`, `player_game`, `team_game.pregame`, earlier seasons' `player_play.on_field` as the answer key), plus `play.ftn` (FTN's charting: backfield, box, pass rushers, blitzers, motion, play action, screens) |
| **Outputs** | `outputs/participation-late/<run_id>/history.parquet`: participation-live's schema, `model` = `participation-late`, `model_version` = `late`: one row per candidate and scrimmage snap, `quantity` `on_field_chance`, `mean` = the chance (q10–q90 equal it), `best` (snap-matched), `likeliest`, `certainty`, `side`, `team`, `n`, `as_of`, `train_end` |
| **Level of detail** | player-play, both sides |
| **Interval** | every completed game, 2023–2024 walk-forward (2022 train only) |
| **Cadence** | in_season |
| **Known at** | the first weekly run at least 14 days after kickoff (FTN's known-at); live, the first run after our fetch has the game's FTN rows |
| **How to use it** | **A later edition of the same map.** For a game, read the newest edition whose `as_of` is before your own moment: the late edition once it exists, the morning-after map before that. Never mix in the late edition earlier (rule c). Everything in participation-live's card applies: the lineup to use is `likeliest`, use `mean` where a measure can take weights, `best` only when lineups must keep the snap counts. In training, read only the walk-forward history (rule e) |
| **Feeds** | the same as participation-live, for uses that can wait two weeks: season plus-minus and value, the retrospective models, fantasy usage trends |

## Open questions for the CEO
1. **The spot-check:** the CEO picked "The leakage check" (2026-11-12): done above, no leak found.
2. **Vetoes on the technical calls?** Decision 0031, calls 1–6.
3. **Merge?**
