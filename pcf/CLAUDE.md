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

Dependencies point down, or sideways within a layer (for example, context feeds VOE). They never form a cycle. The actual dependency graph lives in `ARCHITECTURE.md`.

## Non-negotiable rules

- **a. `old/` is read-only.** Reuse ideas and functions by rewriting them in `pcf/`.
- **b. Free data only.** nflreadpy is the backbone. No paid sources and no manually downloaded CSVs. Where free history doesn't exist (e.g. player-prop lines), we collect it ourselves from now on.
- **c. Point-in-time.** No feature may use information that was unavailable before kickoff. Stacked models leak easily, and leaked backtests look great and then fail live.
- **d. Every model ships with** a backtest, a calibration check and an uncertainty estimate.
- **e. Versioned handoffs.** Higher layers read lower-layer outputs only from saved, versioned results, never by refitting on the fly. In training, lower-layer outputs used as features must be out-of-fold.
- **f. No hardcoded paths.** Everything is configured in one place.
- **g. Data stays out of git**, except small final outputs (e.g. start/sit advice).
- **h. Football sanity check.** Results that defy football logic get flagged, not shipped.
- **i. Notebooks are for exploring only.** Reusable code lives in the package.
- **j. Modularity.** Before writing new code, check the shared package for something that already does it. When writing something reusable, put it in the shared package so new and parallel projects reuse it. Flag duplication when you see it.
- **k. Simple first.** Every complex technique is tested against a cheap, simple baseline (e.g. a rolling average, a linear model, the Vegas line, ECR). If it doesn't clearly beat the baseline, the simple version ships.
- **l. Questions come with context, simple to detailed.** When Claude asks the CEO a question, it gives enough context to answer it, in this order: the question in one line → why it matters in plain language → the options and tradeoffs → technical detail, only if needed.

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

Every new mini-project, sub-problem, feature, model or domain follows these steps:

1. **Brainstorm** the idea together.
2. **Executive brief:** a one-pager the CEO helps write. It covers the idea or question, goals, assumptions, inputs, outputs, football context, technical possibilities and validation criteria.
3. **Build** the code and **validate** the results against the brief's criteria (rules c, d, k).
4. **Technical results:** a one-pager by Claude. It covers what the outputs mean technically, their limitations, and future possibilities. It lists open questions for the CEO to answer.
5. **Update the roadmap.**

## Definition of done

A mini-project is done when:
- [ ] The executive brief was agreed before building.
- [ ] Reusable code is in the package, with tests. Notebooks only explore.
- [ ] The point-in-time check passes: no feature uses post-kickoff information.
- [ ] The model beats its simple baseline, or the simple baseline ships instead.
- [ ] A backtest, a calibration check and an uncertainty estimate are reported.
- [ ] Outputs are saved, versioned, and readable by higher layers.
- [ ] Results pass the football sanity check.
- [ ] The technical results one-pager is written and the CEO's open questions are answered.
- [ ] The roadmap is updated and the CEO approved the merge.

## Where things live

Items marked *(planned)* don't exist yet. `ARCHITECTURE.md` will define the code layout.

```
pcf/
  CLAUDE.md           ← this charter
  docs/               (planned) project-wide docs, linked below
    decisions/        (planned) one short note per technical decision, with the reason
  projects/<name>/    (planned) each mini-project's executive brief and technical results
  <layer folders>/    (planned) each with its own short CLAUDE.md
```

## Further reading (to be written)

- `docs/VISION.md`: the full vision, in the CEO's words
- `docs/ROADMAP.md`: what we're building now, next and later; current status
- `docs/DATA_SOURCES.md`: every source, how it updates, known gaps
- `docs/ARCHITECTURE.md`: code layout, storage, dependency graph, automation
- `docs/VALIDATION.md`: backtest, calibration, uncertainty and leakage standards
- `docs/OLD_INVENTORY.md`: what in `old/` is worth reusing, and where it went
- `docs/CONVENTIONS.md`: code style and naming
- `docs/GLOSSARY.md`: shared terms (EPA, VOE, CLV, ECR…)
