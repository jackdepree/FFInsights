# Old inventory: the salvage map

> What PCF takes from `old/`, where it goes, and what we learned. A first pass, kept light on purpose. When a project starts, its exploration reads the relevant old notebooks closely and records what it took in the "Where it went" log below.
> Surveyed **2026-10-30**: 22 Python notebooks, 17 R projects, about 500 data files, 38 saved models.

**`old/` stays read-only (rule a).** We take ideas and functions by rewriting them in `pcf/`. We never edit, move or delete anything there.

**What we take, in one line:** the **goals** of the four core models, the **cleaning functions**, and the **lessons**. Everything else is logged as an idea.

## The four core models: same goals, new approach

The goals stay. The approach gets retried under PCF's rules: walk-forward splits, the cadence split, and the ladder from simple to complex.

| Old work | The goal we keep | Ideas worth keeping | Goes to |
|---|---|---|---|
| **VOE** (`VOE_Model_Training`, `VOE_Model_Prod`) | Each player's value over what the situation expected | Player slots per play built from depth charts (QB1, WR2, …). A "blank out a position" test of what each slot adds. A forecaster of each player's EPA. **The notebook's own note already proposes two VOEs:** a prospective one built on tendencies, and a retrospective one that splits each play's unexplained EPA using players' stats. That's the `voe-live` / `voe-retro` split. | `voe-live`, `voe-retro` |
| **Context** (`Context_Model_Training`, `Context_Model_Prod`) | How hard each play's situation was | Sub-models per play (pressure, time to throw, rush yards, yards after catch, completion, pass breakup) feeding an expected-EPA model. Personnel and box features: counts, ratios, box advantage, rushers vs blockers. A "co-evolutionary" ensemble of ridge, MLP and XGBoost. | `context-live`, `context-retro` |
| **Fatigue** (`Fatigue_Model_Training`, `Fatigue_Model_Prod`) | How workload and contact wear players down | A strong list of workload and contact features (cumulative snaps, short weeks, hits taken, tackles in the middle of the field, yards after contact). Targets: future snaps, EPA change, injury length, recovery. | `injury-fatigue` |
| **Schemes** (`Schemes_Model`) | Team schemes as structure | Over-expectation features (shotgun, no-huddle, coverage, routes, …) → PCA → clustering. Little signal (see the roadmap's dead ends). | `schemes-v2`, via `roles-archetypes` |

## Functions to port

**Start by copying, then test, then improve:**
1. **Copy** each function into `pcf/src/pcf/data/clean/` almost as-is. Change only what must change: hardcoded paths go, and `nfl_data_py` (archived) becomes `nflreadpy`, converted to pandas where the old code expects it.
2. **Test** that the copy matches the old function's output on a sample season ("golden" tests), and add tests of what we expect (e.g. 11 players per side, no duplicate player on a play, only known position labels).
3. **Improve**, one change at a time, each with its own test: fix the known issues below, make cumulative stats time-ordered, move to Polars, and handle the newer depth-chart format.

| Function | Found in | What it does | Known issues to fix in step 3 |
|---|---|---|---|
| `pivot_wide_both_sides` | VOE, Fatigue | Splits each play's offense and defense player lists into 11 slots per side | Uses participation fields, which are post-season only (rule m). Fine for retrospective use. |
| `pivot_long_both_sides` | VOE, Fatigue | One row per player per play, joined to depth charts | Same as above |
| `clean_depth_charts` | VOE, Fatigue | Normalizes positions (LOT → LT, LDE → DE, …) and ranks players into depth slots | A mislabeled comment ("DB → CB" on the LB → MLB line). Seniority and average depth are computed in file order, not time order, across seasons. Needs the daily snapshot format (2025→). |
| `get_position_groups` | VOE, Fatigue | Position groups (offense, defense, QBs, OL, …) from slot labels | The label list is hardcoded |
| `position_folds_from_counts` | VOE | Groups positions into folds for the "blank out a position" test | — |
| `data_preparation` | Fatigue prod | Ball carriers, tacklers and tackle indicators, joined to injuries, rosters and snaps | Check join keys and timing against DATA_SOURCES.md |
| `feature_engineering` | Context | Personnel counts and ratios, box and pressure features per play | Fills missing values with assumptions (e.g. 4 pass rushers). Keep, but test. |
| `career_averaging`, `team_relative` | 2024 gross projections | Career-to-date averages, stats relative to team | Career averages must be strictly to date (rule c) |
| `moneyline_to_probability` | `touchdown_odds` | American odds → implied probability | Trivial. It joins the odds utilities. |

## Other ideas, logged

Not urgent. These are mostly ideas we'd have anyway. They're recorded so nobody wonders whether they were tried.

| Old work | What it was | Use |
|---|---|---|
| 2024 gross projections | Season-long projections from PFR stats (scraped with Selenium), the combine and salary. XGBoost and MLP. | Feature ideas for `fantasy-projections` and `prospects`. The scraping is not reused (DATA_SOURCES.md). |
| Best Ball Mania | Round-by-round value curves and a bootstrap, on Underdog tournament data | Ideas for the best-ball product. `best_ball_mania_models.ipynb` is corrupted and won't open. |
| ECR and position-rank analysis | How accurate ECR is, position rank vs fantasy points, a draft simulation | Ideas for the crowd expert and the ECR benchmark |
| `touchdown_odds` | One week (2024 week 7): pasted anytime-TD odds turned into probabilities, ranked against PFF's projected TDs to find disagreements | An early version of the TD-props idea. PCF does it with The Odds API and its own TD expert. |
| `trying_out_nflstats` | A recency analysis: how much recent weeks predict the next one | Ideas for `stabilization` |
| PFR passing clean and model | PFR passing tables and a random forest | Skip. nflverse covers the data. |
| R projects (QB and RB discovery, in-season QB and TE projections, passing summaries) | Stepwise linear models on combine and stats data, weekly projections | The in-season TE projection is a baseline idea. Code stays R, as reference (decision 0001). |

## Old data: research and benchmarking only

Nothing in `old/data` feeds the pipeline or becomes a feature.

| Files | Use |
|---|---|
| FantasyPros ADP 2012–2023 and ECR exports | **Research and benchmarking** (the one-time-download exception, rule b). They give ADP history from before nflverse's ECR archive (Dec 2019). |
| `voe_weekly_data.xlsx` (the old VOE outputs) | **A benchmark** for the new VOE: where do they agree, and where do they differ? |
| PFR scrapes, combine CSVs, weekly QB stats | Not used. nflverse has all of it. |
| PFF summaries, DVOA | Never used (paid; DATA_SOURCES.md "Deliberately not used") |

## Old saved models: never loaded

The 38 pickle and joblib files are never loaded. Pickles break between library versions, loading one runs code, and every one was trained with random splits, so its predictions leak (the vintage rule). The new experts retrain from scratch. We don't need the files. Deleting them would be the CEO's call, since `old/` is read-only.

## Lessons learned

Every one of these would now fail a PCF check.

| Pattern in `old/` | Why it's a problem | Now caught by |
|---|---|---|
| Random shuffled cross-validation on plays (`KFold(shuffle=True)`, `train_test_split`) in VOE, Context and Fatigue | Plays from the same game, and from future seasons, land in training. Scores look better than they are. | Random splitters are banned (VALIDATION.md section 2), plus walk-forward splits |
| The Context "variance encoder": EPA variance by personnel and coverage, computed on all the data | Outcome information leaks into a feature | Test-label perturbation (ARCHITECTURE.md check 8) |
| Cumulative depth-chart stats in file order, across seasons | Results depend on row order and may include future weeks | Future perturbation and deletion (checks 3–4) |
| Stepwise feature selection on the full data (R) | Selection happens outside the folds | Nested tuning (VALIDATION.md section 2) |
| Participation fields in "prod" notebooks | Those fields aren't available live | The cadence check (check 5, rule m) |
| Hardcoded paths, pickled models, overwritten outputs | Can't reproduce last month's result | Rule f, MLflow, versioned outputs |
| A complex stacked ensemble with no simple comparison | We don't know whether the complexity helped | The ladder (rule k) |
| Scraping (Selenium on PFR), pasted sportsbook text | Breaks, and can't be automated | Rule b, DATA_SOURCES.md |

## Where it went

One line each time something from `old/` lands in `pcf/`.

| Date | From `old/` | To `pcf/` | Notes |
|---|---|---|---|
| 2026-10-31 | `pivot_wide_both_sides`, `clean_depth_charts`, `pivot_long_both_sides`, `get_position_groups` (`Fatigue_Model_Prod.ipynb`, cells 1–4) | `pcf.data.clean.legacy` | Faithful copy, golden-tested against the notebook on 2016–2024. For comparison only. |
| 2026-10-31 | `pivot_wide_both_sides`, `pivot_long_both_sides` | `pcf.data.clean.players` (`plays_with_players`, `players_on_play`) | Keeps every listed player (the old code cut at 11) and joins participation itself. |
| 2026-10-31 | `clean_depth_charts` | `pcf.data.clean.depth_charts` | Season-to-date depth in time order; 2025+ daily snapshots; the mislabeled comment fixed. |
| 2026-10-31 | `pivot_long_both_sides` (the label join), `get_position_groups` | `pcf.data.clean.slots` (`slot_labels`, `position_groups`) | Players missing from a chart get a real slot (CEO 2A); groups read from the labels present. |
| 2026-10-31 | — (new) | `pcf.data.clean.standard` | Per-source ids, team codes, spread sign, `roof` rule, duplicates (CEO 1B). |
