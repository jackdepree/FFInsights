# Results: Package scaffold and config (`package-scaffold`)

> An infrastructure project: no model, so no MLflow experiment, ladder or vault.

**Date:** 2026-10-30 · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** none (built later by `experiment-tracking`)

## In short
The `pcf` package, its config, a logger that masks keys, the `pcf info` command and the tooling are built. All eight goals in the brief are done. Every success test passed except one I couldn't run myself: opening JupyterLab in a browser. The kernel was checked headlessly instead. Building it turned up two tool defaults that would have quietly touched files they shouldn't (F7, F8).

| Test from the brief | Result |
|---|---|
| Fresh clone: `uv sync`, then `uv run pytest` passes offline | **Pass.** A copy of exactly the files git would commit (no `.venv`, `.env` or data): 35 passed. Network tests are skipped by default. |
| `ruff check` and `ruff format --check` are clean | **Pass** (18 files). |
| `pcf info` paths resolve inside `pcf/` and follow `PCF_DATA_DIR` | **Pass.** Checked by tests and in the fresh copy. |
| Keys never appear in `repr(config)` or log output | **Pass.** Tests cover messages, tracebacks, `.env` values and Actions-style environment variables. `pcf info` lists key names, never values. |
| A notebook committed with outputs is stored without them | **Pass.** The staged copy had empty outputs and null execution counts. Stripping applies only to notebooks in `pcf/` (`git check-attr` shows `unspecified` for `old/`). |
| Deny rule proven on a scratch folder, then applied to `old/` | **Pass.** `Edit(/pcf/_denytest/**)` refused a Write, and no folder was created. The same syntax now reads `Edit(/old/**)`, and a test keeps it there. |
| `uv run jupyter lab` opens, and its kernel imports `pcf` | **Partly checked.** JupyterLab 4.6.5 is installed, and a notebook run headlessly through the kernel printed `pcf` 0.1.0. The browser UI hasn't been opened yet. The CEO's first `uv run jupyter lab` is that check. |
| Football sanity | Not applicable (no football output). |

## Terms
No new terms. Tool names (uv, ruff, pytest, nbstripout) are standard; `README.md` says what each is for.

## Findings
F1–F6 came from the light exploration. F7–F9 came from the build.

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| F1 | FTN `date_pulled` is a re-pull date. For history, FTN is known at kickoff + 14 days. | [EXPLORATION.md](EXPLORATION.md) | strong | FTN charting |
| F2 | Snap counts start in 2013. | [EXPLORATION.md](EXPLORATION.md) | strong | snaps |
| F3 | Depth charts switch to daily `dt` snapshots in 2025, with no season or week. | [EXPLORATION.md](EXPLORATION.md) | strong | depth charts, `cleaning-port` |
| F4 | Duplicate rows to handle at ingest (expected fantasy points, weekly rosters, injuries). | [EXPLORATION.md](EXPLORATION.md) | strong | `data-layer` |
| F5 | Injuries have no `date_modified` from 2025. The known-at rule doesn't need it. | [EXPLORATION.md](EXPLORATION.md) | strong | injuries |
| F6 | All play-by-play at once is about 2.7 GB in memory. Work a season at a time. | [EXPLORATION.md](EXPLORATION.md) | strong | play-by-play |
| F7 | ruff 0.17+ also formats Python code blocks inside Markdown. Left unscoped, it rewrote `docs/ARCHITECTURE.md`. Ruff is limited to `src/` and `tests/` in `pyproject.toml`. | the build (the diff was reverted) | strong | any new tool config |
| F8 | `nbstripout --install` writes a repo-wide `*.ipynb` pattern into `.git/info/attributes` by default. That file overrides `.gitattributes`, so the pattern would reach `old/` notebooks. Install with `--attributes pcf/.venv/nbstripout-attributes` (README). | `git check-attr` before and after | strong | anyone setting up the repo |
| F9 | Claude's path rules use `Edit(<path>)` for Edit, Write and NotebookEdit. A leading `/` means the repo root. A `.claude/settings.json` created mid-session applied straight away. **Deny rules don't cover shell commands**, so for Bash and PowerShell, `old/` is still protected by rule a and `git status`. | the scratch-folder test | strong | `.claude/settings.json` |

## Pitfalls
- Tool defaults reach further than you'd expect (F7, F8). After adding any tool, check `git status -- old` (it should be empty) and `git diff -- docs`.
- The nbstripout filter in `.git/config` points to this machine's `.venv`. On a new machine, rerun the README command.

## Not looked at
- A truly fresh `git clone` on another machine. This was simulated by copying exactly the files git would commit.
- Running the tests in GitHub Actions (that comes with `weekly-run`).
- pandera schemas (planned for `data-layer`).

## Could be improved
1. A pre-commit check that fails if anything under `old/` is staged. It would cover shell edits, which the deny rule misses (F9).
2. Run pytest and ruff in GitHub Actions on every push.

## Don't redo
- Don't let a tool's `--install` write its own attributes or config without reading what it wrote (F8).
- Don't widen ruff's `include` to the whole repo (F7).

## Interface card
Also in `registry.yaml` under `interface`.

| | |
|---|---|
| **Inputs** | none |
| **Outputs** | `pcf.config.get_config()`: paths (`data_dir`, `zone(name)` for the 8 data zones), seasons (2006 / 2016 / vault 2025 / live 2026) and seed. `get_secret(name)` reads keys. `pcf.core.log.get_logger(name)` gives a logger that masks keys. The `pcf` command (`pcf info`). |
| **Level of detail** | not applicable |
| **Interval** | not applicable |
| **Cadence** | not applicable |
| **Known at** | not applicable |
| **How to use it** | Import paths and settings from `pcf.config`, never hardcode them. Log through `get_logger` after `setup_logging()`. Put code in the matching layer folder and read its `CLAUDE.md`. |
| **Feeds** | every project (all depend on it directly or indirectly) |

## Open questions for the CEO
- None blocking. When you first run `uv run jupyter lab`, confirm it opens. That's the one test not checked by hand.
