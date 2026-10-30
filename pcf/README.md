# PCF: Principal Component Football

An in-house NFL analytics and forecasting system for fantasy and betting. The charter is [`CLAUDE.md`](CLAUDE.md), and the docs are in [`docs/`](docs/).

## Set up (once)

You need [uv](https://docs.astral.sh/uv/). It installs Python 3.12 itself if you don't have it. From the `pcf/` folder:

```bash
uv sync
```

That creates `pcf/.venv/` with every dependency, pinned by `uv.lock`.

Then turn on notebook stripping, so notebooks are committed without their outputs (run this from the repo root):

```bash
pcf/.venv/Scripts/python.exe -m nbstripout --install --attributes pcf/.venv/nbstripout-attributes
```

This sets up the filter in your local git config. The repo's `.gitattributes` already limits stripping to notebooks inside `pcf/`. Without the `--attributes` flag, nbstripout would write a repo-wide `*.ipynb` pattern into `.git/info/attributes`. That file overrides `.gitattributes`, so the pattern would also catch the read-only notebooks in `old/`. The flag sends that pattern to a file inside the venv, which git never reads. Check it with `git check-attr filter -- old/x.ipynb`: it should say `unspecified`.

API keys go in `pcf/.env` (gitignored), one `NAME=value` per line. Never commit them, and never paste them into code.

## Everyday commands

Run these from `pcf/`:

| What | Command |
|---|---|
| Run the tests (offline, network tests skipped) | `uv run pytest` |
| Also run the tests that need the internet | `uv run pytest -m network` |
| Lint | `uv run ruff check` |
| Format | `uv run ruff format` |
| Show paths, seasons and which keys are set | `uv run pcf info` |
| Open JupyterLab | `uv run jupyter lab` |

## Where data lives

Local data goes in `pcf/data/` (gitignored), split into zones: raw, interim, tables, features, outputs, mlflow, ledger, logs. To put it somewhere else, set `PCF_DATA_DIR`. Every path comes from `config.toml` through `src/pcf/config.py`, never from hardcoded strings.

## VS Code

Open the repo root. VS Code offers the recommended extensions (Python, Jupyter, Ruff). The workspace settings already point at `pcf/.venv`, run pytest from `pcf/`, and format with ruff on save.

## Notebooks

Notebooks are for exploring only (charter rule i). Put them in `projects/<id>/explore/`. Anything reusable moves into `src/pcf/` with tests.
