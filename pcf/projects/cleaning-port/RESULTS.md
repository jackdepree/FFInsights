# Results: Port the cleaning functions (`cleaning-port`)

> An infrastructure project: no model, so no MLflow experiment, ladder or vault.

**Date:** 2026-10-31 · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** none

## In short
PCF now knows who was on the field for every run and pass play from 2016 to 2025, in which slot (QB1, WR2, CB1, …), and can build depth-chart slots for 2026 up to each team's next game. The old functions are copied unchanged into `pcf.data.clean.legacy` and match the old notebook exactly on every season 2016–2024. The improved version takes each week's labels from that week and earlier only, reads the 2025+ daily depth charts, and gives players missing from a chart a real slot (CEO decision 2A). `special` drops from 3.6–7.6% of player-plays to under 0.03%, and no two players on one side of a play share a label. Each nflverse source also has its standardizing function (decision 1B): ids, team codes, the spread sign, the `roof` rule and known duplicates.

| Test from the brief | Result |
|---|---|
| The copy matches the reference exactly, on the fixture and on 2016–2024 | **Pass.** Equal frame for frame on the two-game fixture (offline) and on all nine seasons (`local_data`). |
| `special` only for K/P/LS, under 0.5% of player-plays | **Pass, 0.004–0.025%** in every season 2016–2025 (the old code: 3.6–7.6%). |
| 2025 and 2026 get labels | **Pass.** 2025: 98.8% of player-plays labelled from that week's chart. 2026: depth labels for weeks 1–9 (248 team-weeks). No 2026 participation is published yet, so no 2026 player-plays (rule m). |
| One QB1 per offense on at least 99% of plays | **Changed: at least one QB on the field on ≥99% of plays, every season** (99.8%+ in 2020 and 2024). Exactly one QB1 is 80–88%, and that's football, not a bug (F14). The test now checks the QB position, not the QB1 label. |
| Deleting later weeks leaves earlier labels unchanged | **Pass** (offline test). The old code changes 19–22% of weeks 1–5 labels when weeks 6+ are removed (F12). |
| 22 players per play, no player twice, only known labels | **Pass**, with 2016's 87% full lists allowed (exploration F5). Repeat listings are dropped and logged (F16). |
| The Polars version equals the improved pandas version | **Not run, by design.** The improvements were written straight in Polars (see Deviations). The guard is the comparison with the legacy copy below. |
| A season takes under 10 seconds | **Pass, about 0.5 seconds.** Depth labels for all of 2001–2026 take 5 seconds. |

**Tests:** 110 offline and 28 `local_data` (the full seasons from our raw copy), all passing.

### How far the improved labels move from the old ones
Measured by `explore/measure_slots.py`. "Same position" and "same label" compare rows the improved version labels from that week's chart.

| Season | From that week's chart | Earlier chart | Roster | None | `special` (old) | Same position | Same label |
|---|---|---|---|---|---|---|---|
| 2016 | 98.5% | 0.8% | 0.7% | 0 | 0.010% (3.7%) | 97.5% | 80.5% |
| 2017 | 98.5% | 0.7% | 0.8% | 0 | 0.025% (4.6%) | 96.4% | 76.1% |
| 2018 | 98.2% | 0.6% | 1.1% | 0.08% | 0.013% (4.7%) | 96.5% | 75.6% |
| 2019 | 98.1% | 0.6% | 1.3% | 0.11% | 0.022% (3.6%) | 98.2% | 78.2% |
| 2020 | 96.0% | 2.5% | 1.5% | 0 | 0.016% (5.9%) | 97.5% | 77.6% |
| 2021 | 94.4% | 3.8% | 1.8% | 0 | 0.008% (7.6%) | 97.5% | 78.6% |
| 2022 | 96.2% | 1.7% | 2.1% | 0 | 0.009% (5.3%) | 98.2% | 74.8% |
| 2023 | 96.2% | 1.6% | 2.2% | 0 | 0.008% (5.0%) | 98.5% | 76.5% |
| 2024 | 95.6% | 2.1% | 2.3% | 0 | 0.007% (5.6%) | 98.5% | 74.7% |
| 2025 | 98.8% | 0.1% | 1.1% | 0.04% | 0.004% (—) | — | — |

Positions agree on 96–98.5% of rows. Labels agree on only 75–81% because the old depth order leaked later weeks (F12): the improved version is the one that's right at the time.

