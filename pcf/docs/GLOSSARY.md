# Glossary

> One line per term, so a definition never drifts between documents, projects or subagents.
> **Standard terms** (football analytics, fantasy, betting) are the common definitions used across the analytics community, with how PCF uses each one. **PCF's own terms** are defined in the brief of the project that introduces them, and copied here when that project is done (CONVENTIONS.md, "Writing docs and notes").
> The **nflverse column** is the exact column name to use (checked 2026-10-30). "pbp" = play-by-play, "stats" = `load_player_stats`, "part." = participation (post-season only).

## Football analytics

| Term | Meaning | nflverse column | PCF notes |
|---|---|---|---|
| **EPA** (expected points added) | How much a play changed the offense's expected points, given down, distance, field position and time | `epa` (pbp), `passing_epa` / `rushing_epa` / `receiving_epa` (stats) | The base unit of most experts |
| **Expected points** | The average points the next score is worth for the offense, from this situation | `ep` (pbp) | |
| **Success rate** | The share of plays with positive EPA | `success` (pbp, 0/1) | |
| **Win probability (WP)**, **WPA** | The chance the offense wins, and how much a play changed it | `wp`, `vegas_wp` (uses the spread), `wpa` | |
| **CPOE** | Completion percentage over expected, given throw depth, location and situation | `cpoe` (pbp, **0–100 scale**), `passing_cpoe` (stats) | Converted to 0–1 in derived columns |
| **xpass**, **PROE** | The chance a play is a dropback given the situation; pass rate over expected | `xpass` (0–1), `pass_oe` (**0–100 scale**) | Pace & play-calling expert |
| **Neutral situation** | Game states where play-calling isn't forced by the score or clock | — | No single standard. Defined in the `pace` brief. |
| **Dropback** | A play where the QB drops back to pass (passes, sacks, scrambles) | `qb_dropback` | |
| **Air yards** | How far the ball travels past the line of scrimmage | `air_yards` (pbp), `receiving_air_yards` (stats) | |
| **aDOT** | Average depth of target: air yards per target | — (air yards ÷ targets) | |
| **YAC**, **xYAC** | Yards after the catch, and its expected value | `yards_after_catch`, `xyac_mean_yardage` | |
| **Target share**, **air yards share** | A player's share of the team's targets, or air yards | `target_share`, `air_yards_share` (stats) | |
| **WOPR** | Weighted opportunity rating: 1.5 × target share + 0.7 × air yards share | `wopr` (stats) | |
| **RACR**, **PACR** | Yards gained per air yard, for receivers and passers | `racr`, `pacr` (stats) | |
| **Snap share** | The share of the team's snaps a player was on the field for | `offense_pct`, `defense_pct` (snap counts, 0–1) | Snap counts key on `pfr_player_id` |
| **Route participation** | The share of team dropbacks on which a player ran a route | — | **Not public.** Estimated from who was on the field on dropbacks (part., post-season only) |
| **YPRR**, **TPRR** | Receiving yards and targets per route run | — | Uses estimated routes, so it's retrospective only |
| **Personnel** | Who's on the field, e.g. "11" = 1 RB, 1 TE, 3 WR | `offense_personnel`, `defense_personnel` (part.) | |
| **Box count** | Defenders near the line at the snap | `defenders_in_box` (part.) | |
| **Pressure**, **time to throw** | Whether the QB was pressured; seconds from snap to throw | `was_pressure`, `time_to_throw` (part.); NGS weekly averages live | |
| **Coverage, man/zone** | The defense's coverage shell, and man vs zone | `defense_coverage_type`, `defense_man_zone_type` (part.) | Partly live via FTN charting |
| **Red zone**, **goal to go** | Inside the opponent's 20; first down with the goal line as the line to gain | `yardline_100 <= 20`, `goal_to_go` | |
| **Explosive play** | A big gain | `rushing_10`, `rushing_12`, `passing_20`, … (stats) | No single standard. Thresholds set in the first brief that uses it. |
| **Stabilization** | How many plays or games a stat needs before it reflects skill more than noise | — | The `stabilization` expert |
| **Regression to the mean** | Extreme results tend to move back toward average, more so for noisy stats | — | |

## Fantasy

