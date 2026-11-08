# PCF: Principal Component Football

This is the charter for every task in `pcf/`. It holds only what is true for *every* task. Everything else gets one line and a link at the bottom.

## Mission

PCF is an in-house NFL analytics system that does what PFF, FantasyPros, ESPN Analytics and Next Gen Stats do. It takes in raw football data, compresses it into meaningful structure, and turns that structure into predictions with honest uncertainty. The predictions cover fantasy (any scoring, any format: redraft, dynasty, best ball, DFS) and betting (sides, totals, props, futures). It runs on free data, updates itself every week, and is built properly for the 2027 season.

Audience: the CEO and a few friends now. Possibly a public subscription product later.

**Success means:**
- **Beating the market:** positive closing line value against sportsbooks (FanDuel preferred).
- **Accurate projections:** at least as accurate as FantasyPros expert consensus (ECR).
- **Honest probabilities:** well calibrated, with uncertainty estimates that are themselves trustworthy. A promising but uncertain prediction should be *known* to be uncertain.

## Layer map

PCF is a hierarchical mixture of experts. Each expert model compresses one part of football, and its outputs become features for the layers above. **We build from the bottom up.**

| Layer | Name | What lives here |
|---|---|---|
| 0 | **Data** | Raw nflreadpy (nflverse) data, cleaned into point-in-time tables |
| 1 | **Experts** | Context (situation and pressure per play) · VOE (value over expected) · injury & fatigue · participation & snaps · roles & archetypes · aging & regression · news & off-field |
| 2 | **Composites** | Team strength · player opportunity · win / TD / contract probabilities |
| 3 | **Products** | Fantasy projections and start/sit (any scoring and format) · props · futures · reports and dashboards |

Dependencies point down, or sideways within a layer (for example, context feeds VOE). They never form a cycle. The actual dependency graph is `depends_on` in [`projects/registry.yaml`](projects/registry.yaml). [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) explains how the code uses it.

## Non-negotiable rules

- **a. `old/` is read-only.** Reuse ideas and functions by rewriting them in `pcf/`.
- **b. Free data only.** nflreadpy is the backbone. No paid sources and **no recurring manual downloads**. A one-time download for a research case study is fine (e.g. Big Data Bowl). Where free history doesn't exist (e.g. player-prop lines), we collect it ourselves from now on.
- **c. Point-in-time.** No feature may use information that was unavailable before kickoff. Stacked models leak easily, and leaked backtests look great and then fail live. Models read data only through the `as_of` gateway, and the stacked leakage checks in `docs/ARCHITECTURE.md` run automatically on every model. We can almost never have too many: when in doubt, add another check.
- **d. Every model ships with** a backtest, a calibration check and an uncertainty estimate.
- **e. Versioned handoffs.** Higher layers read lower-layer outputs only from saved, versioned results, never by refitting on the fly. In training, lower-layer outputs used as features must come from the lower model's **walk-forward history**: made by a model trained only on data before that row. Never run today's best model over past rows to make training features.
- **f. No hardcoded paths.** Everything is configured in one place.
- **g. Data stays out of git**, except small final outputs (e.g. start/sit advice). **The one exception is data we collect that can't be re-downloaded** (betting lines, the prediction ledger). It lives in the private `jackdepree/pcf-data` repo, never in this public one. Tiny test fixtures (under 1 MB, public or synthetic rows) may live in `tests/fixtures/` (`docs/CONVENTIONS.md`). API keys live in `pcf/.env` (gitignored) and in GitHub Actions secrets, never in code.
- **h. Football sanity check.** Results that defy football logic get flagged, not shipped.
- **i. Notebooks are for exploring only.** Reusable code lives in the package.
- **j. Modularity.** Before writing new code, check the shared package for something that already does it. When writing something reusable, put it in the shared package so new and parallel projects reuse it. Flag duplication when you see it.
- **k. Simple first, no noise.** Every complex technique is tested against a cheap, simple version.
  - **Models climb a ladder:** baseline → linear/lasso → structured → trees → … (`docs/ARCHITECTURE.md`). A rung needn't reuse the previous rung's outputs, but it must use its **takeaways** (which features matter, collinearity, interactions), and say which ones it applied. The ladder stops when a rung doesn't beat the one below.
  - **Experts** must show real signal on held-out data: they beat a shuffled, signal-free version of themselves, and they don't add noise. They don't have to beat other models. Downstream feature selection decides whether they get used.
  - **Feature selection always happens inside the cross-validation folds**, never on the full dataset.
  - **Products** must beat simple baselines (e.g. a rolling average, a lasso, the Vegas line, ECR). If they don't, the simple version ships.