## Deviations from the brief
- **Straight to Polars.** The brief planned improvements in pandas first, then a Polars port checked against them (goal 4d). Writing them twice would have doubled the work for a check the legacy comparison already gives. The faithful copy stays in pandas, as the brief's golden tests require.
- **Season-to-date, not career-to-date.** The old code averaged depth over everything loaded (F7). Career-to-date (in time order) lets a long-time starter outrank this season's starter for weeks, so the average now restarts each season.
- **The fallback never repeats a label held that week.** The brief's step 2 reused a player's earlier label as is. In 10–19% of plays that clashed with someone listed that week, so a held label falls to the next free number at that position (F13).
- **The cutoff is the start of game day (New York time), not kickoff.** Kickoff comes from `timeline`, which doesn't exist yet. Snapshots are about daily, so this loses at most the morning-of snapshot and never looks past kickoff.
- **Games after the newest snapshot: only each team's next game is labelled** (F15). Later games' charts will still change.
- **The QB test** checks for a QB on the field, not exactly one QB1 (F14).

## Terms
As in the brief, plus three. All are in `docs/GLOSSARY.md`.
- **Slot label:** a player's position and depth on a play (`WR2`, `CB1`). Depth is the rank within that team's position that week, by average depth over the season so far. `unknown` when no chart or roster row exists.
- **Label source** (`label_source`): where a slot label came from: `week` (that week's chart), `earlier_week` (that team's most recent earlier chart that season), `roster` (roster position, ranked past the deepest in use) or `none`.
- **Depth chart for a game:** as in the brief, with the start of game day as the cutoff until `timeline` supplies kickoff.
- **PCF team codes:** the 32 codes play-by-play uses, current franchise code for every season (the 2017 Raiders are `LV`, the 2016 Chargers `LAC`, the Rams `LA`). Every other code (OAK, SD, STL, ARZ, BLT, CLV, HST, JAC, LAR, LVR, …) is recoded at ingest.
- **Reference version:** as in the brief. The faithful copy is `pcf.data.clean.legacy`.

## Findings
F1–F9 came from the light exploration ([EXPLORATION.md](EXPLORATION.md)). F10–F18 came from the build.

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| F1 | Two versions of `pivot_long_both_sides`; the later one (labels unmatched players `special`) is the reference. | [EXPLORATION.md](EXPLORATION.md) | strong | the old code |
| F2 | The old functions run unchanged on our raw copy for 2016–2024 once participation is joined to play-by-play and `play_id` has one type. | [EXPLORATION.md](EXPLORATION.md), golden tests | strong | play-by-play, participation |
| F3 | They fail on 2025+: depth charts become daily snapshots with no season or week. | [EXPLORATION.md](EXPLORATION.md) | strong | depth charts 2025→ |
| F4 | 4–6% of on-field players aren't on that week's depth chart; the old code calls them `special`. | [EXPLORATION.md](EXPLORATION.md), the table above | strong | slot labels |
| F5 | In 2016 only 87% of run and pass plays list 11 players a side (99.9% in 2020 and 2024). | [EXPLORATION.md](EXPLORATION.md) | strong | participation 2016 |
| F6 | Depth charts and play-by-play number playoff weeks the same way; the Super Bowl bye week has no number (the old code uses 23). | [EXPLORATION.md](EXPLORATION.md) | strong | depth charts |
| F7 | The old depth order depends on which rows are loaded, and averages them in file order. | [EXPLORATION.md](EXPLORATION.md), F12 | strong | the old code |
| F8 | The Context and Fatigue data prep is expert features (with a leak), not cleaning. | [EXPLORATION.md](EXPLORATION.md) | strong | `context-*`, `injury-fatigue` |
| F9 | pandas, NumPy and pyarrow are needed for the legacy copy (now dependencies). | [EXPLORATION.md](EXPLORATION.md) | strong | the package |
| F10 | **The old code cuts player lists at 11 a side, and padding slots become a player called `'None'`.** The improved `players_on_play` keeps every listed player and makes no row for an empty slot. | `legacy.py`, golden tests | strong | participation |
| F11 | **nflverse sources disagree on team codes.** Play-by-play gives each franchise its current code for every season; depth charts, rosters, injuries and others use the code of the time (OAK, SD, STL) or their own (ARZ, BLT, CLV, HST, LAR, LVR, JAC). Unrecoded, 3–6% of 2016–2019 player-plays found no chart row. | `standard.TEAM_CODES`, `local_data` tests | strong | every join on `team` |
| F12 | **The old depth order leaks later weeks.** Removing weeks 6+ changes 19–22% of its weeks 1–5 labels, and the same file sorted by week gives only 78–84% the same labels. This is why old and new labels agree on only 75–81% while positions agree on 96–98.5%. | `measure_slots.py`, offline test | strong | anything trained on old slot labels |
| F13 | **The step-by-step fallback labels nearly everyone without clashes.** 94–99% of player-plays come from that week's chart, 0.1–3.8% from an earlier chart, 0.7–2.3% from the roster, and at most 0.11% get `unknown` (2018–2019 roster gaps). Reusing earlier labels as is would clash on 10–19% of plays; checking free labels per team-week brings that to 0. | the table above | strong | slot labels |
| F14 | **QB1 means the season's established starter, so about 17% of offense plays have no QB1.** The QB on the field is a QB2–QB4 (a backup in, or a new starter whose season average hasn't caught up: 14–32% of those are depth 1 on that week's chart). At least one QB is on the field on 99.8%+ of plays in both seasons; two QBs on 0.6% (2020) and 0.01% (2024). | a check on 2020 and 2024 | strong | QB features, VOE |
| F15 | **2025+ daily snapshots:** 27,764 rows have no `gsis_id` (2025–2026, dropped and logged). A game after the newest snapshot only gets today's chart if it's the team's next game; otherwise later weeks would be labelled from a chart that will still change. | `daily_depth_rows`, offline test | strong | depth charts 2025→, live use |
| F16 | **Participation sometimes lists one player twice on one side** (373 listings in 2019, 1 in 2024). The first listing is kept, and the count is logged. | the build log | strong | participation |
| F17 | **Snap counts carry only PFR's id.** nflverse's `players` file maps 99.93% of rows to `gsis_id`; dynastyprocess's id map only 82%, since it covers fantasy players. | `local_data` test | strong | snap counts, `participation-snaps` |
| F18 | **Smaller duplicates:** `player_stats` has one empty row per season-week (id `"0"` in 1999–2000, null after). `ff_opportunity` has one player with two rows for one game (2013). Weekly rosters list some players twice in a week (kept: the best status, active first). Injuries have repeat reports (kept: the latest `date_modified`). | `local_data` tests | strong | those sources |