| Term | Meaning | nflverse column | PCF notes |
|---|---|---|---|
| **Standard**, **half-PPR**, **PPR** | Scoring with 0, 0.5 or 1 point per reception | `fantasy_points` (standard), `fantasy_points_ppr` (stats) | All formats come from config (CONVENTIONS.md) |
| **Superflex**, **2QB**, **TE premium** | Lineups where a QB can fill a flex spot; two QB spots; extra points per TE reception | — | Config |
| **Redraft**, **keeper**, **dynasty** | Leagues rebuilt every year; keeping a few players; keeping the whole roster for years | — | |
| **Best ball** | No lineup setting: your best scores count automatically each week | — | |
| **DFS** | Daily fantasy: a new salary-capped lineup each slate | — | |
| **ADP** | Average draft position | — | Fantasy Football Calculator (live); old FantasyPros exports (research) |
| **ECR** | FantasyPros' expert consensus ranking | `load_ff_rankings` | The ranking benchmark (VALIDATION.md) |
| **xFP**, **FPOE** | Expected fantasy points from a player's opportunities; actual minus expected | `total_fantasy_points_exp` (`load_ff_opportunity`) | Opportunity-quality benchmark |
| **VOR / VBD** | Value over a replacement-level player at the same position | — | |
| **Replacement level** | The best player freely available on waivers in a given league setup | — | Depends on league settings |
| **Floor**, **ceiling** | A low and a high outcome | — | PCF uses q10 and q90 |
| **Start/sit** | Choosing which players to put in the lineup | — | A product |
| **ROS** | Rest of season | — | |
| **Stack**, **handcuff** | Pairing a QB with his receivers; rostering a starter's backup | — | |
| **FAAB** | Free-agent bidding budget for waivers | — | |

## Betting

| Term | Meaning | PCF notes |
|---|---|---|
| **American odds** | `-110` = bet 110 to win 100; `+250` = bet 100 to win 250 | Stored alongside the implied probability |
| **Implied probability** | The probability a price implies: 110 / 210 for −110, 100 / 350 for +250 | |
| **Vig / juice / hold** | The bookmaker's margin: the implied probabilities of both sides add up to more than 1 | |
| **No-vig (fair) probability** | The implied probabilities with the margin removed | Proportional method (VALIDATION.md section 8) |
| **Spread**, **moneyline**, **total** | Bet on the margin, the winner, or the combined score | `spread_line` (opposite sign), `total_line` in schedules |
| **Team total** | Over/under on one team's points | |
| **Prop** | A bet on a player's or team's stat (e.g. receiving yards over 64.5) | |
| **Alt line** | The same market at a different line, at a different price | |
| **Anytime TD**, **first TD** | A player scores at any point; a player scores the game's first TD | Usually only the "yes" side is offered |
| **Futures** | Season-long bets (Super Bowl, win totals, awards) | |
| **Open**, **close** | The first and last line before kickoff | ESPN history has only these two (DATA_SOURCES.md) |
| **CLV** (closing line value) | How much better our price was than the no-vig closing price | The main betting score (VALIDATION.md) |
| **Key numbers** | Common winning margins (3, 7) where spreads move carefully | |
| **Push** | A tie with the line: the stake is returned | |
| **Units**, **ROI** | Stake size in standard amounts; profit per unit staked | Flat one-unit stakes in evaluation |

## PCF's own terms

