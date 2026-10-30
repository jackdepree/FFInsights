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

The first experts: **Team Elo · opponent-adjusted efficiency · pace & play-calling · environment · stabilization · Context (in-season) · participation & snaps**

## Later

- **The remaining experts:** line play, game script, Context (retrospective), VOE (in-season), VOE (retrospective), opportunity quality, vacated opportunity, touchdowns, aging, injury & fatigue, roles & archetypes, schemes v2, QB talent, prospects, kicker & DST, market, crowd, news
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

- [ ] **Set up the collector:** create the private `pcf-data` repo, a fine-grained token, and the `PCF_DATA_TOKEN` and `ODDS_API_KEY` secrets. Then approve merging `pcf/foundation-docs` into `main`, since schedules only run from `main`.

Decided:
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

## Changelog

One dated line each time something reaches Done, or the roadmap changes shape.

- **2026-10-28:** Charter (`CLAUDE.md`), `VISION.md`, this roadmap and the project registry created.
- **2026-10-30:** `DATA_SOURCES.md` written. Experts now declare a `cadence` (rule m). Context and VOE are each split into in-season and retrospective experts, because play-level participation is published only after the season.