- **l. Questions come with context, simple to detailed.** When Claude asks the CEO a question, it gives enough context to answer it, in this order: the question in one line → why it matters in plain language → the options and tradeoffs → technical detail, only if needed.
- **m. Everything declares its timing.**
  - Every data source states when its data is known (`docs/DATA_SOURCES.md`).
  - Every expert, composite and product declares its `cadence` in the registry:
    - **in_season:** updates between games, and may use only data available live;
    - **retrospective:** updates between seasons, and may use post-season-only data such as participation;
    - **offseason_events:** updates when combine, free agency, trades or the draft happen.
  - When the same idea needs both cadences, it becomes two experts (e.g. `voe-live` and `voe-retro`).
  - A retrospective output feeds an in-season model only from *completed* seasons, as a prior.
  - "Play-level" or "within a game" describes the level of detail an expert works at, computed after the game. Live in-game prediction is still a non-goal (`docs/VISION.md`).

## How we work together

**Roles.** The CEO owns the vision, product calls and football calls, and brings the originality: football hunches and taste. Claude acts as the principal engineer and data scientist. It brings the conventional best practice and does the technical work: code structure, refactors, libraries, data, statistics, and model choice within a layer. The market and the consensus are already the average, so PCF's edge has to come from being different *and* right: the CEO's ideas make it different, and strict testing keeps it right (`docs/VISION.md`).

**Technical calls and taste calls.**
- **Technical calls:** Claude makes them and logs the reason in `docs/decisions/`. Before each merge, Claude lists the technical calls made on the branch so the CEO can veto any of them. It doesn't ask first.
- **Taste calls** (what we predict, what counts as success, which football idea to chase, what feels wrong): Claude asks for the CEO's instinct *before* giving its own view, so its recommendation doesn't anchor the choice.

**Starting a project: the usual way, analogies, then hunches.**
1. **Claude:** names the project, describes in 3–4 sentences how professionals usually do it, and gives 1–2 analogies from other fields to think with. No recommendation yet.
2. **CEO:** gives their hunches. Claude records them word for word in the brief.
3. **Together:** back and forth, using the analogies, to a draft brief and its success tests.
4. **Claude:** the exploration tests each hunch and gives each a verdict (held, failed or unclear, with numbers), adding analogies where they help explain what it found.
5. **CEO:** decides the direction from there, and the brief is agreed with whatever the exploration changed.

**Analogies.** When a problem is stuck or new, Claude brings an analogy from another field (physics, ecology, markets, other sports): not an answer, but a way to look at the problem. A pattern that works somewhere else may be hiding here too. Skip it when the football is clear enough on its own.

**Test it rather than argue it.** If a hunch costs less than about one session to check, Claude tests it instead of arguing against it, even when it expects the hunch to fail. Claude still says up front what it expects and why, so the result means something.

**Two tests for every new measure.** Whenever we build a new measure (a feature, a condition, or a way of summing up what happened, like a game's average win probability), Claude reports two things:
1. **Does it help this project's target** (for example, next game's margin)? That decides whether this project uses it.
2. **Is it consistent?** Does it repeat from week to week and season to season, and differ between teams rather than being the same for everyone? Measure it with `pcf.validation.consistency`.

Both kinds go in [`projects/CONSISTENCY.md`](projects/CONSISTENCY.md):
- **A consistent measure is kept even when it fails test 1.** It's something real about a team, so it may explain something else later.
- **An inconsistent one is marked noise**, so nobody builds on it, or so it's used deliberately as noise (CEO, 2026-11-07).

