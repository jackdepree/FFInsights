# core/

Shared machinery every layer uses. Nothing football-specific lives here.

- `log.py`: `get_logger(__name__)`. Masks key values in every message. Use it instead of `print`.
- `tracking.py`: the only way to use MLflow. `attempt` and `rung` for training runs, `log_model`, `log_checks` and `register` (checked runs only), `log_metrics`, `log_text`, `version_run`, `sync_champions` (the champion comes from `registry.yaml`, decision 0009), `load_model`. Importing it loads MLflow (about 5 seconds), so only modelling code imports it.
- `registry.py`: reads `projects/registry.yaml`.
- `contract.py`: the `Expert` interface every model implements (with `benchmark`, `variant` and `first_train` where needed), `check_expert` (against the registry), the standard output schema and `check_output`, and `find(id, variant)` / `find_all(id)`.
- `ledger.py`: the prediction ledger's files (decision 0017). `open_run`, then `Run.write` per model and `Run.close`; write once, no rows after kickoff, nothing from the future. `read` gives the counted rows (each model's first finished forecast). `ensure_clone` and `push` keep the sparse `pcf-data` clone. The live run itself is `pcf.validation.live`.

Paths and settings come from `pcf.config` (rule f), never from here.
