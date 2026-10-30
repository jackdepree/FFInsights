# 0004: MLflow for tracking and model reuse

**Date:** 2026-10-30 · **Decided by:** CEO

**Decision:** MLflow, run locally (SQLite plus files in `pcf/data/mlflow/`, no server), tracks every run and stores every model. Each expert is a registered model `pcf.<id>`, with a `champion` alias for the current best. Training pins exact versions. Only runs that pass the blocking leakage checks can be registered.

**Why:** the CEO wants to say which model was best, and to reuse a finished project's model, parameters and features without retraining it. MLflow's model registry, versions, aliases and nested runs (for the ladder) do this out of the box.

**Alternatives:** Claude had recommended a lighter manifest file per run. It's simpler, but it would mean building a model registry ourselves.

**Revisit if:** the local database gets slow or needs sharing across machines. Then move to a hosted tracking server.
