# Brief: <project name> (`<id>`)

> Written with the CEO **before building**. One page. Copy to `projects/<id>/BRIEF.md`.
> Before writing it, read `projects/KNOWLEDGE.md` and the RESULTS.md of every project this one depends on.

**Status:** draft | agreed (date) · **Layer:** expert / composite / product · **Cadence:** in_season / retrospective / offseason_events

## The question
One or two sentences, in plain football language.

## Why it matters
What it unlocks: which products or experts get better, and how a user would notice.

## Terms
- **Standard terms used:** list them, linking to `docs/GLOSSARY.md` (e.g. EPA, target share, CLV).
- **New terms this project introduces:** define each one here, in plain language: what it means, how it's computed, and why we need it. They move into the glossary when the project is done.

## Builds on
| Project | What we use | Why |
|---|---|---|
| `<id>` | outputs `<quantity>` / model version / finding `<id>#F2` | |

**Already tried:** what earlier projects or dead ends tell us not to repeat.

## Assumptions
What has to be true for this to work: football assumptions and data assumptions. Each one gets tested or flagged.

## Goals
What we're looking for.

## Tests
The defaults are in `docs/VALIDATION.md`. List only what's specific to this project, and any default it changes (with the reason).
- **Success looks like:** the specific results that would mean it worked (e.g. "beats the shuffled null on 2016–2024 held-out weeks; q10–q90 coverage 75–85%").
- **Failure looks like:** the results that would mean it didn't, or that it should be a dead end.
- **No-noise target** (experts): the downstream target and simple baseline this expert is tested against. **CEO approves.**
- **Baselines** (composites and products): which ones from VALIDATION.md section 6.
- **Seasons:** training start, and the vault (2025 by default; props use 2026 live).

## Inputs and outputs
- **Inputs:** tables and expert outputs, each with its known-at rule.
- **Outputs:** quantity, level of detail (e.g. player-game), and uncertainty.

## How it will be used
Where its outputs go, and what decision they help with.

## Plan
Which rungs of the ladder are planned (`docs/ARCHITECTURE.md`), and the time box.
