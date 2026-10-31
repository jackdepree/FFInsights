# Exploration: Port the cleaning functions (`cleaning-port`)

> A light exploration (infrastructure project). It asks three things: which old functions are really cleaning, what they need as input, and whether they run on our own raw copy (`data-layer`).
> Run on 2026-10-31 with [`explore/profile_inputs.py`](explore/profile_inputs.py). The script reads the old functions straight out of `old/code/Fatigue_Model_Prod.ipynb` (read only) and runs them on `raw/nflverse/`.

**Verdict: GO.** The three functions that build each play's player slots run unchanged on our data for 2016–2024, in under a second per season. Three things need work: 2025 onward (new depth-chart format), the 4–6% of on-field players who aren't on that week's depth chart, and depth order that depends on which rows you happen to load.

## What the old code holds

| Function | Copies in `old/code/` | What it really is |
|---|---|---|
| `pivot_wide_both_sides` | 4, identical | Cleaning: each play's offense and defense player lists split into 11 slots per side (run and pass plays only) |
| `clean_depth_charts` | 4, identical | Cleaning: position names normalized (T/G → LT/LG/…, LDE → DE, LB → MLB, DB → CB, K/P/LS → special), then a depth label per player-week (`WR1`, `CB2`, …) |
| `pivot_long_both_sides` | 4, **two versions** (F1) | Cleaning: one row per player per play, labelled from that week's depth chart |
| `get_position_groups` | 3, identical | A hardcoded label list grouped into offense, defense, QBs, OL, … |
| `position_folds_from_counts` | 2, identical | Groups labels into folds for VOE's "blank out a position" test. A modelling helper, not cleaning |
| `feature_engineering` (Context) | 2, identical | **Expert features**, not cleaning (F8) |
| `data_preparation` (Fatigue prod) | 1 | **Expert features**: ball carrier and tacklers, injury joins, rolling workload (F8) |
| `moneyline_to_probability` | 1 | Odds utility, two lines |

There are no standalone injury or snap-count cleaning functions in `old/`. Injuries are handled inside `data_preparation`, and snap counts are only loaded.

## Findings

| # | Finding | Confidence |
|---|---|---|
| F1 | **Two versions of `pivot_long_both_sides`.** The copy in `VOE_Model_Training` drops players with no depth-chart row. The later copies (Fatigue training and prod, VOE prod) strip whitespace from ids and label those players `special` instead. The later version is the reference for the port. | strong |
| F2 | **The old functions run unchanged on our raw copy for 2016–2024**, under 1 second per season. Two input steps are needed first. Participation has to be joined to play-by-play (`nfl_data_py` used to do that join itself). `play_id` has to be cast to one type: it's a float in older play-by-play files and an integer in participation. 2016 and 2020 failed on that until it was cast. | strong |
| F3 | **They fail on 2025 and 2026.** Depth charts are daily snapshots from 2025 (221 snapshots in 2025, 267 so far in 2026). Each snapshot has a timestamp `dt`, a team and a `pos_rank`, with no `season`, `week` or `club_code`. That matters for this season. It confirms `package-scaffold#F3`. | strong |
| F4 | **4–6% of on-field players aren't on that week's depth chart.** The old code labels them `special`, which makes `special` the most common label of all in 2020 (5.9% of rows) and 2024 (5.6%). In 2024 they're mostly WRs, CBs, DEs, DTs and ILBs, not kickers. 479 of the 637 such players appear on a depth chart in some other week, so most are real players missing from one week's chart (call-ups, injuries, late moves). | strong |
| F5 | **Participation quality.** In the seasons checked (2016, 2020, 2024), every run or pass play has a player list. But in 2016 only 87% of run and pass plays list 11 players a side, against 99.9% in 2020 and 2024. From 2023 the files add names, positions and jersey numbers (26 columns, up from 20). | strong |
| F6 | **Playoff weeks line up.** Depth charts and play-by-play number playoff weeks the same way: 18–21 through 2020, 19–22 from 2021. The old code puts the Super Bowl bye week, which has no week number, at week 23. | strong |
| F7 | **Depth labels depend on what you load.** `clean_depth_charts` ranks players by career-average depth, but it counts the average over whatever rows it's given, in file order. Load one season and you get one set of labels for a week; load nine and you get another. Golden tests must feed both versions identical input. The improvement makes the average time-ordered and to-date. | strong (from the code) |
| F8 | **The Context feature builder and the Fatigue data prep are expert features, not cleaning.** They hold rolling team tendencies, fills (4 rushers and a 40-second play clock when missing), and injury joins. `rolling_pass_over_expected` averages over a window that includes the current play, so the play's own outcome leaks in. They belong to `context-live`/`context-retro` and `injury-fatigue`, under the gateway's leakage checks. | strong |
| F9 | **pandas isn't a PCF dependency yet.** The old functions need pandas and NumPy, and converting from Polars needs pyarrow. The exploration ran with them added temporarily. | strong |

## What it means for the brief
- Port the three slot functions plus `get_position_groups`, golden-test them against the old code, then improve them one tested change at a time. The fixes are: input types (F2), the 2025+ format (F3), unmatched players (F4), and time-ordered depth (F7).
- Leave the Context and Fatigue feature code to their experts (F8). Note the leak there, so it isn't copied.
- Decide how to label players missing from a week's depth chart. That's a football call (F4).

## Next step
The [brief](BRIEF.md).
