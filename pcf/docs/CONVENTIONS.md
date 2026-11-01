# Conventions

> How all PCF code looks and behaves, so every project and every Claude subagent writes it the same way.
> Decided **2026-10-30**. Tooling is set up by `package-scaffold`. Terms are defined in [`GLOSSARY.md`](GLOSSARY.md).

## Style

- **Python 3.12.** `ruff format` formats everything, and `ruff check` lints it. Line length is 100.
- **Type hints** on every function in the package.
- **Docstrings** are short: what goes in, what comes out, and any assumption. One line is often enough.
- **Comments say why**, not what. A football assumption gets a comment with its reason (e.g. `# 4 rushers when missing: the league-wide mode`).
- Plain names over clever ones. No abbreviations a football reader wouldn't know.

## Naming

| Thing | Convention | Example |
|---|---|---|
| Python names | snake_case (classes in PascalCase) | `clean_depth_charts`, `VoeLive` |
| Project ids | kebab-case, also the folder in `projects/` | `voe-live` |
| Package folders for a project | the id with underscores | `experts/voe_live/` |
| Branches | `pcf/<id>` or `pcf/<topic>` | `pcf/voe-live` |
| Notebooks | numbered, in `projects/<id>/explore/` | `01_first_look.ipynb` |
| Tables (files) | snake_case, named for their level of detail | `player_game`, `team_week` |
| MLflow | experiment = project id. Registered model = `pcf.<id>`. Rungs are named `<n>-<method>`. PCF's own tags start with `pcf.`. Always through `pcf.core.tracking`. | `pcf.voe-live`, `1-lasso`, `pcf.train_end` |

### Columns

**Fixed names everywhere.** Every table uses these exact names, and sources are renamed to match at ingest:

