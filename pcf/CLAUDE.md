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
- **g. Data stays out of git**, except small final outputs (e.g. start/sit advice). **The one exception is data we collect that can't be re-downloaded** (betting lines, the prediction ledger). It lives in the private `jackdepree/pcf-data` repo, never in this public one. API keys live in `pcf/.env` (gitignored) and in GitHub Actions secrets, never in code.
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

**Roles.** The CEO owns the vision, product calls and football calls. Claude acts as the principal engineer and data scientist and owns technical calls: code structure, refactors, libraries, and model choice within a layer. Claude logs the reasoning behind technical calls in `docs/decisions/`.

**Assumptions first.** For any idea the CEO brings, Claude first states its assumptions, limitations and advantages, plus a simpler alternative if there is one. Then Claude recommends, and builds on the CEO's go. Claude pushes back when an idea won't work as stated.

**Brainstorm, then build.** For design decisions, Claude lays out options: the strong choices, plus a tempting but bad one that shows what separates good from bad. The CEO picks, then Claude writes or builds.

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

1. **Idea:** brainstorm it together and add it to the registry.
2. **Exploring:** a time-boxed first look. Is the data there? Is there any signal at all? What does it assume? Claude writes a short exploration note ending in go / no-go. **It's a go unless there's literally zero signal.** The production version will be more thorough.
3. **Brief:** a one-pager the CEO helps write ([template](projects/_templates/BRIEF.md)). It covers the question, why it matters, assumptions, goals, what success and failure look like as tests, inputs and outputs, how it will be used, and **what it builds on**: earlier projects' findings, outputs and models, and what was already tried. Read [`projects/KNOWLEDGE.md`](projects/KNOWLEDGE.md) first.
4. **Building:** production-level code in the package, climbing the ladder (rule k), with every run tracked in MLflow.
5. **Validating:** check the results against the brief's tests (rules c, d, k).
6. **Done:** Claude writes the technical results one-pager ([template](projects/_templates/RESULTS.md)) so no later project redoes the work. It covers numbered findings, pitfalls, what could be improved, what we didn't look at, what not to redo, and the **interface card** (inputs, outputs, level of detail, interval, cadence, known-at, how to use it, where it feeds). It lists open questions for the CEO to answer. Then the findings go into `KNOWLEDGE.md`, and the roadmap and registry are updated.

Each project's notes live in `projects/<id>/`: `EXPLORATION.md`, `BRIEF.md`, `RESULTS.md`.

## Definition of done

A mini-project is done when:
- [ ] The executive brief was agreed before building.
- [ ] Reusable code is in the package, with tests. Notebooks only explore.
- [ ] The point-in-time check passes: no feature uses post-kickoff information.
- [ ] Experts show held-out signal over a shuffled null and don't add noise. Products beat their simple baselines, or the baseline ships instead.
- [ ] A backtest, a calibration check and an uncertainty estimate are reported.
- [ ] Outputs (live and walk-forward history) are saved in the standard schema, versioned, and readable by higher layers. The champion model is registered in MLflow.
- [ ] Results pass the football sanity check.
- [ ] The technical results one-pager is written, its findings are in `KNOWLEDGE.md`, its interface card is in the registry, and the CEO's open questions are answered.
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
    _templates/       BRIEF.md and RESULTS.md templates
    <id>/             each project's EXPLORATION.md, BRIEF.md, RESULTS.md, explore/
  src/pcf/            (planned) the package: core, data, experts, composites, products, validation
  tests/              (planned)
  data/               (planned, gitignored) raw, interim, tables, features, outputs, mlflow, ledger, logs
```

## Further reading

- [`docs/VISION.md`](docs/VISION.md): the north star, in the CEO's words. Read it when a tradeoff isn't settled by the rules above.
- [`docs/ROADMAP.md`](docs/ROADMAP.md): now / next / later, milestones, CEO decisions, dead ends

- [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md): every source, its tier, years, update timing, **known-at rule**, how ids join, and known gaps. Read it before using any data.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): code layout, storage, the `as_of` gateway and leakage checks, the expert contract, MLflow, the knowledge tree, the ladder, and how it runs. Read it before writing package code.

To be written:

- `docs/VALIDATION.md`: backtest, calibration, uncertainty and leakage standards
- `docs/OLD_INVENTORY.md`: what in `old/` is worth reusing, and where it went
- `docs/CONVENTIONS.md`: code style and naming
- `docs/GLOSSARY.md`: shared terms (EPA, VOE, CLV, ECR…)
