# Roadmap

> **Status lives in [`projects/registry.yaml`](../projects/registry.yaml).** This page is the readable view: what's now, next and later, plus milestones, decisions and history. If this page and the registry disagree, the registry wins and this page gets fixed.
> Anything can be added anywhere at any time. A new expert is a new registry entry that goes through the lifecycle in [`CLAUDE.md`](../CLAUDE.md).

## Phases

| Phase | What | Notes |
|---|---|---|
| **0: Foundation** | Betting-line collection · package and config · data layer · NFL timeline · cleaning functions · tables at every level of detail · tag tables · validation harness · baselines · prediction ledger · registry tooling | Everything else stands on this |
| **1: Experts** | Every expert model, each focused on one part of football | No sub-phases. The order comes from dependencies in the registry. |
| **2: Composites** | Team strength · player opportunity · game simulator · outcome distributions | Combine the experts |
| **3: Products** | Fantasy projections (all formats) · start/sit · props · DFS/best ball · dynasty · futures · scorecards · reports · builder view | The final outputs |
| **4: Automation & distribution** | Weekly run · emailed reports · dashboard | A basic data refresh exists from Phase 0 |
| **5: Public** | Website and subscriptions | Only once the track record earns it |

## Now

Phase 0, starting with the one item that can't wait:

1. **Betting-line collection** (`odds-collection`). Every week of lines we don't collect is lost for good. Free odds-API tiers and public JSON endpoints only, no scraping.
2. Package scaffold and config · data layer · NFL timeline · cleaning-function port
3. Tables at every level of detail · tag tables · validation harness · baselines · prediction ledger · registry tooling

## Next

The first experts: **Team Elo · opponent-adjusted efficiency · pace & play-calling · environment · stabilization · Context v2 · participation & snaps**

## Later

- **The remaining experts:** line play, game script, VOE v2, opportunity quality, vacated opportunity, touchdowns, aging, injury & fatigue, roles & archetypes, QB talent, prospects, kicker & DST, market, crowd, news
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

- [ ] **Expert catalog:** I put every ⭐ from the brainstorm on the roadmap and every ○ in the parking lot. Confirm, or move items.
- [ ] **Schemes:** parked as `schemes-v2` (a retry from the roles angle), or retired for good?

## Parking lot

Good ideas not scheduled yet, listed in the registry with `horizon: parking`:
- play-caller tendencies
- referee crews
- coverage matchups
- contract & motivation
- schemes v2
- hot hand (exploration only)
- VOE as a conditional diffusion model

## Dead ends

| Project | What we tried | Why it failed | What would make us retry |
|---|---|---|---|
| `schemes-v1` (`old/code/Schemes_Model.ipynb`) | Over-expectation features → PCA → clustering into team schemes | Little usable signal | A new angle, most likely roles & archetypes first (`schemes-v2`) |

## Changelog

One dated line each time something reaches Done, or the roadmap changes shape.

- **2026-10-28:** Charter (`CLAUDE.md`), `VISION.md`, this roadmap and the project registry created.