| Term | Meaning | Defined in |
|---|---|---|
| **PCF** | Principal Component Football | VISION.md |
| **Layer**: data, expert, composite, product | The four levels of the system. Experts model one part of football, composites combine experts, products are what users see. | CLAUDE.md |
| **Registry** | `projects/registry.yaml`: every project's status, dependencies, cadence and interface | CLAUDE.md |
| **Cadence**: `in_season`, `retrospective`, `offseason_events` | When a project updates, and therefore which data it may use | CLAUDE.md rule m |
| **known_at** | The earliest moment PCF could have had a row of data, for a live prediction | DATA_SOURCES.md |
| **as_of** | The moment a prediction is made; only data known by then may be used | ARCHITECTURE.md |
| **Gateway** | The `as_of` function: the only way models read data | ARCHITECTURE.md |
| **Leakage** | A model using information it wouldn't have had at prediction time | CLAUDE.md rule c |
| **Snapshot** | A dated copy of a source that gets revised | DATA_SOURCES.md |
| **History source**, **state source** | A file whose rows describe past events and only grow or get corrected (we keep the latest), vs one that describes how things are now and is overwritten (we keep every change) | data-layer |
| **Manifest** | The append-only log of every raw file fetched: where from, upstream fingerprint, size, SHA-256, when | data-layer |
| **Change log** | How state snapshots are stored: a full copy, then only the rows added or removed at each change | data-layer |
| **Revision report** | What changed when a history file was replaced upstream; flags changes to **watched columns** (ones models use, like `epa` or ids) | data-layer |
| **Slot label** | A player's position and depth on a play (`WR2`, `CB1`): their rank at that position on their team that week, by average depth over the season so far. `special` for K/P/LS, `unknown` with no chart or roster row | cleaning-port |
| **Label source** (`label_source`) | Where a slot label came from: `week` (that week's chart), `earlier_week` (an earlier chart that season), `roster` (roster position, ranked past the deepest in use) or `none` | cleaning-port |
| **Depth chart for a game** | Through 2024, that season-week's chart. From 2025, the latest daily snapshot at or before kickoff | cleaning-port, timeline |
| **Reference version** | An old function compiled straight from its `old/` notebook when a golden test runs. The faithful copy in the package must equal it | cleaning-port |
| **PCF team codes** | The 32 codes play-by-play uses, each franchise's current code for every season (2017 Raiders = `LV`). Other codes (OAK, SD, STL, LAR, …) are recoded at ingest | cleaning-port |
| **Kickoff** | A game's scheduled start in UTC: schedules' `gameday` + `gametime` (US Eastern for every game). Not the actual start | timeline |
| **Week window** | A season-week's span: from midnight Eastern after the previous week's last game day to midnight after its own. Week 1 starts two days before its first game | timeline |
| **Phase** | `offseason`, `free_agency`, `draft`, `after_draft`, `preseason`, `regular_season`, `postseason`. Offseason phases belong to the coming season. `phase_at` gives the phase of any moment | timeline |
| **Known-at rule** | The function that gives a dataset's rows their `known_at` (`pcf.data.timeline.RULES`) | timeline |
| **Offseason dates file** | `offseason_dates.csv`: league year, combine, draft and first preseason game per year, from public sources. A row is added each spring | timeline |
| **Data version** | A fingerprint of the raw files at a moment, logged with every run | data-layer |
| **Tier** | How much we trust a source (1–4) | DATA_SOURCES.md |
| **Level of detail (grain)** | What one row is: a play, player-game, team-week, … | ARCHITECTURE.md |
| **Walk-forward history** | Each past prediction made by a model trained only on earlier data. Higher layers train on it. | ARCHITECTURE.md |
| **train_end**, **vintage rule** | The last `known_at` in a model's training data; a model's output may be used only for rows after it | ARCHITECTURE.md |
| **Champion**, **challenger** | The current best version of a model, and a candidate compared against it | ARCHITECTURE.md |
| **Ladder**, **rung**, **takeaway** | Methods from simple to complex; one step on it; the lesson a rung passes to the next | ARCHITECTURE.md |
| **Brief**, **results**, **exploration** | A project's notes before building, after building, and from its first look | CLAUDE.md |
| **Finding** | A numbered claim in a results page, cited as `<project>#F1` | ARCHITECTURE.md |
| **Interface card** | A finished project's inputs, outputs, level of detail, cadence and how to use it | ARCHITECTURE.md |
| **Vault**, **vault spent** | The season held back until a project's end; a model changed after the vault was opened | VALIDATION.md |
| **Shuffled null**, **signal test** | A model trained on shuffled outcomes; beating 95 of 100 of them shows real signal | VALIDATION.md |
| **No-noise test** | An expert must not make its downstream baseline clearly worse | VALIDATION.md |
| **Scorecard** | The one-page validation report per run | VALIDATION.md |
| **Prediction ledger** | The append-only record of every prediction made before kickoff | ARCHITECTURE.md |
| **VOE** (value over expected) | *Provisional:* how much a player added beyond what the situation and teammates predicted. Final definition in the `voe-retro` and `voe-live` briefs. | to be defined in its brief |
| **Context** | *Provisional:* how hard a play's situation was (personnel, coverage, pressure, down and distance), as an expected outcome. Final definition in the `context-live` and `context-retro` briefs. | to be defined in its brief |