**The hunch scoreboard.** Every unconventional bet goes in [`projects/HUNCHES.md`](projects/HUNCHES.md): what the usual approach says, what we bet instead, how we tested it, and whether it held. Mostly the CEO's; Claude adds one when it notices we're going against convention. Over time it shows where the CEO's instinct beats the average and where to lean on the data.

**Assumptions first.** For any idea the CEO brings, Claude first states its assumptions, limitations and advantages, plus a simpler alternative if there is one. Then Claude recommends, and builds on the CEO's go. Claude pushes back when an idea won't work as stated.

**Brainstorm, then build.** For design decisions, Claude lays out options: the strong choices, plus a tempting but bad one that shows what separates good from bad. On taste calls, the CEO's instinct comes first. The CEO picks, then Claude writes or builds.

**Two loops: discover, then confirm.**
- **Discovery** is cheap and open: explorations, the CEO's hunches, the hypothesis log ([`projects/IDEAS.md`](projects/IDEAS.md)), and where each model misses. Its only bar is "is there any signal?" This is where new problems come from.
- **Confirmation** is strict: the harness, held-out weeks, the vault.
- A discovery result never counts as proof. The more ideas we try, the more the vault and the versions-tried count matter.

**Checks on Claude's work, before every merge:**
- **The case against:** Claude writes the strongest argument that the result is wrong or overstated (in RESULTS.md), so the CEO approves with it in view.
- **One spot-check:** the CEO picks one decision or finding, and Claude walks through it in depth: the rows, the alternative, what would change the answer.

**Needs CEO sign-off first:**
- a new layer or expert model
- changing what a target means
- adding a data source
- anything public-facing
- large technical changes (e.g. a new storage system, rewriting a shared module many projects depend on)

**Git.**
- Each mini-project gets its own branch.
- Claude commits freely on branches.
- The CEO reviews, and the branch merges to `main` only with the CEO's approval.
- `main` always works.
- Claude never pushes to `main` on its own.

## Mini-project lifecycle

Every new mini-project, sub-problem, feature, model or domain gets an entry in [`projects/registry.yaml`](projects/registry.yaml) and moves through these statuses: **idea → exploring → brief → building → validating → done** (or **parked** / **dead_end**).

1. **Idea:** Claude opens with the usual way and 1–2 analogies, the CEO gives their hunches, and together we draft the brief ("Starting a project" above). It goes in the registry. A hypothesis smaller than a project goes in [`projects/IDEAS.md`](projects/IDEAS.md) instead, and graduates to the registry if a cheap check finds something.
2. **Exploring:** a time-boxed first look. Is the data there? Is there any signal at all? What does it assume? It tests each of the CEO's hunches and gives each a verdict. Claude writes a short exploration note ending in go / no-go. **It's a go unless there's literally zero signal.** The production version will be more thorough.
   - **Infrastructure projects** (scaffold, tracking, tooling) have no signal to find, so they get a **light exploration** instead: a quick descriptive profile of the data they touch (rows, columns, date ranges, level of detail, size). Small, but not skipped.
3. **Brief:** a one-pager the CEO helps write ([template](projects/_templates/BRIEF.md)), drafted at the idea stage and agreed after the exploration. It opens with the usual way, the analogies and the CEO's hunches, then covers the question, why it matters, **the terms** (standard ones linked to the glossary, new ones defined), assumptions, goals, what success and failure look like as tests, inputs and outputs, how it will be used, and **what it builds on**: earlier projects' findings, outputs and models, and what was already tried. Read [`projects/KNOWLEDGE.md`](projects/KNOWLEDGE.md) first.
4. **Building:** production-level code in the package, climbing the ladder (rule k), with every run tracked in MLflow.
5. **Validating:** check the results against the brief's tests (rules c, d, k).
6. **Done:** Claude writes the technical results one-pager ([template](projects/_templates/RESULTS.md)) so no later project redoes the work. It covers numbered findings, where the model misses (a short fixed list of lenses), the case against the result, pitfalls, what could be improved, what we didn't look at, what not to redo, and the **interface card** (inputs, outputs, level of detail, interval, cadence, known-at, how to use it, where it feeds). It lists open questions for the CEO to answer. Then the findings go into `KNOWLEDGE.md`, new hypotheses into `IDEAS.md`, hunch verdicts into `HUNCHES.md`, new measures into `CONSISTENCY.md`, and the roadmap and registry are updated.

