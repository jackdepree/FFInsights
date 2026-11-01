# core/

Shared machinery every layer uses. Nothing football-specific lives here.

- `log.py`: `get_logger(__name__)`. Masks key values in every message. Use it instead of `print`.
- `tracking.py`: the only way to use MLflow. `attempt` and `rung` for training runs, `log_model`, `log_checks` and `register` (checked runs only), `sync_champions` (the champion comes from `registry.yaml`, decision 0009), `load_model`. Importing it loads MLflow (about 5 seconds), so only modelling code imports it.
- `registry.py`: reads `projects/registry.yaml`.
- Planned: `contract.py` (the Expert interface and output schema), `ledger.py`. See `docs/ARCHITECTURE.md`.

Paths and settings come from `pcf.config` (rule f), never from here.
