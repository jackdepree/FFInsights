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
| **Series success rate** | The share of a team's series (a first down to the next first down, score or turnover) that earn a new first down or a touchdown. Drive-level, not play-level | `series`, `series_success` (pbp) | `team_game.efficiency`: `eff_series`, `eff_series_success`. The most consistent team measure found (team-efficiency#F9) |
| **Garbage-time rule** (the usual one) | Keep only plays with the offense's win chance between 10% and 90%, outside the last two minutes of each half | `wp` (pbp) | `team_game.efficiency`: `eff_usual_plays`, `eff_usual_epa`. Counting every play beat it (team-efficiency#F1) |
| **Win probability (WP)**, **WPA** | The chance the offense wins, and how much a play changed it | `wp`, `vegas_wp` (uses the spread), `wpa` | |
| **CPOE** | Completion percentage over expected, given throw depth, location and situation | `cpoe` (pbp, **0–100 scale**), `passing_cpoe` (stats) | Converted to 0–1 in derived columns |
| **xpass**, **PROE** | The chance a play is a dropback given the situation; pass rate over expected | `xpass` (0–1), `pass_oe` (**0–100 scale**) | Pace & play-calling expert |
| **PCF expected pass chance**, **PCF PROE** | PCF's own version, fit each season only on the 10 seasons before it (nflverse's `xpass` is in-sample before 2020 and runs 1–2 points high after) | `play.pace`: `pcf_xpass`, `pcf_pass_oe` (0–1); `team_game.pace`: `proe`, `proe_1st`/`_2nd`/`_3rd` | pace, decision 0028 |
| **Pace over expected** (clock-aware) | Game seconds from the previous snap of the drive, less what PCF expects from win chance, expected points, the clock and what stopped it (an incompletion, out of bounds, a penalty, a spike, a sack, a timeout). Negative is fast | `play.pace`: `exp_gap`, `pace_oe`; `team_game.pace`: `pace_oe` (seconds) | pace#F4, decision 0028 |
| **Volume** | A team's scrimmage plays in a game, split into dropbacks and runs | `team_game.pace`: `plays`, `dropbacks`, `runs` | pace's forecast |
| **Neutral situation** | Game states where play-calling isn't forced by the score or clock | — | No single standard. Defined in the `pace` brief. |
| **Dropback** | A play where the QB drops back to pass (passes, sacks, scrambles) | `qb_dropback` | |
| **Air yards** | How far the ball travels past the line of scrimmage | `air_yards` (pbp), `receiving_air_yards` (stats) | |
| **aDOT** | Average depth of target: air yards per target | — (air yards ÷ targets) | |
| **YAC**, **xYAC** | Yards after the catch, and its expected value | `yards_after_catch`, `xyac_mean_yardage` | |
| **Target share**, **air yards share** | A player's share of the team's targets, or air yards | `target_share`, `air_yards_share` (stats) | |
| **WOPR** | Weighted opportunity rating: 1.5 × target share + 0.7 × air yards share | `wopr` (stats) | |
| **RACR**, **PACR** | Yards gained per air yard, for receivers and passers | `racr`, `pacr` (stats) | |
| **Snap share** | The share of the team's snaps a player was on the field for | `offense_pct`, `defense_pct` (snap counts, 0–1) | Snap counts key on `pfr_player_id`. In `participation`, offensive only, and 0 when inactive or never on the field |
| **Leverage** (before the snap) | How much a snap's win chance can swing, from its situation alone (quarter, clock, score margin, down, distance, field position, timeouts, the win chance going in); 1.0 is an average snap. The CEO's "variance of winning percent added per play based on conditions/situations". Not the `high_leverage` tag, which marks plays that turned out to swing 5+ points | `play.leverage`: `wpa_sd` (win-chance units), `leverage`, `high_stakes` (the top fifth of the training snaps) | snap-leverage, decision 0033. Fit each season on up to the 10 before |
| **Leverage share** | A player's snaps, each weighted by its leverage, as a share of his side's weighted snaps: snap share weighted by the stakes | `player_game.leverage_usage`: `lev_share` (0–1) | From true participation (post-season); `pcf.data.usage` computes it from any on-field chances, such as participation-live's map. 0.99 alike with snap share: don't add it beside snap share for playing time (snap-leverage#R1) |
| **Passing-down role gap** | His share of his side's high-stakes snaps minus his snap share. The raw "trust gap", renamed for what it measures: third-down backs, pass rushers and slot backs score high (snap-leverage#F4) | `player_game.leverage_usage`: `lev_role_gap` | The contract market pays for it (+1.7%, F10) |
| **Trust over expected** | His high-stakes snaps beyond what his on-field rate in the same kind of situation (fifths of the expected pass chance) predicts, over his side's high-stakes snaps | `player_game.leverage_usage`: `lev_trust_oe` | Weak: repeats 0.12 week to week (F5) |
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
| **Elo rating** | A team strength number updated after every game by how much the result beat or missed the expectation. Only surprises move it | — | `elo`: in points against an average team on a neutral field; each team moves by 6% of the miss on the margin |
| **Strength of schedule** | How good a team's opponents were. A rating that scores each result against what was expected credits it automatically | — | In Elo, end rating ≈ 0.70 × mean margin + 0.82 × opponents' mean rating (elo#F10) |
| **Seed locked** | A team's playoff seed can't change whatever the remaining games do, so it has nothing to play for and may rest starters | — | `pcf.data.standings`: going into the final week, by the NFL's tiebreakers; `h_lock`, `a_lock` in Elo (decision 0022) |

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
| **Trait** (schemes) | A team's tendency (pass rate over expected, shotgun rate, tempo, throw depth) as a lasting property, forecast for its next game | schemes-v2 RESULTS |
| **Anti-trait** | A team's low use of an option, read as a possible limit: do low users gain less from it? Retired as a forecast (the CEO, 2026-11-10) after failing the vault | decision 0024 |
| **Gain from an option** | EPA per play with the option less without, in neutral situations | decision 0024 |
| **Opening coach** | A team's head coach for its first regular-season game, known from the start of week 1 (`team_game.opening_coach`) | decision 0025 |
| **Retrospective traits** (`team_season.charted`) | A team's charted choices over a finished season (personnel, box, coverage, blitz, nickel and dime), raw and over expected; a prior for the next season, never a live input | decision 0026 |
| **`prior_for`** | On a season's row: the first season whose in-season models may use it (the season + 1) | decision 0026 |
| **Opponent's bend** | How far offenses move off the league's level against a given defense, as a shrunk season gap | decision 0025 |
| **Regime** | A stretch of a team's games with the same head coach and starting QB; schemes are measured per regime | schemes-v2 BRIEF |
| **Matchup type (learned)** | Two hidden numbers per offense and per defense, learned from a season's results, whose product is the matchup part | schemes-v2 EXPLORATION F24 |
| **Cadence**: `in_season`, `retrospective`, `offseason_events` | When a project updates, and therefore which data it may use | CLAUDE.md rule m |
| **known_at** | The earliest moment PCF could have had a row of data, for a live prediction | DATA_SOURCES.md |
| **On-field rate** | A team's pace over expected or PROE on the plays a player was on the field for (participation); a defender's is the opposing offense's | decision 0029 |
| **Player plus-minus** | His team's rate on the field minus off it, same team-game, weighted by on × off ÷ team snaps (`player_game.on_field_pace`); shrunk toward his position group in forecasts | decision 0029 |
| **Expected starting QB** | The team's last starter known by the Saturday run, unless ruled out (Out, Doubtful) or off the roster; then the rostered QB with the most snaps | decision 0029 |
| **Mover** | A player who played for one team and then another, between or within seasons | player-pace BRIEF |
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
| **Table part** | One source's columns for a table, saved with that source's `known_at` and the table's keys. `load` joins the parts known at a moment | grain-tables |
| **Spine** | The part that decides which rows a table has. `player_game`'s is the roster: everyone on the 53-man roster for the game | grain-tables |
| **Inactive** | A player on the 53-man roster who isn't dressed for the game. Named 90 minutes before kickoff; `status` = `INA` in weekly rosters from 2019 | grain-tables |
| **Tag** | A named label on a play, drive, team-game or player-game, computed by one written, versioned rule (`tag_<name>`, `tag_<name>_v2`). Usually yes/no; some are categories (game script). Empty means "doesn't apply", never "no". The catalog is `docs/TAGS.md` | tag-tables |
| **EPA–WPA gap** | How far a play's win-chance change is from what its EPA would usually bring at that score and clock: a large gap means the play mattered to the game more (or less) than its points. Modelled per play from earlier seasons, cut at its 5% tails | team-efficiency#F6, decision 0032 |
| **Situation propensity** | The chance an offense is in a given game state (win-chance band × half, 14 bins) when it snaps, fit from earlier seasons. DML uses it to take the game state out of EPA before rating teams | team-efficiency#F7, decision 0032 |
| **DML** (double machine learning, Robinson partialling) | Rate teams on EPA less what the game state predicts (the outcome model), cross-fitted on two halves of the games, so a team isn't credited for playing while far ahead or behind | team-efficiency#F7 |
| **The weaker pull** (P3) | How much of last season's rating carries into this one, cut after a change: on offense, pull × (1 − 0.25 × new QB − 0.25 × new coach). New QB: the week-1 depth chart's QB1 isn't last season's most-started QB; new coach: the opening coach isn't the one who finished last season. Each flag counts once known | team-efficiency#R11, #R17; `team_efficiency.changes` |
| **Representativeness weight** | How much a play says about a team's other games: plays of each kind (the EPA–WPA gap's tails, the last two minutes of a half, or a win-chance band; each pass or run) are weighted by how much one play of it moves the team's EPA per play in its other games (odd weeks against even), shrunk toward equal, apart for offense and defense, scaled to a mean of 1 | team-efficiency#F8, decision 0032 |
| **Efficiency rating** (`combo`) | A team's EPA per play over or under the league, from DML on representativeness-weighted plays, with a recency half-life and last season as a prior. Offense and defense apart | team-efficiency, decision 0032 |
| **`team_game.efficiency`** | The table part holding, per offense and game, the sums the efficiency ratings need (plays, EPA, the usual rule's plays, passes, runs, series, and per situation bin the DML residuals with both weights). Known at kickoff + 1 day | decision 0032 |
| **Tag family**: measured, situation, lore | A statistical definition (successful = positive EPA); the game state (red zone); a commentator's idea pinned to a rule (answer drive) | tag-tables |
| **Football timing** | Whether a tag describes the moment *before* the event or its *result*: before the snap, before the game, after the play, after the drive, after the game, after the season. Only "before" tags may describe the row being predicted. Separate from `known_at`, which is when PCF has the data | tag-tables |
| **Reference tag** | A catalog entry pointing at a column nflverse already has (FTN's `is_play_action`), listed so it's found, not copied | tag-tables |
| **Rate band** | The share of applicable rows a tag should fire on in a complete season. A season outside it fails the build's checks (rule h) | tag-tables |
| **Drive** | One possession, nflverse's `fixed_drive` within a game. The `drive` table has one row per drive with its result, plays and first downs | tag-tables |
| **Data version** | A fingerprint of the raw files at a moment, logged with every run | data-layer |
| **Tier** | How much we trust a source (1–4) | DATA_SOURCES.md |
| **Level of detail (grain)** | What one row is: a play, player-game, team-week, … | ARCHITECTURE.md |
| **Walk-forward history** | Each past prediction made by a model trained only on earlier data. Higher layers train on it. | ARCHITECTURE.md |
| **train_end**, **vintage rule** | The last `known_at` in a model's training data; a model's output may be used only for rows after it | ARCHITECTURE.md |
| **Champion**, **challenger** | The current best version of a model, and a candidate compared against it. The champion is written in `registry.yaml` and changes only by an approved merge (decision 0009) | ARCHITECTURE.md, experiment-tracking |
| **Attempt** | One try at a project's model: a parent run in MLflow with one child run per rung. Every attempt counts in the scorecard's "versions tried", failed ones too | experiment-tracking |
| **Registered model** | A model saved under a name, `pcf.<id>`, with numbered versions. Only runs that passed the leakage checks can be registered | experiment-tracking |
| **Ladder**, **rung**, **takeaway** | Methods from simple to complex; one step on it; the lesson a rung passes to the next | ARCHITECTURE.md |
| **Brief**, **results**, **exploration** | A project's notes before building, after building, and from its first look | CLAUDE.md |
| **Finding** | A numbered claim in a results page, cited as `<project>#F1` | ARCHITECTURE.md |
| **Interface card** | A finished project's inputs, outputs, level of detail, cadence and how to use it | ARCHITECTURE.md |
| **Vault**, **vault spent** | The season held back until a project's end; a model changed after the vault was opened | VALIDATION.md |
| **Prediction moment** | When a prediction is made: one of the three weekly runs (Tuesday 10:00, Thursday 12:00, Saturday 12:00 ET; Thursday was Wednesday 16:00 until 2026-11-06, decision 0016) that a model declares. Each game is predicted at the latest allowed run before its kickoff (CEO decision 1C) | validation-harness |
| **Fallback moment** | 10:00 ET on the first day of a week window, used for a game when no allowed run comes before its kickoff (weeks that start mid-week, validation-harness#F11) | validation-harness |
| **View** | What the gateway returns for one moment: a model's declared tables and outputs, as known then | validation-harness |
| **Cutoff** | A moment at which a leakage check compares features with and without the data that came after it | validation-harness |
| **Planted leak** | A deliberately leaky toy model kept in the tests: every blocking check must catch its own and pass the honest twin | validation-harness |
| **Benchmark** | A baseline from outside PCF (ECR, the closing line): scored like a model, never used as a feature before it's known, and not signal-tested | baselines |
| **Kickoff moment** | A prediction moment at each game's kickoff, allowed only for benchmarks (the closing line is known then) | baselines |
| **Rank-to-points curve** | The points scored at each ECR rank in a position, fit on training weeks (isotonic: a better rank never projects fewer points). It turns a ranking into a projection | baselines |
| **Variant** | One of several models under one project id, e.g. `baselines/ecr`; its outputs are in `outputs/<id>/<variant>/` | baselines |
| **Discovery loop**, **confirmation loop** | Cheap, open searches for problems and ideas (explorations, `IDEAS.md`, where models miss), versus the strict harness that proves a result. A discovery result never counts as proof | CLAUDE.md |
| **Miss lens** | A tag or category every model's errors are split by, in each RESULTS.md's "Where it misses". The short list is chosen by `miss-lenses` and named by its date (the first: 2026-11-03; in use: 2026-11-15, which adds the player and team change lenses, decision 0035) | miss-lenses |
| **Miss** | Actual minus projected (`y - mean`): positive means the model was too low | miss-lenses |
| **Bias share**, **spread share** | How much of a model's squared miss (bias), or of the size of its misses (spread), a correction per lens group removes when learned on the other half of the seasons | miss-lenses |
| **Diagnostic lens** | A lens known only after the game (snap share, team points): it explains a miss, never feeds a model | miss-lenses |
| **Active** | On the game-day active list. Known about 90 minutes before kickoff, so it's predicted (`p_active`). Before 2019 there are no statuses, so it means "has a snap-count row" | participation |
| **Two-part prediction** | The chance of taking an offensive snap, times the share if they do. Its ranges come from the mixture: a spike at 0, otherwise the share plus residuals | participation |
| **Spike forecast** | A forecast where one exact result is common, here a share of 0 (no offensive snap), on top of a spread of ordinary results. With a 10%+ chance of 0, q10 is 0, so a 0 counts as inside the range and nothing can land below it: coverage settles above 80% even for a perfect forecast (participation#F13) | participation |
| **Range score (pinball loss)** | How we score a forecast range. Each of q10, q50 and q90 is charged for its miss, weighted so a result beyond the range's edge costs most, then the three are averaged. Lower is better, a range too wide or too narrow scores worse than a right one, and it reads in points of whatever is forecast | validation |
| **`p_nonzero`, `if_nonzero_*`** | The two parts of a spike forecast, saved in its history: the chance the result is above 0, and the mean and range if it is. `mean` is the two multiplied (decision 0014) | participation |
| **Horizon** | The window a forecast covers, counted in the team's games from the next one: 1, 3, or the rest of the regular season. The outcome is the average share over it, with 0 for games missed, inactive or off the roster | participation |
| **Played recently** | Took an offensive snap in the last 8 games: the rows scores are reported on, as well as overall | participation |
| **Case against**, **spot-check** | Before a merge: Claude's strongest argument that the result is wrong, and one decision or finding the CEO picks to go through in depth | CLAUDE.md |
| **Expert contract** | The interface every model implements (`pcf.core.contract.Expert`): id, cadence, grain, inputs, run, `features(view, games)`, `target`, `fit`, `predict` | validation-harness |
| **Shuffled null**, **signal test** | A model trained on shuffled outcomes; beating 95 of 100 of them shows real signal | VALIDATION.md |
| **No-noise test** | An expert must not make its downstream baseline clearly worse | VALIDATION.md |
| **Scorecard** | The one-page validation report per run | VALIDATION.md |
| **Prediction ledger** | The append-only record of every prediction made before kickoff | ARCHITECTURE.md |
| **VOE** (value over expected) | *Provisional:* how much a player added beyond what the situation and teammates predicted. Final definition in the `voe-retro` and `voe-live` briefs. | to be defined in its brief |
| **Context** | The situation plus both sides' call fields on a play, and never who the players or teams are. Its expected outcome is what that play "should" have produced. `context-live` is the in-season edition (FTN's charting, known 14 days after the game); `context-retro` will add the after-the-season fields (coverage, routes) | context-live (decision 0036) |
| **The situation** | Before the snap: down, distance, field position, goal to go, quarter, both clocks, the score, both teams' timeouts, home or away. What public expected-points models use | context-live |
| **Call fields** | What each side lined up in or did by design: shotgun, no huddle, where the QB lines up, backs in the backfield, motion, play action, screen, RPO, trick play, sneak, the hash (the offense); box count, blitzers, pass rushers (the defense). Charted after the play, so "screen" and "play action" partly describe what happened | context-live |
| **Expected outcome** | `context-live`'s estimate of one outcome on one play from its context: a chance for yes-or-no outcomes (`*_prob`), an average and a range for yards and seconds (`*_exp`) | context-live |
| **E0** (the expectation before the snap) | `context-retro`'s expected outcome from what was known before the snap: the situation and both sides' calls, coverage included, made after the season (`<outcome>_e0`) | [`context-retro/RESULTS.md`](../projects/context-retro/RESULTS.md) |
| **E1** (given the pressure) | `context-retro`'s expected outcome given the play's real pressure as well as everything in E0 (`<outcome>_e1`); missing where participation has no pressure flag | [`context-retro/RESULTS.md`](../projects/context-retro/RESULTS.md) |
| **Pressure part** | On a dropback, E1 minus E0 for the sack chance: how much the pressure (or its absence) changed the sack's chance. Summed per player per game (`sack_pressure_part`) | [`context-retro/RESULTS.md`](../projects/context-retro/RESULTS.md) |
| **After-pressure part** | On a dropback, the sack (1 or 0) minus E1: what happened after the pressure was known, over what was expected given it. The QB's trait (`sack_after_part`; context-retro#R5) | [`context-retro/RESULTS.md`](../projects/context-retro/RESULTS.md) |
| **The provider rule** | Participation's pressure and time to throw changed provider in 2023, so their models train within one provider: test seasons through 2023 from 2016, 2024 on 2023, 2025 on 2023-2024 (decisions 0038, 0040) | [decision 0040](decisions/0040-context-retro.md) |
| **A player's context**, `ctx_success` | The average expected success of the plays a player was on the field for (weighted by participation-late's chance he was on), minus the league's success rate. `ctx_success_sit`: the same from the situation alone; `ctx_calls`: the difference, what the calls added | context-live |
| **Pull** (between seasons) | How far every rating moves back toward average when a new season starts: rosters change and luck doesn't repeat. 0.4 means 40% of the way | elo (F9, decision 0021) |
| **Carryover** | How much of a season's measure repeats next season: the slope of next season's value on this one's. A season's margin keeps 0.42; Elo's end-of-season rating 0.60–0.68 | elo#F9 |
| **Usual QB**, **same-team share** | The usual QB: the QB with the top offense snap share over a team's last 4 games. Same-team share: the share of the team's usual snaps (offense and defense) whose players are available this week | elo (H1) |
| **Published features** | Numbers an expert computes at a forecast's moment without fitting, saved next to its forecasts so higher layers can use them (`Expert.publishes`): Elo's ratings | decision 0021 |
| **Feature candidate** | An expert output that is consistent and close to as good as the close: recorded in CONSISTENCY.md for downstream models to try (the CEO, 2026-11-07) | CONSISTENCY.md |
| **Known spots**, **open spots** | On a play, the known spots are the players certain to be on it: on every snap by his snap count, or named by the play-by-play (passer, rusher, receiver, tackler...). The open spots are the rest of the 11, which `participation-live` fills | participation-live BRIEF |
| **On-field chance** | `participation-live`'s chance that a player was on the field for a play (`quantity` `on_field_chance`). Each play's chances add to 11 a side and each player's add to his snap count. Use it as a weight (a player 60% likely counts 0.6 on and 0.4 off) to carry the uncertainty | participation-live |
| **Snap-matched best guess** (`best`) | One lineup per play from `participation-live`'s chances, chosen over the whole game so every play has 11, every player's total matches his snap count, and each play's count of each position group matches its chances (participation-live#R3, R4) | participation-live |
| **Likeliest lineup** (`likeliest`) | Each play's own likeliest 11 within its position mix: more players right per play than the snap-matched guess, but each player's total drifts from his snaps and it substitutes too rarely (participation-live#R3) | participation-live |
| **Edition** (vintage) | The same output for the same games, made again at a later moment with more evidence and saved beside the earlier one, never over it. A model reads the newest edition whose `as_of` is before its own moment. The participation map has two: the morning after (`participation-live`) and two weeks later with FTN's charting (`participation-late`) | participation-late |
| **Lineup certainty** (`certainty`) | `participation-live`'s per-play confidence in its likeliest lineup: the expected share of the 11 it names that were really on, (known spots + the chances of the open players it picked) / 11. A play at 0.95 is nearly sure; one at 0.75 is a guess on about 3 players. For downstream models, a weight or a propensity: trust a play's lineup as much as its certainty | participation-live |
| **Position mix** | A play's count of each position group (backs, tight ends, receivers, linemen...). For a lineup guess it is fixed at what the group's on-field chances on the play add to, rounded over the whole game so each group's total still matches its players' snaps (decision 0030, call 6) | participation-live |
| **Crude forecast** (the yardstick) | A deliberately simple forecast of yards (players' passing, rushing and receiving; a team's gained, and allowed as its mirror) from visible inputs: averages of yards, attempts, first downs and touchdowns this season, over the last 4 games and last season, the season's running total, last 4 minus the season, the game-to-game spread and yards per attempt. Rungs: the season-so-far average, a lasso, xgboost trees, their mix; each target's champion is the ladder's (decision 0037). Every expert, hunch and idea is scored by what it adds to it | crude-forecaster |
| **Expected to play** (the row rule) | A player-game is forecast and scored when participation's saved chance of a snap is at least 50%, known before kickoff (the CEO's call, Claude's reading). Rows where he took a snap are a check only, since that filter knows the outcome | crude-forecaster |
| **Added alone** (method A) | The share of the crude forecast's held-out squared error an input removes when it is the only thing added, paired on the same rows, with a 90% interval from resampled weeks. Its range-score change decides the no-noise verdict | crude-forecaster |
| **Fair share** (method C) | An input's average held-out gain over every order in which the members could have been added (a Shapley share), as a share of the crude forecast's squared error. The shares add up to the all-members gain. Each table is dated: shares move when a member joins | crude-forecaster |
| **Shuffled copy** | A yardstick member that must get nothing: one expert's columns shuffled together within each week (participation's for players, Elo's for teams). If its share's interval clears zero, the yardstick is reading noise | crude-forecaster |
| **Yardstick table** | One row per member, target and horizon: added alone and fair share with their intervals, the range-score change, the verdict, the rows and the date (`outputs/crude-forecaster/yardstick/<target>_<horizon>/`) | crude-forecaster |
| **Noise floor** | What a yardstick gain must beat to be read: its 90% interval from resampled weeks clears zero, and it beats all 19 copies of the same expert with its columns shuffled within each week (a permutation test, p = 0.05). About 0.1 points of share for receiving, 0.2–0.3 for rushing, 0.5 for passing, 0.7 for team yards next game, 1 point over the next 3 (crude-forecaster#R7; redefined 2026-11-19 by the CEO's spot-check, from one shuffled copy's largest gain across refits) | crude-forecaster |
| **Chance** | One target (a pass with a receiver, not a sack) or one carry, by a running back, wide receiver or tight end; two-point tries left out (`play.xfp`, decision 0041) | opportunity-quality |
| **Expected points of a chance** (xfp, PCF's) | The fantasy points an average player scores on a chance from its situation alone (yard line, down, distance, goal to go, formation, tempo, quarter, clock, score; throw depth and side; run side and gap), from models fit only on earlier seasons (2009 on). Summed per player-game (`player_game.opportunity`); any scoring from the same pieces (catch chance, yards, touchdown chance). Agrees with nflverse's xFP at r 0.99 | opportunity-quality |
| **Points over expected** (poe) | Actual points on a player's chances minus their expected points: the fantasy analysts' "efficiency". Per chance, it's mostly noise week to week; a small true level per player shows only over a season or more | opportunity-quality |
| **The gap** | A player's points over expected per chance over this season so far and last season, with the chances behind it (the regression measure's input) | opportunity-quality |
| **Kept share** | How much of a player's gap is expected to last: k = τ²/(τ² + V), the spread of true levels at his position over that plus the noise in his gap from his chances (method B, partial pooling). Rises with chances: about 0.12 at 20-50 chances, 0.5-0.6 at 400+ | opportunity-quality |
| **Chance the gap closes** | The probability that his points over expected per chance over the rest of the season end on the near side of half his current gap; from method B's range for his true level and the noise of his expected chances, recalibrated on earlier seasons | opportunity-quality |
| **Chance of a chance** (`p_nonzero`) | In the opportunity forecast, the probability a rostered player gets at least one target or carry next game; the forecast is that times the expected points if he does (a spike forecast, decision 0014) | opportunity-quality |
| **Expected touchdowns** (xtd) | The chance a chance scores, from its situation alone: opportunity-quality's touchdown chance for RB, WR and TE targets and carries, td-expert's own model for a QB's carries (scrambles included). Summed per player-game or team-game. A throw's expected touchdowns are its target's, credited to the passer (`play.xtd`, decision 0043) | td-expert |
| **Touchdowns over expected** (TDOE) | Touchdowns minus expected touchdowns; per chance (or per throw) it is the regression measure's input | td-expert |
| **Luck measure** | Touchdowns over expected in dice spreads, (td − xtd) / √Σp(1−p), and the exact chance of at least that many touchdowns from those chances (Poisson-binomial). Looking back only, never an input | td-expert |
| **Drive chance** (`p_start`, `p_rz`, `p_peak`) | A drive's chance of ending in a touchdown, from the situation at a snap: at its first snap, at its first snap inside the 20, and at its best moment (`drive.td_chance`) | td-expert |
| **Drive-aware hindsight** | The team's touchdown ceiling: each drive that reached the 20 counts its chance there, every other drive what happened. It knows the drives and trips, and leaves the dice from the 20 in | td-expert |
| **Near miss** | A field-goal drive's best chance of a touchdown (`p_peak`). A description, never an input (the brief) | td-expert |
| **Count forecast** (kind `count`) | A forecast of a whole number (touchdowns) as a mean, scored by the Poisson log loss (−log P(y) under a Poisson count with that mean) and judged by its chance of 1+ and of 2+ under that Poisson (decision 0043) | td-expert |
| **Poisson log loss** | −log P(y) for a count y under a Poisson with the forecast mean: lower is better; the count kind's main score | td-expert |
| **Negative binomial** (a count's spread) | A count wider than Poisson: variance mean + α·mean^p (p = 2 the usual one; a lower p spreads big means less). α 0 is Poisson. `pcf.validation.scores.negbin_at_least`, `fit_spread` | td-expert R18 |
| **Opener** (`team_game.openers`) | ESPN's opening line for a game, the median over books, per team: `open_total` and `open_spread` (betting sign). Known at the start of the game's week + 2 days; 2023 on | td-expert R17, decision 0043 call 25 |
| **Pooled role space** | One PCA per side of the ball across its positions together (offense WR, TE, RB; defense DL, OLB, ILB, CB, S), no position label, no measurables; refit each season, rotated to the last fit (Procrustes) | roles-archetypes RESULTS, decision 0048 |
| **Role coordinates** (`z0`-`z5`) | A player-season's six numbers in his side's pooled space, with a 90% split-half interval, shrunk toward his group's mean under 200 snaps (`shrink_w`) | roles-archetypes RESULTS |
| **Role table** (`t*_`) | Six usage features per side (offense: snap share, targets per pass snap, carries per run snap, target depth, run and 11-personnel tilts; defense: snap share, rushes per pass snap, tackles per snap, tackle depth, 11-personnel and 3rd-down tilts): the forecasting input of roles-archetypes | roles-archetypes F1 |
| **Named role**, **coarse role** | A role read by explicit rules on the role table with cuts frozen on 2016-2020: 12 fine roles (working names: early-down back, passing-down back, blocking and inline tight end, slot receiver, deep threat, outside receiver; pass rusher, box linebacker, run defender, slot defender, base defensive back) in 5 coarse groups (back, in tight, split out, front, coverage) | roles-archetypes RESULTS, decision 0048 |
| **How sure** (`sure`) | The chance a named role's cuts would come out the same without sampling noise: the product over its cuts of Φ(distance to the cut / the feature's noise at his snaps) | roles-archetypes RESULTS |