Each project's notes live in `projects/<id>/`: `EXPLORATION.md`, `BRIEF.md`, `RESULTS.md`.

## Definition of done

A mini-project is done when:
- [ ] The executive brief was agreed before building.
- [ ] Reusable code is in the package, with tests. Notebooks only explore.
- [ ] The point-in-time check passes: no feature uses post-kickoff information.
- [ ] Experts show held-out signal over a shuffled null and don't add noise. Products beat their simple baselines, or the baseline ships instead.
- [ ] A backtest, a calibration check and an uncertainty estimate are reported, with the vault result and the validation scorecard (`docs/VALIDATION.md`).
- [ ] Outputs (live and walk-forward history) are saved in the standard schema, versioned, and readable by higher layers. The champion model is registered in MLflow.
- [ ] Results pass the football sanity check.
- [ ] The technical results one-pager is written, its findings are in `KNOWLEDGE.md`, its new terms are in `GLOSSARY.md`, its interface card is in the registry, and the CEO's open questions are answered.
- [ ] The case against is written, and the CEO's spot-check is done.
- [ ] Every hunch in the brief has a verdict in `HUNCHES.md`, and the CEO has seen the branch's technical calls.
- [ ] The registry and roadmap are updated, and the CEO approved the merge.

## Where things live

Items marked *(planned)* don't exist yet. The full code layout is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

```
pcf/
  CLAUDE.md           ← this charter
  docs/               project-wide docs, linked below
    decisions/        one short note per technical decision, with the reason
  projects/
    registry.yaml     ← single source of truth for every project's status, dependencies and interface
    KNOWLEDGE.md      ← every finding from every finished project. Read before any brief.
    IDEAS.md          hypotheses to test: football hunches and patterns in model misses
    HUNCHES.md        the scoreboard of unconventional bets: what we tried against convention, and whether it held
    CONSISTENCY.md    every measure we've built: does it repeat week to week and season to season (signal), or not (noise)?
    _templates/       BRIEF.md and RESULTS.md templates
    <id>/             each project's EXPLORATION.md, BRIEF.md, RESULTS.md, explore/
  src/pcf/            the package: core, data, experts, composites, products, validation (setup: README.md)
  tests/              pytest, mirroring src/pcf/
  data/               (gitignored) raw, interim, tables, features, outputs, mlflow, ledger, logs
```

## Further reading

- [`docs/VISION.md`](docs/VISION.md): the north star, in the CEO's words. Read it when a tradeoff isn't settled by the rules above.
- [`docs/ROADMAP.md`](docs/ROADMAP.md): now / next / later, milestones, CEO decisions, dead ends
- [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md): every source, its tier, years, update timing, **known-at rule**, how ids join, and known gaps. Read it before using any data.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): code layout, storage, the `as_of` gateway and leakage checks, the expert contract, MLflow, the knowledge tree, the ladder, and how it runs. Read it before writing package code.
- [`docs/VALIDATION.md`](docs/VALIDATION.md): the bar every model must clear: the vault, walk-forward backtests, scores, what "beats" means, signal and no-noise tests, baselines, calibration, betting evaluation, leakage thresholds, sanity review, the scorecard. Read it before validating anything.
- [`docs/OLD_INVENTORY.md`](docs/OLD_INVENTORY.md): the salvage map of `old/`: the core models' goals, the functions to port (copy, test, then improve), old data for research only, and lessons learned. Read it before touching anything `old/` did.
- [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md): code style, naming (ids, columns, units), how functions behave, tests, notebooks, git. Read it before writing code.
- [`docs/GLOSSARY.md`](docs/GLOSSARY.md): every term, with its nflverse column and how PCF uses it. Read it when a term is unclear.
