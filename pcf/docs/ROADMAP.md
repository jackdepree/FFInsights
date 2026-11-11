# Roadmap

> **Status lives in [`projects/registry.yaml`](../projects/registry.yaml).** This page is the readable view: what's now, next and later, plus milestones, decisions and history. If this page and the registry disagree, the registry wins and this page gets fixed.
> Anything can be added anywhere at any time. A new expert is a new registry entry that goes through the lifecycle in [`CLAUDE.md`](../CLAUDE.md).

## Phases

| Phase | What | Notes |
|---|---|---|
| **0: Foundation** | Betting-line collection · package and config · experiment tracking · data layer · NFL timeline · cleaning functions · tables at every level of detail · tag tables · validation harness · baselines · prediction ledger · registry tooling | Everything else stands on this |
| **1: Experts** | Every expert model, each focused on one part of football | No sub-phases. The order comes from dependencies in the registry. |
| **2: Composites** | Team strength · player opportunity · game simulator · outcome distributions | Combine the experts |
| **3: Products** | Fantasy projections (all formats) · start/sit · props · DFS/best ball · dynasty · futures · scorecards · reports · builder view | The final outputs |
| **4: Automation & distribution** | Weekly run · emailed reports · dashboard | A basic data refresh exists from Phase 0 |
| **5: Public** | Website and subscriptions | Only once the track record earns it |

## Now

Phase 0, starting with the one item that can't wait:

