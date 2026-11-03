# validation/

The validation harness (`validation-harness` project): everything that decides whether a model is honest and good. The bars come from `docs/VALIDATION.md`; the checks from `docs/ARCHITECTURE.md`.

| Module | What |
|---|---|
| `splits.py` | Walk-forward steps (week, season or event). **The only splitters in PCF.** |
| `backtest.py` | `run(expert)`: per-moment features, outcomes, then the walk. `walk` refits on rows known before each step. Vault and live seasons are refused unless opened. `write_history` |
| `scores.py` | Pinball, log loss, Brier, MAE, points gained, rank correlation |
| `compare.py` | "Beats": paired, resampled by whole weeks, 90% interval |
| `nulls.py` | Signal test (shuffled outcomes, 95 of 100 or 20 of 20) and the no-noise verdict |
| `calibration.py` | Calibration error and slope; range coverage by group; sharpness |
| `leakage.py` | Checks 1-8 and 10, each with a planted leak in `tests/validation/planted.py` |
| `sanity.py` | Shared football-sanity rules and the CEO's review lists |
| `misses.py` | Where a model misses: the dated lens list (`LENS_LIST`), the tags that stand out, `misses.parquet`. On every player-game scorecard; `pcf misses <id>` for a saved run. A new list is a new date, never an edit |
| `scorecard.py`, `validate.py` | One validation run and its HTML scorecard, recorded in MLflow (`pcf backtest <id> [--variant v]`). Baselines rerun at the model's run (`at_run`), benchmarks at their own |
| `toy.py` | The harness's own toy expert (`validation-harness`): recent PPR points |

- **Random splitters (`KFold`, `train_test_split`) are banned everywhere else**, and a test scans the package for them.
- Every threshold comes from `docs/VALIDATION.md`. A change to one needs a reason and the CEO's agreement.
- A new check gets a planted leak and an honest twin in the tests, or it can silently stop working.
