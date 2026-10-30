# experts/ (layer 1)

One subpackage per expert, named for its registry id with underscores (`voe-live` → `voe_live/`).

- Every expert implements the contract in `docs/ARCHITECTURE.md` ("The expert contract"): `id`, `cadence`, `grain`, `inputs`, `features`, `fit`, `predict`, `explain`.
- Read data only through the `as_of` gateway. Never import loaders or open files.
- Outputs use the standard schema, with uncertainty (`q10`, `q50`, `q90`) and `train_end`.
- Before building: the project's `BRIEF.md` is agreed, and `projects/KNOWLEDGE.md` has been read.
- Validation bar: `docs/VALIDATION.md` (signal test, no-noise test, calibration, the vault).
