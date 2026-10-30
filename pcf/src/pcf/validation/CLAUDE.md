# validation/

The validation harness (`validation-harness` project): walk-forward splitters, scores, calibration, the shuffled-null and no-noise tests, the leakage suite, sanity rules and the scorecard.

- **The only place splitters live.** Random splitters (`KFold`, `train_test_split`) are banned everywhere else.
- Every threshold comes from `docs/VALIDATION.md`. A change to one needs a reason and the CEO's agreement.