1. **Betting-line collection** (`odds-collection`). Every week of lines we don't collect is lost for good. Free odds-API tiers and public JSON endpoints only, no scraping.
2. Package scaffold and config · experiment tracking (MLflow) · data layer · NFL timeline · cleaning-function port
3. Tables at every level of detail · tag tables · validation harness (the `as_of` gateway's leakage checks) · baselines · miss lenses · prediction ledger · registry tooling

## Next

The first experts: **Team Elo · opponent-adjusted efficiency · pace & play-calling · environment · stabilization · Context (in-season) · participation & snaps**

## Later

- **The remaining experts:** line play, game script, Context (retrospective), VOE (in-season), VOE (retrospective), opportunity quality, vacated opportunity, touchdowns, aging, injury & fatigue, roles & archetypes, QB talent, prospects, kicker & DST, market, crowd, news
- **Then** composites, products, automation and public, in dependency order

## Milestones

These are targets, not deadlines.

| When | Target |
|---|---|
| **End of the 2026 regular season** (early Jan 2027) | Lines and predictions are logged every week. Phase 0 is mostly done. The first experts are being explored or built. |
| **Super Bowl** (Feb 2027) | The data layer covers the offseason timeline. Most "next" experts are validated. |
| **2027 draft (end of April 2027): the 6-month checkpoint** | "In a really good spot": most experts done, composites underway, and a first end-to-end product (weekly fantasy projections with uncertainty) working on historical data. |
| **2027 Week 1** | Products live. The public track record starts. |

## Decisions needed from the CEO

- [ ] **Backups for MLflow and model outputs** (not urgent until the first expert is built). They live on one PC, and losing them means slow retraining. Options to brainstorm then: a synced folder (OneDrive), an external drive, or champions only into a private repo.

Decided:
- **2026-11-10 · Schemes v2** ([results](../projects/schemes-v2/RESULTS.md)): merged as done. Retrospective traits are a table with timing columns, not an expert (decision 0026). The anti-traits are retired after failing the vault. Schemes feed pace, player opportunity, which players each team goes after in trades and free agency (H18), and context.
- **2026-11-06 · Participation, next-game champion** ([results](../projects/participation/RESULTS.md)): `trees_week` replaces `trees_top`, after the CEO's spot-check on the playoffs. It keeps the plain week over a playoff flag, because the flag loses the ordinary-week gain (F34). Known misses stay open: the final week misleads playoff forecasts (F36, I17), and top teams' last-week starters are over-projected (F35).
- **2026-11-05 · Participation, next-game champion** ([results](../projects/participation/RESULTS.md)): `trees_top` becomes the champion, with QB's range coverage of 90.7% logged as a narrow miss. The 90% group bar stays as written: a true forecast would hold 90.2%, and rewriting a bar after seeing results adds forking paths. The week and last-week inputs come next, on a new branch (F29, I13).
- **2026-11-04 · Participation** ([results](../projects/participation/RESULTS.md)): merged without a registered champion, to be built with the weekly run. Next-game coverage of 85.3% is arithmetic (a perfect forecast scores 85.8%). The CEO proposed judging the chance of 0 and the share if they play separately; the bar is unchanged until the harness can do that.
- **2026-11-03 · Ways of working:** two loops, discover then confirm; a hypothesis log (`projects/IDEAS.md`); a short fixed list of miss lenses in every RESULTS.md, chosen by discovery (`miss-lenses`) instead of every tag; the case against and a CEO spot-check before every merge.
- **2026-11-03 · Baselines** ([results](../projects/baselines/RESULTS.md)): D1–D9 as written; to ship, the weekly fantasy product must match ECR if it doesn't use ECR, and clearly beat ECR if it uses ECR as an input; experts may name ECR as their no-noise baseline (VALIDATION.md §5–6).
- **2026-11-02 · Validation harness** ([results](../projects/validation-harness/RESULTS.md)): prediction moments are the three weekly runs (1C); the harness covers everything a model needs to be done, with betting evaluation and the live gap later (2A); leakage comparisons allow a 1e-9 rounding tolerance.
- **2026-10-30 · Validation** ([VALIDATION.md](VALIDATION.md)): a rolling vault season (2025 now; props use 2026 live), proper scores, "beats" means a 90% week-block interval above zero, signal and no-noise tests for experts, calibration and range-coverage bands, closing line value over ROI, and a CEO sanity review for every expert.
- **2026-10-30 · Architecture** ([ARCHITECTURE.md](ARCHITECTURE.md)): Python only; Parquet, Polars and DuckDB; the `as_of` gateway with stacked leakage checks; one expert contract; MLflow for tracking and model reuse; the knowledge tree (briefs, results, numbered findings); the model ladder; collectors on Actions and modeling on the PC via Task Scheduler.
- **2026-10-29 · Collector set up:** the private `pcf-data` repo, token and secrets were created, and the collector was merged to `main`.
- **2026-10-28 · Odds collection** ([exploration](../projects/odds-collection/EXPLORATION.md)): the CEO signed up for The Odds API. The ESPN backfill (2022–2026) has run. The collector runs on GitHub Actions and saves to the private `pcf-data` repo.

Decided:
- **2026-10-28 · Expert catalog:** confirmed as recommended. Every ⭐ is on the roadmap, every ○ is in the parking lot.
- **2026-10-28 · Schemes:** `schemes-v2` is a full expert, not parked. We didn't find signal before, but we still need to look.

## Parking lot

Good ideas not scheduled yet, listed in the registry with `horizon: parking`:
- play-caller tendencies
- referee crews
- coverage matchups
- contract & motivation
- hot hand (exploration only)
- VOE as a conditional diffusion model

## Dead ends

| Project | What we tried | Why it failed | What would make us retry |
|---|---|---|---|
| `schemes-v1` (`old/code/Schemes_Model.ipynb`) | Over-expectation features → PCA → clustering into team schemes | Little usable signal | Being retried as the `schemes-v2` expert, from the roles & archetypes angle |
| `player-pace` (in season, 2026-11-11) | Team pace's forecasts plus the expected starting QB and who's ruled out | Pass rate over expected improved 0.3% (4% in expected starter changes); volume didn't (player-pace#R2, R3). The CEO kept the findings and discarded the model | A starter-change forecast with probabilities (only 32% of real changes are visible by Saturday, R5), or a Sunday-morning run that sees inactives |

## Changelog

One dated line each time something reaches Done, or the roadmap changes shape.

- **2026-11-11:** `player-pace-retro` is **done** and merged (the CEO: "Merge now"), after the CEO's spot-check of R1 held: a skill player's pass-rate plus-minus forecasts his next season's 15% better than his position's average, 12.7% beyond playing time.
- **2026-11-11:** The CEO discarded the in-season `player-pace` model and kept its results and findings (dead end); `player-pace-retro` goes on to the spot-check.
- **2026-11-11:** `player-pace` and `player-pace-retro` reach validating. New tables `player_game.on_field_pace` and `player_season.on_field_pace` (2016 on). Between seasons, a skill player's pass-rate plus-minus forecasts his next season's 15% better than his position's average (player-pace#R1). In season, the expected starting QB improves team PROE a little (0.3%; 4% in expected changes) but not volume, so the brief's main test failed (R3).
- **2026-11-11:** `pace` is **done**: the CEO called H22 held (the full-sample measurement beats the neutral one like for like, pace#R1). Next: `player-pace`, as the CEO planned.
- **2026-11-11:** `pace` merged (CEO approved) after the CEO's spot-check of R1 (holds: the full-sample win is the measurement). Its 12 finals and their season-to-date yardsticks join the weekly ledger (39 models) from the next run. Stays validating until the CEO's call on H22's verdict.
- **2026-11-11:** `pace` reaches validating: new parts `team_game.pace` (volume and habits per game, measured on every play against PCF's own expected pass chance and clock-aware expected pace) and `play.pace` (per snap, for `player-pace`), and next-game forecasts of plays, dropbacks, runs and six habits, all beating their averages. The CEO's H22 holds as a like-for-like test (full-sample habits beat neutral ones), by a small margin. No line at the Saturday run (pace#R5).
- **2026-11-10:** `schemes-v2` reaches validating: next-game forecasts of four team tendencies (pass rate over expected, shotgun rate, tempo, throw depth) that follow the head coach, beat every simple average, and hold on the 2025 vault except throw depth. Anti-traits hold as a relationship on offense but fail as a forecast. Scheme against scheme (the CEO's H14) found nothing usable. Done once the CEO calls the retrospective traits.
- **2026-11-10:** `schemes-v2` is **done** and merged (CEO approved). Added the retrospective traits table `team_season.charted` (each team's charted traits per season, with `known_at` and `prior_for`; decision 0026). The CEO retired the anti-traits and named the downstream users: pace, player opportunity, which players each team goes after in trades and free agency (H18), and context.
- **2026-11-10:** The retrospective traits are a table, the CEO's call: `team_season.charted`. It holds each team's charted choices per season, 2016–2025: personnel, box, coverage, blitz, nickel and dime, raw and over expected. Each row carries `known_at` and `prior_for`, so in-season models use it only from the next season (decision 0026). It also fixes `team_game.charted`, which missed fullbacks from 2023 on.
- **2026-11-07:** `elo` done, PCF's second expert: a team rating in points (margin, offense, defense) with the usual-QB, same-team and seed-locked adjustments (the CEO's H1 and H8). It forecasts margins 0.27 and totals 0.30 points behind the close, adds nothing to the close when blended, and saves its ratings for higher layers (decisions 0018-0022). New shared module `pcf.data.standings`: NFL tiebreakers, seeds and final-week locks, matching every real playoff field 2002-2024.
- **2026-11-07:** The prediction ledger is on main and scheduled (Tuesday 10:00, Thursday and Saturday noon Eastern); its first counted forecasts come Thursday 2026-11-12, and it moves to validating until two live weeks are scored. Team Elo starts, the first project to open with the CEO's hunches (`projects/elo/BRIEF.md`).
- **2026-11-06:** `participation`'s next-game champion is now `trees_week`: `trees_top` plus the week of the season and the last week times win rate (F33). The spot-check corrected why the playoffs gain: mostly backups on the inactive list, not tighter rotations (F34), and found the final week misleads playoff forecasts (F36).
- **2026-11-05:** `participation`'s next-game champion is now `trees_top`: spike forecasts are judged part by part and their parts saved (decision 0014), QBs get a chance of every snap, and players on the injury report get their own residuals (F25–F28). The Windows block on pandas cleared, so the full tests and MLflow runs are back.
- **2026-11-03:** `participation` built, PCF's first expert: each rostered QB, RB, WR and TE's snap share and chance of being active, before each game, over the next 3 games and for the rest of the season, as four champions. It beats its shuffled self and improves the lasso's fantasy points (decision 0013). `career-snaps` added as an idea (D10).
- **2026-10-28:** Charter (`CLAUDE.md`), `VISION.md`, this roadmap and the project registry created.
- **2026-10-30:** `DATA_SOURCES.md` written. Experts now declare a `cadence` (rule m). Context and VOE are each split into in-season and retrospective experts, because play-level participation is published only after the season.
- **2026-10-30:** `ARCHITECTURE.md` written, with five decision notes, brief and results templates, and `projects/KNOWLEDGE.md`. Added the `experiment-tracking` project.
- **2026-10-30:** `VALIDATION.md` written. The 2025 season is the first vault.
- **2026-10-30:** `OLD_INVENTORY.md` written: the salvage map of `old/`. Old saved models are never loaded, and old data is for research and benchmarking only.
- **2026-10-30:** `CONVENTIONS.md` and `GLOSSARY.md` written. Every brief and results page now has a Terms section. The project-wide docs are complete.
- **2026-10-30:** `package-scaffold` done: the `pcf` package, config, a logger that masks keys, `pcf info`, pytest, ruff, nbstripout, JupyterLab, VS Code settings, and a deny rule that stops Claude's edit tools in `old/`.
- **2026-11-03:** `miss-lenses` done: every player-game scorecard shows where the model misses, through a dated lens list (`pcf.validation.misses`, `pcf misses`). The misses of every baseline come from playing time, team scoring and QB efficiency, not from pre-game tags, so the next expert is `participation` or team scoring. Reviewed each season and on each important new model, and every report is dated (CEO).
- **2026-11-03:** Ways of working added to the charter: discovery and confirmation loops, `projects/IDEAS.md` for hypotheses, "Where it misses" and "The case against" in the results template, and a CEO spot-check before every merge. New idea: `miss-lenses`.
- **2026-11-02:** `baselines` done: eight yardsticks as variants of one project (decision 0012): three points averages and a lasso for any scoring, FantasyPros ECR as points (a new `player_game` part that never ranks a game kicked off before its snapshot), and the no-vig closing line at a new kickoff moment for benchmarks. ECR beats every box-score baseline, so it is the weekly fantasy product's bar; the closing line is calibrated. CEO approved D1–D9.
- **2026-11-02:** `validation-harness` done: one expert contract, the `as_of` gateway, prediction moments at the three weekly runs (CEO decision 1C, decision 0010), features defined per moment (decision 0011), walk-forward backtests, scores and "beats", signal and no-noise tests, calibration and coverage, leakage checks 1–10 each caught by a planted leak, sanity rules and an HTML scorecard (`pcf backtest <id>`). Betting evaluation and the live-vs-backtest gap wait for odds and the ledger (CEO decision 2A).
- **2026-11-01:** `tag-tables` done: 52 tags and 11 references on plays, a new `drive` table, team-games and player-games, each with one versioned rule, a football timing and a rate band (`docs/TAGS.md`). Situation tags use score and clock (CEO decision 1A). On the way: 2000–2005 night kickoffs fixed (they were 12 hours early).
- **2026-11-01:** `experiment-tracking` done: every model trains through `pcf.core.tracking` (local MLflow), registration needs passing leakage checks, and the champion changes only by a merge the CEO approves (CEO decision 1A, decision 0009). `pcf ui` opens the browser view.
- **2026-10-31:** Follow-up to `grain-tables` (F15): players off the 53-man roster are dropped from the 2025+ daily depth charts before labelling; 2025–2026 `player_play` and `player_game` rebuilt.
- **2026-10-31:** `grain-tables` done: `game`, `team_game`, `play`, `player_play` and `player_game`, saved as parts with their own known-at times (decision 0008) and read back as of any moment. `player_game` holds the whole 53-man roster (CEO decision 1A). Three leaks closed: game-day inactives, playoff matchups, and pre-2016 roster statuses.
- **2026-10-31:** `timeline` done: kickoff times, week windows, offseason phases (a small dates file, CEO decision 1A) and a known-at rule for every nflverse dataset. The injury rule was too early for 6–7% of recent reports and is fixed.
- **2026-10-31:** `cleaning-port` done: the old slot functions copied and golden-tested, then improved (time-ordered depth, 2025+ daily charts, a real slot for players missing from a chart, `special` from ~5% to under 0.03%), plus standardizing functions for every nflverse source.
- **2026-10-30:** `data-layer` done: PCF keeps its own copy of nflverse (36 datasets, 786 MB) with `pcf refresh`, a manifest, revision reports, and daily state change logs into `pcf-data` (decision 0007).
