# Brief: Miss lenses (`miss-lenses`)

> A short, fixed list of ways to split every model's misses, so each RESULTS.md shows where a model goes wrong without drowning in 52 tags (CEO, 2026-11-03). Exploration: [EXPLORATION.md](EXPLORATION.md). **Key decisions D1–D6 are at the end of this page, each to approve or deny.**

**Status:** draft, for the CEO · **Layer:** 0, foundation (Phase 0) · **Cadence:** n/a (runs on any model's walk-forward history)

## The question
Which few lenses explain the most of our models' misses, and how should every project report them, the same way each time?

## Why it matters
- **It's the discovery loop's main source of new problems** (CLAUDE.md, "Two loops"). Each pattern in the misses is a candidate feature or expert.
- **Looking at every tag is noise** (the CEO's caveat): 22 pre-game lenses explain under 0.6% each (F1).
- **It already says what to build next:** the misses come from playing time and team scoring (F2).

## Terms
- **Standard terms used:** miss lens, walk-forward history, pinball loss, discovery loop ([`GLOSSARY.md`](../../docs/GLOSSARY.md)).
- **New terms:**
  - **Miss:** actual minus projected (the model's `mean`). Positive means the model was too low.
  - **Bias share:** how much of the squared miss a per-group correction removes, learned on other seasons (cross-fitted).
  - **Spread share:** the same for the size of the miss.
  - **Diagnostic lens:** a lens known only after the game (snap share, team points). It explains a miss; it can never be a feature.

## Builds on
| Project | What we use | Why |
|---|---|---|
| `baselines` | The lasso's and ECR's walk-forward histories | The first misses to study, and the bar every product meets |
| `tag-tables` | Pre-game player and team tags, with their football timing | Candidate lenses; only "before the game" tags may be pre-game lenses |
| `grain-tables` | Depth, snaps, injury reports, game results | The non-tag lenses |
| `validation-harness` | The scorecard, week-block resampling | Where the section lands, and how intervals are drawn |
| Exploration F1–F7 | Which lenses matter | The list in D1 |

**Already tried:** nothing like this in `old/`.

## Assumptions
- **Two baselines speak for later models.** The lasso and ECR are the only models so far. A real expert may miss in new ways; the auto-flagged tags (D1) and a yearly review (D5) catch that.
- **The mean is what we judge.** Lenses look at the projection's average miss and miss size, not the ranges. Coverage by group is already on the scorecard.

## Goals
1. A fixed lens list, agreed once and reviewed each offseason.
2. One function that reports any model's misses through those lenses, plus the tags that stand out.
3. That report on every scorecard, so RESULTS.md copies it rather than computing it.

## Tests
- **Success looks like:**
  - the report runs on any player-game history in under a minute;
  - on the lasso and ECR, it reproduces the exploration's numbers;
  - a planted lens (a fake tag that is truly off by 2 points) is found, and a planted noise tag with many small groups is not;
  - diagnostic lenses are labelled "after the game" everywhere they appear.
- **Failure looks like:** a report so long nobody reads it, or one that ranks noise.
- **Baselines:** none (it's a tool). **Seasons:** whatever the model's history covers. The vault stays shut.

## Inputs and outputs
- **Inputs:** a walk-forward history (`mean`, `q10`, `q90`) and the tables through `load` (lenses are read after the fact, for diagnosis, never by a model).
- **Outputs:** `pcf.validation.misses`: a lens table (lens, before/after, bias share, spread share, top group, its average miss and 90% interval), and a "Where it misses" section on the scorecard.

## How it will be used
Every model's RESULTS.md shows the fixed lenses plus up to 5 tags that stand out. Each pattern worth chasing becomes a line in IDEAS.md. The first use is now: F2 points the next projects at playing time and team scoring.

## Plan
1. `pcf.validation.misses`, with the planted-lens tests.
2. The scorecard section.
3. Rerun on the lasso and ECR; RESULTS.md.

Time box: one session.

---

## Key decisions (approve or deny each)

**D1. The fixed lenses (yours).** For player-game models:
- **Before the game:** position, depth-chart rank (1, 2, 3+, unlisted) and week band (1, 2–4, 5–9, 10–14, 15+).
- **After the game (diagnostic):** snap share (under 25%, 25–50%, 50–75%, 75%+), team points (under 17, 17–23, 24–30, 31+) and final margin (won by 14+, within 13, lost by 14+). For QBs, also a completion-above-expected game.
- **Plus at most 5 other tags** whose average miss is clearly not zero, largest first (as the template already says).
- Game-level models (sides, totals) get their own short list when the first one is built.
- *Alternative:* before-game lenses only. Cleaner, since everything shown could be a feature. But it hides where the misses really come from (F2): nothing before the game explains much (F1).

**D2. How a lens is scored (technical).** Bias and spread shares, cross-fitted on even and odd seasons (F7), and the top group with a week-resampled interval.
- *Alternative:* the plain in-sample share. It's simpler, but a lens with many small groups always looks useful.

**D3. Where it lives (technical).** A function in `pcf.validation`, with the section on every player-game scorecard, not a notebook each project reruns.

**D4. After-game lenses are labelled diagnostic everywhere (technical).** The report marks them, and the tags' football timing decides which list a tag goes in. The leakage checks already stop a model from reading them.

**D5. Reviewed once a season (yours).** Each offseason, rerun the exploration on the champion models and change the list only if a lens moves into or out of the top ranks. The change is a dated line in this project's RESULTS.md.

**D6. Rejected (✗):** pick each project's lenses after seeing its misses. It reads well, but then every report shows its most flattering or most dramatic splits, and the reports stop being comparable.

## Recommended next, from the exploration (yours)
Not a decision for this project, but its main result: **the next expert should be `participation` (a player's share of snaps) or a team-scoring expert (`team-efficiency` with `pace`).** Those are the two parts of the miss nothing predicts well yet (F2). Role changes matter for the lasso but ECR already handles them (F4), so `vacated-opportunity` comes later.
