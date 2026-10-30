# core/

Shared machinery every layer uses. Nothing football-specific lives here.

- `log.py`: `get_logger(__name__)`. Masks key values in every message. Use it instead of `print`.
- Planned: `contract.py` (the Expert interface and output schema), `registry.py`, `tracking.py` (MLflow), `ledger.py`. See `docs/ARCHITECTURE.md`.

Paths and settings come from `pcf.config` (rule f), never from here.
