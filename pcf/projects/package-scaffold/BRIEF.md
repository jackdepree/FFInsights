# Brief: Package scaffold and config (`package-scaffold`)

> An infrastructure project: a short brief, no football calls. Light exploration: [EXPLORATION.md](EXPLORATION.md).

**Status:** draft (2026-10-30) · **Layer:** foundation (Phase 0) · **Cadence:** —

## The question
Can a new PCF project start writing tested, configured, reproducible code on day one, without setting anything up itself?

## Why it matters
Every other project builds on this: the data layer, MLflow, the experts. Without it, each one would invent its own setup, which is what happened in `old/`.

## Terms
- **Standard terms used:** none beyond `docs/GLOSSARY.md`.
- **New terms:** none.

## Builds on
| Project | What we use | Why |
|---|---|---|
| `docs/ARCHITECTURE.md` | the code layout, tooling table | This project makes it real |
| `docs/CONVENTIONS.md` | style, naming, tests, notebooks | Enforced by the tools set up here |
| `odds-collection` | its `PCF_DATA_DIR` variable | Config keeps honoring it, so the collector works unchanged |

**Already tried:** `old/` had no package, hardcoded `C:\Users\Jack\...` paths and notebooks with outputs (OLD_INVENTORY.md lessons).

## Assumptions
- Python 3.12, managed by uv (already installed), matching GitHub Actions.
- The environment lives in `pcf/.venv/` (uv's default, gitignored).
- Local data lives in `pcf/data/` on the C: drive (CEO, 2026-10-30), a few GB over time (EXPLORATION.md).

## Goals: what gets built
1. **The package:** `pcf/pyproject.toml`, `uv.lock`, and `src/pcf/` with the layer folders from ARCHITECTURE.md (`core`, `data`, `experts`, `composites`, `products`, `validation`). Each layer folder gets a short `CLAUDE.md` saying what belongs there.
2. **Config:** `pcf/config.toml` (paths, seasons from VALIDATION.md, random seed) and `src/pcf/config.py`, the only place paths are resolved. Keys are read from `pcf/.env` on demand. The `PCF_DATA_DIR` override still works.
3. **Logging that can't leak keys:** a logger that masks any value from `.env` if it ever appears in a message.
4. **The `pcf` command:** `uv run pcf info` shows the resolved paths and config. Later projects add commands.
5. **Tooling:** pytest (with a `network` marker, skipped by default), ruff, nbstripout (strips notebook outputs on every commit), JupyterLab and a Jupyter kernel, all as dev dependencies.
6. **VS Code:** workspace settings pointing at `pcf/.venv`, ruff as the formatter, and recommended extensions.
7. **The `old/` guardrail:** `.claude/settings.json` denies Claude's file-editing tools inside `old/`.
8. **A short `pcf/README.md`** for humans: set up, run tests, open JupyterLab.

**Not in this project:** MLflow (`experiment-tracking`), data loading (`data-layer`), registry checks (`registry-tooling`), moving the odds scripts (`odds-collection`), and the Task Scheduler (`weekly-run`).

## Tests
- **Success looks like:**
  - From a fresh clone, `uv sync` then `uv run pytest` passes, with no internet needed for tests.
  - `uv run ruff check` and `uv run ruff format --check` are clean.
  - `uv run pcf info` prints paths that resolve inside `pcf/`, and they follow `PCF_DATA_DIR` when it's set.
  - Tests prove keys never appear in `repr(config)` or in log output.
  - Committing a notebook with outputs stores it without outputs.
  - The deny-rule syntax is proven on a scratch folder first, then applied to `old/`. Claude's edit tools are refused there.
  - `uv run jupyter lab` opens, and its kernel imports `pcf`.
- **Failure looks like:** any of these needing a manual step that isn't in the README.

## Inputs and outputs
- **Inputs:** none (no data is read).
- **Outputs:** the package skeleton, config and tooling. No data.

## How it will be used
Every later project starts with `uv sync` and puts its code into the matching layer folder.

## Plan
No ladder (no model). About one session: build, test, results page, then the CEO's merge.