## Pitfalls
- **Joins on `team` silently drop rows** when sources use different codes (F11). It looked like a 3–6% data gap until the codes were compared. Recode every team column at ingest; `standard_teams` raises on any code it doesn't know.
- **A golden test needs identical input on both sides** (F7). The old code's output depends on which seasons are loaded.
- **Windows writes files in cp1252 by default.** A `write_text` without `encoding="utf-8"` truncated a source file to 0 bytes. Pass the encoding every time; print scripts with `PYTHONIOENCODING=utf-8`.
- **"One QB1 per play" sounded like an invariant and isn't** (F14). Check an expectation against football before treating a miss as a bug.

## Not looked at
- **Kickoff times.** The cutoff is the start of game day until `timeline` exists.
- **2026 player-plays.** Participation is published after the season.
- Seasons before 2016 (no participation), and special-teams plays (the old code skipped them too).
- Whether a better depth order exists (e.g. weighting recent weeks). Season-to-date was chosen against career-to-date and the old order only.

## Could be improved
1. **Use kickoff as the cutoff** once `timeline` provides it.
2. **Weight recent weeks** in the depth order, so a new starter becomes QB1 sooner (F14). Measure it against the season-to-date order on next week's chart.
3. Map the 0.07% of snap-count rows without a `gsis_id` (F17) by name and team.

## Don't redo
- Don't train on the old slot labels: they leak later weeks (F12).
- Don't map PFR ids through dynastyprocess's id map (F17).
- Don't treat `special` as "kicker" in old outputs: 3.6–7.6% of it is real players missing from the chart (F4).

## Interface card
Also in `registry.yaml` under `interface`.

| | |
|---|---|
| **Inputs** | Raw nflverse play-by-play, participation, depth charts (weekly and daily), weekly rosters, schedules, and the other sources `standard` covers (player stats, expected fantasy points, snap counts, players, injuries) |
| **Outputs** | Pure functions in `pcf.data.clean`. `players`: `plays_with_players`, `players_on_play`. `depth_charts`: `weekly_depth_rows`, `daily_depth_rows` (takes `timeline.team_kickoffs` since `timeline`; `game_day_cutoffs` was removed), `depth_labels`. `slots`: `slot_labels` (adds `position`, `position_label`, `label_source`), `position_groups`, `position_of`. `standard`: one function per source plus `team`/`standard_teams`. `legacy`: the faithful copy, for comparison only. |
| **Level of detail** | Slot labels: player-play. Depth labels: player-team-week. Standard functions: as published. |
| **Interval** | Depth labels: weekly, from week 1 (2001→). Slot labels: 2016→ (participation). |
| **Cadence** | Slot labels from participation: retrospective only (rule m). Depth labels: in-season use is fine, as each week uses only that week's chart and earlier. |
| **Known at** | No `known_at` yet (`timeline`). Depth labels for a week are known at that week's chart (weekly) or snapshot (`dt`, daily). |
| **How to use it** | Call through `grain-tables`, never from an expert. Standardize every source first (`standard`), then build depth labels for all seasons at once, then `slot_labels` a season at a time. Filter on `label_source` if a use needs chart-listed players only. |
| **Feeds** | `grain-tables` (and through it VOE, Context, fatigue, roles, participation) |

## Open questions for the CEO
- **Approve the merge?** It adds pandas, NumPy and pyarrow as dependencies, and the `local_data` test marker (`uv run pytest -m local_data`, skipped by default).
- No football calls are needed. One for later, if you have a view: should a new starter become QB1 faster than a season-to-date average allows (Could be improved, 2)?