| Column | Meaning |
|---|---|
| `gsis_id` | Player id (nflverse calls it `player_id` in some tables; rename it). **Snap counts and PFR use `pfr_player_id`**, mapped through nflverse's `players` file (`cleaning-port#F17`). |
| `game_id` | nflverse game id, e.g. `2026_08_CAR_GB` (participation calls it `nflverse_game_id`) |
| `play_id` | nflverse play id, unique within a game |
| `season` | The year the season started (the 2026 season's Super Bowl is in 2027) |
| `week` | nflverse numbering: regular season 1–18, playoffs 19–22 (since 2021). Use `season_type` to separate them. |
| `team`, `opponent` | Play-by-play's 32 codes, each franchise's **current** code for every season: `LA` (Rams), `LAC`, `LV`, `WAS`, … Older and other codes (OAK, SD, STL, ESPN's `LAR`, `WSH`, …) are mapped at ingest (`pcf.data.clean.standard`, cleaning-port#F11). |
| `known_at`, `as_of`, `train_end` | Timestamps, always **UTC and timezone-aware** |

**Derived columns end in their kind or unit:**

| Ending | Means | Example |
|---|---|---|
| `_prob` | a probability, 0–1 | `td_prob` |
| `_pct`, `_share`, `_rate` | a fraction, **0–1, never 0–100** | `snap_pct`, `target_share`, `success_rate` |
| `_per_game`, `_per_play`, `_per_route` | a rate per unit | `targets_per_route` |
| `_epa` | expected points | `rec_epa` |
| `_oe` | over expected (actual minus expected) | `rec_yards_oe` |
| `_exp` | expected value (matches nflverse) | `receptions_exp` |
| `_q10`, `_q50`, `_q90` | quantiles of a prediction | `rec_yards_q90` |

**nflverse columns keep their names and scales** in `raw/` and `interim/`, because nflverse is the Bible. In `tables/` too, except that NGS, PFR and ff_opportunity columns get their source as a prefix (`ngs_rec_`, `pfr_rush_`, `ffo_`), since their names would clash with player stats. Two of them are on a 0–100 scale: `cpoe` and `pass_oe`. They're converted to 0–1 only in columns we derive from them.

## Functions and modules

- **Shared functions are pure:** a dataframe in, a dataframe out. No hidden file reads, downloads or writes.
- **Reading and writing data happens in two places only:** `data/sources/` (fetching and saving) and the gateway (reading for models). This is what lets the leakage checks see everything.
- **Everything configurable comes from config** (`pcf/config.toml`): paths, seasons, thresholds, scoring formats and random seeds. No hardcoded paths (rule f).
- **Logging, not printing.** Use Python's `logging`. **Never log keys, tokens or anything from `.env`**, since Actions logs on this repo are public.
- **Fail loudly.** A missing column, an unexpected duplicate or an unmatched id raises an error. Never silently fill or drop rows. If a fill is a deliberate assumption, it's a named constant with a comment.
- **Polars by default.** Ported functions may stay in pandas until their "improve" step (OLD_INVENTORY.md). Convert to pandas or NumPy only at the edge of a library that needs it.
- **Check before writing** (rule j): search the package for an existing function first. Shared helpers live in the package, never inside an expert.

## Football and betting units

- **Probabilities are 0–1.** Percentages appear only in reports.
- **Odds are stored twice:** as American odds (`-110`, `+250`) *and* as the implied probability. Prices from the source are never overwritten.
- **Yards, seconds and EPA are per play** unless the column name says otherwise.
- **Fantasy scoring is defined in config**, never in code: standard, half-PPR, PPR, superflex, TE premium, and custom league settings. A function takes a scoring format as an argument. It never contains `0.5 * receptions`.
- **Spreads are from the home team's point of view, betting-style:** `home_spread = -3.5` means the home team is favored by 3.5. **nflverse's `spread_line` has the opposite sign** (positive means the home team is favored), so it's flipped at ingest. Every odds table says which side its prices are for.

## Tests

- `tests/` mirrors `src/pcf/` (`tests/data/clean/test_depth_charts.py`). Run with `uv run pytest`.
- **Kinds of test:**
  - **unit:** one function, small inputs;
  - **golden:** a ported function gives the same output as the old one (OLD_INVENTORY.md);
  - **expectation:** what football says must be true (11 players per side, shares add up to at most 1);
  - **contract and leakage:** run on every expert by the validation harness (ARCHITECTURE.md).
- **Test fixtures may live in git** (an exception to rule g): `tests/fixtures/`, **under 1 MB in total**. They hold a few rows of public nflverse data, or synthetic rows. **Never collected odds or anything from `pcf-data`** (it's private, and this repo is public), and never keys.
- Tests don't touch the internet. Anything that needs a download is marked `@pytest.mark.network` and skipped by default.
- Tests that read full seasons from the local raw copy are marked `@pytest.mark.local_data` and skipped by default. Run them with `uv run pytest -m local_data` after `pcf refresh`.

## Notebooks

- **For exploring only** (rule i), in `projects/<id>/explore/`.
- **Outputs are stripped automatically before every commit** (nbstripout). The old notebooks were 1–4 MB because of their outputs, and outputs can carry data into this public repo.
- A chart worth keeping is saved as an image into the project's notes.
- When a notebook's code becomes reusable, it moves into the package with tests. The notebook then imports it.

## Git

- One branch per project or doc: `pcf/<id>`. Claude commits freely on branches. Merging to `main` needs the CEO's approval, and `main` always works.
- **Commit subjects** are short and in the imperative ("Add the depth-chart cleaner"). The body says why when it isn't obvious.
- Never commit data, keys, notebook outputs or anything from `pcf/data/`. Tiny test fixtures are the one exception (above).

## Dependencies

- Added only with `uv add`, so `pyproject.toml` and `uv.lock` always match.
- **A major new library** (a new modeling framework, a database, an orchestration tool) gets a note in `docs/decisions/`. Large changes need CEO sign-off (charter).

## Writing docs and notes

- Plain language first, technical detail after (rule l).
- **Every brief and results page has a Terms section** (see the templates). Standard football, fantasy and betting terms link to [`GLOSSARY.md`](GLOSSARY.md). Terms a project invents are defined in its brief, and move into the glossary when the project is done.
- Dates are written `YYYY-MM-DD`.
